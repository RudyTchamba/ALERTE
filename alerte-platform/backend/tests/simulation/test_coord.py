from __future__ import annotations

from app.contracts import PostedMessage
from app.simulation.coord import Dec, Msg, evaluate
from tests.simulation.fakes import Behavior, decision

SEATS = {"A": "iA", "B": "iB", "C": "iC"}
INJ = {"demands": [{"action_code": "act1"}]}


def ev(messages=(), decisions=(), recipients=("A", "B", "C"), inject=INJ):
    return evaluate(inject=inject, seat_institution=SEATS, recipients=list(recipients), messages=list(messages),
                    decisions=list(decisions))


def names(sigs):
    return [s.signal for s in sigs]


def test_r_orphan_request_never_accepted():
    s = ev([Msg("m1", "A", "B", "REQUEST", "do x")], [Dec("d", "A"), Dec("e", "B"), Dec("f", "C")])
    assert names(s) == ["ORPHAN_REQUEST"] and s[0].rule == "R-ORPHAN" and s[0].institutions == ["iA", "iB"]
    assert s[0].action_code == "act1"


def test_r_orphan_not_raised_when_accepted():
    s = ev([Msg("m1", "A", "B", "REQUEST", "do x"), Msg("m2", "B", "A", "INFO", "ok", "m1", "accepted", 2)],
           [Dec("d", "A"), Dec("e", "B"), Dec("f", "C")])
    assert s == []


def test_r_notourrole_when_all_recipients_decline_role():
    msgs = [Msg("m1", "A", "B", "REQUEST", "Do X"), Msg("m2", "A", "C", "REQUEST", "do   x"),
            Msg("m3", "B", "A", "INFO", "no", "m1", "not_our_role", 2), Msg("m4", "C", "A", "INFO", "no", "m2", "not_our_role", 2)]
    s = ev(msgs, [Dec("d", "A"), Dec("e", "B"), Dec("f", "C")])
    assert names(s) == ["NO_OWNER"] and s[0].institutions == ["iA", "iB", "iC"]


def test_partial_not_our_role_is_orphan():
    msgs = [Msg("m1", "A", "B", "REQUEST", "x"), Msg("m2", "A", "C", "REQUEST", "x"),
            Msg("m3", "B", "A", "INFO", "no", "m1", "not_our_role", 2)]
    assert names(ev(msgs, [Dec("d", "A"), Dec("e", "B"), Dec("f", "C")])) == ["ORPHAN_REQUEST"]


def test_r_overlap_without_lead_and_resolved_with_lead():
    decs = [Dec("d1", "A", action_code="act1", outcome="act"), Dec("d2", "B", action_code="act1", outcome="act"),
            Dec("d3", "C")]
    s = ev([], decs)
    assert names(s) == ["CLAIM_OVERLAP"] and s[0].action_code == "act1" and s[0].institutions == ["iA", "iB"]
    lead = [Msg("m", "A", "B", "DECISION", "we lead")]
    assert ev(lead, decs) == []


def test_r_conflict_opposite_outcomes():
    decs = [Dec("d1", "A", action_code="act1", outcome="act"), Dec("d2", "B", action_code="act1", outcome="decline"),
            Dec("d3", "C", action_code="other", outcome="refer")]
    s = ev([], decs)
    assert names(s) == ["CONFLICTING_DECISIONS"] and s[0].evidence["act"] == ["A"] and s[0].evidence["decline"] == ["B"]


def test_r_nobasis_citefail_silent_aiflag():
    decs = [Dec("d1", "A", action_code="act1", outcome="no_legal_basis_found"),
            Dec("d2", "B", outcome="act", status="not_verified"),
            Dec("d4", "A", gap_flags=({"hint": "G1", "text": "no owner?"},))]
    s = ev([Msg("m", "B", "A", "GAP_FLAG", "hmm")], decs)
    assert names(s) == ["MISSING_BASIS", "UNSUPPORTED_DECISION", "NO_RESPONSE", "AGENT_HYPOTHESIS", "AGENT_HYPOTHESIS"]
    silent = next(x for x in s if x.signal == "NO_RESPONSE")
    assert silent.evidence["seat"] == "C"
    hyp = [x for x in s if x.signal == "AGENT_HYPOTHESIS"]
    assert hyp[0].evidence["hint"] == "G1" and hyp[1].evidence["text"] == "hmm"


def test_fallback_decisions_are_excluded_from_signals():
    decs = [Dec("d1", "A", action_code="act1", outcome="no_legal_basis_found", author="fallback"),
            Dec("d2", "B", status="not_verified", author="fallback"), Dec("d3", "C", outcome="refer", author="fallback")]
    assert ev([], decs) == []


def test_coord_never_concludes_gaps():
    for sig in ev([Msg("m1", "A", "B", "REQUEST", "x")], []):
        assert sig.signal in {"ORPHAN_REQUEST", "NO_OWNER", "CLAIM_OVERLAP", "CONFLICTING_DECISIONS", "MISSING_BASIS",
                              "NO_RESPONSE", "UNSUPPORTED_DECISION", "AGENT_HYPOTHESIS"}


# --------------------------------------------------------------------------- intégré au runner
def gap_events(world, ex_id, ref=None):
    return [e for e in world.ledger(ex_id) if e["type"] == "GAP" and (ref is None or e["payload"]["inject_ref"] == ref)]


def test_runner_emits_coordinator_signals_with_scripted_marker(world):
    def script(c):
        if c.inject["inject_ref"] != "inj-001":
            return None
        if c.seat_code == "MET":
            # la demande n'est postée qu'au tour 1 : avec 3 tours, MET est réactivé au tour 3 (réponse d'OPS) et n'a plus rien à demander
            return Behavior(decision=decision("issue_alert", "act"),
                            messages=[PostedMessage("OPS", "REQUEST", "take lead?")] if c.round == 1 else [])
        if c.seat_code == "OPS" and c.round == 1:
            return Behavior(decision=decision("issue_alert", "act"))
        if c.seat_code == "OPS":
            return Behavior(decision=decision("issue_alert", "decline"), messages=[
                PostedMessage("MET", "INFO", "not ours", in_reply_to=c.inbox[0]["msg_id"], reply_status="not_our_role")])
    world.runtime.script = script
    ex_id = world.new_exercise()
    world.run(ex_id)
    sigs = gap_events(world, ex_id, "inj-001")
    kinds = [e["payload"]["signal"] for e in sigs]
    # OPS décide « act » au tour 1 puis « decline » au tour 2 : seule sa DERNIÈRE décision fait foi (MET : act, OPS : decline) ->
    # conflit entre sièges, mais pas de chevauchement (OPS ne revendique plus l'action).
    assert "NO_OWNER" in kinds and "CONFLICTING_DECISIONS" in kinds and "CLAIM_OVERLAP" not in kinds
    for e in sigs:
        pl = e["payload"]
        assert e["visibility"] == "audit" and e["actor"] == "coord"
        assert pl["origin_kind"] == "coordinator_signal" and pl["scripted"] is True
        assert pl["institutions"] and set(pl["institutions"]) <= set(world.inst.values())
    conflict = next(e for e in sigs if e["payload"]["signal"] == "CONFLICTING_DECISIONS")
    assert conflict["payload"]["action_code"] == "issue_alert"


def test_signals_not_marked_scripted_in_ai_mode(world):
    world.runtime.script = lambda c: Behavior(decision=None, status="not_recorded") if c.seat_code == "DPC" else None
    ex_id = world.new_exercise(ai_mode="cassette")
    world.run(ex_id)
    # cassette : profils scripted interdits seulement en mode ai ; aucun signal ne porte scripted=True
    assert all(e["payload"]["scripted"] is False for e in gap_events(world, ex_id))


def test_silent_seat_signal(world):
    world.runtime.script = lambda c: Behavior(no_decision=True) if c.seat_code == "DPC" else None
    ex_id = world.new_exercise()
    world.run(ex_id)
    silent = [e for e in gap_events(world, ex_id) if e["payload"]["signal"] == "NO_RESPONSE"]
    assert len(silent) == 1 and silent[0]["payload"]["inject_ref"] == "inj-002"
    assert silent[0]["payload"]["institutions"] == [world.inst["DPC"]]


def test_a_provisional_decision_revised_later_never_conflicts_with_itself():
    """F1 : décision provisoire (decline) puis révisée (act) par le MÊME siège : aucune contradiction ni chevauchement avec soi-même."""
    decs = [Dec("d1", "A", action_code="act1", outcome="decline"), Dec("d2", "A", action_code="act1", outcome="act")]
    assert [x.signal for x in ev([], decs, recipients=("A",))] == []
    # une décision provisoire sans base légale, remplacée par une décision fondée, ne laisse pas de MISSING_BASIS
    decs = [Dec("d1", "A", action_code="act1", outcome="no_legal_basis_found"), Dec("d2", "A", action_code="act1", outcome="act")]
    assert "MISSING_BASIS" not in [x.signal for x in ev([], decs, recipients=("A",))]
    # en revanche deux SIÈGES différents restent en conflit
    decs = [Dec("d1", "A", action_code="act1", outcome="act"), Dec("d2", "B", action_code="act1", outcome="decline")]
    assert "CONFLICTING_DECISIONS" in [x.signal for x in ev([], decs, recipients=("A", "B"))]
    # et une décision finale non enregistrée (outcome None) n'efface pas la position provisoire précédente
    decs = [Dec("d1", "A", action_code="act1", outcome="no_legal_basis_found"), Dec("d2", "A", status="not_recorded")]
    assert "MISSING_BASIS" in [x.signal for x in ev([], decs, recipients=("A",))]


def test_a_request_too_late_to_be_answered_and_any_last_round_post_are_dropped_with_an_error(world):
    """F2 : une REQUEST postée au tour MAX-1 serait livrée au dernier tour où l'on ne peut plus répondre : refusée (erreur de routage)."""
    def script(c):
        if c.inject["inject_ref"] != "inj-001":
            return None
        if c.seat_code == "MET" and c.round == 1:
            return Behavior(messages=[PostedMessage("OPS", "REQUEST", "please act")])
        if c.seat_code == "OPS" and c.round == 2:
            req = next(i for i in c.inbox if i.get("msg_type") == "REQUEST")
            return Behavior(messages=[PostedMessage("MET", "REQUEST", "and you?"),                       # trop tard : refusée
                                      PostedMessage("MET", "INFO", "done", in_reply_to=req["msg_id"], reply_status="accepted")])  # réponse : permise
        if c.seat_code == "MET" and c.round == 3:
            return Behavior(messages=[PostedMessage("OPS", "INFO", "thanks")])                               # dernier tour : refusé
    world.runtime.script = script
    ex_id = world.new_exercise()
    world.run(ex_id)
    led = world.ledger(ex_id)
    board = [(e["payload"]["from"], e["payload"]["to"], e["payload"]["msg_type"], e["payload"]["round"]) for e in led if e["type"] == "BOARD"]
    assert board == [("MET", "OPS", "REQUEST", 1), ("OPS", "MET", "INFO", 2)]
    errs = [e["payload"]["message"] for e in led if e["type"] == "ERROR" and e["payload"]["component"] == "coord.routing"]
    assert any("demande trop tardive" in m for m in errs) and any("dernier tour" in m for m in errs)
