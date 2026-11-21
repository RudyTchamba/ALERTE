"""Routes du gestionnaire de rapports (sans préfixe /api/v1). Contrôle d'espace : `exercise_guard` (simulation) pour les
exercices ; filtrage `workspace_id` pour tout le reste (autre espace -> 404)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from sqlalchemy.orm import Session

from ..core.auth import Principal, require_role
from ..core.context import AppContext, get_ctx, get_session
from ..core.errors import AppError, NotFound
from . import service
from .schemas import ContentPut, FindingIn, FindingOut, GenerateIn, LinkIn, ReportCreate

router = APIRouter()
Read = require_role("facilitator", "auditor")
Write = require_role("facilitator")


def _guard(ctx: AppContext, session: Session, p: Principal, exercise_id: str) -> None:
    g = ctx.services.get("exercise_guard")
    if g is None:
        raise NotFound("exercice introuvable")
    g(session, p, exercise_id)


def _who(p: Principal) -> str:
    return p.label or p.token_id


def _version_out(v: Any, with_content: bool) -> dict[str, Any]:
    d = {"id": v.id, "report_id": v.report_id, "version_no": v.version_no, "status": v.status, "content_sha256": v.content_sha256,
         "ledger_head_seq": v.ledger_head_seq, "ledger_head_hash": v.ledger_head_hash, "parent_version_id": v.parent_version_id,
         "generator_version": v.generator_version, "created_at": v.created_at.isoformat(),
         "published_at": v.published_at.isoformat() if v.published_at else None}
    if with_content:
        d["content"] = v.content
    return d


def _finding_out(f: Any) -> FindingOut:
    return FindingOut(id=f.id, report_id=f.report_id, title=f.title, body=f.body, code_hint=f.code_hint,
                      severity_hint=f.severity_hint, source_page=f.source_page, status=f.status)


# --- rapports ----------------------------------------------------------------------------------------------
@router.get("/reports", tags=["reports"])
def list_reports(kind: str | None = None, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    from sqlalchemy import select

    from .models import Report
    q = select(Report).where(Report.workspace_id == p.workspace_id)
    if kind:
        q = q.where(Report.kind == kind)
    return [service.report_summary(session, r) for r in session.scalars(q.order_by(Report.id.desc()))]


@router.post("/reports", status_code=201, tags=["reports"])
def create_report(body: ReportCreate, p: Principal = Depends(Write), session: Session = Depends(get_session),
                  ctx: AppContext = Depends(get_ctx)):
    if body.exercise_id:
        _guard(ctx, session, p, body.exercise_id)
    r = service.create_report(session, p.workspace_id, body.kind, body.title, body.exercise_id, body.confidentiality, _who(p))
    return service.report_summary(session, r)


@router.post("/reports/import", status_code=201, tags=["reports"])
async def import_report(file: UploadFile = File(...), title: str = Form(...), exercise_id: str | None = Form(None),
                        confidentiality: str = Form("internal"), original_date: str | None = Form(None),
                        source_note: str | None = Form(None), p: Principal = Depends(Write),
                        session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)):
    if exercise_id:
        _guard(ctx, session, p, exercise_id)
    data = await file.read(ctx.settings.upload_max_mb * 1024 * 1024 + 1)
    if len(data) > ctx.settings.upload_max_mb * 1024 * 1024:
        raise AppError("fichier trop volumineux", status_code=413, code="upload.too_large")
    r = service.import_report(ctx, session, p.workspace_id, title=title, filename=file.filename or "", data=data,
                              exercise_id=exercise_id, confidentiality=confidentiality, original_date=original_date,
                              source_note=source_note, by=_who(p))
    return service.report_summary(session, r)


@router.get("/reports/compare-exercises", tags=["reports"])
def compare_exercises(a: str, b: str, p: Principal = Depends(Read), session: Session = Depends(get_session),
                      ctx: AppContext = Depends(get_ctx)):
    _guard(ctx, session, p, a)
    _guard(ctx, session, p, b)
    return service.compare_exercises(ctx, session, p.workspace_id, a, b)


@router.get("/reports/{report_id}", tags=["reports"])
def get_report(report_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    r = service.get_report(session, p.workspace_id, report_id)
    out = service.report_summary(session, r)
    out["version_list"] = [_version_out(v, False) for v in service.list_versions(session, r.id)]
    if r.kind == "imported":
        out["findings"] = [_finding_out(f).model_dump() for f in service.list_findings(session, p.workspace_id, r.id)]
    return out


@router.get("/reports/{report_id}/document", tags=["reports"])
def download_original(report_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session),
                      ctx: AppContext = Depends(get_ctx)):
    r = service.get_report(session, p.workspace_id, report_id)
    if r.kind != "imported" or not r.document_sha256:
        raise NotFound("aucun document original pour ce rapport")
    name = (r.document_filename or "document").replace('"', "")
    return Response(ctx.blobs.read_bytes(r.document_sha256), media_type=r.document_media_type or "application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{name}"', "X-Content-SHA256": r.document_sha256})


@router.get("/reports/{report_id}/compare", tags=["reports"])
def compare(report_id: str, a: str, b: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return service.compare_versions(session, p.workspace_id, report_id, a, b)


# --- constats importés ---------------------------------------------------------------------------------------
@router.post("/reports/{report_id}/findings", response_model=list[FindingOut], status_code=201, tags=["reports"])
def add_findings(report_id: str, body: list[FindingIn] | FindingIn, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    rows = [b.model_dump() for b in (body if isinstance(body, list) else [body])]
    return [_finding_out(f) for f in service.add_findings(session, p.workspace_id, report_id, rows)]


@router.get("/reports/{report_id}/findings", response_model=list[FindingOut], tags=["reports"])
def list_findings(report_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return [_finding_out(f) for f in service.list_findings(session, p.workspace_id, report_id)]


@router.post("/imported-findings/{finding_id}/links", status_code=201, tags=["reports"])
def link_finding(finding_id: str, body: LinkIn, p: Principal = Depends(Write), session: Session = Depends(get_session),
                 ctx: AppContext = Depends(get_ctx)):
    _guard(ctx, session, p, body.exercise_id)
    link = service.link_prior(ctx, session, p.workspace_id, finding_id, body.gap_id, body.exercise_id, body.relation, body.note)
    return {"id": link.id, "gap_id": link.gap_id, "imported_finding_id": link.imported_finding_id, "relation": link.relation,
            "origin": service.ORIGIN_PRIOR}


@router.get("/reports/{report_id}/links", tags=["reports"])
def list_links(report_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return [{"id": x.id, "gap_id": x.gap_id, "exercise_id": x.exercise_id, "imported_finding_id": x.imported_finding_id,
             "relation": x.relation, "note": x.note, "origin": service.ORIGIN_PRIOR}
            for x in service.list_links(session, p.workspace_id, report_id)]


# --- génération et versions -----------------------------------------------------------------------------------
@router.post("/exercises/{exercise_id}/reports", status_code=202, tags=["reports"])
def generate(exercise_id: str, body: GenerateIn | None = None, p: Principal = Depends(Write),
             session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)):
    _guard(ctx, session, p, exercise_id)
    body = body or GenerateIn()
    if body.report_id:
        service.get_report(session, p.workspace_id, body.report_id)  # 404 avant de lancer le job
    ws, who = p.workspace_id, _who(p)

    def job(jc: Any) -> dict[str, Any]:
        jc.update(0.1, "assemblage du rapport")
        with jc.session() as s:
            v = service.generate_version(ctx, s, ws, exercise_id, title=body.title, report_id=body.report_id,
                                         confidentiality=body.confidentiality, by=who)
            return {"report_id": v.report_id, "version_id": v.id, "version_no": v.version_no}

    jid = ctx.jobs.submit("report.generate", job, workspace_id=ws, payload={"exercise_id": exercise_id})
    return {"job": {"id": jid, "status": "queued"}, "job_id": jid}  # forme alignée sur le module knowledge


@router.get("/report-versions/{version_id}", tags=["reports"])
def get_version(version_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    v = service.get_version(session, p.workspace_id, version_id)
    out = _version_out(v, True)
    out["artifacts"] = [{"format": a.format, "sha256": a.blob_sha256, "bytes": a.bytes, "renderer": a.renderer}
                        for a in service.list_artifacts(session, v.id)]
    return out


@router.put("/report-versions/{version_id}/content", tags=["reports"])
def put_content(version_id: str, body: ContentPut, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return _version_out(service.update_draft(session, p.workspace_id, version_id, body.content), False)


@router.post("/report-versions/{version_id}/publish", tags=["reports"])
def publish(version_id: str, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return _version_out(service.publish(session, p.workspace_id, version_id), False)


@router.get("/report-versions/{version_id}/artifacts/{fmt}", tags=["reports"])
def artifact(version_id: str, fmt: str, p: Principal = Depends(Read), session: Session = Depends(get_session),
             ctx: AppContext = Depends(get_ctx)):
    v = service.get_version(session, p.workspace_id, version_id)
    data, media, filename, art = service.render_artifact(ctx, session, v, fmt)
    return Response(data, media_type=media, headers={
        "Content-Disposition": f'attachment; filename="{filename}"', "X-Content-SHA256": art.blob_sha256,
        "X-Report-Content-SHA256": v.content_sha256, "X-Ledger-Head": f"{v.ledger_head_seq}:{v.ledger_head_hash}"})
