from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..core.auth import Principal, require_role
from ..core.context import AppContext, get_ctx, get_session
from ..core.errors import NotFound
from . import reform, service
from .schemas import (
    GapDetail,
    GapOut,
    GapPatch,
    GapReferenceIn,
    GapReferencePatch,
    ImprovementIn,
    ImprovementOut,
    ImprovementPatch,
    InternationalReferenceIn,
    InternationalReferenceOut,
    ReferenceOut,
    ReviewIn,
    ReviewOut,
)

router = APIRouter()
Read = require_role("facilitator", "auditor", "observer")
Facilitator = require_role("facilitator")


def _gap_out(session: Session, g: Any, ref: dict | None = None) -> GapOut:
    out = GapOut.model_validate(g)
    out.section = service.section(g)
    out.reference_status = ref if ref is not None else service.reference_status(session, g.id)
    return out


def _guard(ctx: AppContext, session: Session, p: Principal, exercise_id: str) -> None:
    guard = ctx.services.get("exercise_guard")
    if guard is not None:
        guard(session, p, exercise_id)  # NotFound/Forbidden hors espace


@router.get("/gaps", response_model=list[GapOut], tags=["gaps"])
def list_gaps(exercise: str | None = None, country: str | None = None, institution: str | None = None,
              domain: str | None = None, category: str | None = None, code: str | None = None,
              severity: int | None = Query(default=None, ge=1, le=3), status: str | None = None, basis: str | None = None,
              confidence: str | None = None, origin: str | None = None, include_stale: bool = False,
              p: Principal = Depends(Read), session: Session = Depends(get_session)):
    rows = service.list_gaps(session, p.workspace_id, p.role, exercise=exercise, country=country, institution=institution,
                             domain=domain, category=category, code=code, severity=severity, status=status, basis=basis,
                             confidence=confidence, origin=origin, include_stale=include_stale)
    refs = service.reference_statuses(session, [g.id for g in rows])
    return [_gap_out(session, g, refs[g.id]) for g in rows]


@router.get("/gaps/compare", tags=["gaps"])
def compare(a: str, b: str, p: Principal = Depends(Read), session: Session = Depends(get_session),
            ctx: AppContext = Depends(get_ctx)):
    for ex in (a, b):
        _guard(ctx, session, p, ex)
    return service.compare(session, p.workspace_id, p.role, a, b)


@router.get("/gaps/{gap_id}", response_model=GapDetail, tags=["gaps"])
def get_gap(gap_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    g = service.get_gap(session, p.workspace_id, gap_id, p.role)
    parts = service.gap_detail_parts(session, g)
    return GapDetail(**_gap_out(session, g).model_dump(), **{k: v for k, v in parts.items()})


@router.post("/gaps/{gap_id}/reviews", response_model=ReviewOut, status_code=201, tags=["gaps"])
def post_review(gap_id: str, body: ReviewIn, p: Principal = Depends(Facilitator), session: Session = Depends(get_session)):
    return ReviewOut.model_validate(service.review(session, p.workspace_id, gap_id, p, body))


@router.patch("/gaps/{gap_id}", response_model=GapOut, tags=["gaps"])
def patch_gap(gap_id: str, body: GapPatch, p: Principal = Depends(Facilitator), session: Session = Depends(get_session)):
    return _gap_out(session, service.patch_gap(session, p.workspace_id, gap_id, p, body))


@router.post("/gaps/{gap_id}/references", response_model=ReferenceOut, status_code=201, tags=["gaps"])
def link_reference(gap_id: str, body: GapReferenceIn, p: Principal = Depends(Facilitator), session: Session = Depends(get_session)):
    return ReferenceOut.model_validate(service.link_reference(session, p.workspace_id, gap_id, body.reference_id, body.fit_note, body.fit_score))


@router.get("/gaps/{gap_id}/reference-suggestions", tags=["gaps"])
def suggestions(gap_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return service.suggest_references(session, p.workspace_id, gap_id)


@router.patch("/gap-references/{ref_id}", response_model=ReferenceOut, tags=["gaps"])
def patch_gap_reference(ref_id: str, body: GapReferencePatch, p: Principal = Depends(Facilitator),
                        session: Session = Depends(get_session)):
    return ReferenceOut.model_validate(service.patch_gap_reference(session, p.workspace_id, ref_id,
                                                                   **body.model_dump(exclude_unset=True)))


@router.get("/international-references", response_model=list[InternationalReferenceOut], tags=["gaps"])
def list_international_references(jurisdiction: str | None = None, gap_code: str | None = None, domain: str | None = None,
                                  p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return service.list_references(session, p.workspace_id, jurisdiction=jurisdiction, gap_code=gap_code, domain=domain)


@router.post("/international-references", response_model=InternationalReferenceOut, status_code=201, tags=["gaps"])
def create_international_reference(body: InternationalReferenceIn, p: Principal = Depends(Facilitator),
                                   session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)):
    return service.create_reference(session, p.workspace_id, body, ctx.services.get("knowledge"))


@router.get("/gaps/{gap_id}/improvement-actions", response_model=list[ImprovementOut], tags=["gaps"])
def list_improvements(gap_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return service.list_improvements(session, p.workspace_id, gap_id)


@router.post("/gaps/{gap_id}/improvement-actions", response_model=ImprovementOut, status_code=201, tags=["gaps"])
def add_improvement(gap_id: str, body: ImprovementIn, p: Principal = Depends(Facilitator), session: Session = Depends(get_session)):
    return service.add_improvement(session, p.workspace_id, gap_id, body)


@router.patch("/improvement-actions/{action_id}", response_model=ImprovementOut, tags=["gaps"])
def patch_improvement(action_id: str, body: ImprovementPatch, p: Principal = Depends(Facilitator),
                      session: Session = Depends(get_session)):
    return service.patch_improvement(session, p.workspace_id, action_id, body)


@router.post("/exercises/{exercise_id}/detect-gaps", tags=["gaps"])
def detect_gaps(exercise_id: str, p: Principal = Depends(Facilitator), session: Session = Depends(get_session),
                ctx: AppContext = Depends(get_ctx)):
    """Détection finale, idempotente : relancer ne crée aucun doublon et ne touche pas aux revues humaines."""
    _guard(ctx, session, p, exercise_id)
    engine = ctx.services.get("gap_engine")
    if engine is None:
        raise NotFound("moteur de lacunes indisponible")
    snapshot, _sha = engine.load_snapshot(session, exercise_id)
    if snapshot.get("workspace_id") != p.workspace_id:
        raise NotFound("exercice introuvable")
    return engine.run(session, exercise_id, final=True)


# --- projets de texte vérifiables ------------------------------------------------------------------
@router.post("/gaps/{gap_id}/reform-drafts", status_code=201, tags=["gaps"])
def create_reform_draft(gap_id: str, p: Principal = Depends(Facilitator), session: Session = Depends(get_session),
                        ctx: AppContext = Depends(get_ctx)):
    """L'IA rédige un article qui comble la lacune ; citations vérifiées ; ancré dans le registre (empreinte SHA-256)."""
    g = service.get_gap(session, p.workspace_id, gap_id, p.role)
    _guard(ctx, session, p, g.exercise_id)
    return reform.draft_out(reform.generate(ctx, session, p.workspace_id, gap_id, p.role))


@router.get("/gaps/{gap_id}/reform-drafts", tags=["gaps"])
def list_reform_drafts(gap_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session),
                       ctx: AppContext = Depends(get_ctx)):
    from sqlalchemy import select

    from .models import ReformDraft
    g = service.get_gap(session, p.workspace_id, gap_id, p.role)
    _guard(ctx, session, p, g.exercise_id)
    rows = session.scalars(select(ReformDraft).where(ReformDraft.workspace_id == p.workspace_id, ReformDraft.gap_id == g.id)
                           .order_by(ReformDraft.created_at.desc()))
    return [reform.draft_out(d) for d in rows]


@router.get("/verify/reform/{sha256}", tags=["gaps"])
def verify_reform_draft(sha256: str, session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)):
    """PUBLIC (sans jeton) : qui détient le document imprimé (donc son empreinte) peut vérifier son authenticité,
    son intégrité et celle du registre de l'exercice. Rien d'autre n'est exposé."""
    if len(sha256) != 64 or any(c not in "0123456789abcdef" for c in sha256):
        raise NotFound("empreinte inconnue")
    return reform.verify(ctx, session, sha256)
