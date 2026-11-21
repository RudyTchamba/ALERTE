from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from ..core.auth import Principal, require_role
from ..core.context import get_session
from ..core.errors import Unprocessable
from . import csv_import, service
from .models import Mandate, MandateSource
from .schemas import (
    ActionCreate,
    ActionOut,
    ActionUpdate,
    ImportReport,
    MandateCreate,
    MandateOut,
    MandateUpdate,
    RegistryReviewIn,
    RegistryReviewOut,
    RejectIn,
    SourceIn,
    SourceOut,
    ValidateIn,
)

router = APIRouter()
Read = require_role("facilitator", "observer", "auditor")
Write = require_role("facilitator")


def _out(session: Session, m: Mandate) -> MandateOut:
    srcs: list[MandateSource] = service._sources(session, m.id)
    active, reason = service.source_status(session, m, srcs)
    out = MandateOut.model_validate(m)
    out.sources = [SourceOut.model_validate(s) for s in srcs]
    out.active, out.inactive_reason = active, reason
    return out


# --- catalogue d'actions ---------------------------------------------------------------------------
@router.get("/actions", response_model=list[ActionOut], tags=["mandates"])
def list_actions(p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return service.list_actions(session, p.workspace_id)


@router.post("/actions", response_model=ActionOut, status_code=201, tags=["mandates"])
def create_action(body: ActionCreate, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return service.action_dict(service.create_action(session, p.workspace_id, body))


@router.get("/actions/{action_id}", response_model=ActionOut, tags=["mandates"])
def get_action(action_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return service.action_dict(service.get_action(session, p.workspace_id, action_id))


@router.patch("/actions/{action_id}", response_model=ActionOut, tags=["mandates"])
def update_action(action_id: str, body: ActionUpdate, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return service.action_dict(service.update_action(session, p.workspace_id, action_id, body))


# --- mandats ---------------------------------------------------------------------------------------
@router.get("/mandates", response_model=list[MandateOut], tags=["mandates"])
def list_mandates(institution_id: str | None = None, action_code: str | None = None, kind: str | None = None,
                  validation: str | None = None, active: bool | None = None, p: Principal = Depends(Read),
                  session: Session = Depends(get_session)):
    rows = [_out(session, m) for m in service.list_mandates(session, p.workspace_id, institution_id=institution_id,
                                                           action_code=action_code, kind=kind, validation=validation)]
    return [r for r in rows if active is None or r.active == active]


@router.post("/mandates", response_model=MandateOut, status_code=201, tags=["mandates"])
def create_mandate(body: MandateCreate, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return _out(session, service.create_mandate(session, p.workspace_id, body, p))


@router.post("/mandates/import-csv", response_model=ImportReport, tags=["mandates"])
async def import_csv(request: Request, dry_run: bool = False, p: Principal = Depends(Write),
                     session: Session = Depends(get_session)):
    """Corps : JSON `{"csv_text": "..."}` ou `text/csv` brut (UTF-8)."""
    raw = await request.body()
    if "json" in request.headers.get("content-type", ""):
        import json
        try:
            text = json.loads(raw)["csv_text"]
        except (ValueError, KeyError, TypeError) as exc:
            raise Unprocessable("corps JSON attendu : {csv_text}", code="mandate.import.bad_body") from exc
    else:
        text = raw.decode("utf-8-sig")
    return csv_import.import_csv(session, p.workspace_id, text, p, dry_run=dry_run)


@router.get("/mandates/{mandate_id}", response_model=MandateOut, tags=["mandates"])
def get_mandate(mandate_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return _out(session, service.get_mandate(session, p.workspace_id, mandate_id))


@router.patch("/mandates/{mandate_id}", response_model=MandateOut, tags=["mandates"])
def update_mandate(mandate_id: str, body: MandateUpdate, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return _out(session, service.update_mandate(session, p.workspace_id, mandate_id, body, p))


@router.delete("/mandates/{mandate_id}", status_code=204, tags=["mandates"])
def delete_mandate(mandate_id: str, p: Principal = Depends(Write), session: Session = Depends(get_session)) -> Response:
    service.delete_mandate(session, p.workspace_id, mandate_id)
    return Response(status_code=204)


@router.post("/mandates/{mandate_id}/sources", response_model=SourceOut, status_code=201, tags=["mandates"])
def add_source(mandate_id: str, body: SourceIn, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return SourceOut.model_validate(service.add_source(session, p.workspace_id, mandate_id, body, p))


@router.delete("/mandates/{mandate_id}/sources/{source_id}", status_code=204, tags=["mandates"])
def remove_source(mandate_id: str, source_id: str, p: Principal = Depends(Write), session: Session = Depends(get_session)) -> Response:
    service.remove_source(session, p.workspace_id, mandate_id, source_id, p)
    return Response(status_code=204)


@router.post("/mandates/{mandate_id}/validate", response_model=MandateOut, tags=["mandates"])
def validate_mandate(mandate_id: str, body: ValidateIn | None = None, p: Principal = Depends(Write),
                     session: Session = Depends(get_session)):
    body = body or ValidateIn()
    return _out(session, service.validate_mandate(session, p.workspace_id, mandate_id, p, note=body.note,
                                                  corrections=body.corrections))


@router.post("/mandates/{mandate_id}/reject", response_model=MandateOut, tags=["mandates"])
def reject_mandate(mandate_id: str, body: RejectIn, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return _out(session, service.reject_mandate(session, p.workspace_id, mandate_id, p, note=body.note))


@router.get("/mandates/{mandate_id}/history", tags=["mandates"])
def mandate_history(mandate_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return [{"actor": r.actor, "action": r.action, "from": r.from_status, "to": r.to_status, "note": r.note,
             "changes": r.changes, "at": r.created_at} for r in service.mandate_history(session, p.workspace_id, mandate_id)]


# --- revue de registre -------------------------------------------------------------------------------
@router.get("/registry-reviews", response_model=list[RegistryReviewOut], tags=["mandates"])
def list_registry_reviews(p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return [RegistryReviewOut(institution_id=r.institution_id, status=r.status, reviewer=r.reviewer, note=r.note,
                              reviewed_at=r.reviewed_at) for r in service.list_registry_reviews(session, p.workspace_id)]


@router.get("/institutions/{institution_id}/registry-review", response_model=RegistryReviewOut, tags=["mandates"])
def get_registry_review(institution_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    from ..workspaces import service as ws
    ws.get_institution(session, p.workspace_id, institution_id)
    return RegistryReviewOut(institution_id=institution_id, status=service.registry_state(session, p.workspace_id, institution_id))


@router.put("/institutions/{institution_id}/registry-review", response_model=RegistryReviewOut, tags=["mandates"])
def put_registry_review(institution_id: str, body: RegistryReviewIn, p: Principal = Depends(Write),
                        session: Session = Depends(get_session)):
    r = service.set_registry_review(session, p.workspace_id, institution_id, body.status, p, body.note)
    return RegistryReviewOut(institution_id=institution_id, status=r.status, reviewer=r.reviewer, note=r.note,
                             reviewed_at=r.reviewed_at)
