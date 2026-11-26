"""Routes de la base de connaissances (doc 12 §12.2) + suivi des jobs (JSON et SSE).

Rôles : lecture = facilitator/auditor ; écriture = facilitator (`owner` toujours autorisé). Les jetons `player` et
`observer` n'ont AUCUN accès aux bases (403). Toute requête filtre par espace (objet d'un autre espace → 404).
La portée de recherche est construite ICI à partir du rôle/espace du jeton, jamais d'un paramètre.
"""
from __future__ import annotations

import json
import time
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..contracts import SearchFilters
from ..core.auth import Principal, require_role
from ..core.context import AppContext, get_ctx, get_session
from ..core.db import utcnow
from ..core.errors import AppError, Conflict, NotFound
from ..core.jobs import JobStatus
from . import archive, kbops
from . import archive_format as af
from .kbops import get_document, get_kb
from .models import (
    Chunk,
    Document,
    DocumentVersion,
    KBExpectedDocument,
    KBExport,
    KBImport,
    KBVersion,
    KBVersionItem,
    KnowledgeBase,
)
from .runtime import KnowledgeRuntime
from .schemas import (
    AdoptRequest,
    BuildRequest,
    DocumentUpdate,
    EmbedRequest,
    ExpectedCreate,
    ExpectedUpdate,
    ExportRequest,
    ImportConfirm,
    KBCreate,
    KBUpdate,
    PublishRequest,
    SearchRequest,
)
from .services import build as bld
from .services import pipeline

router = APIRouter()
Read = require_role("facilitator", "auditor")
Write = require_role("facilitator")
_META = ("title", "code", "doc_type", "doc_number", "doc_date", "jurisdiction", "language", "source_url", "reliability",
         "validity", "license_spdx", "redistribution", "evidence_default", "accessed_at")


def rt_of(ctx: AppContext) -> KnowledgeRuntime:
    return ctx.service("knowledge")


def _job(ctx: AppContext, kind: str, fn, ws: str, payload: dict | None = None) -> dict:
    jid = ctx.jobs.submit(kind, fn, workspace_id=ws, payload=payload)
    return {"id": jid, "status": JobStatus.QUEUED}


def kb_out(kb: KnowledgeBase) -> dict:
    return {"id": kb.id, "code": kb.code, "name": kb.name, "description": kb.description, "country_id": kb.country_id,
            "domain": kb.domain, "kind": kb.kind, "scope_kind": kb.scope_kind, "scope_path": pipeline.kb_scope(kb), "languages": kb.languages or [], "embedder_key": kb.embedder_key,
            "embedder_fingerprint": kb.embedder_fingerprint, "chunking_params": kb.chunking_params, "status": kb.status,
            "archived_at": kb.archived_at.isoformat() if kb.archived_at else None}


def doc_out(d: Document, v: DocumentVersion | None = None) -> dict:
    out = {f: getattr(d, f) for f in ("id", "kb_id", "code", "title", "doc_type", "doc_number", "jurisdiction", "language",
                                      "source_url", "reliability", "validity", "replaced_by_id", "license_spdx",
                                      "redistribution", "evidence_default", "current_version_id")}
    out["doc_date"] = d.doc_date.isoformat() if d.doc_date else None
    out["accessed_at"] = d.accessed_at.isoformat() if d.accessed_at else None
    if v is not None:
        out["version"] = ver_out(v)
    return out


def ver_out(v: DocumentVersion, full: bool = False) -> dict:
    out = {"id": v.id, "version_no": v.version_no, "status": v.status, "bytes": v.bytes, "blob_sha256": v.blob_sha256,
           "original_name": v.original_name, "processing_state": v.processing_state, "processing_error": v.processing_error,
           "storage_path": v.storage_path, "migration_filename": v.migration_filename, "download_name": v.download_name,
           "provenance": v.provenance, "extraction_method": v.extraction_method,
           "extraction_quality": v.extraction_quality, "pages_to_review": v.pages_to_review or [],
           "supersedes_id": v.supersedes_id, "note": v.note, "created_at": v.created_at.isoformat()}
    if full:
        out["quality_report"] = v.quality_report
    return out


# --------------------------------------------------------------------------- bases
@router.get("/knowledge-bases", tags=["knowledge"])
def list_kbs(include_archived: bool = False, p: Principal = Depends(Read), session: Session = Depends(get_session),
             ctx: AppContext = Depends(get_ctx)) -> list[dict]:
    q = select(KnowledgeBase).where(KnowledgeBase.workspace_id == p.workspace_id).order_by(KnowledgeBase.code)
    if not include_archived:
        q = q.where(KnowledgeBase.archived_at.is_(None))
    return [kb_out(k) | {"overview": rt_of(ctx).kb_overview(session, p.workspace_id, k.id)} for k in session.scalars(q)]


@router.post("/knowledge-bases", status_code=201, tags=["knowledge"])
def create_kb(body: KBCreate, p: Principal = Depends(Write), session: Session = Depends(get_session),
              ctx: AppContext = Depends(get_ctx)) -> dict:
    rt = rt_of(ctx)
    kb = kbops.create_kb(rt, session, p.workspace_id, code=body.code, name=body.name, kind=body.kind, scope_kind=body.scope_kind,
                         country_id=body.country_id, domain=body.domain, languages=body.languages, description=body.description,
                         chunking_params=body.chunking_params)
    return kb_out(kb)


@router.get("/knowledge-bases/{kb_id}", tags=["knowledge"])
def get_kb_route(kb_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session),
                 ctx: AppContext = Depends(get_ctx)) -> dict:
    kb = get_kb(session, p.workspace_id, kb_id)
    return kb_out(kb) | {"overview": rt_of(ctx).kb_overview(session, p.workspace_id, kb_id)}


@router.patch("/knowledge-bases/{kb_id}", tags=["knowledge"])
def update_kb(kb_id: str, body: KBUpdate, p: Principal = Depends(Write), session: Session = Depends(get_session),
              ctx: AppContext = Depends(get_ctx)) -> dict:
    kb = get_kb(session, p.workspace_id, kb_id, allow_archived=False)
    data = body.model_dump(exclude_unset=True)
    if data.get("country_id") and rt_of(ctx).country_lookup:
        rt_of(ctx).country_lookup(session, p.workspace_id, data["country_id"])
    for k, v in data.items():
        setattr(kb, k, v)
    return kb_out(kb)


@router.post("/knowledge-bases/{kb_id}/archive", tags=["knowledge"])
def archive_kb(kb_id: str, p: Principal = Depends(Write), session: Session = Depends(get_session)) -> dict:
    kb = get_kb(session, p.workspace_id, kb_id)
    kb.archived_at, kb.status = utcnow(), "archived"
    return kb_out(kb)


# --------------------------------------------------------------------------- documents
@router.get("/knowledge-bases/{kb_id}/documents", tags=["knowledge"])
def list_documents(kb_id: str, limit: int = Query(50, ge=1, le=200), cursor: str | None = None,
                   status: str | None = None, state: str | None = None, p: Principal = Depends(Read),
                   session: Session = Depends(get_session)) -> dict:
    """Documents d'une base avec leur DERNIÈRE version (y compris un document importé et pas encore traité)."""
    get_kb(session, p.workspace_id, kb_id)
    q = select(Document, DocumentVersion).outerjoin(
        DocumentVersion, (DocumentVersion.document_id == Document.id) & DocumentVersion.id.in_(pipeline.latest_ids(kb_id))) \
        .where(Document.kb_id == kb_id, Document.workspace_id == p.workspace_id).order_by(Document.id).limit(limit + 1)
    if cursor:
        q = q.where(Document.id > cursor)
    if status:
        q = q.where(DocumentVersion.status == status)
    if state:
        q = q.where(DocumentVersion.processing_state == state)
    rows = session.execute(q).all()
    items = [doc_out(d, v) for d, v in rows[:limit]]
    return {"items": items, "next_cursor": rows[limit - 1][0].id if len(rows) > limit else None}


async def _form_meta(request: Request) -> dict:
    form = await request.form()
    return {k: (str(form[k]) or None) for k in _META if k in form}


@router.post("/knowledge-bases/{kb_id}/documents", status_code=202, tags=["knowledge"])
async def upload_document(kb_id: str, request: Request, file: UploadFile = File(...),
                          p: Principal = Depends(Write), session: Session = Depends(get_session),
                          ctx: AppContext = Depends(get_ctx)) -> dict:
    rt = rt_of(ctx)
    meta = await _form_meta(request)

    def work() -> dict:
        kb = get_kb(session, p.workspace_id, kb_id, allow_archived=False)
        clean = _clean_meta(meta)
        sha, size, rel = kbops.store_original(rt, session, kb, file.file, file.filename or "")
        doc, ver = kbops.create_document(session, p.workspace_id, kb, sha, size, file.filename or "", clean, storage_path=rel)
        pipeline.mark_queued(session, ver)
        session.commit()  # le job (autre thread) doit voir les lignes
        from .ingest import ingest_version
        job = _job(ctx, "kb_ingest", lambda jc: ingest_version(rt, jc, ver.id), p.workspace_id, {"version_id": ver.id})
        return {"job": job, "document": doc_out(doc, ver)}

    return await run_in_threadpool(work)


def _clean_meta(meta: dict) -> dict:
    from pydantic import ValidationError
    try:
        parsed = DocumentUpdate(**{k: v for k, v in meta.items() if k not in ("code",)})
    except ValidationError as exc:
        from ..core.errors import Unprocessable
        raise Unprocessable("métadonnées invalides", code="validation.failed",
                            details={"errors": [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]}) from exc
    out = parsed.model_dump(exclude_none=True)
    if meta.get("code"):
        out["code"] = meta["code"]
    return out


@router.get("/documents/{doc_id}", tags=["knowledge"])
def get_doc(doc_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)) -> dict:
    d = get_document(session, p.workspace_id, doc_id)
    return doc_out(d, pipeline.latest_version(session, d.id))


@router.patch("/documents/{doc_id}", tags=["knowledge"])
def patch_doc(doc_id: str, body: DocumentUpdate, p: Principal = Depends(Write), session: Session = Depends(get_session)) -> dict:
    d = get_document(session, p.workspace_id, doc_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("replaced_by_id"):
        tgt = get_document(session, p.workspace_id, data["replaced_by_id"])  # 404 si autre espace
        if tgt.id == d.id:
            raise AppError("un document ne peut pas se remplacer lui-même", code="kb.document.self_replace")
        data.setdefault("validity", "replaced")
    for k, v in data.items():
        if k in ("title", "reliability", "validity", "redistribution", "evidence_default") and v is None:
            continue
        setattr(d, k, v)
    return doc_out(d, pipeline.latest_version(session, d.id))


@router.delete("/documents/{doc_id}", status_code=200, tags=["knowledge"])
def retire_doc(doc_id: str, p: Principal = Depends(Write), session: Session = Depends(get_session)) -> dict:
    d = kbops.retire_document(session, p.workspace_id, doc_id)
    return doc_out(d)


@router.get("/documents/{doc_id}/versions", tags=["knowledge"])
def list_versions(doc_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)) -> list[dict]:
    d = get_document(session, p.workspace_id, doc_id)
    return [ver_out(v) for v in session.scalars(select(DocumentVersion).where(DocumentVersion.document_id == d.id)
                                                .order_by(DocumentVersion.version_no))]


@router.post("/documents/{doc_id}/versions", status_code=202, tags=["knowledge"])
def new_version(doc_id: str, file: UploadFile = File(...), note: str | None = Form(default=None),
                p: Principal = Depends(Write), session: Session = Depends(get_session),
                ctx: AppContext = Depends(get_ctx)) -> dict:
    rt = rt_of(ctx)
    d = get_document(session, p.workspace_id, doc_id)
    kb = get_kb(session, p.workspace_id, d.kb_id, allow_archived=False)
    sha, size, rel = kbops.store_original(rt, session, kb, file.file, file.filename or "")
    ver = kbops.add_version(session, p.workspace_id, d, sha, size, file.filename or "", note, storage_path=rel)
    pipeline.mark_queued(session, ver)
    session.commit()
    from .ingest import ingest_version
    job = _job(ctx, "kb_ingest", lambda jc: ingest_version(rt, jc, ver.id), p.workspace_id, {"version_id": ver.id})
    return {"job": job, "version": ver_out(ver)}


def _version(session: Session, ws: str, doc_id: str, version_no: int) -> tuple[Document, DocumentVersion]:
    d = get_document(session, ws, doc_id)
    v = session.scalar(select(DocumentVersion).where(DocumentVersion.document_id == d.id, DocumentVersion.version_no == version_no))
    if v is None:
        raise NotFound("version introuvable", code="kb.version.not_found")
    return d, v


@router.get("/documents/{doc_id}/versions/{version_no}/preview", tags=["knowledge"])
def preview(doc_id: str, version_no: int, page: int = Query(1, ge=1), limit: int = Query(5, ge=1, le=50),
            p: Principal = Depends(Read), session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)) -> dict:
    _, v = _version(session, p.workspace_id, doc_id, version_no)
    rt = rt_of(ctx)
    if v.text_blob_sha256 and rt.blobs.exists(v.text_blob_sha256):
        pages = json.loads(rt.blobs.read_bytes(v.text_blob_sha256))
    else:  # version importée : aperçu reconstruit depuis les chunks
        pages = [{"page": c.page_start, "text": c.text, "method": "chunk", "review": None}
                 for c in session.scalars(select(Chunk).where(Chunk.document_version_id == v.id).order_by(Chunk.ordinal))]
    sel = pages[(page - 1) * limit: page * limit]
    return {"version": ver_out(v, full=True), "total_pages": len(pages), "page": page, "pages": sel}


@router.get("/documents/{doc_id}/versions/{version_no}/chunks", tags=["knowledge"])
def version_chunks(doc_id: str, version_no: int, limit: int = Query(50, ge=1, le=200), cursor: int = -1,
                   p: Principal = Depends(Read), session: Session = Depends(get_session)) -> dict:
    _, v = _version(session, p.workspace_id, doc_id, version_no)
    rows = session.scalars(select(Chunk).where(Chunk.document_version_id == v.id, Chunk.workspace_id == p.workspace_id,
                                               Chunk.ordinal > cursor).order_by(Chunk.ordinal).limit(limit + 1)).all()
    items = [KnowledgeRuntime.chunk_dict(c) for c in rows[:limit]]
    return {"items": items, "next_cursor": rows[limit - 1].ordinal if len(rows) > limit else None}


# --------------------------------------------------------------------------- traitement individuel, historique, construction par base
@router.get("/documents/{doc_id}/versions/{version_no}/events", tags=["knowledge"])
def version_events(doc_id: str, version_no: int, p: Principal = Depends(Read), session: Session = Depends(get_session)) -> dict:
    _, v = _version(session, p.workspace_id, doc_id, version_no)
    return {"version": ver_out(v), "events": pipeline.events(session, v.id)}


@router.post("/documents/{doc_id}/versions/{version_no}/reprocess", status_code=202, tags=["knowledge"])
def reprocess_version(doc_id: str, version_no: int, p: Principal = Depends(Write), session: Session = Depends(get_session),
                      ctx: AppContext = Depends(get_ctx)) -> dict:
    """Relance INDIVIDUELLE : seul ce document est retraité (chunks, FTS et vecteurs de cette version recréés, sans doublon)."""
    rt = rt_of(ctx)
    d, v = _version(session, p.workspace_id, doc_id, version_no)
    get_kb(session, p.workspace_id, d.kb_id, allow_archived=False)
    if not pipeline.original_exists(rt, v):
        raise Conflict("fichier source introuvable : réimportez le document", code="kb.reprocess.source_missing")
    pipeline.prepare_reprocess(session, p.workspace_id, v.id)
    session.commit()
    from .ingest import ingest_version
    return {"job": _job(ctx, "kb_ingest", lambda jc: ingest_version(rt, jc, v.id), p.workspace_id, {"version_id": v.id})}


@router.get("/knowledge-bases/{kb_id}/status", tags=["knowledge"])
def kb_status_route(kb_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session),
                    ctx: AppContext = Depends(get_ctx)) -> dict:
    return bld.kb_status(rt_of(ctx), session, get_kb(session, p.workspace_id, kb_id))


@router.get("/knowledge-bases/{kb_id}/check", tags=["knowledge"])
def kb_check_route(kb_id: str, files: bool = True, p: Principal = Depends(Read), session: Session = Depends(get_session),
                   ctx: AppContext = Depends(get_ctx)) -> dict:
    return bld.check_coherence(rt_of(ctx), session, get_kb(session, p.workspace_id, kb_id), verify_files=files)


@router.post("/knowledge-bases/{kb_id}/build", status_code=202, tags=["knowledge"])
def kb_build_route(kb_id: str, body: BuildRequest | None = None, p: Principal = Depends(Write),
                   session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)) -> dict:
    """Construit CETTE base uniquement (documents en attente, embeddings manquants, index, contrôle ; publication si demandée)."""
    rt = rt_of(ctx)
    get_kb(session, p.workspace_id, kb_id, allow_archived=False)
    b = body or BuildRequest()
    return {"job": _job(ctx, "kb_build", lambda jc: bld.build_kb(rt, jc, kb_id, steps=tuple(b.steps), reembed=b.reembed,
                                                                 publish=b.publish, note=b.note), p.workspace_id,
                        {"kb_id": kb_id, "steps": b.steps})}


@router.get("/knowledge-bases/{kb_id}/unregistered", tags=["knowledge"])
def kb_unregistered(kb_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session),
                    ctx: AppContext = Depends(get_ctx)) -> dict:
    """Fichiers présents dans le dossier du périmètre de cette base mais sans enregistrement documentaire."""
    return {"scope_path": pipeline.kb_scope(get_kb(session, p.workspace_id, kb_id)),
            "files": kbops.list_unregistered(rt_of(ctx), session, get_kb(session, p.workspace_id, kb_id))}


@router.post("/knowledge-bases/{kb_id}/adopt", status_code=202, tags=["knowledge"])
def kb_adopt(kb_id: str, body: AdoptRequest, p: Principal = Depends(Write), session: Session = Depends(get_session),
             ctx: AppContext = Depends(get_ctx)) -> dict:
    rt = rt_of(ctx)
    kb = get_kb(session, p.workspace_id, kb_id, allow_archived=False)
    meta = _clean_meta(body.meta)
    out, jobs = [], []
    for rel in body.files:
        try:
            doc, ver = kbops.adopt_file(rt, session, kb, rel, dict(meta))
            pipeline.mark_queued(session, ver)
            session.commit()
            out.append({"path": rel, "document_id": doc.id, "version_id": ver.id})
        except AppError as exc:  # un fichier refusé n'arrête pas les autres
            session.rollback()
            out.append({"path": rel, "error": exc.message if hasattr(exc, "message") else str(exc), "code": exc.code})
    from .ingest import ingest_version
    for o in out:
        if "version_id" in o:
            vid = o["version_id"]
            jobs.append(_job(ctx, "kb_ingest", lambda jc, vid=vid: ingest_version(rt, jc, vid), p.workspace_id, {"version_id": vid}))
    return {"documents": out, "jobs": jobs}


# --------------------------------------------------------------------------- qualité, publication, index
@router.get("/knowledge-bases/{kb_id}/quality", tags=["knowledge"])
def quality(kb_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session),
            ctx: AppContext = Depends(get_ctx)) -> dict:
    return kbops.quality_report(rt_of(ctx), session, p.workspace_id, kb_id)


@router.post("/knowledge-bases/{kb_id}/publish", status_code=201, tags=["knowledge"])
def publish(kb_id: str, body: PublishRequest | None = None, p: Principal = Depends(Write),
            session: Session = Depends(get_session)) -> dict:
    kv = kbops.publish_kb(session, p.workspace_id, kb_id, body.note if body else None)
    n = session.scalar(select(func.count()).select_from(KBVersionItem).where(KBVersionItem.kb_version_id == kv.id))
    return {"id": kv.id, "kb_id": kv.kb_id, "version_no": kv.version_no, "manifest_sha256": kv.manifest_sha256,
            "note": kv.note, "documents": n}


@router.get("/knowledge-bases/{kb_id}/versions", tags=["knowledge"])
def kb_versions(kb_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)) -> list[dict]:
    get_kb(session, p.workspace_id, kb_id)
    return [{"id": k.id, "version_no": k.version_no, "manifest_sha256": k.manifest_sha256, "note": k.note,
             "created_at": k.created_at.isoformat()}
            for k in session.scalars(select(KBVersion).where(KBVersion.kb_id == kb_id).order_by(KBVersion.version_no))]


@router.post("/knowledge-bases/{kb_id}/reindex", status_code=202, tags=["knowledge"])
def reindex(kb_id: str, p: Principal = Depends(Write), session: Session = Depends(get_session),
            ctx: AppContext = Depends(get_ctx)) -> dict:
    rt = rt_of(ctx)
    get_kb(session, p.workspace_id, kb_id)
    return {"job": _job(ctx, "kb_reindex", lambda jc: kbops.reindex_kb(rt, jc, kb_id), p.workspace_id, {"kb_id": kb_id})}


@router.post("/knowledge-bases/{kb_id}/embed", status_code=202, tags=["knowledge"])
def embed(kb_id: str, body: EmbedRequest | None = None, p: Principal = Depends(Write),
          session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)) -> dict:
    rt = rt_of(ctx)
    kb = get_kb(session, p.workspace_id, kb_id)
    reembed = bool(body and body.reembed)
    try:
        kbops.precheck_embed(rt, session, kb, reembed)  # 409 explicite si empreinte différente
    except AppError:
        raise
    except Exception as exc:  # noqa: BLE001 - serveur d'embeddings injoignable / non configuré
        raise AppError(f"serveur d'embeddings indisponible : {exc}", code="kb.embedder_unavailable", status_code=503) from exc
    return {"job": _job(ctx, "kb_embed", lambda jc: kbops.embed_kb(rt, jc, kb_id, reembed=reembed), p.workspace_id,
                        {"kb_id": kb_id, "reembed": reembed})}


@router.post("/knowledge-bases/{kb_id}/search", tags=["knowledge"])
def search(kb_id: str, body: SearchRequest, p: Principal = Depends(Read), session: Session = Depends(get_session),
           ctx: AppContext = Depends(get_ctx)) -> dict:
    rt = rt_of(ctx)
    get_kb(session, p.workspace_id, kb_id)
    scope = rt.ui_scope(session, p.workspace_id, kb_id)  # portée dérivée du jeton, jamais du corps
    flt = SearchFilters(languages=frozenset(body.languages) if body.languages else None,
                        doc_types=frozenset(body.doc_types) if body.doc_types else None, article=body.article)
    hits = rt.search.search(scope, body.query, body.k, filters=flt)
    degraded = any(h.signals.get("degraded") for h in hits) if hits else False
    return {"scope_hash": scope.scope_hash(), "degraded": degraded or _probe_degraded(rt),
            "label": "BM25 (FTS5) + vectoriel + RRF" if not degraded else "recherche dégradée : lexical seul",
            "hits": [{"chunk_id": h.chunk_id, "document_version_id": h.document_version_id, "doc_code": h.doc_code,
                      "doc_title": h.doc_title, "article": h.article, "page": h.page, "score": h.score, "snippet": h.snippet,
                      "text": h.text, "signals": h.signals} for h in hits]}


def _probe_degraded(rt: KnowledgeRuntime) -> bool:
    from .embedders import UnavailableEmbedder
    return isinstance(rt.embedder, UnavailableEmbedder)


# --------------------------------------------------------------------------- couverture attendue
def _expected(session: Session, ws: str, kb_id: str, eid: str) -> KBExpectedDocument:
    e = session.scalar(select(KBExpectedDocument).where(KBExpectedDocument.id == eid, KBExpectedDocument.kb_id == kb_id,
                                                        KBExpectedDocument.workspace_id == ws))
    if e is None:
        raise NotFound("document attendu introuvable", code="kb.expected.not_found")
    return e


def _exp_out(e: KBExpectedDocument) -> dict:
    return {"id": e.id, "title": e.title, "jurisdiction": e.jurisdiction, "citation": e.citation, "status": e.status,
            "matched_document_id": e.matched_document_id}


@router.get("/knowledge-bases/{kb_id}/expected", tags=["knowledge"])
def list_expected(kb_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session),
                  ctx: AppContext = Depends(get_ctx)) -> dict:
    get_kb(session, p.workspace_id, kb_id)
    items = session.scalars(select(KBExpectedDocument).where(KBExpectedDocument.kb_id == kb_id,
                                                             KBExpectedDocument.workspace_id == p.workspace_id)
                            .order_by(KBExpectedDocument.id)).all()
    return {"items": [_exp_out(e) for e in items], "coverage": rt_of(ctx).coverage(session, p.workspace_id, [kb_id])}


@router.post("/knowledge-bases/{kb_id}/expected", status_code=201, tags=["knowledge"])
def add_expected(kb_id: str, body: ExpectedCreate, p: Principal = Depends(Write),
                 session: Session = Depends(get_session)) -> dict:
    get_kb(session, p.workspace_id, kb_id)
    if body.matched_document_id and get_document(session, p.workspace_id, body.matched_document_id).kb_id != kb_id:
        raise NotFound("document introuvable dans cette base", code="kb.document.not_found")
    e = KBExpectedDocument(workspace_id=p.workspace_id, kb_id=kb_id, **body.model_dump())
    session.add(e)
    session.flush()
    return _exp_out(e)


@router.patch("/knowledge-bases/{kb_id}/expected/{eid}", tags=["knowledge"])
def patch_expected(kb_id: str, eid: str, body: ExpectedUpdate, p: Principal = Depends(Write),
                   session: Session = Depends(get_session)) -> dict:
    e = _expected(session, p.workspace_id, kb_id, eid)
    data = body.model_dump(exclude_unset=True)
    if data.get("matched_document_id") and get_document(session, p.workspace_id, data["matched_document_id"]).kb_id != kb_id:
        raise NotFound("document introuvable dans cette base", code="kb.document.not_found")
    for k, v in data.items():
        setattr(e, k, v)
    return _exp_out(e)


@router.delete("/knowledge-bases/{kb_id}/expected/{eid}", status_code=204, tags=["knowledge"])
def del_expected(kb_id: str, eid: str, p: Principal = Depends(Write), session: Session = Depends(get_session)) -> None:
    _expected(session, p.workspace_id, kb_id, eid)
    session.execute(delete(KBExpectedDocument).where(KBExpectedDocument.id == eid))


# --------------------------------------------------------------------------- exports / imports
@router.post("/knowledge-bases/{kb_id}/exports", status_code=202, tags=["knowledge"])
def start_export(kb_id: str, body: ExportRequest, p: Principal = Depends(Write), session: Session = Depends(get_session),
                 ctx: AppContext = Depends(get_ctx)) -> dict:
    rt = rt_of(ctx)
    req = body.model_dump()
    plan = archive.plan_export(session, p.workspace_id, kb_id, req)  # 422 synchrone (droits, sélection)
    ex = KBExport(workspace_id=p.workspace_id, kb_id=kb_id, kb_version_id=body.kb_version_id, mode=body.mode,
                  options={k: req[k] for k in ("document_ids", "include", "purpose", "kb_version_id")}, status="queued")
    session.add(ex)
    session.commit()
    eid = ex.id
    job = _job(ctx, "kb_export", lambda jc: archive.run_export(rt, jc, eid), p.workspace_id, {"export_id": eid})
    with rt.factory() as s:
        s.get(KBExport, eid).job_id = job["id"]
        s.commit()
    return {"job": job, "export": {"id": eid, "status": "queued", "mode": body.mode}, "warnings": plan["warnings"]}


def _export_row(session: Session, ws: str, eid: str) -> KBExport:
    e = session.scalar(select(KBExport).where(KBExport.id == eid, KBExport.workspace_id == ws))
    if e is None:
        raise NotFound("export introuvable", code="kb.export.not_found")
    return e


@router.get("/exports/{export_id}", tags=["knowledge"])
def get_export(export_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)) -> dict:
    e = _export_row(session, p.workspace_id, export_id)
    return {"id": e.id, "kb_id": e.kb_id, "mode": e.mode, "status": e.status, "error": e.error, "job_id": e.job_id,
            "bytes": e.bytes, "filename": e.filename, "blob_sha256": e.blob_sha256}


@router.get("/exports/{export_id}/download", tags=["knowledge"])
def download_export(export_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session),
                    ctx: AppContext = Depends(get_ctx)):  # noqa: ANN201
    e = _export_row(session, p.workspace_id, export_id)
    if e.status != "done" or not e.blob_sha256:
        raise Conflict("export non terminé", code="kb.export.not_ready")
    return FileResponse(rt_of(ctx).blobs.path_for(e.blob_sha256), media_type="application/zip",
                        filename=e.filename or "alerte-kb.zip")


@router.post("/knowledge-bases/import", status_code=202, tags=["knowledge"])
def start_import(file: UploadFile = File(...), p: Principal = Depends(Write), session: Session = Depends(get_session),
                 ctx: AppContext = Depends(get_ctx)) -> dict:
    rt = rt_of(ctx)
    try:
        sha, _ = rt.blobs.put_stream(file.file, max_bytes=af.MAX_UNCOMPRESSED)
    except ValueError as exc:
        raise AppError("archive trop volumineuse", code="kb.import.too_large", status_code=413) from exc
    imp = KBImport(workspace_id=p.workspace_id, blob_sha256=sha, status="validating")
    session.add(imp)
    session.commit()
    iid = imp.id
    job = _job(ctx, "kb_import_validate", lambda jc: archive.validate_import(rt, jc, iid), p.workspace_id, {"import_id": iid})
    with rt.factory() as s:
        s.get(KBImport, iid).job_id = job["id"]
        s.commit()
    return {"job": job, "import": {"id": iid, "status": "validating"}}


def _import_row(session: Session, ws: str, iid: str) -> KBImport:
    i = session.scalar(select(KBImport).where(KBImport.id == iid, KBImport.workspace_id == ws))
    if i is None:
        raise NotFound("import introuvable", code="kb.import.not_found")
    return i


@router.get("/imports/{import_id}", tags=["knowledge"])
def get_import(import_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)) -> dict:
    i = _import_row(session, p.workspace_id, import_id)
    return {"id": i.id, "status": i.status, "report": i.report, "result_kb_id": i.result_kb_id, "import_map": i.import_map,
            "job_id": i.job_id}


@router.post("/imports/{import_id}/confirm", status_code=202, tags=["knowledge"])
def confirm_import(import_id: str, body: ImportConfirm | None = None, p: Principal = Depends(Write),
                   session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)) -> dict:
    rt = rt_of(ctx)
    i = _import_row(session, p.workspace_id, import_id)
    if i.status != "validated":
        raise Conflict("l'import doit être validé (dry-run sans erreur) avant confirmation", code="kb.import.not_validated",
                       details={"status": i.status})
    opts = (body or ImportConfirm()).model_dump()
    if opts["mode"] == "new_version":
        if not opts["target_kb_id"]:
            raise AppError("target_kb_id requis pour new_version", code="validation.failed", status_code=422)
        get_kb(session, p.workspace_id, opts["target_kb_id"], allow_archived=False)
    return {"job": _job(ctx, "kb_import_confirm", lambda jc: archive.confirm_import(rt, jc, import_id, opts),
                        p.workspace_id, {"import_id": import_id})}


# --------------------------------------------------------------------------- jobs (JSON + SSE)
def _job_of(ctx: AppContext, ws: str, job_id: str) -> dict:
    j = ctx.jobs.get(job_id)
    if j is None or j["workspace_id"] != ws:
        raise NotFound("job introuvable", code="job.not_found")
    return j


@router.get("/jobs/{job_id}", tags=["jobs"])
def get_job(job_id: str, p: Principal = Depends(Read), ctx: AppContext = Depends(get_ctx)) -> dict:
    return _job_of(ctx, p.workspace_id, job_id)


def sse_events(ctx: AppContext, ws: str, job_id: str, after: int, *, poll_s: float = 0.3, heartbeat_s: float = 15.0,
               max_s: float = 3600.0):  # noqa: ANN201
    """`id` = compteur monotone : progression en millièmes (0..1000), 1001 pour l'événement final."""
    last_id, started, last_beat = after, time.monotonic(), time.monotonic()
    yield "retry: 3000\n\n"
    while time.monotonic() - started < max_s:
        j = ctx.jobs.get(job_id)
        if j is None or j["workspace_id"] != ws:
            yield 'event: failed\ndata: {"error": "job introuvable"}\n\n'
            return
        counter = int(round(j["progress"] * 1000))
        if counter > last_id and j["status"] not in JobStatus.TERMINAL:
            last_id = counter
            yield (f"id: {counter}\nevent: progress\ndata: " + json.dumps(
                {"pct": round(j["progress"] * 100, 1), "step": j["kind"], "message": j["message"]}) + "\n\n")
        if j["status"] in JobStatus.TERMINAL:
            if last_id < 1001:
                if j["status"] == JobStatus.DONE:
                    yield "id: 1001\nevent: done\ndata: " + json.dumps({"result_ref": j["result"]}, default=str) + "\n\n"
                else:
                    yield "id: 1001\nevent: failed\ndata: " + json.dumps({"error": (j["error"] or j["status"])[:500]}) + "\n\n"
            return
        if time.monotonic() - last_beat > heartbeat_s:
            last_beat = time.monotonic()
            yield ": heartbeat\n\n"
        time.sleep(poll_s)


@router.get("/jobs/{job_id}/stream", tags=["jobs"])
def stream_job(job_id: str, after: int = Query(0, ge=0), last_event_id: str | None = Header(default=None),
               p: Principal = Depends(Read), ctx: AppContext = Depends(get_ctx)) -> StreamingResponse:
    _job_of(ctx, p.workspace_id, job_id)
    start = after
    if last_event_id and last_event_id.isdigit():
        start = max(start, int(last_event_id))
    return StreamingResponse(sse_events(ctx, p.workspace_id, job_id, start), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


__all__: list[Any] = ["router"]
