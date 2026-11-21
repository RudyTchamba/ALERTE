"""Opérations de la base de connaissances : documents, versions, publication, embeddings (reprenables), reindex, qualité."""
from __future__ import annotations

import dataclasses
import hashlib
import logging
import re
import unicodedata
from typing import Any, BinaryIO

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from ..contracts import VectorRecord
from ..core.canonical_json import canonical_sha256
from ..core.errors import AppError, Conflict, NotFound, Unprocessable
from ..core.jobs import JobContext
from .embedders import EmbedderError, blob_to_vec, vec_to_blob
from .extract import ALLOWED_EXTENSIONS, ExtractionError, sniff_kind
from .indexes import chunk_fts_row, fts_delete_kb, fts_insert
from .models import Chunk, ChunkEmbedding, Document, DocumentVersion, KBVersion, KBVersionItem, KnowledgeBase
from .runtime import KnowledgeRuntime
from .textproc import analyze

log = logging.getLogger("alerte.knowledge.ops")


# --------------------------------------------------------------------------- accès avec isolation d'espace
def get_kb(session: Session, ws: str, kb_id: str, *, allow_archived: bool = True) -> KnowledgeBase:
    kb = session.scalar(select(KnowledgeBase).where(KnowledgeBase.id == kb_id, KnowledgeBase.workspace_id == ws))
    if kb is None or (not allow_archived and kb.archived_at):
        raise NotFound("base de connaissances introuvable", code="kb.not_found")
    return kb


def get_document(session: Session, ws: str, doc_id: str) -> Document:
    d = session.scalar(select(Document).where(Document.id == doc_id, Document.workspace_id == ws))
    if d is None:
        raise NotFound("document introuvable", code="kb.document.not_found")
    return d


def slugify_code(s: str, fallback: str = "KB") -> str:
    n = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]+", "-", n).strip("-")[:40] or fallback


# --------------------------------------------------------------------------- téléversement
def store_upload(rt: KnowledgeRuntime, session: Session, stream: BinaryIO, filename: str) -> tuple[str, int, str]:
    """Contrôles d'entrée : extension blanche, taille max, signature réelle ; stockage par hash. Renvoie (sha, taille, ext)."""
    name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    ext = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise AppError(f"extension non autorisée : {ext or '(aucune)'}", code="kb.document.bad_type", status_code=415,
                       details={"allowed": sorted(ALLOWED_EXTENSIONS)})
    limit = rt.settings.upload_max_mb * 1024 * 1024
    try:
        sha, size = rt.blobs.put_stream(stream, max_bytes=limit)
    except ValueError as exc:
        raise AppError(f"fichier trop volumineux (maximum {rt.settings.upload_max_mb} Mo)",
                       code="kb.document.too_large", status_code=413) from exc
    if size == 0:
        raise Unprocessable("fichier vide", code="kb.document.empty")
    path = rt.blobs.path_for(sha)
    try:
        with path.open("rb") as fh:
            sniff_kind(ext, fh.read(4096), path)
    except ExtractionError as exc:
        if not session.scalar(select(DocumentVersion.id).where(DocumentVersion.blob_sha256 == sha).limit(1)):
            path.unlink(missing_ok=True)
        raise AppError(str(exc), code=exc.code, status_code=415) from exc
    return sha, size, ext


def _check_duplicate(session: Session, kb_id: str, sha: str) -> None:
    dup = session.execute(select(Document.id, Document.code).join(DocumentVersion, DocumentVersion.document_id == Document.id)
                          .where(DocumentVersion.kb_id == kb_id, DocumentVersion.blob_sha256 == sha,
                                 DocumentVersion.status != "retired").limit(1)).first()
    if dup:
        raise Conflict("ce fichier (même SHA-256) est déjà dans la base", code="kb.document.duplicate",
                       details={"document_id": dup[0], "document_code": dup[1], "sha256": sha})


def create_document(session: Session, ws: str, kb: KnowledgeBase, sha: str, size: int, filename: str,
                    meta: dict[str, Any]) -> tuple[Document, DocumentVersion]:
    _check_duplicate(session, kb.id, sha)
    name = (filename or "document").replace("\\", "/").rsplit("/", 1)[-1][:300]
    stem = name.rsplit(".", 1)[0]
    code = meta.get("code") or None
    if not code:
        n = (session.scalar(select(func.count()).select_from(Document).where(Document.kb_id == kb.id)) or 0) + 1
        code = f"DOC-{n:04d}"
        while session.scalar(select(Document.id).where(Document.kb_id == kb.id, Document.code == code)):
            n += 1
            code = f"DOC-{n:04d}"
    elif session.scalar(select(Document.id).where(Document.kb_id == kb.id, Document.code == code)):
        raise Conflict("code de document déjà utilisé dans cette base", code="kb.document.code_taken")
    fields = {k: v for k, v in meta.items() if k in {"doc_type", "doc_number", "doc_date", "jurisdiction", "language",
                                                     "source_url", "reliability", "validity", "license_spdx",
                                                     "redistribution", "evidence_default", "accessed_at"} and v is not None}
    doc = Document(workspace_id=ws, kb_id=kb.id, code=code, title=(meta.get("title") or stem)[:500], **fields)
    session.add(doc)
    session.flush()
    ver = DocumentVersion(workspace_id=ws, kb_id=kb.id, document_id=doc.id, version_no=1, blob_sha256=sha, bytes=size,
                          original_name=name, status="processing", mime=None)
    session.add(ver)
    session.flush()
    return doc, ver


def add_version(session: Session, ws: str, doc: Document, sha: str, size: int, filename: str,
                note: str | None) -> DocumentVersion:
    _check_duplicate(session, doc.kb_id, sha)
    last = session.scalar(select(DocumentVersion).where(DocumentVersion.document_id == doc.id)
                          .order_by(DocumentVersion.version_no.desc()).limit(1))
    ver = DocumentVersion(workspace_id=ws, kb_id=doc.kb_id, document_id=doc.id, version_no=(last.version_no + 1) if last else 1,
                          blob_sha256=sha, bytes=size, original_name=(filename or "document")[:300], status="processing",
                          supersedes_id=last.id if last else None, note=note)
    session.add(ver)
    session.flush()
    return ver


def retire_document(session: Session, ws: str, doc_id: str) -> Document:
    doc = get_document(session, ws, doc_id)
    session.execute(update(DocumentVersion).where(DocumentVersion.document_id == doc.id).values(status="retired"))
    return doc


# --------------------------------------------------------------------------- embeddings (job reprenable par chunk)
def _check_fingerprint(kb: KnowledgeBase, key: str, reembed: bool) -> None:
    if kb.embedder_key and kb.embedder_key != key and not reembed:
        raise Conflict("la base contient des vecteurs d'une autre empreinte d'embedder : refus de mélanger "
                       "(utiliser reembed=true pour tout recalculer)", code="kb.embedder_mismatch",
                       details={"kb_embedder_key": kb.embedder_key, "current_embedder_key": key,
                                "kb_fingerprint": kb.embedder_fingerprint})


def precheck_embed(rt: KnowledgeRuntime, session: Session, kb: KnowledgeBase, reembed: bool) -> str:
    fp = rt.embedder.ensure_fingerprint() if hasattr(rt.embedder, "ensure_fingerprint") else rt.embedder.fingerprint
    _check_fingerprint(kb, fp.key(), reembed)
    return fp.key()


def embed_kb(rt: KnowledgeRuntime, job: JobContext | None, kb_id: str, *, version_ids: list[str] | None = None,
             reembed: bool = False, _span: tuple[float, float] = (0.0, 1.0)) -> dict:
    fp = rt.embedder.ensure_fingerprint() if hasattr(rt.embedder, "ensure_fingerprint") else rt.embedder.fingerprint
    key = fp.key()
    with rt.factory() as s:
        kb = s.get(KnowledgeBase, kb_id)
        _check_fingerprint(kb, key, reembed)
        if kb.embedder_key and kb.embedder_key != key:  # reembed explicite : on repart de zéro
            old = kb.embedder_key
            ids = s.scalars(select(Chunk.id).where(Chunk.kb_id == kb_id)).all()
            for i in range(0, len(ids), 500):
                s.execute(delete(ChunkEmbedding).where(ChunkEmbedding.chunk_id.in_(ids[i:i + 500])))
            kb.embedder_key = None
            s.commit()
            try:
                rt.vector_for(old).delete(ids)
            except Exception as exc:  # noqa: BLE001
                log.warning("nettoyage de l'ancien index vectoriel impossible : %s", exc)
        if kb.embedder_key is None:
            kb.embedder_key, kb.embedder_fingerprint = key, dataclasses.asdict(fp)
            s.commit()
        q = select(Chunk.id, Chunk.text, Chunk.kb_id, Chunk.document_version_id).where(
            Chunk.kb_id == kb_id,
            ~select(ChunkEmbedding.chunk_id).where(ChunkEmbedding.chunk_id == Chunk.id,
                                                   ChunkEmbedding.embedder_key == key).exists())
        if version_ids:
            q = q.where(Chunk.document_version_id.in_(version_ids))
        pending = s.execute(q.order_by(Chunk.document_version_id, Chunk.ordinal)).all()
        total_in_kb = s.scalar(select(func.count()).select_from(Chunk).where(Chunk.kb_id == kb_id)) or 0
    bs = max(1, rt.settings.embed_batch_size)
    done, index_pending = 0, False
    lo, hi = _span
    for i in range(0, len(pending), bs):
        batch = pending[i:i + bs]
        vecs = rt.embedder.embed([b[1] for b in batch])
        if len(vecs) != len(batch) or any(len(v) != fp.dimension for v in vecs):
            raise EmbedderError("dimension/nombre de vecteurs incohérent avec l'empreinte : refus de mélanger")
        with rt.factory() as s:  # un commit par lot : une interruption ne perd que le lot en cours
            s.add_all([ChunkEmbedding(chunk_id=b[0], embedder_key=key, dim=fp.dimension, vector=vec_to_blob(v))
                       for b, v in zip(batch, vecs, strict=True)])
            s.commit()
        try:
            rt.vector_for(key).upsert([VectorRecord(b[0], b[2], b[3], list(v)) for b, v in zip(batch, vecs, strict=True)])
        except Exception as exc:  # noqa: BLE001 - SQLite fait foi ; `reindex` reconstruira l'index
            index_pending = True
            log.warning("index vectoriel non mis à jour (%s) : reindex nécessaire", type(exc).__name__)
        done += len(batch)
        if job:
            job.update(lo + (hi - lo) * (i + len(batch)) / max(1, len(pending)), f"embeddings {done}/{len(pending)}")
    return {"embedded": done, "already_embedded": total_in_kb - len(pending) if not version_ids else None,
            "embedder_key": key, "index_pending": index_pending}


# --------------------------------------------------------------------------- reindex
def reindex_kb(rt: KnowledgeRuntime, job: JobContext | None, kb_id: str) -> dict:
    """Régénère FTS5 (et `search_text`) puis l'index vectoriel depuis SQLite, sans toucher aux chunks."""
    n = 0
    with rt.factory() as s:
        fts_delete_kb(s, kb_id)
        ids = s.scalars(select(Chunk.id).where(Chunk.kb_id == kb_id).order_by(Chunk.document_version_id, Chunk.ordinal)).all()
        key = s.get(KnowledgeBase, kb_id).embedder_key
        s.commit()
    for i in range(0, len(ids), 500):  # un commit par lot (jamais de mise à jour de job dans une transaction ouverte)
        with rt.factory() as s:
            for c in s.scalars(select(Chunk).where(Chunk.id.in_(ids[i:i + 500]))):
                st = analyze(c.text)
                if st != c.search_text:
                    s.execute(update(Chunk).where(Chunk.id == c.id).values(search_text=st))
                    c.search_text = st
                fts_insert(s, [chunk_fts_row(c)])
                n += 1
            s.commit()
        if job:
            job.update(0.5 * min(1, (i + 500) / max(1, len(ids))), f"index lexical {min(i + 500, len(ids))}/{len(ids)}")
    vectors = 0
    if key:
        vec = rt.vector_for(key)
        for i in range(0, len(ids), 500):
            part = ids[i:i + 500]
            vec.delete(part)
            with rt.factory() as s:
                rows = s.execute(select(ChunkEmbedding.chunk_id, ChunkEmbedding.vector, Chunk.kb_id, Chunk.document_version_id)
                                 .join(Chunk, Chunk.id == ChunkEmbedding.chunk_id)
                                 .where(ChunkEmbedding.embedder_key == key, Chunk.id.in_(part))).all()
            vec.upsert([VectorRecord(r[0], r[2], r[3], blob_to_vec(r[1]).tolist()) for r in rows])
            vectors += len(rows)
            if job:
                job.update(0.5 + 0.5 * min(1, (i + 500) / max(1, len(ids))), f"index vectoriel {vectors}")
    return {"chunks_indexed": n, "vectors_indexed": vectors, "embedder_key": key}


# --------------------------------------------------------------------------- publication (kb_version)
def publish_kb(session: Session, ws: str, kb_id: str, note: str | None) -> KBVersion:
    kb = get_kb(session, ws, kb_id, allow_archived=False)
    vers = session.scalars(select(DocumentVersion).join(Document, Document.current_version_id == DocumentVersion.id)
                           .where(Document.kb_id == kb_id, Document.workspace_id == ws)).all()
    if any(v.status == "processing" for v in vers):
        raise Conflict("des documents sont encore en cours de traitement", code="kb.publish.processing")
    items = sorted((v for v in vers if v.status in ("ready", "needs_review")), key=lambda v: v.id)
    if not items:
        raise Unprocessable("aucune version de document prête à publier", code="kb.publish.empty")
    entries = []
    for v in items:
        hashes = session.scalars(select(Chunk.text_sha256).where(Chunk.document_version_id == v.id)
                                 .order_by(Chunk.ordinal)).all()
        entries.append({"document_version_id": v.id, "blob_sha256": v.blob_sha256,
                        "chunks_sha256": hashlib.sha256("".join(hashes).encode()).hexdigest()})
    manifest = canonical_sha256({"kb_id": kb.id, "items": entries})
    last = session.scalar(select(KBVersion).where(KBVersion.kb_id == kb_id).order_by(KBVersion.version_no.desc()).limit(1))
    if last and last.manifest_sha256 == manifest:
        raise Conflict("aucun changement depuis la dernière version publiée", code="kb.publish.unchanged",
                       details={"kb_version_id": last.id, "version_no": last.version_no})
    kv = KBVersion(workspace_id=ws, kb_id=kb_id, version_no=(last.version_no + 1) if last else 1, note=note,
                   manifest_sha256=manifest)
    session.add(kv)
    session.flush()
    session.add_all([KBVersionItem(kb_version_id=kv.id, document_version_id=v.id) for v in items])
    session.flush()
    return kv


# --------------------------------------------------------------------------- rapport de qualité de la KB (critère C1)
def quality_report(rt: KnowledgeRuntime, session: Session, ws: str, kb_id: str) -> dict:
    get_kb(session, ws, kb_id)
    rows = session.execute(select(Document, DocumentVersion).join(DocumentVersion, DocumentVersion.id == Document.current_version_id)
                           .where(Document.kb_id == kb_id, Document.workspace_id == ws)).all()
    docs = []
    totals = {"pages": 0, "ocr_pages": 0, "pages_to_review": 0, "with_articles": 0, "injection_flags": 0}
    langs: dict[str, int] = {}
    redistribution: dict[str, int] = {}
    alerts: list[str] = []
    seen: dict[str, list[str]] = {}
    for d, v in rows:
        rep = v.quality_report or {}
        totals["pages"] += rep.get("pages", 0)
        totals["ocr_pages"] += rep.get("ocr_pages", 0)
        totals["pages_to_review"] += len(v.pages_to_review or [])
        totals["with_articles"] += 1 if rep.get("articles_detected", 0) > 0 else 0
        totals["injection_flags"] += len(rep.get("injection_flags", []))
        langs[d.language or "und"] = langs.get(d.language or "und", 0) + 1
        redistribution[d.redistribution] = redistribution.get(d.redistribution, 0) + 1
        seen.setdefault(v.blob_sha256, []).append(d.code)
        if v.status != "retired" and rep.get("chars_total", 1 << 30) < 500:
            alerts.append(f"{d.code} : moins de 500 caractères utiles")
        docs.append({"document_id": d.id, "code": d.code, "title": d.title, "status": v.status,
                     "extraction_quality": v.extraction_quality, "pages": rep.get("pages"),
                     "ocr_pct": rep.get("ocr_pct"), "articles_detected": rep.get("articles_detected"),
                     "pages_to_review": v.pages_to_review or [], "injection_flags": rep.get("injection_flags", []),
                     "warnings": rep.get("warnings", []), "missing_metadata": [
                         f for f in ("jurisdiction", "doc_type", "doc_date") if not getattr(d, f)]})
    n = len(rows)
    qs = [v.extraction_quality for _, v in rows if v.extraction_quality is not None]
    return {"kb_id": kb_id, "documents": n, "avg_extraction_quality": round(sum(qs) / len(qs), 3) if qs else None,
            "totals": totals, "pct_documents_with_articles": round(100 * totals["with_articles"] / n, 1) if n else None,
            "languages": langs, "redistribution": redistribution, "duplicates": [c for c in seen.values() if len(c) > 1],
            "alerts": alerts, "coverage": rt.coverage(session, ws, [kb_id]), "items": docs}
