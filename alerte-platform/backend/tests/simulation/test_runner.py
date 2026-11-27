from __future__ import annotations

from sqlalchemy import func, select

from app.contracts import PostedMessage
from app.core.db import session_scope
from app.simulation.models import BoardMessage, Decision, InboxItem, Step
from tests.simulation.conftest import API
from tests.simulation.fakes import Behavior, decision


def types(world, ex_id):
    return [e["type"] for e in world.ledger(ex_id)]


def test_full_run_completes_with_verified_chain_and_anchors(world):
    ex_id = world.new_exercise()
    assert world.run(ex_id) == "completed"
    led = world.ledger(ex_id)
    assert [e["seq"] for e in led] == list(range(1, len(led) + 1))
    assert led[0]["type"] == "SNAPSHOT" and led[1]["type"] == "STATE" and led[1]["payload"]["to"] == "running"
    assert led[-1]["type"] == "STATE" and led[-1]["payload"]["to"] == "completed"
    assert [e["payload"]["inject_ref"] for e in led if e["type"] == "INJECT"] == ["inj-001", "inj-002"]
    inj1 = next(e for e in led if e["type"] == "INJECT")
    assert inj1["payload"]["recipients"] == ["MET", "OPS"] and inj1["payload"]["surprise"] is False
    v = world.verify(ex_id)
    assert v["ok"] and not v["truncated_after_anchor"]
    anchors = world.client.get(f"{API}/exercises/{ex_id}/anchors", headers=world.aud).json()
    assert len(anchors) >= 3 and anchors[-1]["kind"] == "final"
    assert world.gap.closed == ["inj-001", "inj-002"] and world.gap.finished == 1


def test_at_most_three_rounds_per_inject(world):
    # MET écrit à OPS à chaque activation : sans limite, la conversation ne s'arrêterait jamais
    def script(ctx):
        if ctx.seat_code == "MET":
            return Behavior(messages=[PostedMessage("OPS", "INFO", f"hi r{ctx.round}")])
        if ctx.seat_code == "OPS":
            return Behavior(messages=[PostedMessage("MET", "INFO", f"yo r{ctx.round}")])
    world.runtime.script = script
    ex_id = world.new_exercise()
    assert world.run(ex_id) == "completed"
    rounds = {int(k.split(":")[3]) for k in world.runtime.calls}
    assert rounds == {1, 2, 3}
    assert all(k.startswith("inject:") for k in world.runtime.calls)
    assert sorted(k for k in world.runtime.calls if k.startswith("inject:1:")) == sorted([
        f"inject:1:round:{r}:seat:{c}" for r in (1, 2, 3) for c in ("MET", "OPS")])
    with session_scope(world.ctx.session_factory) as s:
        keys = list(s.scalars(select(Step.step_key).where(Step.exercise_id == ex_id)))
        assert not any(":round:4" in k for k in keys)
        assert len(keys) == len(set(keys))


def test_activation_writes_events_decision_board_and_inbox(world):
    world.runtime.script = lambda c: Behavior(messages=[PostedMessage("OPS", "REQUEST", "please")]) \
        if c.seat_code == "MET" and c.round == 1 else None
    ex_id = world.new_exercise()
    world.run(ex_id)
    led = world.ledger(ex_id)
    board = [e for e in led if e["type"] == "BOARD"]
    assert len(board) == 1 and board[0]["visibility"] == "board" and board[0]["payload"]["to"] == "OPS"
    assert board[0]["payload"]["round"] == 1
    dec = [e for e in led if e["type"] == "DECISION"]
    assert dec and all(e["visibility"] == "public" for e in dec)
    assert dec[0]["payload"]["seat_code"] == "MET" and dec[0]["payload"]["author"] == "agent"
    with session_scope(world.ctx.session_factory) as s:
        assert s.scalar(select(func.count()).select_from(BoardMessage)) == 1
        assert s.scalar(select(func.count()).select_from(Decision)) == len(dec)
        # la boîte d'OPS reçoit l'inject puis le message du tour 2
        assert s.scalar(select(func.count()).select_from(InboxItem).where(InboxItem.source == "board")) == 1
    # le contexte du tour 2 d'OPS contient le REQUEST
    ctx2 = next(c for c in world.runtime.contexts if c.step_key == "inject:1:round:2:seat:OPS")
    assert ctx2.inbox[0]["body"] == "please" and ctx2.board[0]["msg_type"] == "REQUEST"
    # la portée vient du snapshot : grants ∩ versions figées
    assert ctx2.scope.kb_ids == frozenset({"kb1"}) and ctx2.scope.document_version_ids == frozenset({"dv1", "dv2"})
    assert ctx2.seat_codes == ["MET", "DPC"] and ctx2.mandates[0]["institution_id"] == world.inst["OPS"]


def test_invalid_messages_are_dropped_with_error(world):
    world.runtime.script = lambda c: Behavior(messages=[
        PostedMessage("NOPE", "INFO", "x"), PostedMessage(c.seat_code, "INFO", "self"),
        PostedMessage("DPC", "BAD", "x"), PostedMessage("DPC", "INFO", "ok", reply_status="accepted")]) \
        if c.seat_code == "MET" else None
    ex_id = world.new_exercise()
    world.run(ex_id)
    led = world.ledger(ex_id)
    assert not [e for e in led if e["type"] == "BOARD"]
    assert len([e for e in led if e["type"] == "ERROR" and e["payload"]["component"] == "coord.routing"]) >= 4


def test_not_recorded_and_fallback_decisions_are_visible(world):
    def script(c):
        if c.seat_code == "MET":
            return Behavior(decision=None, status="not_recorded")
        if c.seat_code == "OPS":
            return Behavior(decision=decision(None, "refer", rationale="fallback: model unavailable", author="fallback"),
                            status="fallback", author="fallback")
    world.runtime.script = script
    ex_id = world.new_exercise()
    world.run(ex_id)
    led = world.ledger(ex_id)
    decs = {e["payload"]["seat_code"]: e["payload"] for e in led if e["type"] == "DECISION"}
    assert decs["MET"]["status"] == "not_recorded" and decs["MET"]["outcome"] is None
    assert decs["OPS"]["author"] == "fallback"
    errs = [e["payload"]["component"] for e in led if e["type"] == "ERROR"]
    assert errs.count("agents.runtime") == 2
    gaps = [e["payload"]["signal"] for e in led if e["type"] == "GAP"]
    assert "NO_RESPONSE" not in gaps  # une ligne de décision existe : ce n'est pas un silence d'institution
    assert "UNSUPPORTED_DECISION" not in gaps and "MISSING_BASIS" not in gaps  # repli exclu des signaux


def test_gap_engine_failure_does_not_stop_the_exercise(world):
    world.gap.fail = True
    ex_id = world.new_exercise()
    assert world.run(ex_id) == "completed"
    errs = [e for e in world.ledger(ex_id) if e["type"] == "ERROR" and e["payload"]["component"] == "gap_engine"]
    assert len(errs) == 2 and world.verify(ex_id)["ok"]


def test_seat_visibility_of_events_and_scripted_marker(world):
    ex_id = world.new_exercise()
    world.run(ex_id)
    led = world.ledger(ex_id)
    seat_events = [e for e in led if e["visibility"] == "seat"]
    assert seat_events and all(e["seat_id"] for e in seat_events)
    assert {e["type"] for e in led} >= {"SNAPSHOT", "STATE", "INJECT", "LLM_CALL", "TOOL_CALL", "RETRIEVAL", "DECISION"}
    assert API and types(world, ex_id)[0] == "SNAPSHOT"


def test_request_reply_decision_cycle_is_delivered_across_three_rounds(world):
    """Cycle technique demande -> transmission -> réponse -> prise en compte -> décision, avec un runtime SIMULÉ (FakeRuntime).

    Prouve la LIVRAISON des messages par le moteur (tour 1 -> tour 2 -> tour 3), pas une coordination intelligente : les
    contenus sont écrits par le test, ils ne sont PAS générés par un modèle."""
    seen: dict[str, object] = {}

    def script(c):
        if c.seat_code == "MET" and c.round == 1:
            return Behavior(messages=[PostedMessage("OPS", "REQUEST", "can you deploy teams?")])
        if c.seat_code == "OPS" and c.round == 2:
            req = next(i for i in c.inbox if i.get("msg_type") == "REQUEST")
            seen["request_id"] = req["msg_id"]
            return Behavior(messages=[PostedMessage("MET", "INFO", "yes, deploying", in_reply_to=req["msg_id"],
                                                    reply_status="accepted")])
        if c.seat_code == "MET" and c.round == 3:
            seen["met_r3_inbox"] = list(c.inbox)
            return Behavior(decision=decision("issue_alert", "act", rationale="OPS accepted the request"))
        return None

    world.runtime.script = script
    ex_id = world.new_exercise()
    assert world.run(ex_id) == "completed"
    board = [e["payload"] for e in world.ledger(ex_id) if e["type"] == "BOARD"]
    assert [(b["from"], b["to"], b["msg_type"], b["round"]) for b in board] == [("MET", "OPS", "REQUEST", 1), ("OPS", "MET", "INFO", 2)]
    assert board[1]["in_reply_to"] == seen["request_id"] == board[0]["msg_id"] and board[1]["reply_status"] == "accepted"
    # transmission : la réponse du tour 2 est livrée au demandeur au tour 3, avec son statut
    r3 = seen["met_r3_inbox"]
    assert len(r3) == 1 and r3[0]["from"] == "OPS" and r3[0]["reply_status"] == "accepted" and r3[0]["in_reply_to"] == seen["request_id"]
    assert "inject:1:round:3:seat:MET" in world.runtime.calls
    decs = [e["payload"] for e in world.ledger(ex_id) if e["type"] == "DECISION" and e["payload"]["seat_code"] == "MET"]
    assert any(d["rationale"] == "OPS accepted the request" for d in decs)


def test_seat_directory_is_passed_to_every_activation(world):
    ex_id = world.new_exercise()
    world.run(ex_id)
    ctx = next(c for c in world.runtime.contexts if c.seat_code == "MET")
    codes = [d["code"] for d in ctx.seat_directory]
    assert codes == ctx.seat_codes and "MET" not in codes and codes
    assert all({"code", "name", "kind", "mission", "mandates"} <= set(d) for d in ctx.seat_directory)
    assert all("instructions" not in d and "inbox" not in d for d in ctx.seat_directory)  # information publique de rôle seulement


def test_a_seat_woken_only_by_a_message_does_not_see_the_event_text(world):
    """Asymétrie d'information : DPC n'est pas destinataire de inj-001 ; réveillé par un message de MET, il ne voit ni le texte ni le titre."""
    world.runtime.script = lambda c: Behavior(messages=[PostedMessage("DPC", "INFO", "FYI")]) \
        if c.seat_code == "MET" and c.round == 1 and c.inject["inject_ref"] == "inj-001" else None
    ex_id = world.new_exercise()
    world.run(ex_id)
    dpc = next(c for c in world.runtime.contexts if c.step_key == "inject:1:round:2:seat:DPC")
    assert dpc.inject.get("not_recipient") is True and dpc.inject["body"] == "" and "Inject 1" not in dpc.inject["title"]
    assert dpc.inbox and dpc.inbox[0]["body"] == "FYI"          # il agit sur son courrier
    met = next(c for c in world.runtime.contexts if c.step_key == "inject:1:round:1:seat:MET")
    assert met.inject["title"] == "Inject 1"                    # un destinataire voit l'événement complet
