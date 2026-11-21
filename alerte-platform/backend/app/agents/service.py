"""Cas d'usage du module agents. Toute requête est filtrée par `workspace_id` (autre espace → 404)."""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..contracts import SearchScope, SeatContext
from ..core.db import utcnow
from ..core.errors import AppError, Conflict, NotFound, Unprocessable
from ..workspaces import service as ws_service
from .models import Agent, AgentKbGrant, ModelProfile
from .prompt import PROMPT_VERSION, build_system_prompt, estimate_tokens
from .providers import ProviderError, provider_for
from .schemas import (
    DEFAULT_LIMITS,
    AgentClone,
    AgentCreate,
    AgentUpdate,
    ModelProfileCreate,
    ModelProfileUpdate,
)

# --------------------------------------------------------------------------- profils


def get_profile(session: Session, workspace_id: str, profile_id: str) -> ModelProfile:
    row = session.scalar(select(ModelProfile).where(ModelProfile.id == profile_id, ModelProfile.workspace_id == workspace_id))
    if row is None:
        raise NotFound("profil de modèle introuvable", code="model_profile.not_found")
    return row


def list_profiles(session: Session, workspace_id: str) -> list[ModelProfile]:
    return list(session.scalars(select(ModelProfile).where(ModelProfile.workspace_id == workspace_id).order_by(ModelProfile.name)))


def _check_profile(provider: str, endpoint_ref: str | None, extra: dict | None) -> None:
    if provider == "cassette" and not (extra or {}).get("cassette"):
        raise Unprocessable("un profil cassette exige extra.cassette (nom de cassette)", code="model_profile.cassette_required")
    if endpoint_ref and "://" in endpoint_ref:  # défense en profondeur (le schéma l'interdit déjà)
        raise Unprocessable("endpoint_ref est un NOM de variable, pas une URL", code="model_profile.endpoint_not_a_name")


def create_profile(session: Session, workspace_id: str, data: ModelProfileCreate) -> ModelProfile:
    _check_profile(data.provider, data.endpoint_ref, data.extra)
    row = ModelProfile(workspace_id=workspace_id, **data.model_dump())
    session.add(row)
    try:
        session.flush()
    except IntegrityError as exc:
        raise Conflict("un profil de ce nom existe déjà", code="model_profile.duplicate") from exc
    return row


def update_profile(session: Session, workspace_id: str, profile_id: str, data: ModelProfileUpdate) -> ModelProfile:
    row = get_profile(session, workspace_id, profile_id)
    ch = data.model_dump(exclude_unset=True)
    _check_profile(ch.get("provider", row.provider), ch.get("endpoint_ref", row.endpoint_ref), ch.get("extra", row.extra))
    for k, v in ch.items():
        setattr(row, k, v)
    try:
        session.flush()
    except IntegrityError as exc:
        raise Conflict("un profil de ce nom existe déjà", code="model_profile.duplicate") from exc
    return row


def test_profile(row: ModelProfile, settings: Any, blobs: Any = None) -> dict[str, Any]:
    """Appel de test (readiness). N'expose jamais d'URL saisie ni de secret."""
    import time

    from ..contracts import LLMMessage
    out: dict[str, Any] = {"ok": False, "provider": row.provider, "model": row.model, "ai_involved": row.provider != "scripted",
                           "endpoint": None, "ms": 0, "error": None}
    t0 = time.monotonic()
    try:
        prov = provider_for(row, settings, blobs=blobs)
        kw = {"step_key": "profile-test"} if getattr(prov, "uses_step_key", False) else {}
        raw = prov.complete([LLMMessage("system", "Reply with the JSON object {\"ok\": true}."),
                             LLMMessage("user", "ping")], schema={"title": "AlerteProfileTest", "type": "object"},
                            temperature=0.0, max_tokens=32, **kw)
        out.update(ok=True, model=raw.model, endpoint=raw.endpoint, tokens_in=raw.tokens_in, tokens_out=raw.tokens_out)
        out["label"] = "SANS IA (scripted)" if row.provider == "scripted" else "model reachable"
    except ProviderError as exc:
        out["error"] = re.sub(r"https?://\S+", "<url>", str(exc))[:300]
    out["ms"] = int((time.monotonic() - t0) * 1000)
    return out


# --------------------------------------------------------------------------- agents


def get_agent(session: Session, workspace_id: str, agent_id: str) -> Agent:
    row = session.scalar(select(Agent).where(Agent.id == agent_id, Agent.workspace_id == workspace_id))
    if row is None:
        raise NotFound("agent introuvable", code="agent.not_found")
    return row


def list_agents(session: Session, workspace_id: str, *, institution_id: str | None = None, role_kind: str | None = None,
                include_archived: bool = False) -> list[Agent]:
    q = select(Agent).where(Agent.workspace_id == workspace_id).order_by(Agent.code)
    if institution_id:
        q = q.where(Agent.institution_id == institution_id)
    if role_kind:
        q = q.where(Agent.role_kind == role_kind)
    if not include_archived:
        q = q.where(Agent.archived_at.is_(None))
    return list(session.scalars(q))


def kb_grants(session: Session, workspace_id: str, agent_id: str) -> list[str]:
    get_agent(session, workspace_id, agent_id)
    return list(session.scalars(select(AgentKbGrant.kb_id).where(
        AgentKbGrant.agent_id == agent_id, AgentKbGrant.workspace_id == workspace_id).order_by(AgentKbGrant.kb_id)))


def _validate_refs(session: Session, workspace_id: str, institution_id: str | None, profile_id: str | None, role_kind: str) -> None:
    if institution_id:
        ws_service.get_institution(session, workspace_id, institution_id)
    elif role_kind != "legal_adviser":
        raise Unprocessable("institution_id est obligatoire sauf pour un conseiller juridique", code="agent.institution_required")
    if profile_id:
        get_profile(session, workspace_id, profile_id)


def create_agent(session: Session, workspace_id: str, data: AgentCreate) -> Agent:
    _validate_refs(session, workspace_id, data.institution_id, data.model_profile_id, data.role_kind)
    row = Agent(workspace_id=workspace_id, **data.model_dump())
    session.add(row)
    try:
        session.flush()
    except IntegrityError as exc:
        raise Conflict("un agent de ce code existe déjà dans l'espace", code="agent.duplicate") from exc
    return row


def update_agent(session: Session, workspace_id: str, agent_id: str, data: AgentUpdate) -> Agent:
    row = get_agent(session, workspace_id, agent_id)
    if row.archived_at is not None:
        raise Conflict("agent archivé : non modifiable", code="agent.archived")
    ch = data.model_dump(exclude_unset=True)
    _validate_refs(session, workspace_id, ch.get("institution_id", row.institution_id),
                   ch.get("model_profile_id", row.model_profile_id), ch.get("role_kind", row.role_kind))
    for k, v in ch.items():
        if v is None and k in ("code", "name", "tools", "limits", "role_kind", "mission", "instructions", "is_template"):
            continue
        setattr(row, k, v)
    try:
        session.flush()
    except IntegrityError as exc:
        raise Conflict("un agent de ce code existe déjà dans l'espace", code="agent.duplicate") from exc
    return row


def archive_agent(session: Session, workspace_id: str, agent_id: str) -> Agent:
    row = get_agent(session, workspace_id, agent_id)
    row.archived_at = row.archived_at or utcnow()
    return row


def delete_agent(session: Session, workspace_id: str, agent_id: str) -> None:
    row = get_agent(session, workspace_id, agent_id)
    if ws_service.is_referenced(session, "agent", agent_id):
        raise Conflict("cet agent est utilisé : archivez-le", code="agent.in_use")
    for g in session.scalars(select(AgentKbGrant).where(AgentKbGrant.agent_id == agent_id)):
        session.delete(g)
    session.flush()
    session.delete(row)


def clone_agent(session: Session, workspace_id: str, agent_id: str, data: AgentClone) -> Agent:
    src = get_agent(session, workspace_id, agent_id)
    inst = data.institution_id or src.institution_id
    existing = set(session.scalars(select(Agent.code).where(Agent.workspace_id == workspace_id)))
    code = data.code
    if not code:
        code, n = f"{src.code}-copy", 1
        while code in existing:
            n += 1
            code = f"{src.code}-copy{n}"
    new = create_agent(session, workspace_id, AgentCreate(
        institution_id=inst, code=code, name=data.name or f"{src.name} (copy)", role_kind=src.role_kind,
        mission=src.mission, instructions=src.instructions, model_profile_id=src.model_profile_id,
        tools=list(src.tools), limits=dict(src.limits), is_template=False))
    new.cloned_from_id = src.id
    if data.copy_grants:
        for kb in kb_grants(session, workspace_id, src.id):
            session.add(AgentKbGrant(agent_id=new.id, kb_id=kb, workspace_id=workspace_id))
    session.flush()
    return new


def set_kb_grants(session: Session, workspace_id: str, agent_id: str, kb_ids: list[str], knowledge: Any) -> list[str]:
    row = get_agent(session, workspace_id, agent_id)
    if row.archived_at is not None:
        raise Conflict("agent archivé : non modifiable", code="agent.archived")
    kbs = list(dict.fromkeys(kb_ids))
    if kbs:
        if knowledge is None:
            raise AppError("service knowledge indisponible", code="agents.knowledge_unavailable", status_code=503)
        for kb in kbs:  # la KB doit appartenir au même espace
            try:
                overview = knowledge.kb_overview(session, workspace_id, kb)
            except NotFound:
                overview = None
            if not overview:
                raise NotFound("base de connaissances introuvable", code="kb.not_found", details={"kb_id": kb})
    current = {g.kb_id: g for g in session.scalars(select(AgentKbGrant).where(AgentKbGrant.agent_id == agent_id))}
    for kb, g in current.items():
        if kb not in kbs:
            session.delete(g)
    for kb in kbs:
        if kb not in current:
            session.add(AgentKbGrant(agent_id=agent_id, kb_id=kb, workspace_id=workspace_id))
    session.flush()
    return kbs


def access_matrix(session: Session, workspace_id: str, knowledge: Any, include_archived: bool = False) -> dict[str, Any]:
    agents = list_agents(session, workspace_id, include_archived=include_archived)
    ids = [a.id for a in agents]
    grants = [] if not ids else list(session.scalars(select(AgentKbGrant).where(
        AgentKbGrant.workspace_id == workspace_id, AgentKbGrant.agent_id.in_(ids))))
    kbs: dict[str, dict[str, Any]] = {}
    for g in grants:
        if g.kb_id in kbs:
            continue
        info: dict[str, Any] = {}
        if knowledge is not None:
            try:
                info = knowledge.kb_overview(session, workspace_id, g.kb_id) or {}
            except NotFound:
                info = {}
        kbs[g.kb_id] = {"id": g.kb_id, "code": info.get("code"), "name": info.get("name")}
    return {"agents": [{"id": a.id, "code": a.code, "name": a.name, "institution_id": a.institution_id,
                        "role_kind": a.role_kind, "archived": a.archived_at is not None} for a in agents],
            "knowledge_bases": sorted(kbs.values(), key=lambda k: k["id"]),
            "grants": sorted(({"agent_id": g.agent_id, "kb_id": g.kb_id, "mode": g.mode} for g in grants),
                             key=lambda g: (g["agent_id"], g["kb_id"]))}


def export_agent_snapshot(session: Session, workspace_id: str, agent_id: str) -> dict[str, Any]:
    a = get_agent(session, workspace_id, agent_id)
    prof = get_profile(session, workspace_id, a.model_profile_id) if a.model_profile_id else None
    limits = {**DEFAULT_LIMITS, **(a.limits or {})}
    return {"id": a.id, "code": a.code, "name": a.name, "institution_id": a.institution_id, "role_kind": a.role_kind,
            "mission": a.mission, "instructions": a.instructions, "tools": list(a.tools or []), "limits": limits,
            "model_profile": None if prof is None else {
                "provider": prof.provider, "model": prof.model, "endpoint_ref": prof.endpoint_ref,
                "temperature": prof.temperature, "max_tokens": prof.max_tokens, "timeout_s": prof.timeout_s,
                "extra": prof.extra or {}}}


def prompt_preview(session: Session, workspace_id: str, agent_id: str, services: dict[str, Any]) -> dict[str, Any]:
    """Aperçu du prompt assemblé SANS secret (aucun profil/endpoint n'entre dans le prompt)."""
    snap = export_agent_snapshot(session, workspace_id, agent_id)
    inst = {"id": snap["institution_id"], "code": "—", "name": "(institution)", "kind": "other"}
    if snap["institution_id"]:
        i = ws_service.get_institution(session, workspace_id, snap["institution_id"])
        inst = {"id": i.id, "code": i.code, "name": i.name, "kind": i.kind}
    kb_ids = kb_grants(session, workspace_id, agent_id)
    mandates: list[dict[str, Any]] = []
    knowledge, mand = services.get("knowledge"), services.get("mandates")
    if knowledge and mand and kb_ids and snap["institution_id"]:
        try:
            dvs = knowledge.published_document_version_ids(session, workspace_id, kb_ids)
            mandates = mand.export_active_mandates(session, workspace_id, [snap["institution_id"]], dvs)
        except Exception:  # noqa: BLE001 - l'aperçu reste disponible sans mandats
            mandates = []
    ctx = SeatContext(
        exercise_id="preview", workspace_id=workspace_id, seat_id="preview", seat_code=inst["code"], institution=inst,
        agent=snap, scope=SearchScope(workspace_id, frozenset(kb_ids), frozenset(), purpose="ui_preview"),
        inject={"title": "(inject title)", "body": "(inject text appears here)", "sim_time": "D1 06:00"}, round=1,
        inbox=[], board=[], own_decisions=[], mandates=mandates, seat_codes=["(other seat codes)"], step_key="preview")
    text = build_system_prompt(ctx)
    return {"version": PROMPT_VERSION, "system_prompt": text, "approx_tokens": estimate_tokens(text),
            "mandates_included": len(mandates), "granted_kb_ids": kb_ids}
