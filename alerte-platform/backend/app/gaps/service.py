"""Lecture, revue humaine (ajout seul), références, plan d'amélioration, comparaison d'exercices."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.errors import Conflict, NotFound, Unprocessable
from ..workspaces import service as ws_service
from .models import (
    Gap,
    GapEvidence,
    GapReference,
    GapReview,
    ImprovementAction,
    InternationalReference,
    NegativeSearch,
)
from .negative_search import NegativeResult
from .schemas import GapPatch, ImprovementIn, ImprovementPatch, InternationalReferenceIn, ReviewIn

TRANSITIONS = {"confirm": ({"proposed", "disputed"}, "confirmed"), "dispute": ({"proposed", "confirmed"}, "disputed"),
               "reject": ({"proposed", "disputed"}, "rejected"), "reopen": ({"rejected"}, "proposed")}
REASON_REQUIRED = {"dispute", "reject"}
MIN_JURISDICTIONS = 2


def actor_of(p: Any) -> str:
    return getattr(p, "label", None) or getattr(p, "token_id", None) or "system"


def section(g: Gap) -> str:
    return "hypotheses" if g.evidence_basis == "hypothesis" else "findings"


def visible_to(g: Gap, role: str) -> bool:
    """Facilitateur/auditeur/propriétaire : tout. Observateur : seulement les constats CONFIRMÉS (publics), jamais d'hypothèses."""
    if role in ("owner", "facilitator", "auditor"):
        return True
    return g.validation_status == "confirmed" and g.evidence_basis != "hypothesis"


# --------------------------------------------------------------------------- lecture
def get_gap(session: Session, workspace_id: str, gap_id: str, role: str = "owner") -> Gap:
    g = session.scalar(select(Gap).where(Gap.id == gap_id, Gap.workspace_id == workspace_id))
    if g is None or not visible_to(g, role):
        raise NotFound("lacune introuvable")
    return g


def reference_status(session: Session, gap_id: str) -> dict[str, Any]:
    rows = session.execute(select(GapReference.status, InternationalReference.jurisdiction)
                           .join(InternationalReference, InternationalReference.id == GapReference.reference_id)
                           .where(GapReference.gap_id == gap_id, GapReference.status != "rejected")).all()
    juris = sorted({j.strip().lower() for _s, j in rows})
    ok = len(juris) >= MIN_JURISDICTIONS
    return {"status": "sufficient" if ok else "insufficient_sources", "jurisdictions": juris, "count": len(juris),
            "accepted": sum(1 for s, _j in rows if s == "accepted"),
            "message": None if ok else f"sources internationales insuffisantes : {len(juris)} trouvée(s) (minimum {MIN_JURISDICTIONS} juridictions)"}


def list_gaps(session: Session, workspace_id: str, role: str, *, exercise: str | None = None, country: str | None = None,
              institution: str | None = None, domain: str | None = None, category: str | None = None, code: str | None = None,
              severity: int | None = None, status: str | None = None, basis: str | None = None, confidence: str | None = None,
              origin: str | None = None, include_stale: bool = False) -> list[Gap]:
    q = select(Gap).where(Gap.workspace_id == workspace_id)
    for col, v in ((Gap.exercise_id, exercise), (Gap.domain, domain), (Gap.category, category), (Gap.code, code),
                   (Gap.severity, severity), (Gap.validation_status, status), (Gap.evidence_basis, basis),
                   (Gap.confidence, confidence), (Gap.origin, origin)):
        if v is not None:
            q = q.where(col == v)
    if not include_stale:
        q = q.where(Gap.is_current.is_(True))
    rows = [g for g in session.scalars(q.order_by(Gap.severity.desc(), Gap.code, Gap.created_at, Gap.id)) if visible_to(g, role)]
    if institution:
        rows = [g for g in rows if institution in (g.institution_ids or [])]
    if country:
        ids = {i.id for i in ws_service.list_institutions(session, workspace_id, country_id=country, include_archived=True)}
        rows = [g for g in rows if ids & set(g.institution_ids or [])]
    return rows


def gap_detail_parts(session: Session, g: Gap) -> dict[str, Any]:
    ev = list(session.scalars(select(GapEvidence).where(GapEvidence.gap_id == g.id).order_by(GapEvidence.created_at, GapEvidence.id)))
    neg_ids = [e.ref.get("negative_search_id") for e in ev if e.kind == "negative_search" and e.ref.get("negative_search_id")]
    negs = []
    for n in session.scalars(select(NegativeSearch).where(NegativeSearch.id.in_(neg_ids))) if neg_ids else []:
        nr = NegativeResult(n.action_code, n.queries, n.languages, n.kb_ids, n.corpus_documents, n.corpus_coverage,
                            n.coverage_missing, n.top_hits, n.verdict)
        negs.append({"id": n.id, "action_code": n.action_code, "kb_ids": n.kb_ids, "queries": n.queries, "languages": n.languages,
                     "corpus_documents": n.corpus_documents, "corpus_coverage": n.corpus_coverage,
                     "coverage_missing": n.coverage_missing, "top_hits": n.top_hits, "verdict": n.verdict, "run_at": n.run_at,
                     "statement": nr.statement()})
    refs = []
    for r, lib in session.execute(select(GapReference, InternationalReference)
                                  .join(InternationalReference, InternationalReference.id == GapReference.reference_id)
                                  .where(GapReference.gap_id == g.id)):
        refs.append({"id": r.id, "gap_id": r.gap_id, "reference_id": r.reference_id, "fit_note": r.fit_note,
                     "fit_score": r.fit_score, "status": r.status,
                     "reference": {"jurisdiction": lib.jurisdiction, "instrument": lib.instrument, "article": lib.article,
                                   "summary": lib.summary, "binding": lib.binding, "chunk_id": lib.chunk_id, "url": lib.url,
                                   "evidence_tag": lib.evidence_tag}})
    reviews = list(session.scalars(select(GapReview).where(GapReview.gap_id == g.id).order_by(GapReview.created_at, GapReview.id)))
    actions = [{"id": a.id, "owner_institution_id": a.owner_institution_id, "description": a.description,
                "due_date": a.due_date, "status": a.status, "kpi": a.kpi}
               for a in session.scalars(select(ImprovementAction).where(ImprovementAction.gap_id == g.id))]
    return {"evidence": ev, "negative_searches": negs, "references": refs, "reviews": reviews, "improvement_actions": actions}


# --------------------------------------------------------------------------- revue humaine
def review(session: Session, workspace_id: str, gap_id: str, principal: Any, body: ReviewIn) -> GapReview:
    g = get_gap(session, workspace_id, gap_id)
    comment = (body.comment or "").strip() or None
    if body.action in REASON_REQUIRED and not comment:
        raise Unprocessable("un motif est obligatoire pour contester ou rejeter", code="gap.review.reason_required")
    if body.action == "comment":
        if not comment:
            raise Unprocessable("commentaire vide", code="gap.review.reason_required")
        to = g.validation_status
    else:
        allowed, to = TRANSITIONS[body.action]
        if g.validation_status not in allowed:
            raise Conflict(f"transition interdite : {g.validation_status} -> {to}", code="gap.review.invalid_transition")
    row = GapReview(gap_id=g.id, reviewer=actor_of(principal), action=body.action, from_status=g.validation_status,
                    to_status=to, reality_label=body.reality_label, blind=body.blind, comment=comment)
    session.add(row)
    g.validation_status = to
    session.flush()
    return row


def patch_gap(session: Session, workspace_id: str, gap_id: str, principal: Any, body: GapPatch) -> Gap:
    g = get_gap(session, workspace_id, gap_id)
    changes = body.model_dump(exclude_unset=True, exclude={"reason"})
    diff = {k: {"from": getattr(g, k), "to": v} for k, v in changes.items() if getattr(g, k) != v}
    if not diff:
        return g
    reason = (body.reason or "").strip() or None
    if "severity" in diff and not reason:
        raise Unprocessable("un motif est obligatoire pour modifier la gravité", code="gap.review.reason_required")
    for k, d in diff.items():
        setattr(g, k, d["to"])
    g.edited_fields = sorted(set(g.edited_fields or []) | set(diff))
    session.add(GapReview(gap_id=g.id, reviewer=actor_of(principal), action="edit", from_status=g.validation_status,
                          to_status=g.validation_status, comment=reason, changes=diff))
    session.flush()
    return g


# --------------------------------------------------------------------------- références internationales
def create_reference(session: Session, workspace_id: str, data: InternationalReferenceIn, knowledge: Any) -> InternationalReference:
    """I4 : aucune entrée sans source — un chunk d'une KB `global_practices`, ou une URL marquée `summary`."""
    tag = data.evidence_tag
    if data.chunk_id:
        chunk = knowledge.get_chunk(session, data.chunk_id) if knowledge is not None else None
        if chunk is None:
            raise Unprocessable("la référence doit pointer vers un chunk existant", code="reference.chunk_unresolved")
        if chunk.get("kb_id") and hasattr(knowledge, "kb_overview"):
            kind = (knowledge.kb_overview(session, workspace_id, chunk["kb_id"]) or {}).get("kind")
            if kind is not None and kind != "global_practices":
                raise Unprocessable("le chunk doit appartenir à une KB « global_practices »", code="reference.not_global_practices")
        dv = chunk.get("document_version_id") or data.document_version_id
        tag = tag or "documented"
        row = InternationalReference(workspace_id=workspace_id, document_version_id=dv, evidence_tag=tag,
                                     **data.model_dump(exclude={"document_version_id", "evidence_tag"}))
    elif data.url:
        if tag != "summary":
            raise Unprocessable("une référence par URL doit être marquée evidence_tag=summary", code="reference.url_needs_summary_tag")
        row = InternationalReference(workspace_id=workspace_id, evidence_tag="summary",
                                     **data.model_dump(exclude={"evidence_tag"}))
    else:
        raise Unprocessable("référence sans source : chunk d'une KB global_practices ou URL (summary) requis",
                            code="reference.source_required")
    session.add(row)
    session.flush()
    return row


def list_references(session: Session, workspace_id: str, *, jurisdiction: str | None = None, gap_code: str | None = None,
                    domain: str | None = None) -> list[InternationalReference]:
    rows = list(session.scalars(select(InternationalReference).where(InternationalReference.workspace_id == workspace_id)
                                .order_by(InternationalReference.jurisdiction, InternationalReference.instrument)))
    return [r for r in rows if (not jurisdiction or r.jurisdiction.lower() == jurisdiction.lower())
            and (not gap_code or gap_code in (r.gap_codes or [])) and (not domain or domain in (r.domains or []))]


def link_reference(session: Session, workspace_id: str, gap_id: str, reference_id: str, fit_note: str | None,
                   fit_score: float | None) -> GapReference:
    g = get_gap(session, workspace_id, gap_id)
    ref = session.scalar(select(InternationalReference).where(InternationalReference.id == reference_id,
                                                              InternationalReference.workspace_id == workspace_id))
    if ref is None:
        raise NotFound("référence introuvable")
    if session.scalar(select(GapReference.id).where(GapReference.gap_id == g.id, GapReference.reference_id == ref.id)):
        raise Conflict("référence déjà associée", code="gap.reference.duplicate")
    row = GapReference(gap_id=g.id, reference_id=ref.id, fit_note=fit_note, fit_score=fit_score)
    session.add(row)
    session.flush()
    return row


def patch_gap_reference(session: Session, workspace_id: str, ref_id: str, **changes: Any) -> GapReference:
    row = session.scalar(select(GapReference).join(Gap, Gap.id == GapReference.gap_id)
                         .where(GapReference.id == ref_id, Gap.workspace_id == workspace_id))
    if row is None:
        raise NotFound("association introuvable")
    for k, v in changes.items():
        if v is not None:
            setattr(row, k, v)
    session.flush()
    return row


def suggest_references(session: Session, workspace_id: str, gap_id: str) -> list[dict[str, Any]]:
    g = get_gap(session, workspace_id, gap_id)
    linked = set(session.scalars(select(GapReference.reference_id).where(GapReference.gap_id == g.id)))
    out = []
    for r in list_references(session, workspace_id):
        if r.id in linked:
            continue
        score = 0.5 * (g.code in (r.gap_codes or [])) + 0.5 * bool(g.domain and g.domain in (r.domains or []))
        if score > 0:
            out.append({"reference_id": r.id, "jurisdiction": r.jurisdiction, "instrument": r.instrument, "fit_score": score})
    return sorted(out, key=lambda x: (-x["fit_score"], x["jurisdiction"]))


# --------------------------------------------------------------------------- plan d'amélioration
def add_improvement(session: Session, workspace_id: str, gap_id: str, data: ImprovementIn) -> ImprovementAction:
    g = get_gap(session, workspace_id, gap_id)
    if data.owner_institution_id:
        ws_service.get_institution(session, workspace_id, data.owner_institution_id)
    row = ImprovementAction(workspace_id=workspace_id, gap_id=g.id, **data.model_dump())
    session.add(row)
    session.flush()
    return row


def list_improvements(session: Session, workspace_id: str, gap_id: str) -> list[ImprovementAction]:
    g = get_gap(session, workspace_id, gap_id)
    return list(session.scalars(select(ImprovementAction).where(ImprovementAction.gap_id == g.id).order_by(ImprovementAction.created_at)))


def patch_improvement(session: Session, workspace_id: str, action_id: str, data: ImprovementPatch) -> ImprovementAction:
    row = session.scalar(select(ImprovementAction).where(ImprovementAction.id == action_id,
                                                         ImprovementAction.workspace_id == workspace_id))
    if row is None:
        raise NotFound("action d'amélioration introuvable")
    ch = data.model_dump(exclude_unset=True)
    if ch.get("owner_institution_id"):
        ws_service.get_institution(session, workspace_id, ch["owner_institution_id"])
    for k, v in ch.items():
        setattr(row, k, v)
    session.flush()
    return row


# --------------------------------------------------------------------------- comparaison d'exercices
def compare(session: Session, workspace_id: str, role: str, a: str, b: str) -> dict[str, Any]:
    def load(ex: str) -> dict[str, Gap]:
        out: dict[str, Gap] = {}
        for g in list_gaps(session, workspace_id, role, exercise=ex):
            if g.validation_status == "rejected":
                continue
            if g.fingerprint not in out or g.severity > out[g.fingerprint].severity:
                out[g.fingerprint] = g
        return out

    ga, gb = load(a), load(b)

    def brief(g: Gap) -> dict[str, Any]:
        return {"id": g.id, "fingerprint": g.fingerprint, "code": g.code, "action_code": g.action_code, "title": g.title,
                "severity": g.severity, "validation_status": g.validation_status, "evidence_basis": g.evidence_basis}

    persistent = [{"a": brief(ga[f]), "b": brief(gb[f]), "severity_changed": ga[f].severity != gb[f].severity,
                   "status_changed": ga[f].validation_status != gb[f].validation_status} for f in ga if f in gb]
    return {"a": a, "b": b, "new": [brief(gb[f]) for f in gb if f not in ga], "persistent": persistent,
            "resolved": [brief(ga[f]) for f in ga if f not in gb],
            "summary": {"new": len([f for f in gb if f not in ga]), "persistent": len(persistent),
                        "resolved": len([f for f in ga if f not in gb])}}

