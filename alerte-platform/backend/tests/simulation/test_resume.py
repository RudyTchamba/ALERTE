from __future__ import annotations

from collections import Counter

import pytest
from sqlalchemy import func, select

from app.contracts import PostedMessage
from app.core.db import session_scope
from app.simulation.engine import RunnerKilled
from app.simulation.models import BoardMessage, Decision, Step
from tests.simulation.conftest import API, wait_for
from tests.simulation.fakes import Behavior


def chatty(c):
    if c.seat_code == "MET" and c.round == 1:
        return Behavior(messages=[PostedMessage("OPS", "REQUEST", f"req {c.inject['inject_ref']}")])
    if c.seat_code == "OPS" and c.round == 2:
        return Behavior(messages=[PostedMessage("MET", "INFO", "ack", in_reply_to=c.inbox[0]["msg_id"], reply_status="accepted")])


def kill_at(world, key, *, in_tx=False):
    def hook(k):
        if k == key:
            raise RunnerKilled()
    if in_tx:
        world.mgr.hooks.before_commit = hook
    else:
        world.mgr.hooks.before_step = hook


def counts(world, ex_id):
    led = world.ledger(ex_id)
    c = Counter(e["type"] for e in led)
    with session_scope(world.ctx.session_factory) as s:
        keys = list(s.scalars(select(Step.step_key).where(Step.exercise_id == ex_id)))
        msgs = list(s.scalars(select(BoardMessage.id).where(BoardMessage.exercise_id == ex_id)))
        decs = s.scalar(select(func.count()).select_from(Decision))
    return c, keys, msgs, decs, led


def crash_and_resume(world, ex_id, key, in_tx):
    kill_at(world, key, in_tx=in_tx)
    world.start(ex_id)
    wait_for(lambda: not world.mgr.is_active(ex_id))
    assert world.client.get(f"{API}/exercises/{ex_id}", headers=world.fac).json()["state"] == "running"  # arrêt brutal
    world.mgr.hooks.before_step = world.mgr.hooks.before_commit = None
    assert world.mgr.recover_interrupted() == [ex_id]
    assert world.client.get(f"{API}/exercises/{ex_id}", headers=world.fac).json()["state"] == "interrupted"
    r = world.cmd(ex_id, "resume")
    assert r.status_code == 202, r.text
    return world.wait(ex_id, {"completed"})


@pytest.mark.parametrize("key,in_tx", [
    ("inject:1:round:1:seat:OPS", False),     # tué entre deux étapes
    ("inject:1:round:1:seat:OPS", True),      # tué DANS la transaction de l'étape (rien ne doit rester)
    ("inject:1:release", False), ("inject:1:round:1:close", True), ("inject:1:close", True),
    ("inject:1:round:2:seat:OPS", False), ("inject:2:round:1:seat:DPC", True), ("final", True)])
def test_resume_after_abnormal_stop_is_idempotent(world, key, in_tx):
    world.runtime.script = chatty
    clean = world.new_exercise()
    assert world.run(clean) == "completed"
    c_clean, keys_clean, msgs_clean, _, _ = counts(world, clean)

    ex_id = world.new_exercise()
    crash_and_resume(world, ex_id, key, in_tx)
    c, keys, msgs, _, led = counts(world, ex_id)
    # aucune séquence dupliquée, chaîne vérifiable, aucun message dupliqué
    seqs = [e["seq"] for e in led]
    assert seqs == list(range(1, len(seqs) + 1))
    v = world.verify(ex_id)
    assert v["ok"], v
    assert len(keys) == len(set(keys)) == len(keys_clean)
    assert len(msgs) == len(set(msgs)) == len(msgs_clean) == 2
    assert len([e for e in led if e["type"] == "BOARD"]) == 2
    extra = {"STATE": 2, "FACILITATOR": 1}  # interrupted + running (reprise) ; commande resume
    for t_, n in c_clean.items():
        assert c[t_] == n + extra.get(t_, 0), (t_, c[t_], n)
    states_ = [e["payload"]["to"] for e in led if e["type"] == "STATE"]
    assert states_ == ["running", "interrupted", "running", "completed"]
    # le runtime n'a pas été rappelé pour les étapes déjà terminées
    calls = Counter(k for k in world.runtime.calls if k in keys_clean)
    redone = [k for k, n in calls.items() if n > (3 if (in_tx and k == key) else 2)]
    assert not redone


def test_transaction_killed_mid_step_leaves_no_event_of_that_step(world):
    world.runtime.script = chatty
    ex_id = world.new_exercise()
    kill_at(world, "inject:1:round:1:seat:MET", in_tx=True)
    world.start(ex_id)
    wait_for(lambda: not world.mgr.is_active(ex_id))
    led = world.ledger(ex_id)
    assert not [e for e in led if e["type"] in ("DECISION", "BOARD")]
    assert led[-1]["type"] == "INJECT"  # la libération de l'inject est commitée, pas l'activation
    assert world.verify(ex_id)["ok"]


def test_runner_exception_interrupts_with_error_and_can_resume(world):
    boom = {"n": 0}

    def script(c):
        if c.step_key == "inject:1:round:1:seat:OPS" and boom["n"] == 0:
            boom["n"] += 1
            raise RuntimeError("runtime crash")
    world.runtime.script = script
    ex_id = world.new_exercise()
    assert world.run(ex_id) == "interrupted"
    errs = [e for e in world.ledger(ex_id) if e["type"] == "ERROR"]
    assert errs[-1]["payload"]["component"] == "runner" and "runtime crash" in errs[-1]["payload"]["message"]
    assert world.cmd(ex_id, "resume").status_code == 202
    world.wait(ex_id, {"completed"})
    assert world.verify(ex_id)["ok"]


def test_startup_recovery_marks_running_as_interrupted(world):
    ex_id = world.new_exercise()
    kill_at(world, "inject:1:round:1:seat:MET")
    world.start(ex_id)
    wait_for(lambda: not world.mgr.is_active(ex_id))
    # simule un redémarrage de l'application
    from app.simulation import setup
    setup.register(world.ctx)
    assert world.client.get(f"{API}/exercises/{ex_id}", headers=world.fac).json()["state"] == "interrupted"
    world.ctx.services["simulation"].hooks.before_step = None
    world.mgr = world.ctx.service("simulation")
    assert world.cmd(ex_id, "resume").status_code == 202
    world.wait(ex_id, {"completed"})


def test_two_exercises_run_concurrently_without_locking_errors(world):
    import time
    world.runtime.script = chatty
    world.mgr.hooks.before_step = lambda k: time.sleep(0.005)
    a, b = world.new_exercise(), world.new_exercise()
    world.start(a)
    world.start(b)
    world.wait(a, {"completed"})
    world.wait(b, {"completed"})
    for x in (a, b):
        assert world.verify(x)["ok"]
        assert not [e for e in world.ledger(x) if e["type"] == "ERROR"]
    assert world.digest(a) == world.digest(b)
