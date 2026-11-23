from __future__ import annotations

from app.gaps.detection import Registry, demands_from_snapshot, detect
from tests.gaps.helpers import INST, action, by, ev, gap_ev, inject, mandate, run, snapshot

ACT = [action("a1"), action("a2")]


def snap(tags=None, actions=("a1",), **kw):
    return snapshot([inject("inj-001", 1, list(actions), tags)], ACT, **kw)


def test_g1_orphan_documented_with_reviewed_registry_and_severity():
    c = run(snap(["life_risk"]), [mandate("m9", "B", "power", "a2")])
    g1 = by(c, "G1", "a1")
    assert g1.evidence_basis == "documented" and g1.confidence == "medium" and g1.severity == 3
    assert g1.registry_state == "reviewed_complete" and g1.origin == "rule" and g1.cause == "institutional"
    assert g1.category == "mandate_absent_or_incomplete" and g1.needs_negative_search
    assert g1.evidence[0].ref["registry_check"]["found"] == 0
    assert by(c, "G1", "a2") is None  # a2 n'est pas demandée
    assert run(snap([]), [])[0].severity == 2


def test_g1_time_critical_becomes_crisis_category():
    g1 = by(run(snap(["time_critical"]), []), "G1")
    assert g1.category == "crisis_preparedness_response_gap"


def test_g1_not_triggered_when_a_holder_exists():
    assert by(run(snap(), [mandate("m1", "B", "duty", "a1")]), "G1") is None
    # `lead` seul ne suffit pas pour G1 (power|duty) : kind testé strictement
    assert by(run(snap(), [mandate("m1", "B", "lead", "a1")]), "G1") is not None


def test_g2_overlap_without_lead_and_lead_resolves():
    ms = [mandate("m1", "A", "power", "a1"), mandate("m2", "B", "power", "a1")]
    g2 = by(run(snap(["time_critical", "life_risk"]), ms), "G2")
    assert g2.severity == 3 and sorted(g2.institutions) == sorted([INST["A"], INST["B"]]) and g2.evidence_basis == "documented"
    assert by(run(snap(), ms), "G2").severity == 2
    assert by(run(snap(), ms + [mandate("m3", "C", "lead", "a1")]), "G2") is None
    assert by(run(snap(), ms[:1]), "G2") is None


def test_g3_missing_procedure_and_deadline():
    weak = [mandate("m1", "A", "duty", "a1", procedure_status="general")]
    g3 = by(run(snap(["life_risk"]), weak), "G3")
    assert g3.severity == 3 and g3.category == "regulatory_gap" and "procédure" in g3.description
    assert by(run(snap(), [mandate("m1", "A", "duty", "a1")]), "G3") is None
    # procédure spécifique mais pas de délai alors que time_critical
    nodl = [mandate("m1", "A", "duty", "a1", has_deadline=False)]
    g = by(run(snap(["time_critical"]), nodl), "G3")
    assert g is not None and "délai" in g.description and g.category == "crisis_preparedness_response_gap"
    assert "a une procédure spécifique mais aucun délai" in g.description and "aucune procédure" not in g.description
    assert by(run(snap([]), nodl), "G3") is None
    # un mandat `procedure` spécifique compense
    assert by(run(snap(), weak + [mandate("m2", "B", "procedure", "a1")]), "G3") is None
    assert by(run(snap(), []), "G3") is None  # pas de détenteur : c'est G1


def test_g4_dependency_missing_and_resolved():
    dep = mandate("m1", "A", "duty", "a1", dependency_text="décret d'application", has_deadline=True)
    g4 = by(run(snap(), [dep]), "G4")
    assert g4 and g4.severity == 2 and "décret" in g4.description
    assert by(run(snap(), [{**dep, "dependency_ready": "yes"}]), "G4") is None
    target = mandate("m0", "B", "procedure", "a2")
    assert by(run(snap(), [{**dep, "depends_on_id": "m0"}, target]), "G4") is None
    assert by(run(snap(), [{**dep, "depends_on_id": "absent-du-registre"}]), "G4") is not None


def test_g5_conflict_requires_both_duties_triggered():
    m1 = mandate("m1", "A", "duty", "a1", conflicts_with_id="m2")
    m2 = mandate("m2", "B", "duty", "a2")
    both = by(run(snap(actions=("a1", "a2")), [m1, m2]), "G5")
    assert both and both.action_key == "a1|a2" and both.category == "conflicting_mandates"
    assert by(run(snap(actions=("a1",)), [m1, m2]), "G5") is None
    assert by(run(snap(actions=("a1", "a2")), [{**m1, "kind": "power"}, m2]), "G5") is None


def test_g6_to_g10_require_their_tag_and_kind():
    table = {"G6": ("harm_possible", "liability"), "G7": ("public_communication", "inclusion"),
             "G8": ("ai_output_used_in_decision", "human_oversight"), "G9": ("channel_abuse", "channel_protection"),
             "G10": ("foreign_actor", "international_agreement")}
    base = [mandate("mb", "A", "duty", "a1")]
    for code, (tag, kind) in table.items():
        assert by(run(snap([]), base), code) is None, f"{code} sans étiquette"
        g = by(run(snap([tag]), base), code)
        assert g is not None and g.evidence_basis == "documented", code
        assert by(run(snap([tag]), base + [mandate("mx", "B", kind, "a1")]), code) is None, f"{code} avec mandat"
    # sévérités
    assert by(run(snap(["harm_possible", "life_risk"]), base), "G6").severity == 3
    assert by(run(snap(["public_communication"]), base), "G7").severity == 1
    assert by(run(snap(["public_communication", "life_risk"]), base), "G7").severity == 2
    assert by(run(snap(["ai_output_used_in_decision"]), base), "G8").severity == 2
    assert by(run(snap(["ai_output_used_in_decision", "life_risk"]), base), "G8").severity == 3
    assert by(run(snap(["channel_abuse", "life_risk"]), base), "G9").severity == 3
    assert by(run(snap(["foreign_actor"]), base), "G10").severity == 2


def test_cross_cutting_mandate_matches_by_domain():
    acts = [action("a1", "alerting"), action("a2", "alerting"), action("a3", "other")]
    s = snapshot([inject("inj-001", 1, ["a1"], ["ai_output_used_in_decision"])], acts)
    oversight_same_domain = mandate("mo", "B", "human_oversight", "a2")
    assert by(run(s, [mandate("mb", "A", "duty", "a1"), oversight_same_domain]), "G8") is None
    other_domain = mandate("mo", "B", "human_oversight", "a3")
    assert by(run(s, [mandate("mb", "A", "duty", "a1"), other_domain]), "G8") is not None


def test_unreviewed_registry_is_not_an_absent_mandate():
    for states in ("unreviewed", "partial", {INST["A"]: "reviewed_complete"}):  # B, C non revus mais A = destinataire
        c = run(snap(), [], states)
        g1 = by(c, "G1")
        if isinstance(states, dict):
            assert g1.evidence_basis == "documented"  # seul le destinataire compte
            continue
        assert g1.evidence_basis == "inferred" and g1.confidence == "low" and g1.registry_state == states
        assert any("registre non revu" in n for n in g1.notes)
    c = run(snap(), [], {INST["A"]: "partial"})
    assert by(c, "G1").evidence_basis == "inferred"
    # G2/G3 : « pas de chef de file / pas de procédure » sont aussi des absences
    ms = [mandate("m1", "A", "power", "a1"), mandate("m2", "B", "power", "a1")]
    assert by(run(snap(), ms, "partial"), "G2").evidence_basis == "inferred"
    assert by(run(snap(), [mandate("m1", "A", "duty", "a1", procedure_status="none")], "unreviewed"), "G3").evidence_basis == "inferred"


def test_proposed_mandate_blocks_documented_and_gives_low_confidence():
    prop = mandate("mp", "B", "duty", "a1", validation="proposed")
    g1 = by(run(snap(), [prop]), "G1")
    assert g1 is not None and g1.evidence_basis == "inferred" and g1.confidence == "low"
    assert any("mandat proposé non validé" in n for n in g1.notes)
    assert any(e.ref.get("validation") == "proposed" and e.role == "context" for e in g1.evidence)


def test_negative_control_complete_registry_yields_no_gap():
    s = snapshot([inject("inj-001", 1, ["a1"], ["life_risk", "harm_possible", "public_communication", "channel_abuse",
                                                "ai_output_used_in_decision", "foreign_actor", "time_critical"])], ACT)
    full = [mandate("m1", "A", "duty", "a1"), mandate("m2", "A", "lead", "a1"), mandate("m3", "B", "liability", "a1"),
            mandate("m4", "B", "inclusion", "a1"), mandate("m5", "C", "human_oversight", "a1"),
            mandate("m6", "C", "channel_protection", "a1"), mandate("m7", "C", "international_agreement", "a1")]
    assert run(s, full) == []


def test_fingerprint_is_stable_and_discriminating():
    s = snap(["life_risk"])
    a, b = by(run(s, []), "G1"), by(run(s, []), "G1")
    assert a.fingerprint == b.fingerprint and len(a.fingerprint) == 64
    other = by(run(snap(["life_risk"], actions=("a2",)), []), "G1")
    assert other.fingerprint != a.fingerprint
    # un horodatage/identifiant d'événement ne change pas l'empreinte
    assert by(run(s, [], events=[ev(5, "INJECT", {"inject_ref": "inj-001"})]), "G1").fingerprint == a.fingerprint


def test_demand_derivation_is_recorded():
    s = snap()
    s["scenario"]["injects"][0]["demands"][0]["derivation"] = "scenario_author"
    assert by(run(s, []), "G1").demand_derivation == "scenario_author"


def test_signals_reinforce_rule_candidates_and_alone_are_weaker():
    # G1 documenté + signal observé => confiance haute
    sig = gap_ev(10, "ORPHAN_REQUEST", action_code="a1", institutions=[INST["A"]])
    g = by(run(snap(), [], events=[sig]), "G1")
    assert g.evidence_basis == "documented" and g.confidence == "high" and g.observed_signals == 1 and g.origin == "rule"
    # signal seul (le registre contient un détenteur) : inferred, origin coordinator_signal
    only = by(run(snap(), [mandate("m1", "B", "duty", "a1")], events=[sig]), "G1")
    assert only.origin == "coordinator_signal" and only.evidence_basis == "inferred"
    # CLAIM_OVERLAP / CONFLICTING_DECISIONS seuls : observed
    ov = by(run(snap(), [mandate("m1", "B", "duty", "a1")], events=[gap_ev(11, "CLAIM_OVERLAP", action_code="a1")]), "G2")
    assert ov.evidence_basis == "observed" and ov.confidence == "medium" and ov.category == "ambiguous_responsibility"
    cf = by(run(snap(), [], events=[gap_ev(12, "CONFLICTING_DECISIONS", action_code="a1")]), "G5")
    assert cf.evidence_basis == "observed"
    nr = by(run(snap(), [], events=[gap_ev(13, "NO_RESPONSE", action_code="a1")]), "X4")
    assert nr.evidence_basis == "observed" and nr.category == "operational_gap"
    # MISSING_BASIS : G1 si pas de détenteur, G3 sinon
    mb = gap_ev(14, "MISSING_BASIS", action_code="a2", inject_ref="inj-001")
    assert by(run(snap(), [], events=[mb]), "G1", "a2") is not None
    assert by(run(snap(), [mandate("m1", "B", "duty", "a2")], events=[mb]), "G3", "a2") is not None
    # qualité : ignoré
    assert by(run(snap(), [mandate("m1", "B", "duty", "a1")], events=[gap_ev(15, "UNSUPPORTED_DECISION", action_code="a1")]), "G1") is None


def test_signals_of_scripted_exercise_are_never_observed():
    s = snap(ai_mode="scripted")
    ov = gap_ev(11, "CLAIM_OVERLAP", action_code="a1")
    c = by(run(s, [mandate("m1", "B", "duty", "a1")], events=[ov]), "G2")
    assert c.evidence_basis == "inferred" and c.scripted and c.observed_signals == 0
    assert any("scripted" in n for n in c.notes)
    # même avec une règle documentaire : pas de renforcement « high » par un signal scripted
    g1 = by(run(s, [], events=[gap_ev(10, "ORPHAN_REQUEST", action_code="a1")]), "G1")
    assert g1.confidence == "medium" and g1.observed_signals == 0
    # en mode cassette (vrai modèle enregistré), le signal est observé
    cas = by(run(snap(ai_mode="cassette"), [mandate("m1", "B", "duty", "a1")], events=[ov]), "G2")
    assert cas.evidence_basis == "observed"


def test_agent_hypothesis_alone_is_not_a_finding():
    dec = ev(20, "DECISION", {"decision_id": "D1", "seat_code": "SA", "inject_ref": "inj-001", "action_code": "a1",
                              "outcome": "refer", "author": "agent",
                              "gap_flags": [{"hint": "technical", "text": "capteurs insuffisants"}]})
    c = run(snap(), [mandate("m1", "B", "duty", "a1")], events=[dec])
    h = [x for x in c if x.origin == "agent_hypothesis"]
    assert len(h) == 1 and h[0].evidence_basis == "hypothesis" and h[0].confidence == "low"
    assert h[0].category == "technical_gap" and all(e.is_agent for e in h[0].evidence)
    # événement GAP AGENT_HYPOTHESIS + message GAP_FLAG : idem
    e2 = gap_ev(21, "AGENT_HYPOTHESIS", origin="agent_hypothesis", action_code="a1", evidence={"hint": "oversight", "text": "x"})
    h2 = [x for x in run(snap(), [mandate("m1", "B", "duty", "a1")], events=[e2]) if x.origin == "agent_hypothesis"]
    assert h2[0].code == "G8" and h2[0].evidence_basis == "hypothesis"
    board = ev(22, "BOARD", {"msg_id": "M1", "from": "SA", "msg_type": "GAP_FLAG", "body": "personne ne répond", "inject_ref": "inj-001"})
    h3 = [x for x in run(snap(), [], events=[board]) if x.origin == "agent_hypothesis"]
    assert h3 and h3[0].evidence_basis == "hypothesis"
    # l'hypothèse concordante avec un G1 documenté ne devient PAS la preuve : elle reste du contexte d'agent
    g1 = by(run(snap(), [], events=[ev(23, "DECISION", {"decision_id": "D2", "seat_code": "SA", "inject_ref": "inj-001",
                                                         "action_code": "a1", "gap_flags": [{"hint": "no_owner", "text": "t"}]})]), "G1")
    assert g1.origin == "rule" and g1.evidence_basis == "documented"
    assert any(e.is_agent and e.role == "context" for e in g1.evidence)


def test_gap_events_with_rule_origin_are_not_reingested():
    e = gap_ev(30, "ORPHAN_REQUEST", origin="rule", action_code="a1")
    assert by(run(snap(), [mandate("m1", "B", "duty", "a1")], events=[e]), "G1") is None


def test_ablation_of_registry_makes_gap_appear_and_disappear():
    holder = [mandate("m1", "B", "duty", "a1")]
    assert by(run(snap(), holder), "G1") is None
    assert by(run(snap(), []), "G1") is not None  # le document (donc le mandat) retiré de la portée
    assert by(run(snap(), holder), "G1") is None  # ajouté de nouveau : la lacune disparaît


def test_no_country_or_institution_names_in_rule_code():
    import pathlib
    import re
    root = pathlib.Path(__file__).resolve().parents[2] / "app" / "gaps"
    banned = re.compile(r"cameroun|cameroon|emirat|\bUAE\b|\bNCEMA\b|\bTDRA\b|\bMINAT\b|\bMETEO\b|france|senegal", re.I)
    for f in ("rules.py", "detection.py", "scoring.py", "constants.py"):
        assert not banned.search((root / f).read_text(encoding="utf-8")), f


def test_registry_and_demands_are_the_only_inputs():
    # detect est pure : même entrée => même sortie
    s = snap(["life_risk"])
    reg = Registry.build([mandate("m1", "B", "duty", "a2")], {})
    a = detect(s, reg, demands_from_snapshot(s), [])
    b = detect(s, reg, demands_from_snapshot(s), [])
    assert [(c.fingerprint, c.evidence_basis) for c in a] == [(c.fingerprint, c.evidence_basis) for c in b]


def test_gap_without_action_is_titled_by_inject_and_institutions_never_question_mark():
    from app.gaps.detection import _Ctx
    snap = {"scenario": {"language": "fr", "injects": [{"inject_ref": "inj-001", "title": "Crue à Maroua"}]},
            "institutions": [{"id": "I1", "code": "MAIRIE"}], "actions": [], "seats": []}
    ctx = _Ctx(snap, None, [], [])  # type: ignore[arg-type]
    assert ctx.label(None, "inj-001", ["I1"]) == "Crue à Maroua — MAIRIE"
    assert ctx.label(None) == "action non précisée"
    assert "?" not in ctx.label(None, "inj-404")
