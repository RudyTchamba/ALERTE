"""Fabrique de snapshots/registres synthétiques (aucune dépendance aux autres modules)."""
from __future__ import annotations

from typing import Any

from app.gaps.detection import Registry, demands_from_snapshot

INST = {"A": "01INSTAAAAAAAAAAAAAAAAAAAA", "B": "01INSTBBBBBBBBBBBBBBBBBBBB", "C": "01INSTCCCCCCCCCCCCCCCCCCCC"}


def action(code: str, domain: str = "dom", derivation: str = "referential") -> dict[str, Any]:
    return {"code": code, "label": f"action {code}", "domain": domain, "derivation": derivation,
            "justification": "j" if derivation != "referential" else None}


def inject(ref: str, seq: int, actions: list[str], tags: list[str] | None = None, recipients: list[str] | None = None) -> dict:
    return {"inject_ref": ref, "seq": seq, "sim_time": f"D1 0{seq}:00", "title": ref, "body": "", "from_actor": "x",
            "recipients": recipients if recipients is not None else [INST["A"]], "tags": tags or [],
            "demands": [{"action_code": a, "derivation": "referential"} for a in actions], "fault_mode": "none",
            "system_output": None}


def snapshot(injects: list[dict], actions: list[dict], *, ai_mode: str = "ai", mandates: list[dict] | None = None,
             seats: list[dict] | None = None) -> dict[str, Any]:
    return {"workspace_id": "W", "exercise": {"id": "EX", "code": "e", "title": "t", "ai_mode": ai_mode, "settings": {}},
            "scenario": {"id": "S", "code": "s", "title": "s", "language": "fr", "injects": injects},
            "institutions": [{"id": i, "code": c, "name": c, "kind": "agency", "country_id": None, "domains": []}
                             for c, i in INST.items()],
            "seats": seats or [{"seat_id": "S1", "code": "SA", "institution_id": INST["A"], "controller": "agent",
                                "agent": {"id": "AG1", "role_kind": "institution"}}],
            "kb": [{"kb_id": "KB1", "code": "nat", "name": "nat", "document_version_ids": ["DV1"]}],
            "grants": {"AG1": ["KB1"]}, "mandates": mandates or [], "actions": actions}


def mandate(mid: str, inst: str, kind: str, action_code: str, **kw: Any) -> dict[str, Any]:
    d = {"id": mid, "institution_id": INST[inst], "kind": kind, "action_code": action_code, "description": "",
         "procedure_status": "specific", "has_deadline": True, "validation": "validated",
         "sources": [{"document_version_id": "DV1", "chunk_id": f"CH-{mid}", "article": "1", "page": 1, "quote": "q"}]}
    d.update(kw)
    return d


def run(snap: dict, mandates: list[dict], states: dict[str, str] | str = "reviewed_complete", events: list[dict] | None = None):
    from app.gaps.detection import detect
    if isinstance(states, str):
        states = {i: states for i in INST.values()}
    reg = Registry.build(mandates, states)
    return detect(snap, reg, demands_from_snapshot(snap), events or [])


def ev(seq: int, type_: str, payload: dict, seat_id: str | None = None) -> dict:
    return {"seq": seq, "type": type_, "actor": "x", "seat_id": seat_id, "sim_time": None, "visibility": "audit",
            "payload": payload}


def gap_ev(seq: int, signal: str, origin: str = "coordinator_signal", **kw: Any) -> dict:
    return ev(seq, "GAP", {"origin_kind": origin, "signal": signal, "inject_ref": kw.get("inject_ref", "inj-001"),
                           "action_code": kw.get("action_code"), "institutions": kw.get("institutions", []),
                           "evidence": kw.get("evidence", {})})


def by(cands, code: str, action: str | None = None):
    r = [c for c in cands if c.code == code and (action is None or c.action_code == action)]
    return r[0] if r else None
