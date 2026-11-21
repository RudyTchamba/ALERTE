from __future__ import annotations

import pytest

from tests.conftest import auth
from tests.simulation.conftest import API, wait_for
from tests.simulation.fakes import GOOD_QUOTE


def setup_human(world, seat="MET", settings=None):
    ex_id = world.new_exercise({seat: "human"}, settings=settings or {"human_deadline_s": 60})
    r = world.client.post(f"{API}/exercises/{ex_id}/seats/{seat}/invite", headers=world.fac)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["link"] == f"/play#t={body['token']}"
    world.start(ex_id)
    player = auth(body["token"])
    wait_for(lambda: world.client.get(f"{API}/seats/me/task", headers=player).json()["task"])
    return ex_id, player


def task(world, player):
    return world.client.get(f"{API}/seats/me/task", headers=player).json()["task"]


def decision_body(**kw):
    d = {"action": "Issue public alert", "action_code": "issue_alert", "outcome": "act", "confidence": "high",
         "legal_basis": [{"chunk_id": "c1", "article": "33", "quote": GOOD_QUOTE}], "options_considered": ["wait"],
         "gap_flags": [], "evidence_tag": "documented", "rationale": "The law says so."}
    d.update(kw)
    return d


def test_human_seat_full_flow_valid_and_invalid_submissions(world):
    ex_id, player = setup_human(world)
    assert world.fac and world.client.get(f"{API}/exercises/{ex_id}", headers=world.fac).json()["substate"] == "waiting_human"
    card = world.client.get(f"{API}/seats/me", headers=player).json()
    assert card["seat"]["code"] == "MET" and card["institution"]["code"] == "MET" and card["role"]["mission"] == "mission MET"
    assert card["knowledge_bases"][0]["kb_id"] == "kb1" and "MET" not in card["seat_codes"]
    t = task(world, player)
    assert t["round"] == 1 and t["inject"]["title"] == "Inject 1" and t["inbox"][0]["kind"] == "inject"
    # --- décision invalide : citation d'un chunk non récupéré (422 avec la raison précise)
    r = world.client.post(f"{API}/seats/me/decision", json=decision_body(), headers=player)
    assert r.status_code == 422 and r.json()["error"]["code"] == "decision.citation_failed"
    assert r.json()["error"]["details"]["failures"] == [{"chunk_id": "c1", "reason": "not_retrieved"}]
    # --- recherche limitée à SES droits, question au conseiller
    hits = world.client.post(f"{API}/seats/me/search", json={"query": "alerts"}, headers=player).json()["hits"]
    assert {h["chunk_id"] for h in hits} == {"c1", "c2"}
    assert world.search.scopes[-1].purpose == "human_seat" and world.search.scopes[-1].kb_ids == {"kb1"}
    legal = world.client.post(f"{API}/seats/me/ask-legal", json={"question": "May we?"}, headers=player)
    assert legal.status_code == 200 and legal.json()["closing"].startswith("For exercise")
    # --- citation altérée, hors catalogue, sans base : 422
    bad_quote = decision_body(legal_basis=[{"chunk_id": "c1", "article": "33", "quote": "invented text that is not there"}])
    r = world.client.post(f"{API}/seats/me/decision", json=bad_quote, headers=player)
    assert r.status_code == 422 and r.json()["error"]["details"]["failures"][0]["reason"] == "quote_not_in_chunk"
    assert world.client.post(f"{API}/seats/me/decision", json=decision_body(action_code="ghost"), headers=player).status_code == 422
    r = world.client.post(f"{API}/seats/me/decision", json=decision_body(legal_basis=[]), headers=player)
    assert r.status_code == 422 and r.json()["error"]["code"] == "decision.invalid"
    # la tâche est toujours en attente : rien n'a été écrit
    assert task(world, player) is not None
    assert not [e for e in world.ledger(ex_id) if e["type"] == "DECISION"]
    # --- message sur le tableau puis décision valide
    assert world.client.post(f"{API}/seats/me/post", headers=player,
                             json={"to": "MET", "msg_type": "INFO", "body": "x"}).status_code == 422
    assert world.client.post(f"{API}/seats/me/post", headers=player, json={
        "to": "OPS", "msg_type": "REQUEST", "body": "please relay"}).json()["staged"] == 1
    ok = world.client.post(f"{API}/seats/me/decision", json=decision_body(), headers=player)
    assert ok.status_code == 200 and ok.json()["status"] == "recorded"
    assert world.client.post(f"{API}/seats/me/decision", json=decision_body(), headers=player).status_code == 409
    assert world.wait(ex_id, {"completed"}) == "completed"
    led = world.ledger(ex_id)
    dec = next(e for e in led if e["type"] == "DECISION" and e["payload"]["seat_code"] == "MET")
    assert dec["actor"] == "human:Human MET" and dec["payload"]["author"] == "human" and dec["payload"]["status"] == "recorded"
    assert dec["payload"]["legal_basis"][0]["check"] == "pass"
    brd = next(e for e in led if e["type"] == "BOARD")
    assert brd["actor"] == "human:Human MET" and brd["payload"]["to"] == "OPS"
    kinds = [e["payload"]["kind"] for e in led if e["type"] == "HUMAN"]
    assert kinds == ["task_opened", "submitted"]
    assert any(e["type"] == "CITATION_CHECK" and e["payload"]["citations"][0]["pass"] for e in led)
    assert any(e["type"] == "RETRIEVAL" and e["actor"] == "human:Human MET" for e in led)
    assert world.verify(ex_id)["ok"]
    # une fois fini, plus de tâche ni de soumission
    assert world.client.post(f"{API}/seats/me/search", json={"query": "x"}, headers=player).status_code == 409


def test_human_decision_without_legal_basis_when_outcome_says_so(world):
    ex_id, player = setup_human(world)
    r = world.client.post(f"{API}/seats/me/decision", headers=player, json=decision_body(
        outcome="no_legal_basis_found", legal_basis=[], confidence="low", evidence_tag="assumed"))
    assert r.status_code == 200
    world.wait(ex_id, {"completed"})
    sigs = [e["payload"]["signal"] for e in world.ledger(ex_id) if e["type"] == "GAP"]
    assert "MISSING_BASIS" in sigs


def test_post_only_completion_and_reply_rules(world):
    ex_id = world.new_exercise({"OPS": "human"}, settings={"human_deadline_s": 60})
    tok = world.client.post(f"{API}/exercises/{ex_id}/seats/OPS/invite", headers=world.fac).json()["token"]
    player = auth(tok)
    world.start(ex_id)
    wait_for(lambda: task(world, player))
    r = world.client.post(f"{API}/seats/me/post", headers=player, json={
        "to": "MET", "msg_type": "INFO", "body": "x", "reply_status": "accepted"})
    assert r.status_code == 422 and r.json()["error"]["details"]["errors"][0]["field"] == "reply_status"
    r = world.client.post(f"{API}/seats/me/post", headers=player, json={
        "to": "MET", "msg_type": "INFO", "body": "just info", "final": True})
    assert r.json()["task_status"] == "submitted"
    world.wait(ex_id, {"completed"})
    assert not [e for e in world.ledger(ex_id) if e["type"] == "DECISION" and e["payload"]["seat_code"] == "OPS"]


def test_human_deadline_agent_takeover(world):
    ex_id = world.new_exercise({"MET": "human"}, settings={"human_deadline_s": 0})
    assert world.run(ex_id) == "completed"
    led = world.ledger(ex_id)
    assert [e["payload"]["kind"] for e in led if e["type"] == "HUMAN"] == ["task_opened", "expired"]
    seat_ev = next(e for e in led if e["type"] == "SEAT")
    assert seat_ev["payload"] == {"seat": "MET", "from": "human", "to": "agent", "human_name": "Human MET",
                                  "reason": "deadline_expired"}
    assert seat_ev["visibility"] == "board" and seat_ev["actor"] == "coord"
    dec = next(e for e in led if e["type"] == "DECISION" and e["payload"]["seat_code"] == "MET")
    assert dec["payload"]["author"] == "agent"
    assert "inject:1:round:1:seat:MET" in world.runtime.calls


def test_human_deadline_skip_fallback_signals_silence(world):
    ex_id = world.new_exercise({"MET": "human"}, settings={"human_deadline_s": 0, "human_fallback": "skip"})
    assert world.run(ex_id) == "completed"
    led = world.ledger(ex_id)
    assert "inject:1:round:1:seat:MET" not in world.runtime.calls
    assert not [e for e in led if e["type"] == "DECISION" and e["payload"]["seat_code"] == "MET"]
    silent = [e for e in led if e["type"] == "GAP" and e["payload"]["signal"] == "NO_RESPONSE"]
    assert [s["payload"]["institutions"] for s in silent] == [[world.inst["MET"]]]
    assert [e["payload"]["kind"] for e in led if e["type"] == "HUMAN"] == ["task_opened", "expired"]


def test_seat_switch_human_to_agent_while_waiting_cancels_task_and_revokes_link(world):
    ex_id, player = setup_human(world)
    r = world.cmd(ex_id, "seat_switch", {"seat": "MET", "controller": "agent", "reason": "player left"})
    assert r.status_code == 202
    assert world.wait(ex_id, {"completed"}) == "completed"
    led = world.ledger(ex_id)
    sw = next(e for e in led if e["type"] == "SEAT")
    assert sw["payload"]["from"] == "human" and sw["payload"]["to"] == "agent" and sw["payload"]["reason"] == "player left"
    assert next(e for e in led if e["type"] == "DECISION" and e["payload"]["seat_code"] == "MET")["payload"]["author"] == "agent"
    assert world.client.get(f"{API}/seats/me", headers=player).status_code == 401  # lien révoqué


def test_seat_switch_agent_to_human_between_activations(world):
    ex_id = world.new_exercise(pace="manual", settings={"human_deadline_s": 60})
    world.start(ex_id)
    wait_for(lambda: world.client.get(f"{API}/exercises/{ex_id}", headers=world.fac).json()["substate"] == "idle_between_injects")
    assert world.cmd(ex_id, "seat_switch", {"seat": "DPC", "controller": "human"}).status_code == 422  # nom requis
    assert world.cmd(ex_id, "seat_switch", {"seat": "DPC", "controller": "human", "human_name": "Dana"}).status_code == 202
    world.cmd(ex_id, "step")
    inv = world.client.post(f"{API}/exercises/{ex_id}/seats/DPC/invite", headers=world.fac)
    assert inv.status_code == 201
    world.cmd(ex_id, "step")
    player = auth(inv.json()["token"])
    wait_for(lambda: task(world, player))
    assert task(world, player)["inject_ref"] == "inj-002"
    world.client.post(f"{API}/seats/me/search", json={"query": "a"}, headers=player)
    assert world.client.post(f"{API}/seats/me/decision", json=decision_body(action_code="relay_alert"), headers=player).status_code == 200
    world.wait(ex_id, {"completed"})
    led = world.ledger(ex_id)
    assert [e["payload"]["to"] for e in led if e["type"] == "SEAT"] == ["human"]
    assert next(e for e in led if e["type"] == "DECISION" and e["payload"]["seat_code"] == "DPC")["actor"] == "human:Dana"


def test_player_limits_duplicates_and_scope_violation(world):
    ex_id, player = setup_human(world)
    h1 = world.client.post(f"{API}/seats/me/search", json={"query": "alerts"}, headers=player).json()
    dup = world.client.post(f"{API}/seats/me/search", json={"query": "alerts"}, headers=player).json()
    assert dup["hits"] == h1["hits"] and "dupliquée" in dup["warning"]
    world.search.leak = True  # moteur défaillant : renvoie un chunk d'une autre KB
    r = world.client.post(f"{API}/seats/me/search", json={"query": "second"}, headers=player).json()
    assert "c9" not in {h["chunk_id"] for h in r["hits"]}
    third = world.client.post(f"{API}/seats/me/search", json={"query": "third"}, headers=player)
    assert third.status_code == 429 and third.json()["error"]["code"] == "seat.limit_reached"
    assert world.client.post(f"{API}/seats/me/ask-legal", json={"question": "q1"}, headers=player).status_code == 200
    assert world.client.post(f"{API}/seats/me/ask-legal", json={"question": "q2"}, headers=player).status_code == 429
    assert world.client.post(f"{API}/seats/me/search", json={"query": ""}, headers=player).status_code == 422
    errs = [e for e in world.ledger(ex_id) if e["type"] == "ERROR" and e["payload"]["message"] == "SCOPE_VIOLATION"]
    assert len(errs) == 1
    world.cmd(ex_id, "stop")


def test_player_privacy_and_role_boundaries(world):
    ex_id, player = setup_human(world)
    # sa propre boîte seulement ; pas celle d'un autre siège ; pas de ledger complet (audit)
    assert world.client.get(f"{API}/exercises/{ex_id}/inbox", headers=player).status_code == 200
    assert world.client.get(f"{API}/exercises/{ex_id}/inbox?seat=MET", headers=player).status_code == 200
    r = world.client.get(f"{API}/exercises/{ex_id}/inbox?seat=OPS", headers=player)
    assert r.status_code == 403
    led = world.client.get(f"{API}/exercises/{ex_id}/ledger", headers=player).json()
    assert led and not [e for e in led if e["visibility"] == "audit"]
    assert all(e["visibility"] != "seat" or e["seat_id"] for e in led)
    # un joueur ne pilote pas, ne voit pas le snapshot ni la readiness
    for path, method in ((f"/exercises/{ex_id}/commands", "post"), (f"/exercises/{ex_id}/snapshot", "get"),
                         (f"/exercises/{ex_id}/readiness", "get"), (f"/exercises/{ex_id}/seats/MET/invite", "post"),
                         ("/exercises", "post")):
        resp = getattr(world.client, method)(f"{API}{path}", headers=player, **({"json": {"kind": "stop"}} if method == "post" else {}))
        assert resp.status_code == 403, (path, resp.status_code)
    # un agent-seat ne peut pas utiliser les routes du siège humain
    assert world.client.get(f"{API}/seats/me", headers=world.fac).status_code == 403
    assert world.client.get(f"{API}/seats/me", headers=world.owner).status_code == 409
    world.cmd(ex_id, "stop")


@pytest.mark.parametrize("controller", ["agent", "scripted"])
def test_invite_requires_named_human_seat(world, controller):
    ex_id = world.new_exercise({"MET": controller})
    r = world.client.post(f"{API}/exercises/{ex_id}/seats/MET/invite", headers=world.fac)
    assert r.status_code == 409 and r.json()["error"]["code"] == "seat.not_assigned"
    assert world.client.post(f"{API}/exercises/{ex_id}/seats/NOPE/invite", headers=world.fac).status_code == 404
