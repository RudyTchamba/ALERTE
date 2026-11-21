from __future__ import annotations

import copy

from sqlalchemy import select

from app.core.canonical_json import canonical_sha256
from app.core.db import session_scope
from app.simulation import snapshot as snapmod
from app.simulation.models import ExerciseSnapshot
from tests.simulation.conftest import API


def get_snapshot(world, ex_id):
    r = world.client.get(f"{API}/exercises/{ex_id}/snapshot", headers=world.aud)
    assert r.status_code == 200, r.text
    return r.json()


def test_snapshot_conforms_to_contract_and_hash_matches(world):
    ex_id = world.new_exercise()
    world.run(ex_id)
    snap = get_snapshot(world, ex_id)
    p = snap["payload"]
    assert set(p) == {"workspace_id", "exercise", "scenario", "institutions", "seats", "kb", "grants", "mandates", "actions"}
    assert set(p["exercise"]) == {"id", "code", "title", "ai_mode", "settings"} and p["exercise"]["ai_mode"] == "scripted"
    assert [i["inject_ref"] for i in p["scenario"]["injects"]] == ["inj-001", "inj-002"]
    assert {s["code"] for s in p["seats"]} == {"MET", "OPS", "DPC"}
    assert all(s["agent"]["tools"] for s in p["seats"])
    assert p["kb"] == [{"kb_id": "kb1", "code": "KB1", "name": "KB kb1", "document_version_ids": ["dv1", "dv2"]}]
    assert all(v == ["kb1"] for v in p["grants"].values()) and len(p["grants"]) == 3
    assert {a["code"] for a in p["actions"]} == {"issue_alert", "relay_alert"}
    assert len(p["mandates"]) == 3 and len(p["institutions"]) == 3
    assert snap["payload_sha256"] == canonical_sha256(p)
    assert snap["snapshot_sha256"] == snapmod.snapshot_hash(p)
    led = world.ledger(ex_id)
    assert led[0]["type"] == "SNAPSHOT" and led[0]["payload"]["snapshot_sha256"] == snap["snapshot_sha256"]
    assert led[0]["payload"]["commitment_sha256"] == snap["commitment_sha256"]
    assert led[0]["payload"]["ai_mode"] == "scripted" and led[0]["payload"]["readiness"]["ok"] is True
    assert led[0]["visibility"] == "audit"
    ex = world.client.get(f"{API}/exercises/{ex_id}", headers=world.fac).json()
    assert ex["snapshot_sha256"] == snap["snapshot_sha256"]


def test_hash_is_stable_across_instances_and_sensitive_to_config(world):
    a, b = world.new_exercise(), world.new_exercise()
    world.start(a)
    world.wait(a, {"completed"})
    world.start(b)
    world.wait(b, {"completed"})
    sa, sb = get_snapshot(world, a), get_snapshot(world, b)
    assert sa["payload"]["exercise"]["id"] != sb["payload"]["exercise"]["id"]
    assert sa["snapshot_sha256"] == sb["snapshot_sha256"] and sa["commitment_sha256"] == sb["commitment_sha256"]
    assert sa["payload_sha256"] != sb["payload_sha256"]
    # une configuration différente change l'empreinte
    world.knowledge.versions["kb1"] = ["dv1"]
    c = world.new_exercise()
    world.run(c)
    assert get_snapshot(world, c)["snapshot_sha256"] != sa["snapshot_sha256"]
    # la reconstruction de l'empreinte est déterministe
    p = copy.deepcopy(sa["payload"])
    assert snapmod.snapshot_hash(p) == snapmod.snapshot_hash(copy.deepcopy(p))


def test_snapshot_is_immutable_after_launch_even_if_live_config_changes(world):
    ex_id = world.new_exercise()
    world.run(ex_id)
    before = get_snapshot(world, ex_id)
    world.knowledge.versions["kb1"] = ["dvNEW"]
    world.agents.agents[world.agent["MET"]]["mission"] = "CHANGED"
    world.scenarios.scenarios[world.scenario_id]["title"] = "Other"
    assert get_snapshot(world, ex_id) == before
    # la configuration n'est plus modifiable
    r = world.client.put(f"{API}/exercises/{ex_id}/seats", json={"seats": world.seats()}, headers=world.fac)
    assert r.status_code == 409 and r.json()["error"]["code"] == "exercise.immutable"
    with session_scope(world.ctx.session_factory) as s:
        row = s.scalar(select(ExerciseSnapshot).where(ExerciseSnapshot.exercise_id == ex_id))
        assert row.payload["scenario"]["title"] == "Scenario"


def test_snapshot_requires_auditor_and_launch(world):
    ex_id = world.new_exercise()
    assert world.client.get(f"{API}/exercises/{ex_id}/snapshot", headers=world.aud).status_code == 409
    assert world.client.get(f"{API}/exercises/{ex_id}/snapshot", headers=world.fac).status_code == 403
    assert world.client.get(f"{API}/exercises/{ex_id}/snapshot", headers=world.obs).status_code == 403


def test_search_scope_is_built_from_snapshot_only(world):
    ex_id = world.new_exercise()
    world.run(ex_id)
    p = get_snapshot(world, ex_id)["payload"]
    scope = snapmod.scope_for_seat(p, "MET")
    assert scope.kb_ids == {"kb1"} and scope.document_version_ids == {"dv1", "dv2"} and scope.purpose == "agent"
    assert scope.seat_id == next(s["seat_id"] for s in p["seats"] if s["code"] == "MET")
    # un agent sans droit => portée vide
    p["grants"][world.agent["MET"]] = []
    assert snapmod.scope_for_seat(p, "MET").is_empty


# --------------------------------------------------------------------------- readiness
def blocking(world, ex_id):
    r = world.client.get(f"{API}/exercises/{ex_id}/readiness", headers=world.fac)
    assert r.status_code == 200, r.text
    return r.json(), {c["code"] for c in r.json()["blocking"]}


def test_readiness_ok_for_valid_exercise(world):
    ex_id = world.new_exercise()
    res, codes = blocking(world, ex_id)
    assert res["ok"] and not codes and res["estimated_llm_calls"] > 0


def test_readiness_blocks_launch_with_409(world):
    ex_id = world.new_exercise(codes=("MET", "OPS"))  # DPC (destinataire de inj-002) sans siège
    res, codes = blocking(world, ex_id)
    assert not res["ok"] and "inject.recipient_without_seat" in codes
    r = world.cmd(ex_id, "start")
    assert r.status_code == 409 and r.json()["error"]["code"] == "exercise.readiness_blocked"
    assert r.json()["error"]["details"]["blocking"]
    # aucun événement n'a été écrit
    assert world.ledger(ex_id) == []
    assert world.client.get(f"{API}/exercises/{ex_id}", headers=world.fac).json()["state"] == "draft"


def test_readiness_checks_agents_kb_and_providers(world):
    ex_id = world.new_exercise()
    world.agents.grants[world.agent["MET"]] = []
    assert "agent.no_kb_grant" in blocking(world, ex_id)[1]
    world.agents.grants[world.agent["MET"]] = ["kb1"]
    world.knowledge.versions["kb1"] = []
    assert "kb.not_ready" in blocking(world, ex_id)[1]
    world.knowledge.versions["kb1"] = ["dv1", "dv2"]
    ai = world.new_exercise(ai_mode="ai")  # profils 'scripted' interdits en mode ai
    assert "provider.not_ai" in blocking(world, ai)[1]
    world.agents.agents[world.agent["MET"]]["model_profile"] = {}
    assert "agent.no_model_profile" in blocking(world, ai)[1]


def test_readiness_scenario_and_human_checks_and_warnings(world):
    sc = world.scenarios.scenarios[world.scenario_id]
    sc["injects"][0]["recipients"] = []
    sc["injects"][1]["demands"] = [{"action_code": "ghost", "derivation": "x"}]
    ex_id = world.new_exercise()
    codes = blocking(world, ex_id)[1]
    assert {"inject.no_recipient", "inject.unknown_action"} <= codes
    # siège humain sans nom
    r = world.client.put(f"{API}/exercises/{ex_id}/seats", headers=world.fac, json={"seats": [
        {"code": "MET", "institution_id": world.inst["MET"], "agent_id": world.agent["MET"], "controller": "human"}]})
    assert r.status_code == 422 and r.json()["error"]["code"] == "seat.human_unnamed"
    # avertissements : registre non revu, pas de mandat
    sc["injects"][0]["recipients"] = [world.inst["MET"]]
    sc["injects"][1]["demands"] = []
    world.mandates.registry, world.mandates.mandates = "unreviewed", []
    res, codes = blocking(world, ex_id)
    warn = {c["code"] for c in res["warnings"]}
    assert {"registry.not_reviewed", "institution.no_mandates"} <= warn


def test_readiness_budget_estimate_thresholds(world):
    ex_id = world.new_exercise(settings={"max_llm_calls": 10})  # estimé 3*... > 15 => bloquant
    res, codes = blocking(world, ex_id)
    assert "budget.exceeds" in codes
    ex2 = world.new_exercise(settings={"max_llm_calls": res["estimated_llm_calls"] - 1})
    res2, codes2 = blocking(world, ex2)
    assert res2["ok"] and "budget.high" in {c["code"] for c in res2["warnings"]}


def test_missing_services_block_readiness(world):
    ex_id = world.new_exercise()
    del world.ctx.services["knowledge"]
    assert "service.unavailable" in blocking(world, ex_id)[1]


def test_ready_endpoint_and_modification_returns_to_draft(world):
    ex_id = world.new_exercise()
    assert world.client.post(f"{API}/exercises/{ex_id}/ready", headers=world.fac).json()["ok"] is True
    state = lambda: world.client.get(f"{API}/exercises/{ex_id}", headers=world.fac).json()["state"]  # noqa: E731
    assert state() == "ready"
    world.client.put(f"{API}/exercises/{ex_id}/seats", json={"seats": world.seats()}, headers=world.fac)
    assert state() == "draft"
