"""Cas d'usage du module mandates (registre de mandats, catalogue d'actions, revue de registre).

Intégrité : un mandat n'est ACTIF que s'il est `validated` ET qu'au moins une source résout vers un chunk réel
(`knowledge.get_chunk`). Sans résolveur de chunks (service absent), aucune source n'est vérifiable : tout est inactif.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.db import utcnow
from ..core.errors import Conflict, NotFound, Unprocessable
from ..workspaces import service as ws_service
from .models import ActionItem, Mandate, MandateReview, MandateSource, RegistryReview
from .schemas import ActionCreate, ActionUpdate, MandateCreate, MandateUpdate, SourceIn

ChunkResolver = Callable[[Session, str], "dict[str, Any] | None"]
_chunk_resolver: ChunkResolver | None = None
REGISTRY_STATES = ("unreviewed", "partial", "reviewed_complete")
PRESENTATION = {"referential": "attente documentée", "scenario_author": "attente fixée par le concepteur du scénario",
                "agent_proposed": "proposée par un agent (non vérifiée)"}


def set_chunk_resolver(fn: ChunkResolver | None) -> None:
    global _chunk_resolver
    _chunk_resolver = fn


def _resolve_chunk(session: Session, chunk_id: str) -> dict[str, Any] | None:
    if _chunk_resolver is None:
        return None
    try:
        return _chunk_resolver(session, chunk_id)
    except Exception:  # un résolveur défaillant = source non vérifiable = inactif (échec fermé)
        return None


# --------------------------------------------------------------------------- actions
def _check_action(derivation: str, justification: str | None) -> None:
    if derivation in ("scenario_author", "agent_proposed") and not (justification or "").strip():
        raise Unprocessable("une justification est obligatoire pour une action dérivée de l'auteur ou d'un agent",
                            code="action.justification_required")


def action_dict(a: ActionItem) -> dict[str, Any]:
    pres = PRESENTATION[a.derivation]
    if a.derivation == "referential" and not (a.reference_note or "").strip():
        pres = "référentiel (référence à citer)"
    return {"id": a.id, "code": a.code, "label": a.label, "domain": a.domain, "derivation": a.derivation,
            "justification": a.justification, "reference_note": a.reference_note, "presentation": pres}


def _get_action(session: Session, workspace_id: str, action_id: str) -> ActionItem:
    row = session.scalar(select(ActionItem).where(ActionItem.id == action_id, ActionItem.workspace_id == workspace_id))
    if row is None:
        raise NotFound("action introuvable")
    return row


def create_action(session: Session, workspace_id: str, data: ActionCreate) -> ActionItem:
    _check_action(data.derivation, data.justification)
    if action_exists(session, workspace_id, data.code):
        raise Conflict("une action de ce code existe déjà", code="action.duplicate")
    row = ActionItem(workspace_id=workspace_id, **data.model_dump())
    session.add(row)
    session.flush()
    return row


def update_action(session: Session, workspace_id: str, action_id: str, data: ActionUpdate) -> ActionItem:
    row = _get_action(session, workspace_id, action_id)
    changes = data.model_dump(exclude_unset=True)
    deriv = changes.get("derivation", row.derivation)
    _check_action(deriv, changes.get("justification", row.justification))
    for k, v in changes.items():
        setattr(row, k, v)
    session.flush()
    return row


def get_action(session: Session, workspace_id: str, action_id: str) -> ActionItem:
    return _get_action(session, workspace_id, action_id)


def action_exists(session: Session, workspace_id: str, code: str) -> bool:
    return session.scalar(select(ActionItem.id).where(ActionItem.workspace_id == workspace_id,
                                                      ActionItem.code == code)) is not None


def list_actions(session: Session, workspace_id: str) -> list[dict[str, Any]]:
    rows = session.scalars(select(ActionItem).where(ActionItem.workspace_id == workspace_id).order_by(ActionItem.code))
    return [action_dict(a) for a in rows]


# --------------------------------------------------------------------------- mandats
def _actor(p: Any) -> str:
    return (getattr(p, "label", None) or getattr(p, "token_id", None) or "system") if p is not None else "system"


def _log(session: Session, workspace_id: str, mandate_id: str, actor: str, action: str, frm: str | None, to: str | None,
         note: str | None = None, changes: dict | None = None) -> None:
    session.add(MandateReview(workspace_id=workspace_id, mandate_id=mandate_id, actor=actor, action=action,
                              from_status=frm, to_status=to, note=note, changes=changes))


def _sources(session: Session, mandate_id: str) -> list[MandateSource]:
    return list(session.scalars(select(MandateSource).where(MandateSource.mandate_id == mandate_id)
                                .order_by(MandateSource.created_at, MandateSource.id)))


def _norm(s: str) -> str:
    return " ".join(s.split()).lower()


def _make_source(session: Session, mandate_id: str, data: SourceIn) -> MandateSource:
    chunk = _resolve_chunk(session, data.chunk_id)
    if chunk is None:
        raise Unprocessable("la source ne résout vers aucun chunk réel", code="mandate.source_unresolved",
                            details={"chunk_id": data.chunk_id})
    dv = chunk.get("document_version_id")
    if dv and dv != data.document_version_id:
        raise Unprocessable("le chunk n'appartient pas à la version de document indiquée",
                            code="mandate.source_mismatch", details={"chunk_id": data.chunk_id})
    found = None
    if data.quote and chunk.get("text"):
        found = _norm(data.quote) in _norm(str(chunk["text"]))
    return MandateSource(mandate_id=mandate_id, document_version_id=data.document_version_id, chunk_id=data.chunk_id,
                         article=data.article or chunk.get("article"), page=data.page, quote=data.quote,
                         quote_sha256=hashlib.sha256(data.quote.encode()).hexdigest() if data.quote else None,
                         quote_found=found)


def _get(session: Session, workspace_id: str, mandate_id: str) -> Mandate:
    row = session.scalar(select(Mandate).where(Mandate.id == mandate_id, Mandate.workspace_id == workspace_id))
    if row is None:
        raise NotFound("mandat introuvable")
    return row


def _check_refs(session: Session, workspace_id: str, data: dict[str, Any]) -> None:
    if data.get("institution_id"):
        ws_service.get_institution(session, workspace_id, data["institution_id"])  # 404 si autre espace
    if data.get("action_code") is not None and not action_exists(session, workspace_id, data["action_code"]):
        raise Unprocessable("action absente du catalogue", code="mandate.unknown_action",
                            details={"action_code": data["action_code"]})
    for k in ("depends_on_id", "conflicts_with_id"):
        if data.get(k):
            _get(session, workspace_id, data[k])


def create_mandate(session: Session, workspace_id: str, data: MandateCreate, principal: Any = None, *,
                   origin: str = "manual", import_ref: str | None = None, notes: str | None = None,
                   validation: str = "proposed") -> Mandate:
    payload = data.model_dump(exclude={"sources"})
    _check_refs(session, workspace_id, payload)
    row = Mandate(workspace_id=workspace_id, **payload, origin=origin, import_ref=import_ref, notes=notes,
                  validation=validation, created_by=_actor(principal))
    session.add(row)
    session.flush()
    for s in data.sources:
        session.add(_make_source(session, row.id, s))
    _log(session, workspace_id, row.id, _actor(principal), "create", None, row.validation)
    session.flush()
    return row


def add_source(session: Session, workspace_id: str, mandate_id: str, data: SourceIn, principal: Any = None) -> MandateSource:
    m = _get(session, workspace_id, mandate_id)
    if any(x.chunk_id == data.chunk_id for x in _sources(session, m.id)):
        # un double clic ou un nouvel essai après une réponse perdue ne doit pas lier deux fois le même passage au même mandat
        raise Conflict("ce passage est déjà une source de ce mandat", code="mandate.source_duplicate",
                       details={"chunk_id": data.chunk_id})
    src = _make_source(session, m.id, data)
    session.add(src)
    _log(session, workspace_id, m.id, _actor(principal), "update", m.validation, m.validation,
         changes={"source_added": data.chunk_id})
    session.flush()
    return src


def remove_source(session: Session, workspace_id: str, mandate_id: str, source_id: str, principal: Any = None) -> None:
    m = _get(session, workspace_id, mandate_id)
    src = session.scalar(select(MandateSource).where(MandateSource.id == source_id, MandateSource.mandate_id == m.id))
    if src is None:
        raise NotFound("source introuvable")
    session.delete(src)
    _log(session, workspace_id, m.id, _actor(principal), "update", m.validation, m.validation,
         changes={"source_removed": src.chunk_id})
    session.flush()


def update_mandate(session: Session, workspace_id: str, mandate_id: str, data: MandateUpdate, principal: Any = None,
                   *, action: str = "update") -> Mandate:
    row = _get(session, workspace_id, mandate_id)
    changes = data.model_dump(exclude_unset=True)
    _check_refs(session, workspace_id, changes)
    diff = {k: {"from": getattr(row, k), "to": v} for k, v in changes.items() if getattr(row, k) != v}
    for k, v in changes.items():
        setattr(row, k, v)
    if diff and row.validation == "validated" and action == "update":
        row.validation = "proposed"  # toute modification d'un mandat validé exige une nouvelle validation
        diff["validation"] = {"from": "validated", "to": "proposed"}
    if diff:
        _log(session, workspace_id, row.id, _actor(principal), action, None, row.validation, changes=diff)
    session.flush()
    return row


def get_mandate(session: Session, workspace_id: str, mandate_id: str) -> Mandate:
    return _get(session, workspace_id, mandate_id)


def list_mandates(session: Session, workspace_id: str, *, institution_id: str | None = None, action_code: str | None = None,
                  kind: str | None = None, validation: str | None = None) -> list[Mandate]:
    q = select(Mandate).where(Mandate.workspace_id == workspace_id).order_by(Mandate.created_at, Mandate.id)
    for col, val in ((Mandate.institution_id, institution_id), (Mandate.action_code, action_code),
                     (Mandate.kind, kind), (Mandate.validation, validation)):
        if val:
            q = q.where(col == val)
    return list(session.scalars(q))


def delete_mandate(session: Session, workspace_id: str, mandate_id: str) -> None:
    row = _get(session, workspace_id, mandate_id)
    if row.validation == "validated":
        raise Conflict("un mandat validé ne se supprime pas : le rejeter", code="mandate.delete_validated")
    for ref in session.scalars(select(Mandate).where(Mandate.workspace_id == workspace_id).where(
            (Mandate.depends_on_id == row.id) | (Mandate.conflicts_with_id == row.id))):
        ref.depends_on_id = None if ref.depends_on_id == row.id else ref.depends_on_id
        ref.conflicts_with_id = None if ref.conflicts_with_id == row.id else ref.conflicts_with_id
    for s in _sources(session, row.id):
        session.delete(s)
    session.flush()
    session.delete(row)
    session.flush()


def source_status(session: Session, mandate: Mandate, sources: list[MandateSource] | None = None) -> tuple[bool, str | None]:
    """(actif ?, raison d'inactivité)."""
    if mandate.validation != "validated":
        return False, f"mandat {mandate.validation}"
    srcs = sources if sources is not None else _sources(session, mandate.id)
    if not srcs:
        return False, "aucune source"
    if any(_resolve_chunk(session, s.chunk_id) is not None for s in srcs):
        return True, None
    return False, "source introuvable (chunk non résolu)"


def validate_mandate(session: Session, workspace_id: str, mandate_id: str, principal: Any = None, *, note: str | None = None,
                     corrections: MandateUpdate | None = None) -> Mandate:
    row = _get(session, workspace_id, mandate_id)
    if corrections is not None and corrections.model_dump(exclude_unset=True):
        update_mandate(session, workspace_id, mandate_id, corrections, principal, action="correct")
    srcs = _sources(session, row.id)
    if not any(_resolve_chunk(session, s.chunk_id) is not None for s in srcs):
        raise Unprocessable("validation impossible : aucune source ne résout vers un chunk réel",
                            code="mandate.validate.no_source")
    frm = row.validation
    row.validation = "validated"
    _log(session, workspace_id, row.id, _actor(principal), "validate", frm, "validated", note)
    session.flush()
    return row


def reject_mandate(session: Session, workspace_id: str, mandate_id: str, principal: Any = None, *, note: str) -> Mandate:
    row = _get(session, workspace_id, mandate_id)
    if not (note or "").strip():
        raise Unprocessable("motif de rejet obligatoire", code="mandate.reject.reason_required")
    frm = row.validation
    row.validation = "rejected"
    _log(session, workspace_id, row.id, _actor(principal), "reject", frm, "rejected", note)
    session.flush()
    return row


def mandate_history(session: Session, workspace_id: str, mandate_id: str) -> list[MandateReview]:
    _get(session, workspace_id, mandate_id)
    return list(session.scalars(select(MandateReview).where(MandateReview.mandate_id == mandate_id)
                                .order_by(MandateReview.created_at, MandateReview.id)))


# --------------------------------------------------------------------------- revue de registre
def registry_state(session: Session, workspace_id: str, institution_id: str) -> str:
    row = session.scalar(select(RegistryReview.status).where(RegistryReview.workspace_id == workspace_id,
                                                             RegistryReview.institution_id == institution_id))
    return row or "unreviewed"


def set_registry_review(session: Session, workspace_id: str, institution_id: str, status: str, principal: Any = None,
                        note: str | None = None) -> RegistryReview:
    ws_service.get_institution(session, workspace_id, institution_id)
    if status not in REGISTRY_STATES:
        raise Unprocessable("état de registre inconnu", code="registry.invalid_status")
    row = session.scalar(select(RegistryReview).where(RegistryReview.workspace_id == workspace_id,
                                                      RegistryReview.institution_id == institution_id))
    if row is None:
        row = RegistryReview(workspace_id=workspace_id, institution_id=institution_id)
        session.add(row)
    row.status, row.note, row.reviewer, row.reviewed_at = status, note, _actor(principal), utcnow()
    session.flush()
    return row


def list_registry_reviews(session: Session, workspace_id: str) -> list[RegistryReview]:
    return list(session.scalars(select(RegistryReview).where(RegistryReview.workspace_id == workspace_id)))


# --------------------------------------------------------------------------- export (contrat)
def export_active_mandates(session: Session, workspace_id: str, institution_ids: list[str] | set[str] | None,
                           document_version_ids: set[str] | list[str] | frozenset[str]) -> list[dict[str, Any]]:
    """Mandats validés dont au moins une source (chunk résolu) appartient aux versions de documents de l'exercice.

    C'est ce filtre qui rend l'ablation de corpus possible : retirer un document retire les mandats qu'il fonde.
    """
    docs = set(document_version_ids)
    q = select(Mandate).where(Mandate.workspace_id == workspace_id, Mandate.validation == "validated")
    if institution_ids is not None:
        q = q.where(Mandate.institution_id.in_(list(institution_ids)))
    out = []
    for m in session.scalars(q.order_by(Mandate.created_at, Mandate.id)):
        srcs = []
        for s in _sources(session, m.id):
            if s.document_version_id in docs and _resolve_chunk(session, s.chunk_id) is not None:
                srcs.append({"document_version_id": s.document_version_id, "chunk_id": s.chunk_id,
                             "article": s.article, "page": s.page, "quote": s.quote})
        if not srcs:
            continue
        out.append({"id": m.id, "institution_id": m.institution_id, "kind": m.kind, "action_code": m.action_code,
                    "description": m.description, "procedure_status": m.procedure_status,
                    "has_deadline": m.has_deadline, "dependency_text": m.dependency_text,
                    "dependency_ready": m.dependency_ready, "depends_on_id": m.depends_on_id,
                    "conflicts_with_id": m.conflicts_with_id, "evidence_tag": m.evidence_tag, "validation": "validated",
                    "sources": srcs})
    return out
