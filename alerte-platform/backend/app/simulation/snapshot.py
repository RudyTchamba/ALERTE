"""Construction du snapshot d'exercice (CONTRACTS.md), empreintes, portée de recherche par siège.

`snapshot_sha256` = hachage canonique du snapshot PRIVÉ de son identité d'instance (exercise.id/code, seat_id) :
deux exercices de même configuration ont la même empreinte (T5, golden). `payload_sha256` couvre le payload complet.
"""
from __future__ import annotations

import copy
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..contracts import SearchScope
from ..core.canonical_json import canonical_sha256
from ..core.errors import NotFound
from .common import svc
from .models import Exercise, Seat

INJECT_DEFAULTS = {"tags": [], "demands": [], "fault_mode": "none", "system_output": None, "from_actor": "",
                   "body": "", "title": "", "sim_time": None}


REFORM_SOURCE_ARTICLE = "Réforme (hypothèse)"


def reform_entries(settings: dict | None, seat_institutions: set[str] | list[str]) -> list[dict[str, Any]]:
    """Mandats hypothétiques (`settings.reform_mandates`) au format des mandats du snapshot.

    Seuls ceux qui visent une institution présente à l'exercice sont retenus. Ils entrent dans l'empreinte
    d'engagement comme les autres mandats : un exercice « Et si » est donc distinct et vérifiable."""
    seats = set(seat_institutions)
    out = []
    for i, r in enumerate((settings or {}).get("reform_mandates") or []):
        if r.get("institution_id") not in seats:
            continue
        out.append({"id": f"reform-{i + 1}", "institution_id": r["institution_id"], "kind": r.get("kind", "duty"),
                    "action_code": r["action_code"], "description": r.get("description", ""),
                    "procedure_status": r.get("procedure_status", "specific"), "has_deadline": bool(r.get("has_deadline")),
                    "dependency_text": None, "dependency_ready": None, "depends_on_id": None, "conflicts_with_id": None,
                    "evidence_tag": "assumed", "validation": "validated", "hypothesis": True,
                    "sources": [{"document_version_id": None, "chunk_id": None, "article": REFORM_SOURCE_ARTICLE, "page": None,
                                 "quote": r.get("description") or None}]})
    return out


def normalized_for_hash(payload: dict) -> dict:
    p = copy.deepcopy(payload)
    p["exercise"].pop("id", None)
    p["exercise"].pop("code", None)
    for s in p.get("seats", []):
        s.pop("seat_id", None)
    return p


def snapshot_hash(payload: dict) -> str:
    return canonical_sha256(normalized_for_hash(payload))


def commitment_hash(payload: dict, registry: dict[str, str]) -> str:
    demands = sorted(
        ({"inject_ref": i["inject_ref"], "action_code": d.get("action_code"), "derivation": d.get("derivation")}
         for i in payload["scenario"]["injects"] for d in i.get("demands", [])),
        key=lambda d: (d["inject_ref"], str(d["action_code"])))
    return canonical_sha256({"demands": demands, "mandates": payload["mandates"], "actions": payload["actions"],
                             "registry": dict(sorted(registry.items()))})


def effective_profile(ctx: Any, ex: Exercise, profile: dict | None) -> dict | None:
    """Profil de modèle EFFECTIF d'un agent pour cet exercice.

    * `ai_mode=scripted` : fournisseur de test `scripted` (SANS IA), quel que soit le profil de l'agent ;
    * `ai_mode=cassette` : rejeu de la cassette `exercise.settings.cassette` (SANS IA) ;
    * `ai_mode=ai` : le profil de l'agent, ou à défaut le serveur par défaut `ALERTE_LLM_BASE_URL`/`ALERTE_LLM_MODEL`."""
    if ex.ai_mode == "scripted":
        return {"provider": "scripted", "model": "scripted-rules-v1", "endpoint_ref": None, "temperature": 0.0,
                "max_tokens": None, "timeout_s": None, "extra": {}}
    if ex.ai_mode == "cassette":
        return {"provider": "cassette", "model": "cassette", "endpoint_ref": None, "temperature": 0.0, "max_tokens": None,
                "timeout_s": None, "extra": {"cassette": (ex.settings or {}).get("cassette")}}
    if profile and profile.get("provider"):
        return profile
    st = ctx.settings
    if st.llm_mode == "openai_compat":
        return {"provider": "openai_compat", "model": st.llm_model, "endpoint_ref": "ALERTE_LLM_BASE_URL", "temperature": 0.0,
                "max_tokens": None, "timeout_s": None, "extra": {}}
    return profile


def build_snapshot(ctx: Any, session: Session, ex: Exercise, seats: list[Seat]) -> tuple[dict, dict[str, str]]:
    ws = ex.workspace_id
    scen = copy.deepcopy(svc(ctx, "scenarios").export_scenario_snapshot(session, ws, ex.scenario_id))
    injects = []
    for i in sorted(scen.get("injects", []), key=lambda x: x["seq"]):
        injects.append({**INJECT_DEFAULTS, **i})
    scen["injects"] = injects
    agents, knowledge, mandates = svc(ctx, "agents"), svc(ctx, "knowledge"), svc(ctx, "mandates")
    inst_ids = sorted({s.institution_id for s in seats} | {r for i in injects for r in i.get("recipients", [])})
    institutions = []
    for iid in inst_ids:
        inst = svc(ctx, "workspaces").get_institution(session, ws, iid)
        institutions.append({"id": inst.id, "code": inst.code, "name": inst.name, "kind": inst.kind,
                             "country_id": inst.country_id, "domains": list(inst.domains or [])})
    seat_entries, grants = [], {}
    for s in sorted(seats, key=lambda x: x.position):
        agent = None
        if s.agent_id:
            agent = copy.deepcopy(agents.export_agent_snapshot(session, ws, s.agent_id))
            agent.setdefault("id", s.agent_id)
            agent["model_profile"] = effective_profile(ctx, ex, agent.get("model_profile"))
            grants[s.agent_id] = sorted(agents.kb_grants(session, ws, s.agent_id))
        seat_entries.append({"seat_id": s.id, "code": s.code, "institution_id": s.institution_id,
                             "controller": s.controller, "agent": agent})
    kb_ids = sorted({k for v in grants.values() for k in v})
    kbs, all_versions = [], set()
    for kb_id in kb_ids:
        versions = sorted(knowledge.published_document_version_ids(session, ws, [kb_id]))
        try:
            ov = knowledge.kb_overview(session, ws, kb_id) or {}
        except Exception:  # noqa: BLE001 - métadonnée facultative
            ov = {}
        kbs.append({"kb_id": kb_id, "code": ov.get("code", kb_id), "name": ov.get("name", kb_id),
                    "document_version_ids": versions})
        all_versions.update(versions)
    seat_inst = sorted({s.institution_id for s in seats})
    mand = sorted(mandates.export_active_mandates(session, ws, seat_inst, sorted(all_versions)), key=lambda m: m["id"])
    mand += reform_entries(ex.settings, seat_inst)  # hypothèses « Et si » : jamais écrites dans le registre réel
    codes = {d["action_code"] for i in injects for d in i.get("demands", []) if d.get("action_code")}
    codes |= {m["action_code"] for m in mand if m.get("action_code")}
    catalogue = {a["code"]: a for a in (mandates.list_actions(session, ws) if hasattr(mandates, "list_actions") else [])}
    actions = []
    for c in sorted(codes):
        a = catalogue.get(c, {})
        actions.append({"code": c, "label": a.get("label", c), "derivation": a.get("derivation"),
                        "justification": a.get("justification")})
    payload = {
        "workspace_id": ws,
        "exercise": {"id": ex.id, "code": ex.code, "title": ex.title, "ai_mode": ex.ai_mode,
                     "settings": copy.deepcopy(ex.settings)},
        "scenario": scen, "institutions": institutions, "seats": seat_entries, "kb": kbs, "grants": grants,
        "mandates": mand, "actions": actions}
    registry = {i: str(mandates.registry_state(session, ws, i)) for i in seat_inst}
    return payload, registry


def reference_rows(payload: dict) -> list[tuple[str, str]]:
    refs: set[tuple[str, str]] = {("scenario", payload["scenario"]["id"])}
    if payload["scenario"].get("country_id"):
        refs.add(("country", payload["scenario"]["country_id"]))
    for i in payload["institutions"]:
        refs.add(("institution", i["id"]))
        if i.get("country_id"):
            refs.add(("country", i["country_id"]))
    for s in payload["seats"]:
        if s.get("agent"):
            refs.add(("agent", s["agent"]["id"]))
    for k in payload["kb"]:
        refs.add(("knowledge_base", k["kb_id"]))
        refs.update(("document_version", v) for v in k["document_version_ids"])
    refs.update(("mandate", m["id"]) for m in payload["mandates"])
    refs.update(("action", a["code"]) for a in payload["actions"])
    return sorted(refs)


# --------------------------------------------------------------------------- lecture du snapshot figé
def seat_entry(payload: dict, seat_code: str) -> dict:
    for s in payload["seats"]:
        if s["code"] == seat_code:
            return s
    raise NotFound("siège introuvable dans le snapshot")


def scope_for_seat(payload: dict, seat_code: str, purpose: str = "agent") -> SearchScope:
    """Portée construite UNIQUEMENT depuis le snapshot : droits de l'agent du siège ∩ versions figées."""
    entry = seat_entry(payload, seat_code)
    agent = entry.get("agent") or {}
    granted = set(payload["grants"].get(agent.get("id", ""), []))
    kbs = [k for k in payload["kb"] if k["kb_id"] in granted]
    versions = {v for k in kbs for v in k["document_version_ids"]}
    return SearchScope(workspace_id=payload["workspace_id"], kb_ids=frozenset(k["kb_id"] for k in kbs),
                       document_version_ids=frozenset(versions), purpose=purpose,  # type: ignore[arg-type]
                       seat_id=entry["seat_id"])


def load_payload(session: Session, exercise_id: str) -> dict:
    from .models import ExerciseSnapshot
    snap = session.get(ExerciseSnapshot, exercise_id)
    if snap is None:
        raise NotFound("snapshot introuvable (exercice non lancé)")
    return snap.payload


def seat_rows(session: Session, exercise_id: str) -> list[Seat]:
    return list(session.scalars(select(Seat).where(Seat.exercise_id == exercise_id).order_by(Seat.position, Seat.code)))


def payload_hash(payload: dict) -> str:
    return canonical_sha256(payload)
