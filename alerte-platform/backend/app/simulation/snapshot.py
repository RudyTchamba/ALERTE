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
