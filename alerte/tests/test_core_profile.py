"""The hackathon core profile (Technical Report v2): UAE first, six agents, 12 events, seven gap rules,
Legal Adviser consultation, at most 150 model calls."""

from __future__ import annotations

import json

import pytest

from alerte.sim.engine import Drill
from alerte.sim.ledger import read_ledger, verify_ledger

RULES = {"G1", "G2", "G3", "G6", "G7", "G8", "G9"}


@pytest.fixture(scope="module")
def ae():
    return Drill("ae-core", brain="offline").run()


@pytest.fixture(scope="module")
def cm():
    return Drill("cm-core", brain="offline").run()


def _gaps(res):
    return json.loads((res.run_dir / "gaps.json").read_text(encoding="utf-8"))


def test_only_the_seven_core_rules_fire(ae, cm):
    for res in (ae, cm):
        types = {g["type"] for g in _gaps(res)}
        assert types <= RULES, types - RULES
        assert {"G1", "G6", "G7", "G8", "G9"} <= types


def test_core_scenarios_are_twins_with_twelve_events():
    for sid in ("ae-core", "cm-core"):
        d = Drill(sid, brain="offline")
        assert len(d.scenario.events) == 12 and d.scenario.profile == "core"
        assert set(d.seats) == {"MET", "DPC", "OPS", "ART", "ANTIC", "HYDRO"}   # five institutions + the AI under test; LEGAL is the adviser
        assert "LEGAL" in d.roles and "HYDRO" in d.roles


def test_uae_core_targets(ae):
    s = ae.summary
    assert s["expected_gap_coverage"]["rate"] >= 0.8, s["expected_gap_coverage"]       # T3
    assert s["citations"]["rate"] >= 0.95                                               # T2
    assert s["ledger"]["ok"] and s["seconds"] < 1200                                    # T6


def test_uae_has_no_operator_relay_duty_and_two_issuers(ae):
    kinds = {(g["type"], g["action"]) for g in _gaps(ae)}
    assert ("G1", "compel_operator_alert") in kinds          # no text found obliging operators to relay (report, gap G1)
    assert ("G2", "decide_public_alert") in kinds            # NCEMA and the Ministry of Interior, no lead (gap G2)
    assert ("G3", "human_validate_ai_alert") in kinds        # no check before an AI-drafted alert (gap G3)
    assert ("G8", "authorise_automatic_ai_alert") in kinds   # stress test: vendor auto-send (G3, G8 escalated)
    assert ("G7", "multilingual_alerting") in kinds          # TS040 English and Arabic only


def test_each_gap_has_two_precedents_from_different_jurisdictions(ae, cm):
    for res in (ae, cm):
        for g in _gaps(res):
            js = [p["jurisdiction"] for p in g["precedents"]]
            assert len(js) == len(set(js))
            assert len(js) >= 2, f"{g['gap_id']} has fewer than two precedents"


def test_seats_consult_the_legal_adviser(ae):
    entries = read_ledger(ae.run_dir / "ledger.jsonl")
    legal = [e for e in entries if e["type"] == "LEGAL"]
    assert legal and all(e["payload"]["answer"]["disclaimer"] for e in legal)
    board = [e["payload"] for e in entries if e["type"] == "BOARD" and e["payload"]["sender"] == "LEGAL"]
    assert board and all("lawyer" in m["text"].lower() or "avocat" in m["text"].lower() or "juriste" in m["text"].lower() for m in board)


def test_no_seat_acts_outside_its_inbox(ae):
    entries = read_ledger(ae.run_dir / "ledger.jsonl")
    injects = {e["payload"]["event_id"]: set(e["payload"]["to"]) for e in entries if e["type"] == "INJECT"}
    for e in entries:
        if e["type"] == "DECISION" and not e["payload"]["reasoning_summary"].startswith("Accepted request"):
            assert e["actor"] in injects[e["payload"]["event_id"]]


def test_llm_budget_under_150_calls(mock_llm):
    res = Drill("ae-core", brain="llm").run()
    calls = [e for e in read_ledger(res.run_dir / "ledger.jsonl") if e["type"] == "LLM_CALL"]
    assert 0 < len(calls) <= 150, len(calls)
    assert verify_ledger(res.run_dir / "ledger.jsonl")["ok"]
