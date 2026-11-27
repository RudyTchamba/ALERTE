from __future__ import annotations

from app.contracts import PostedMessage
from tests.simulation.conftest import API
from tests.simulation.fakes import Behavior, FakeRuntime


def one_step_agents(world):
    for a in world.agents.agents.values():
        a["limits"] = {"max_steps": 1, "max_search_calls": 1, "max_legal_calls_per_inject": 1}


def state(world, ex_id):
    return world.client.get(f"{API}/exercises/{ex_id}", headers=world.fac).json()


# --------------------------------------------------------------------------- budget (T-SEC-11)
def test_budget_exhaustion_pauses_with_explicit_error_never_loops(world):
    one_step_agents(world)
    # 3 appels par activation. La préparation estime au pire 3 sièges x 3 tours x 1 pas = 9 appels : un plafond de 6 (= 9 / 1,5) est le plus
    # bas qui ne bloque pas le lancement ; l'exercice atteint ce plafond au runtime après 2 activations.
    world.runtime.script = lambda c: Behavior(llm_calls=3)
    ex_id = world.new_exercise(settings={"max_llm_calls": 6})
    assert world.run(ex_id) == "paused"
    led = world.ledger(ex_id)
    err = [e for e in led if e["type"] == "ERROR"]
    assert len(err) == 1 and err[0]["payload"]["component"] == "budget" and err[0]["payload"]["next_action"] == "pause"
    st = [e["payload"] for e in led if e["type"] == "STATE"][-1]
    assert st["to"] == "paused" and st["reason"] == "budget_exhausted"
    assert len(world.runtime.calls) == 2 and state(world, ex_id)["llm_calls_used"] == 6
    assert not world.mgr.is_active(ex_id)
    # reprise sans rallonge : nouvelle pause explicite (jamais de boucle silencieuse)
    world.cmd(ex_id, "resume")
    world.wait(ex_id, {"paused"})
    assert len(world.runtime.calls) == 2
    assert len([e for e in world.ledger(ex_id) if e["type"] == "ERROR"]) == 2
    # rallonge accordée par l'animateur : l'exercice se termine
    assert world.cmd(ex_id, "resume", {"extend_budget": 10}).status_code == 202
    assert world.wait(ex_id, {"completed"}) == "completed"
    assert world.verify(ex_id)["ok"]
    assert state(world, ex_id)["llm_calls_used"] == 9


def test_runtime_signalled_budget_exhaustion_pauses_and_step_is_retried(world):
    flag = {"exhausted": True}

    def script(c):
        if c.step_key == "inject:1:round:1:seat:OPS" and flag["exhausted"]:
            return Behavior(status="budget_exhausted", llm_calls=1)
    world.runtime.script = script
    ex_id = world.new_exercise()
    assert world.run(ex_id) == "paused"
    led = world.ledger(ex_id)
    assert [e for e in led if e["type"] == "ERROR" and e["payload"]["component"] == "budget"]
    assert not [e for e in led if e["type"] == "DECISION" and e["payload"]["seat_code"] == "OPS"]
    flag["exhausted"] = False
    world.cmd(ex_id, "resume")
    assert world.wait(ex_id, {"completed"}) == "completed"
    assert [e for e in world.ledger(ex_id) if e["type"] == "DECISION" and e["payload"]["seat_code"] == "OPS"]


def test_default_budget_comes_from_application_settings(world):
    ex = state(world, world.new_exercise())
    assert ex["settings"]["max_llm_calls"] == world.ctx.settings.max_llm_calls == 199
    assert world.client.post(f"{API}/exercises", headers=world.fac, json={
        "scenario_id": world.scenario_id, "settings": {"nonsense": 1}}).status_code == 422


# --------------------------------------------------------------------------- golden run
def chatty(c):
    if c.seat_code == "MET":
        return Behavior(messages=[PostedMessage("OPS", "REQUEST", "can you issue?")])
    if c.seat_code == "OPS" and c.round == 2:
        return Behavior(messages=[PostedMessage("MET", "INFO", "yes", in_reply_to=c.inbox[0]["msg_id"],
                                                reply_status="accepted")])


def test_golden_run_same_snapshot_same_runtime_same_replay_digest(world):
    world.runtime.script = chatty
    a, b = world.new_exercise(), world.new_exercise()
    world.start(a)
    world.wait(a, {"completed"})
    world.start(b)
    world.wait(b, {"completed"})
    assert world.digest(a) == world.digest(b)
    # la tête de chaîne diffère (ULID, horodatages, latences) : attendu
    heads = [world.client.get(f"{API}/exercises/{x}/anchors", headers=world.aud).json()[-1]["hash"] for x in (a, b)]
    assert heads[0] != heads[1]
    assert world.verify(a)["ok"] and world.verify(b)["ok"]
    la, lb = world.ledger(a), world.ledger(b)
    assert [(e["type"], e["actor"], e["visibility"]) for e in la] == [(e["type"], e["actor"], e["visibility"]) for e in lb]
    assert any(e["type"] == "LLM_CALL" for e in la)


def test_golden_run_is_sensitive_to_behaviour_changes(world):
    world.runtime.script = chatty
    a = world.new_exercise()
    world.run(a)
    world.runtime.script = lambda c: None if c.seat_code != "DPC" else Behavior(
        decision={"action": "other", "action_code": None, "outcome": "refer", "confidence": "low",
                  "rationale": "different", "evidence_tag": "assumed", "legal_basis": []})
    b = world.new_exercise()
    world.run(b)
    assert world.digest(a) != world.digest(b)


def test_golden_digest_with_independent_runtime_instance(world):
    a = world.new_exercise()
    world.run(a)
    world.agents._runtime = FakeRuntime()  # autre instance, mêmes comportements
    b = world.new_exercise()
    world.run(b)
    assert world.digest(a) == world.digest(b)
