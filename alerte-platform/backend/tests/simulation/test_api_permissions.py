from __future__ import annotations

import pytest

from app.contracts import PostedMessage
from app.core.auth import Principal
from app.core.db import session_scope
from app.core.errors import Forbidden, NotFound
from app.simulation.service import exercise_guard, reference_guard
from tests.conftest import auth
from tests.simulation.conftest import API
from tests.simulation.fakes import Behavior


def other_workspace(world):
    r = world.client.post(f"{API}/workspaces", json={"name": "Other"}, headers=world.owner)
    assert r.status_code == 201
    return auth(r.json()["owner_token"])


def test_workspace_isolation_everywhere(world):
    ex_id = world.new_exercise()
    world.run(ex_id)
    other = other_workspace(world)
    for method, path, kw in (
            ("get", f"/exercises/{ex_id}", {}), ("get", f"/exercises/{ex_id}/readiness", {}),
            ("get", f"/exercises/{ex_id}/snapshot", {}), ("get", f"/exercises/{ex_id}/board", {}),
            ("get", f"/exercises/{ex_id}/decisions", {}), ("get", f"/exercises/{ex_id}/inbox?seat=MET", {}),
            ("get", f"/exercises/{ex_id}/ledger", {}), ("get", f"/exercises/{ex_id}/ledger/verify", {}),
            ("post", f"/exercises/{ex_id}/commands", {"json": {"kind": "correction", "args": {"corrects_seq": 1, "reason": "x"}}}),
            ("put", f"/exercises/{ex_id}/seats", {"json": {"seats": []}}),
            ("post", f"/exercises/{ex_id}/seats/MET/invite", {}), ("delete", f"/exercises/{ex_id}", {}),
            ("post", f"/exercises/{ex_id}/archive", {}), ("post", f"/exercises/{ex_id}/stream-token", {})):
        r = getattr(world.client, method)(f"{API}{path}", headers=other, **kw)
        assert r.status_code == 404, (method, path, r.status_code, r.text)
    assert world.client.get(f"{API}/exercises", headers=other).json() == []
    # le scénario d'un autre espace n'est pas utilisable ; le clonage d'un exercice étranger non plus
    assert world.client.post(f"{API}/exercises", json={"scenario_id": world.scenario_id}, headers=other).status_code == 404
    assert world.client.post(f"{API}/exercises?from={ex_id}", headers=other).status_code == 404
    # aucun effet de bord sur l'exercice d'origine
    assert world.client.get(f"{API}/exercises/{ex_id}", headers=world.fac).json()["state"] == "completed"


def test_exercise_guard_function_contract(world):
    ex_id = world.new_exercise()
    other_ex = world.new_exercise()
    with session_scope(world.ctx.session_factory) as s:
        ok = Principal(workspace_id=world.ws, role="facilitator", token_id="t")
        assert exercise_guard(s, ok, ex_id).id == ex_id
        with pytest.raises(NotFound):
            exercise_guard(s, Principal(workspace_id="other", role="owner", token_id="t"), ex_id)
        with pytest.raises(NotFound):
            exercise_guard(s, ok, "nope")
        with pytest.raises(Forbidden):
            exercise_guard(s, Principal(workspace_id=world.ws, role="observer", token_id="t", exercise_id=other_ex), ex_id)
    assert world.ctx.services["exercise_guard"] is exercise_guard


def test_observer_is_read_only_and_public_only(world):
    world.runtime.script = lambda c: Behavior(messages=[PostedMessage("OPS", "INFO", "x")]) if c.seat_code == "MET" else None
    ex_id = world.new_exercise()
    world.run(ex_id)
    obs = world.obs
    assert world.client.get(f"{API}/exercises/{ex_id}", headers=obs).status_code == 200
    assert world.client.get(f"{API}/exercises", headers=obs).status_code == 200
    assert world.client.get(f"{API}/exercises/{ex_id}/decisions", headers=obs).json()
    for method, path, kw in (
            ("post", f"/exercises/{ex_id}/commands", {"json": {"kind": "stop"}}), ("post", "/exercises", {"json": {}}),
            ("put", f"/exercises/{ex_id}/seats", {"json": {"seats": []}}), ("delete", f"/exercises/{ex_id}", {}),
            ("post", f"/exercises/{ex_id}/seats/MET/invite", {}), ("get", f"/exercises/{ex_id}/readiness", {}),
            ("get", f"/exercises/{ex_id}/snapshot", {}), ("get", f"/exercises/{ex_id}/board", {}),
            ("get", f"/exercises/{ex_id}/inbox?seat=MET", {}), ("post", f"/exercises/{ex_id}/archive", {}),
            ("post", f"/exercises/{ex_id}/ready", {}), ("get", "/seats/me", {}),
            ("post", "/seats/me/decision", {"json": {}})):
        r = getattr(world.client, method)(f"{API}{path}", headers=obs, **kw)
        assert r.status_code == 403, (method, path, r.status_code)
    assert all(e["visibility"] == "public" for e in world.client.get(f"{API}/exercises/{ex_id}/ledger", headers=obs).json())
    # l'observateur ne voit pas les champs sensibles du siège (nom d'humain, agent)
    seats = world.client.get(f"{API}/exercises/{ex_id}", headers=obs).json()["seats"]
    assert all(s["agent_id"] is None and s["human_name"] is None for s in seats)


def test_auditor_reads_everything_but_cannot_drive(world):
    ex_id = world.new_exercise()
    world.run(ex_id)
    assert world.client.get(f"{API}/exercises/{ex_id}/snapshot", headers=world.aud).status_code == 200
    assert world.client.get(f"{API}/exercises/{ex_id}/board", headers=world.aud).status_code == 200
    assert world.client.get(f"{API}/exercises/{ex_id}/inbox?seat=MET", headers=world.aud).status_code == 200
    assert world.cmd(ex_id, "correction", {"corrects_seq": 1, "reason": "x"}, who=world.aud).status_code == 403
    assert world.client.get(f"{API}/exercises/{ex_id}/inbox", headers=world.aud).status_code == 422


def test_exercise_bound_token_cannot_touch_another_exercise(world):
    a, b = world.new_exercise(), world.new_exercise()
    tok = world.token("observer", exercise_id=a)
    assert world.client.get(f"{API}/exercises/{a}", headers=tok).status_code == 200
    r = world.client.get(f"{API}/exercises/{b}", headers=tok)
    assert r.status_code == 403
    assert [e["id"] for e in world.client.get(f"{API}/exercises", headers=tok).json()] == [a]
    assert world.client.post(f"{API}/exercises/{b}/stream-token", headers=tok).status_code == 403


def test_rest_reads_board_decisions_inbox(world):
    world.runtime.script = lambda c: Behavior(messages=[PostedMessage("OPS", "REQUEST", "help")]) \
        if c.seat_code == "MET" and c.round == 1 else None
    ex_id = world.new_exercise()
    world.run(ex_id)
    board = world.client.get(f"{API}/exercises/{ex_id}/board", headers=world.fac).json()
    assert len(board) == 1 and board[0]["from"] == "MET" and board[0]["msg_type"] == "REQUEST"
    decs = world.client.get(f"{API}/exercises/{ex_id}/decisions?seat=OPS", headers=world.fac).json()
    assert {d["seat_code"] for d in decs} == {"OPS"} and decs[0]["legal_basis"][0]["chunk_id"] == "c1"
    assert decs[0]["legal_basis"][0]["check"] == "pass" and decs[0]["author"] == "agent"
    only = world.client.get(f"{API}/exercises/{ex_id}/decisions?inject_ref=inj-002", headers=world.fac).json()
    assert [d["seat_code"] for d in only] == ["DPC"]
    inbox = world.client.get(f"{API}/exercises/{ex_id}/inbox?seat=OPS", headers=world.fac).json()
    assert [i["source"] for i in inbox] == ["inject", "board"] and inbox[1]["body"] == "help"
    assert world.client.get(f"{API}/exercises/{ex_id}/inbox?seat=NOPE", headers=world.fac).status_code == 404


def test_clone_list_delete_archive(world):
    ex_id = world.new_exercise(settings={"max_llm_calls": 150})
    c = world.client.post(f"{API}/exercises?from={ex_id}", headers=world.fac)
    assert c.status_code == 201
    clone = c.json()
    assert clone["parent_exercise_id"] == ex_id and clone["code"] != world.client.get(f"{API}/exercises/{ex_id}", headers=world.fac).json()["code"]
    assert clone["settings"]["max_llm_calls"] == 150 and [s["code"] for s in clone["seats"]] == ["MET", "OPS", "DPC"]
    assert clone["state"] == "draft" and clone["scenario_id"] == world.scenario_id
    assert len(world.client.get(f"{API}/exercises", headers=world.fac).json()) == 2
    assert len(world.client.get(f"{API}/exercises?state=running", headers=world.fac).json()) == 0
    assert world.client.get(f"{API}/exercises/nope", headers=world.fac).status_code == 404
    assert world.client.post(f"{API}/exercises?from=nope", headers=world.fac).status_code == 404
    # suppression d'un brouillon jamais lancé ; jamais d'un exercice lancé
    assert world.client.delete(f"{API}/exercises/{clone['id']}", headers=world.fac).status_code == 204
    assert world.client.get(f"{API}/exercises/{clone['id']}", headers=world.fac).status_code == 404
    world.run(ex_id)
    r = world.client.delete(f"{API}/exercises/{ex_id}", headers=world.fac)
    assert r.status_code == 409 and r.json()["error"]["code"] == "exercise.started"
    arch = world.client.post(f"{API}/exercises/{ex_id}/archive", headers=world.fac)
    assert arch.status_code == 200 and arch.json()["state"] == "archived"
    assert world.client.post(f"{API}/exercises/{ex_id}/archive", headers=world.fac).status_code == 409
    other = world.new_exercise()
    assert world.client.post(f"{API}/exercises/{other}/archive", headers=world.fac).status_code == 409  # brouillon
    assert world.client.delete(f"{API}/exercises/{ex_id}", headers=world.fac).status_code == 409  # archivé : jamais supprimé


def test_create_validation(world):
    assert world.client.post(f"{API}/exercises", json={}, headers=world.fac).status_code == 422
    assert world.client.post(f"{API}/exercises", json={"scenario_id": "nope"}, headers=world.fac).status_code == 404
    ex_id = world.new_exercise()
    base = {"seats": world.seats()}
    dup = {"seats": base["seats"] + [base["seats"][0]]}
    assert world.client.put(f"{API}/exercises/{ex_id}/seats", json=dup, headers=world.fac).status_code == 422
    bad_inst = {"seats": [{**base["seats"][0], "institution_id": "nope"}]}
    assert world.client.put(f"{API}/exercises/{ex_id}/seats", json=bad_inst, headers=world.fac).status_code == 404
    bad_agent = {"seats": [{**base["seats"][0], "agent_id": "nope"}]}
    assert world.client.put(f"{API}/exercises/{ex_id}/seats", json=bad_agent, headers=world.fac).status_code == 404
    # l'institution d'un autre espace est introuvable (isolation)
    other = other_workspace(world)
    foreign = world.client.post(f"{API}/institutions", json={"code": "ZZ", "name": "Z"}, headers=other).json()["id"]
    assert world.client.put(f"{API}/exercises/{ex_id}/seats", headers=world.fac,
                            json={"seats": [{**base["seats"][0], "institution_id": foreign}]}).status_code == 404


# --------------------------------------------------------------------------- garde de référence
def test_reference_guard_blocks_deletion_of_objects_used_by_a_launched_exercise(world):
    draft = world.new_exercise()
    spare = world.client.post(f"{API}/institutions", json={"code": "SPARE", "name": "Spare"}, headers=world.owner).json()["id"]
    # brouillon : ne bloque pas encore
    with session_scope(world.ctx.session_factory) as s:
        assert not reference_guard(s, "institution", world.inst["MET"])
    country = world.client.post(f"{API}/countries", json={"name": "Landia"}, headers=world.owner).json()["id"]
    world.client.patch(f"{API}/institutions/{world.inst['MET']}", json={"country_id": country}, headers=world.owner)
    ex_id = world.new_exercise()
    world.run(ex_id)
    with session_scope(world.ctx.session_factory) as s:
        assert reference_guard(s, "country", country)
    r = world.client.delete(f"{API}/institutions/{world.inst['MET']}", headers=world.owner)
    assert r.status_code == 409 and r.json()["error"]["code"] == "institution.in_use"
    assert world.client.delete(f"{API}/institutions/{spare}", headers=world.owner).status_code == 204
    with session_scope(world.ctx.session_factory) as s:
        assert reference_guard(s, "scenario", world.scenario_id) and reference_guard(s, "agent", world.agent["OPS"])
        assert reference_guard(s, "knowledge_base", "kb1") and reference_guard(s, "kb", "kb1")
        assert reference_guard(s, "document_version", "dv2") and reference_guard(s, "mandate", "m-MET")
        assert reference_guard(s, "action", "issue_alert")
        assert not reference_guard(s, "agent", "other") and not reference_guard(s, "scenario", "nope")
    # l'archivage ne lève pas la garde
    world.client.post(f"{API}/exercises/{ex_id}/archive", headers=world.fac)
    assert world.client.delete(f"{API}/institutions/{world.inst['DPC']}", headers=world.owner).status_code == 409
    assert draft
