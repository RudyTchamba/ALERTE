"""Export / import d'archives (doc 07 §7.6) adossés à la base. Le format et la validation durcie sont dans `archive_format`."""
from __future__ import annotations

import datetime as dt
import importlib.metadata as md
import re
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..contracts import VectorRecord
from ..core.canonical_json import canonical_bytes
from ..core.db import utcnow
from ..core.errors import Conflict, NotFound, Unprocessable
from ..core.jobs import JobContext
from . import archive_format as af
from .embedders import blob_to_vec
from .indexes import chunk_fts_row, fts_insert
from .kbops import get_kb
from .models import (
    Chunk,
    ChunkEmbedding,
    Document,
    DocumentVersion,
    KBExport,
    KBImport,
    KBVersion,
    KBVersionItem,
    KnowledgeBase,
)
from .runtime import KnowledgeRuntime
from .textproc import ANALYZER_VERSION, analyze

EXPORTER = {"name": "alerte-platform/knowledge", "version": "0.1.0"}
_DOC_FIELDS = ("code", "title", "doc_type", "doc_number", "jurisdiction", "language", "source_url", "reliability",
               "validity", "license_spdx", "redistribution", "evidence_default")


def _pkg(name: str) -> str:
    try:
        return md.version(name)
    except md.PackageNotFoundError:
        return "?"


# =========================================================================== export
def plan_export(session: Session, ws: str, kb_id: str, req: dict) -> dict:
    """Sélection + règles de droits. Lève 422 `kb.export.restricted_documents` avec la liste le cas échéant."""
    kb = get_kb(session, ws, kb_id)
    mode = req.get("mode", "full_reimportable")
    explicit = req.get("document_ids")
    if mode == "selection" and not explicit:
        raise Unprocessable("le mode « sélection » exige document_ids", code="kb.export.selection_required")
    if req.get("kb_version_id"):
        kv = session.scalar(select(KBVersion).where(KBVersion.id == req["kb_version_id"], KBVersion.kb_id == kb.id,
                                                    KBVersion.workspace_id == ws))
        if kv is None:
            raise NotFound("version de base introuvable", code="kb.version.not_found")
        q = select(Document, DocumentVersion).join(DocumentVersion, DocumentVersion.document_id == Document.id) \
            .join(KBVersionItem, KBVersionItem.document_version_id == DocumentVersion.id) \
            .where(KBVersionItem.kb_version_id == kv.id)
    else:
        q = select(Document, DocumentVersion).join(DocumentVersion, DocumentVersion.id == Document.current_version_id) \
            .where(Document.kb_id == kb.id, DocumentVersion.status.in_(("ready", "needs_review")))
    rows = [(d, v) for d, v in session.execute(q.where(Document.workspace_id == ws).order_by(Document.code,
                                                                                            DocumentVersion.version_no)).all()]
    if explicit:
        known = {d.id for d, _ in rows}
        unknown = [i for i in explicit if i not in known]
        if unknown:
            raise Unprocessable("documents inconnus ou non exportables dans cette base", code="kb.export.unknown_documents",
                                details={"document_ids": unknown})
        rows = [(d, v) for d, v in rows if d.id in set(explicit)]
    warnings: list[str] = []
    open_pub = mode == "open_publication" or req.get("purpose") == "open_publication"
    if open_pub:
        bad = [d for d, _ in rows if d.redistribution != "allowed"]
        listing = [{"document_id": d.id, "code": d.code, "redistribution": d.redistribution} for d in bad]
        if bad and explicit:
            raise Unprocessable("publication ouverte refusée : documents restreints ou de droits inconnus",
                                code="kb.export.restricted_documents", details={"documents": listing})
        if bad:
            warnings.append("documents exclus (redistribution ≠ allowed) : " + ", ".join(d.code for d in bad))
            rows = [(d, v) for d, v in rows if d.redistribution == "allowed"]
        if not rows:
            raise Unprocessable("publication ouverte impossible : aucun document redistribuable",
                                code="kb.export.restricted_documents", details={"documents": listing})
    if not rows:
        raise Unprocessable("aucun document à exporter", code="kb.export.empty")
    inc = req.get("include") or {}
    originals = (mode != "processed_only") if inc.get("originals") is None else (bool(inc["originals"]) and mode != "processed_only")
    for key in ("mandates", "references"):
        if inc.get(key):
            warnings.append(f"{key} : non inclus (registre géré par un autre module)")
    return {"kb": kb, "rows": rows, "mode": mode, "originals": originals, "chunks": mode != "documents_only",
            "embeddings": bool(inc.get("embeddings")) and mode != "documents_only",
            "warnings": warnings}


def _doc_record(d: Document, v: DocumentVersion, source: str | None, is_current: bool, needs_review: bool) -> dict:
    rec: dict[str, Any] = {"document_id": d.id, "replaced_by_id": d.replaced_by_id,
                           "doc_date": d.doc_date.isoformat() if d.doc_date else None,
                           "accessed_at": d.accessed_at.isoformat() if d.accessed_at else None, "is_current": is_current}
    rec.update({f: getattr(d, f) for f in _DOC_FIELDS})
    rec["version"] = {"id": v.id, "version_no": v.version_no, "blob_sha256": v.blob_sha256, "mime": v.mime, "bytes": v.bytes,
                      "original_name": v.original_name, "extraction_method": v.extraction_method,
                      "extraction_quality": v.extraction_quality, "pages_to_review": v.pages_to_review or [],
                      "status": "needs_review" if needs_review else v.status, "note": v.note, "supersedes_id": v.supersedes_id,
                      "quality_report": v.quality_report, "source_file": source}
    return rec


def run_export(rt: KnowledgeRuntime, job: JobContext | None, export_id: str) -> dict:
    def prog(p: float, m: str) -> None:
        if job:
            job.update(p, m)

    with rt.factory() as s:
        ex = s.get(KBExport, export_id)
        ex.status = "running"
        s.commit()
        try:
            plan = plan_export(s, ex.workspace_id, ex.kb_id, {"mode": ex.mode, **(ex.options or {})})
            result = _build_export(rt, s, ex, plan, prog)
            ex.status, ex.blob_sha256, ex.bytes, ex.filename = "done", result["sha"], result["bytes"], result["filename"]
            s.commit()
            return {k: v for k, v in result.items() if k != "sha"} | {"export_id": ex.id, "blob_sha256": result["sha"]}
        except Exception as exc:
            s.rollback()
            ex = s.get(KBExport, export_id)
            ex.status, ex.error = "failed", str(getattr(exc, "message", exc))[:500]
            s.commit()
            raise


def _build_export(rt: KnowledgeRuntime, s: Session, ex: KBExport, plan: dict, prog) -> dict:  # noqa: ANN001
    kb: KnowledgeBase = plan["kb"]
    tmp = rt.settings.exports_dir / f".tmp-{ex.id}.zip"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    writer = af.ArchiveWriter(tmp)
    warnings = list(plan["warnings"])
    try:
        used: set[str] = set()
        docs, sources = [], {}
        for d, v in plan["rows"]:
            src = None
            if plan["originals"]:
                if rt.blobs.exists(v.blob_sha256):
                    ext = Path(v.original_name or "").suffix.lower() or ".bin"
                    src = "data/sources/" + af.safe_source_name(d.code, v.version_no, ext, used)
                    sources[src] = rt.blobs.path_for(v.blob_sha256)
                else:
                    warnings.append(f"original indisponible pour {d.code} v{v.version_no}")
            docs.append(_doc_record(d, v, src, d.current_version_id == v.id, not plan["chunks"]))
        order = {v.id: i for i, (_, v) in enumerate(plan["rows"])}
        chunk_rows: list[Chunk] = []
        if plan["chunks"]:
            for _, v in plan["rows"]:
                chunk_rows.extend(s.scalars(select(Chunk).where(Chunk.document_version_id == v.id).order_by(Chunk.ordinal)))
        chunks = [{"id": c.id, "document_version_id": c.document_version_id, "ordinal": c.ordinal, "page_start": c.page_start,
                   "page_end": c.page_end, "article": c.article, "section": c.section, "language": c.language,
                   "text": c.text, "text_sha256": c.text_sha256, "char_start": c.char_start, "char_end": c.char_end,
                   "doc_title": c.doc_title, "evidence_tag": c.evidence_tag, "topics": c.topics}
                  for c in sorted(chunk_rows, key=lambda c: (order[c.document_version_id], c.ordinal))]
        prog(0.3, "écriture des fichiers")
        kbj = {"id": kb.id, "code": kb.code, "name": kb.name, "description": kb.description, "domain": kb.domain,
               "kind": kb.kind, "languages": kb.languages or [], "chunking_params": kb.chunking_params,
               "embedder_fingerprint": kb.embedder_fingerprint}
        writer.add_bytes("data/kb.json", canonical_bytes(kbj), 1)
        writer.add_bytes("data/documents.jsonl", af.jsonl_bytes(docs), len(docs))
        writer.add_bytes("data/chunks.jsonl", af.jsonl_bytes(chunks), len(chunks))
        emb_meta: dict[str, Any] = {"included": False}
        if plan["embeddings"] and kb.embedder_key and chunks:
            rows = {r[0]: r[1] for r in s.execute(select(ChunkEmbedding.chunk_id, ChunkEmbedding.vector).where(
                ChunkEmbedding.embedder_key == kb.embedder_key, ChunkEmbedding.chunk_id.in_([c["id"] for c in chunks])))}
            ids = [c["id"] for c in chunks if c["id"] in rows]
            if ids:
                fp = kb.embedder_fingerprint or {}
                writer.add_bytes(f"data/embeddings/{kb.embedder_key}.f32.npy",
                                 af.npy_bytes(np.vstack([blob_to_vec(rows[i]) for i in ids])))
                writer.add_bytes("data/embeddings/embeddings.index.jsonl",
                                 af.jsonl_bytes([{"chunk_id": i, "row": n} for n, i in enumerate(ids)]), len(ids))
                emb_meta = {"included": True, "key": kb.embedder_key, "model": fp.get("model"), "dimension": fp.get("dimension"),
                            "normalized": fp.get("normalized"), "fingerprint": fp, "count": len(ids)}
        if not emb_meta["included"]:
            emb_meta.update({"key": kb.embedder_key, "model": (kb.embedder_fingerprint or {}).get("model"),
                             "dimension": (kb.embedder_fingerprint or {}).get("dimension")})
        for n, (name, path) in enumerate(sources.items()):
            writer.add_file(name, path)
            prog(0.3 + 0.6 * (n + 1) / max(1, len(sources)), f"original {n + 1}/{len(sources)}")
        ver = s.scalar(select(KBVersion.version_no).where(KBVersion.kb_id == kb.id).order_by(KBVersion.version_no.desc()).limit(1))
        lic: dict[str, int] = {}
        red: dict[str, int] = {}
        for d, _ in plan["rows"]:
            lic[d.license_spdx or "unspecified"] = lic.get(d.license_spdx or "unspecified", 0) + 1
            red[d.redistribution] = red.get(d.redistribution, 0) + 1
        manifest = {
            "format": af.FORMAT, "format_version": af.FORMAT_VERSION,
            "kb": {"id": kb.id, "code": kb.code, "name": kb.name, "version": ver, "languages": kb.languages or [],
                   "domain": kb.domain, "kind": kb.kind},
            "created_at": utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "exporter": EXPORTER, "mode": plan["mode"],
            "embedding": emb_meta, "chunking": kb.chunking_params or {"strategy": "article-aware"},
            "documents_summary": {"count": len(docs), "licenses": lic, "redistribution": red},
            "provenance": {"tool": "alerte-platform/knowledge ingest", "analyzer_version": ANALYZER_VERSION,
                           "libs": {n: _pkg(n) for n in ("pdfplumber", "pypdfium2", "python-docx", "snowballstemmer")}},
            "warnings": warnings, "files": []}
        writer.finish(manifest, signer=getattr(rt, "signer", None))
        with tmp.open("rb") as fh:
            sha, size = rt.blobs.put_stream(fh)
    finally:
        tmp.unlink(missing_ok=True)
    name = f"alerte-kb-{re.sub(r'[^A-Za-z0-9._-]+', '_', kb.code)}-v{ver or 0}-{dt.date.today().isoformat()}.zip"
    return {"sha": sha, "bytes": size, "filename": name, "documents": len(docs), "chunks": len(chunks),
            "mode": plan["mode"], "warnings": warnings}


# =========================================================================== import : dry-run
def _existing(session: Session, model: Any, ids: list[str]) -> set[str]:
    out: set[str] = set()
    for i in range(0, len(ids), 500):
        out.update(session.scalars(select(model.id).where(model.id.in_(ids[i:i + 500]))).all())
    return out


def validate_import(rt: KnowledgeRuntime, job: JobContext | None, import_id: str) -> dict:
    with rt.factory() as s:
        imp = s.get(KBImport, import_id)
        path = rt.blobs.path_for(imp.blob_sha256)
        try:
            p = af.open_and_validate(path)
        except af.ArchiveError as exc:
            imp.status, imp.report = "rejected", {"ok": False, "errors": [{"code": exc.code, "message": exc.message,
                                                                            "details": exc.details}], "warnings": []}
            s.commit()
            return imp.report
        ws = imp.workspace_id
        conflicts = {"kb": bool(_existing(s, KnowledgeBase, [p.kb["id"]])),
                     "documents": len(_existing(s, Document, [d["document_id"] for d in p.documents])),
                     "versions": len(_existing(s, DocumentVersion, [d["version"]["id"] for d in p.documents])),
                     "chunks": len(_existing(s, Chunk, [c["id"] for c in p.chunks])),
                     "code": s.scalar(select(KnowledgeBase.id).where(KnowledgeBase.workspace_id == ws,
                                                                     KnowledgeBase.code == p.kb["code"])) is not None}
        prior = s.scalar(select(KBImport).where(KBImport.workspace_id == ws, KBImport.manifest_sha256 == p.manifest_sha256,
                                                KBImport.status == "confirmed", KBImport.id != imp.id))
        already = prior.result_kb_id if prior and s.get(KnowledgeBase, prior.result_kb_id) else None
        warnings = list(p.warnings)
        red: dict[str, int] = {}
        for d in p.documents:
            red[d["redistribution"]] = red.get(d["redistribution"], 0) + 1
        if red.get("unknown") or red.get("restricted"):
            warnings.append(f"droits : {red.get('unknown', 0)} document(s) de redistribution inconnue, "
                            f"{red.get('restricted', 0)} restreint(s)")
        if any(conflicts[k] for k in ("kb", "documents", "versions", "chunks")):
            warnings.append("conflits d'identifiants : de nouveaux identifiants seront attribués (import_map)")
        if conflicts["code"]:
            warnings.append("code de base déjà utilisé dans l'espace : un suffixe sera ajouté")
        emb = p.manifest["embedding"]
        reuse = False
        if p.embeddings is not None:
            try:
                reuse = rt.embedder.ensure_fingerprint().key() == emb.get("key")
            except Exception:  # noqa: BLE001
                reuse = False
            warnings.append("embeddings réutilisés (empreinte identique)" if reuse else
                            "embeddings non réutilisables (empreinte différente) : à recalculer")
        report = {"ok": already is None, "errors": ([] if already is None else
                                                      [{"code": "kb.import.already_imported",
                                                        "message": "cette archive (même manifest.sha256) est déjà importée",
                                                        "details": {"kb_id": already}}]),
                  "warnings": warnings, "conflicts": conflicts, "already_imported": already,
                  "manifest_sha256": p.manifest_sha256,
                  "summary": {"kb": p.kb["code"], "documents": len(p.documents), "chunks": len(p.chunks),
                              "sources": len(p.sources), "embeddings": len(p.embeddings[0]) if p.embeddings else 0,
                              "mode": p.manifest["mode"], "format_version": p.manifest["format_version"],
                              "redistribution": red, "embeddings_reusable": reuse,
                              "signature": p.signature, "signed_by_this_instance": bool(
                                  p.signature and getattr(rt, "signer", None) is not None and p.signature["key_id"] == rt.signer.key_id())}}
        imp.status, imp.report, imp.manifest_sha256 = ("validated" if report["ok"] else "rejected"), report, p.manifest_sha256
        s.commit()
        return report


# =========================================================================== import : confirmation transactionnelle
def _remap(existing: set[str], ids: list[str]) -> dict[str, str]:
    from ..core.ids import new_id
    return {i: (new_id() if i in existing else i) for i in ids}


def confirm_import(rt: KnowledgeRuntime, job: JobContext | None, import_id: str, opts: dict) -> dict:
    import zipfile

    def prog(p: float, m: str) -> None:
        if job:
            job.update(p, m)

    with rt.factory() as s:
        imp = s.get(KBImport, import_id)
        ws, blob = imp.workspace_id, imp.blob_sha256
    path = rt.blobs.path_for(blob)
    p = af.open_and_validate(path)  # on ne fait jamais confiance à un rapport antérieur
    mode, target_id = opts.get("mode", "new_kb"), opts.get("target_kb_id")
    prog(0.1, "archive validée")
    # --- 1. originaux → blobs (vérifiés par hash) AVANT toute écriture en base
    with zipfile.ZipFile(path) as z:
        for d in p.documents:
            src = d["version"].get("source_file")
            if src:
                with z.open(src) as fh:
                    sha, _ = rt.blobs.put_stream(fh, max_bytes=af.MAX_UNCOMPRESSED)
                if sha != d["version"]["blob_sha256"]:
                    raise af.ArchiveError("kb.import.integrity_failed", f"original altéré : {src}")
    prog(0.3, "originaux stockés")
    emb_ok = False
    if p.embeddings is not None:
        try:
            emb_ok = rt.embedder.ensure_fingerprint().key() == p.manifest["embedding"].get("key")
        except Exception:  # noqa: BLE001
            emb_ok = False
    result: dict[str, Any] = {}
    vec_records: list[VectorRecord] = []
    with rt.factory() as s:
        try:
            if s.scalar(select(KBImport.id).where(KBImport.workspace_id == ws, KBImport.manifest_sha256 == p.manifest_sha256,
                                                  KBImport.status == "confirmed", KBImport.id != import_id)):
                raise Conflict("archive déjà importée dans cet espace", code="kb.import.already_imported")
            if mode == "new_version":
                kb = get_kb(s, ws, target_id or "")
                kb_map = {p.kb["id"]: kb.id}
            else:
                code, n = opts.get("code") or p.kb["code"], 1
                base = code
                while s.scalar(select(KnowledgeBase.id).where(KnowledgeBase.workspace_id == ws, KnowledgeBase.code == code)):
                    n += 1
                    code = f"{base}-{n}"[:64]
                kbid = _remap(_existing(s, KnowledgeBase, [p.kb["id"]]), [p.kb["id"]])[p.kb["id"]]
                kb = KnowledgeBase(id=kbid, workspace_id=ws, code=code, name=opts.get("name") or p.kb["name"],
                                   description=p.kb.get("description"), domain=p.kb.get("domain"), kind=p.kb["kind"],
                                   languages=p.kb.get("languages") or [], chunking_params=p.kb.get("chunking_params"))
                s.add(kb)
                s.flush()
                kb_map = {p.kb["id"]: kb.id}
            d_ids = list(dict.fromkeys(d["document_id"] for d in p.documents))
            doc_map = _remap(_existing(s, Document, d_ids), d_ids)
            ver_map = _remap(_existing(s, DocumentVersion, [d["version"]["id"] for d in p.documents]),
                             [d["version"]["id"] for d in p.documents])
            chunk_map = _remap(_existing(s, Chunk, [c["id"] for c in p.chunks]), [c["id"] for c in p.chunks])
            # --- 2. documents / versions
            created: dict[str, Document] = {}
            skipped_versions: set[str] = set()
            for rec in p.documents:
                v = rec["version"]
                did = rec["document_id"]
                existing = None
                if mode == "new_version":
                    existing = s.scalar(select(Document).where(Document.kb_id == kb.id, Document.code == rec["code"]))
                if existing is not None:
                    if s.scalar(select(DocumentVersion.id).where(DocumentVersion.document_id == existing.id,
                                                                 DocumentVersion.blob_sha256 == v["blob_sha256"])):
                        skipped_versions.add(v["id"])
                        continue
                    doc_map[did] = existing.id
                    doc = existing
                elif did in created:
                    doc = created[did]
                else:
                    doc = Document(id=doc_map[did], workspace_id=ws, kb_id=kb.id,
                                   doc_date=dt.date.fromisoformat(rec["doc_date"]) if rec.get("doc_date") else None,
                                   accessed_at=dt.date.fromisoformat(rec["accessed_at"]) if rec.get("accessed_at") else None,
                                   **{f: rec.get(f) for f in _DOC_FIELDS})
                    s.add(doc)
                    created[did] = doc
                    s.flush()
                last = s.scalar(select(DocumentVersion).where(DocumentVersion.document_id == doc.id)
                                .order_by(DocumentVersion.version_no.desc()).limit(1))
                no = v["version_no"] if existing is None else ((last.version_no + 1) if last else 1)
                s.add(DocumentVersion(
                    id=ver_map[v["id"]], workspace_id=ws, kb_id=kb.id, document_id=doc.id, version_no=no,
                    blob_sha256=v["blob_sha256"], mime=v.get("mime"), bytes=v.get("bytes") or 0,
                    original_name=v.get("original_name"), extraction_method=v.get("extraction_method"),
                    extraction_quality=v.get("extraction_quality"), pages_to_review=v.get("pages_to_review"),
                    quality_report=v.get("quality_report"), status=v["status"], note=v.get("note"),
                    supersedes_id=(last.id if (existing is not None and last) else None)))
                s.flush()
                if existing is not None or rec.get("is_current", True):
                    doc.current_version_id = ver_map[v["id"]]
            for rec in p.documents:  # replaced_by_id (second passage : toutes les cibles existent)
                tgt = rec.get("replaced_by_id")
                if tgt and rec["document_id"] in created and tgt in doc_map:
                    created[rec["document_id"]].replaced_by_id = doc_map[tgt]
            s.flush()
            for doc in created.values():
                if doc.current_version_id is None:
                    last = s.scalar(select(DocumentVersion.id).where(DocumentVersion.document_id == doc.id)
                                    .order_by(DocumentVersion.version_no.desc()).limit(1))
                    doc.current_version_id = last
            # --- 3. chunks + FTS
            titles = {r["version"]["id"]: r["title"] for r in p.documents}
            rows: list[Chunk] = []
            for c in p.chunks:
                if c["document_version_id"] in skipped_versions:
                    continue
                ch = Chunk(id=chunk_map[c["id"]], workspace_id=ws, kb_id=kb.id,
                           document_version_id=ver_map[c["document_version_id"]], ordinal=c["ordinal"],
                           page_start=c.get("page_start"), page_end=c.get("page_end"), article=c.get("article"),
                           section=c.get("section"), language=c.get("language"), text=c["text"],
                           search_text=analyze(c["text"]), text_sha256=c["text_sha256"], char_start=c.get("char_start"),
                           char_end=c.get("char_end"), doc_title=c.get("doc_title") or titles.get(c["document_version_id"], ""),
                           evidence_tag=c.get("evidence_tag") or "documented", topics=c.get("topics"))
                s.add(ch)
                rows.append(ch)
            s.flush()
            fts_insert(s, [chunk_fts_row(c) for c in rows])
            # --- 4. embeddings : réutilisés SEULEMENT si l'empreinte est identique à celle du serveur configuré
            reused = 0
            if p.embeddings is not None and emb_ok and (kb.embedder_key in (None, p.manifest["embedding"]["key"])):
                key = p.manifest["embedding"]["key"]
                ids, mat = p.embeddings
                kept = {c.id: c for c in rows}
                for cid, vec in zip(ids, mat, strict=True):
                    new = chunk_map[cid]
                    if new in kept:
                        s.add(ChunkEmbedding(chunk_id=new, embedder_key=key, dim=int(mat.shape[1]),
                                             vector=np.asarray(vec, dtype="<f4").tobytes()))
                        vec_records.append(VectorRecord(new, kb.id, kept[new].document_version_id, vec.tolist()))
                        reused += 1
                if reused:
                    kb.embedder_key = key
                    kb.embedder_fingerprint = p.manifest["embedding"].get("fingerprint")
            imp_row = s.get(KBImport, import_id)
            changed = {"kb": {k: v for k, v in kb_map.items() if k != v},
                       "documents": {k: v for k, v in doc_map.items() if k != v},
                       "versions": {k: v for k, v in ver_map.items() if k != v},
                       "chunks": {k: v for k, v in chunk_map.items() if k != v}}
            imp_row.status, imp_row.result_kb_id, imp_row.import_map = "confirmed", kb.id, changed
            imp_row.manifest_sha256 = p.manifest_sha256
            result = {"kb_id": kb.id, "kb_code": kb.code, "documents": len(created),
                      "documents_skipped_duplicates": len(skipped_versions), "chunks": len(rows),
                      "embeddings_reused": reused, "embeddings_to_recompute": bool(p.embeddings is not None and not reused),
                      "id_conflicts_remapped": any(changed.values()), "import_map_size": sum(len(v) for v in changed.values())}
            s.commit()
        except Exception:
            s.rollback()  # transaction unique : rien n'est créé en cas d'échec (les blobs orphelins sont inoffensifs)
            with rt.factory() as s2:
                imp2 = s2.get(KBImport, import_id)
                imp2.status = "failed"
                s2.commit()
            raise
    if vec_records:
        try:
            rt.vector_for(kb.embedder_key).upsert(vec_records)
        except Exception as exc:  # noqa: BLE001 - reconstructible : `reindex`
            result["index_pending"] = f"index vectoriel non alimenté ({type(exc).__name__}) : lancer reindex"
    prog(1.0, "import terminé")
    return result
