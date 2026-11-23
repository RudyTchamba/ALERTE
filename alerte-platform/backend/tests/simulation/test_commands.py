from __future__ import annotations

import time

from tests.simulation.conftest import API, wait_for
from tests.simulation.fakes import Behavior


def state(world, ex_id):
    return world.client.get(f"{API}/exercises/{ex_id}", headers=world.fac).json()["state"]


def injects(world, ex_id):
    return [e["payload"]["inject_ref"] for e in world.ledger(ex_id) if e["type"] == "INJECT"]


def pause_at(world, ex_id, key, kind="pause"):
    fired = []

    def hook(k):
        if k == key and not fired:
            fired.append(1)
            world.mgr.submit_command(ex_id, kind, {}, "test")
    world.mgr.hooks.before_step = hook


def test_pause_between_steps_then_resume(world):
    ex_id = world.new_exercise()
    pause_at(world, ex_id, "inject:1:round:1:seat:OPS")
    assert world.run(ex_id) == "paused"
    calls_at_pause = list(world.runtime.calls)
    assert "inject:1:round:1:seat:OPS" in calls_at_pause and "inject:2:round:1:seat:DPC" not in calls_at_pause
    led = world.ledger(ex_id)
    assert [e["type"] for e in led if e["type"] in ("FACILITATOR",)] == ["FACILITATOR"]
    assert world.verify(ex_id)["ok"] and not world.mgr.is_active(ex_id)
    # pause rejetée si déjà en pause ; resume reprend
    assert world.cmd(ex_id, "pause").status_code == 409
    world.mgr.hooks.before_step = None
    assert world.cmd(ex_id, "resume").status_code == 202
    world.wait(ex_id, {"completed"})
    assert injects(world, ex_id) == ["inj-001", "inj-002"]
    states_ = [e["payload"]["to"] for e in world.ledger(ex_id) if e["type"] == "STATE"]
    assert states_ == ["running", "paused", "running", "completed"]
    assert len(world.runtime.calls) == len(set(world.runtime.calls))  # aucune étape rejouée


def test_stop_finalizes_with_detection_and_anchor(world):
    ex_id = world.new_exercise()
    pause_at(world, ex_id, "inject:1:round:1:seat:MET", "stop")
    assert world.run(ex_id) == "stopped"
    led = world.ledger(ex_id)
    assert led[-1]["payload"] == {"from": "running", "to": "stopped", "reason": "stopped_by_facilitator"}
    assert world.gap.finished == 1 and injects(world, ex_id) == ["inj-001"]
    v = world.verify(ex_id)
    assert v["ok"]
    anchors = world.client.get(f"{API}/exercises/{ex_id}/anchors", headers=world.aud).json()
    assert anchors[-1]["kind"] == "final"
    # plus aucune commande de pilotage après l'arrêt
    assert world.cmd(ex_id, "resume").status_code == 409 and world.cmd(ex_id, "stop").status_code == 409


def test_stop_from_paused_without_runner(world):
    ex_id = world.new_exercise()
    pause_at(world, ex_id, "inject:1:round:1:seat:OPS")
    assert world.run(ex_id) == "paused"
    assert world.cmd(ex_id, "stop").status_code == 202
    world.wait(ex_id, {"stopped"})
    assert world.gap.finished == 1 and world.verify(ex_id)["ok"]


def test_manual_pace_requires_step_and_surprise_runs_first(world):
    ex_id = world.new_exercise(pace="manual")
    world.start(ex_id)
    time.sleep(0.25)
    assert injects(world, ex_id) == [] and state(world, ex_id) == "running"
    sub = world.client.get(f"{API}/exercises/{ex_id}", headers=world.fac).json()["substate"]
    assert sub == "idle_between_injects"
    r = world.cmd(ex_id, "surprise", {"title": "Flood!", "body": "river rising", "recipients": ["MET"]})
    assert r.status_code == 202
    assert world.cmd(ex_id, "step").status_code == 202
    wait_for(lambda: injects(world, ex_id) == ["surprise-1"])
    sur = next(e for e in world.ledger(ex_id) if e["type"] == "INJECT")
    assert sur["payload"]["surprise"] is True and sur["payload"]["recipients"] == ["MET"]
    time.sleep(0.15)
    assert injects(world, ex_id) == ["surprise-1"]  # il attend le step suivant
    world.cmd(ex_id, "step")
    wait_for(lambda: injects(world, ex_id) == ["surprise-1", "inj-001"])
    world.cmd(ex_id, "step")
    world.wait(ex_id, {"completed"})
    assert injects(world, ex_id) == ["surprise-1", "inj-001", "inj-002"]
    assert world.gap.closed == ["surprise-1", "inj-001", "inj-002"]
    fac = [e["payload"]["command"] for e in world.ledger(ex_id) if e["type"] == "FACILITATOR"]
    assert fac == ["surprise", "step", "step", "step"]
    assert any(k.startswith("inject:s1:") for k in world.runtime.calls)
    assert world.verify(ex_id)["ok"]


def test_step_while_paused_runs_one_inject_and_stays_paused(world):
    ex_id = world.new_exercise()
    pause_at(world, ex_id, "inject:1:close")
    assert world.run(ex_id) == "paused"
    assert injects(world, ex_id) == ["inj-001"]
    world.mgr.hooks.before_step = None
    assert world.cmd(ex_id, "step").status_code == 202
    wait_for(lambda: not world.mgr.is_active(ex_id) and injects(world, ex_id) == ["inj-001", "inj-002"])
    assert state(world, ex_id) == "paused"
    assert world.gap.closed == ["inj-001", "inj-002"] and world.gap.finished == 0
    world.cmd(ex_id, "resume")
    world.wait(ex_id, {"completed"})
    assert world.gap.finished == 1
    assert world.cmd(ex_id, "step").status_code == 409  # terminé


def test_step_refused_when_running_in_auto_pace(world):
    ex_id = world.new_exercise()
    world.mgr.hooks.before_step = lambda k: time.sleep(0.05)
    world.start(ex_id)
    r = world.cmd(ex_id, "step")
    assert r.status_code == 409 and r.json()["error"]["code"] == "exercise.invalid_transition"
    world.wait(ex_id, {"completed"})


def test_surprise_validation_and_ordering_while_paused(world):
    ex_id = world.new_exercise()
    pause_at(world, ex_id, "inject:1:close")
    world.run(ex_id)
    assert world.cmd(ex_id, "surprise", {"title": "t", "body": "b", "recipients": ["NOPE"]}).status_code == 422
    assert world.cmd(ex_id, "surprise", {"title": "t", "body": "b", "recipients": []}).status_code == 422
    assert world.cmd(ex_id, "surprise", {"title": "t", "body": "b", "recipients": ["OPS"]}).json()["status"] == "queued"
    world.mgr.hooks.before_step = None
    world.cmd(ex_id, "resume")
    world.wait(ex_id, {"completed"})
    assert injects(world, ex_id) == ["inj-001", "surprise-1", "inj-002"]
    ctx = next(c for c in world.runtime.contexts if c.inject["inject_ref"] == "surprise-1")
    assert ctx.seat_code == "OPS" and ctx.inject["title"] == "t"


def test_correction_is_appended_and_nothing_is_erased(world):
    ex_id = world.new_exercise()
    world.run(ex_id)
    before = world.ledger(ex_id)
    target = next(e for e in before if e["type"] == "DECISION")
    r = world.cmd(ex_id, "correction", {"corrects_seq": target["seq"], "reason": "typo", "replacement": {"x": 1}})
    assert r.status_code == 202 and r.json()["status"] == "applied"
    after = world.ledger(ex_id)
    assert after[:len(before)] == before and len(after) == len(before) + 1
    corr = after[-1]
    assert corr["type"] == "CORRECTION" and corr["visibility"] == "audit"
    assert corr["payload"]["corrects_seq"] == target["seq"] and corr["payload"]["reason"] == "typo"
    assert world.verify(ex_id)["ok"]
    assert world.cmd(ex_id, "correction", {"corrects_seq": 99999, "reason": "x"}).status_code == 422
    # autorisée aussi sur un exercice archivé, refusée sur un brouillon
    assert world.client.post(f"{API}/exercises/{ex_id}/archive", headers=world.fac).json()["state"] == "archived"
    assert world.cmd(ex_id, "correction", {"corrects_seq": 1, "reason": "x"}).status_code == 202
    draft = world.new_exercise()
    assert world.cmd(draft, "correction", {"corrects_seq": 1, "reason": "x"}).status_code == 409


def test_speed_changes_pace_and_validates(world):
    ex_id = world.new_exercise(pace="manual")
    world.start(ex_id)
    wait_for(lambda: world.client.get(f"{API}/exercises/{ex_id}", headers=world.fac).json()["substate"] == "idle_between_injects")
    assert world.cmd(ex_id, "speed", {"pace": "fast"}).status_code == 422
    assert world.cmd(ex_id, "speed", {"pace": "auto"}).status_code == 202
    world.wait(ex_id, {"completed"})
    assert injects(world, ex_id) == ["inj-001", "inj-002"]


def test_unexpected_arguments_are_rejected(world):
    ex_id = world.new_exercise()
    assert world.cmd(ex_id, "start", {"x": 1}).status_code == 422
    pause_at(world, ex_id, "inject:1:release")
    world.run(ex_id)
    assert world.cmd(ex_id, "resume", {"bogus": 1}).status_code == 422


def test_capacity_cap_on_concurrent_runners(world):
    world.ctx.settings.max_concurrent_exercises = 1
    a, b = world.new_exercise(), world.new_exercise()
    gate = {"open": False}
    world.mgr.hooks.before_step = lambda k: wait_for(lambda: gate["open"])
    world.start(a)
    r = world.cmd(b, "start")
    assert r.status_code == 409 and r.json()["error"]["code"] == "exercise.capacity_reached"
    assert world.client.get(f"{API}/exercises/{b}", headers=world.fac).json()["state"] == "draft"
    gate["open"] = True
    world.wait(a, {"completed"})
    assert world.start(b)
    world.wait(b, {"completed"})
    assert Behavior and not world.mgr.is_active(b)


def test_stop_survives_gap_engine_and_error_logging_failures(world, monkeypatch):
    """Cas réel (EX-018) : base verrouillée pendant la détection finale, puis aussi pendant l'écriture de l'ERROR."""
    from app.simulation import engine as eng

    def boom(session, exercise_id):  # noqa: ANN001
        raise RuntimeError("database is locked")
    monkeypatch.setattr(world.gap, "on_exercise_finished", boom)
    real_append = eng.Writer.append

    def flaky_append(self, s, ex_id, type_, actor, payload, **kw):  # noqa: ANN001
        if type_ == "ERROR" and payload.get("component") == "gap_engine":
            raise RuntimeError("database is locked")
        return real_append(self, s, ex_id, type_, actor, payload, **kw)
    monkeypatch.setattr(eng.Writer, "append", flaky_append)
    ex_id = world.new_exercise()
    pause_at(world, ex_id, "inject:1:round:1:seat:MET", "stop")
    assert world.run(ex_id) == "stopped" and world.verify(ex_id)["ok"]


def test_failed_finalization_interrupts_instead_of_freezing(world, monkeypatch):
    from app.simulation import engine as eng

    def broken(self, final_state):  # noqa: ANN001
        raise RuntimeError("database is locked")
    monkeypatch.setattr(eng.ExerciseRunner, "_finalize", broken)
    ex_id = world.new_exercise()
    pause_at(world, ex_id, "inject:1:round:1:seat:MET", "stop")
    world.start(ex_id)
    world.wait(ex_id, {"interrupted"})
    wait_for(lambda: ex_id not in world.mgr._runners)  # le fil s'est terminé proprement : rien ne reste « vivant »
    errs = [e for e in world.ledger(ex_id) if e["type"] == "ERROR" and e["payload"]["component"] == "runner"]
    assert errs and errs[-1]["payload"]["next_action"] == "interrupted"
