import json

import pytest

from alerte.analysis.compare import compare_markdown, compare_runs
from alerte.analysis.replay import snapshot
from alerte.knowledge.store import get_store
from alerte.models import Citation
from alerte.sim.adviser import ask
from alerte.sim.citations import check_citation
from alerte.sim.engine import Drill
from alerte.sim.ledger import read_ledger, verify_ledger


@pytest.fixture(scope="module")
def cm_run():
    return Drill("cm01", brain="offline").run()


@pytest.fixture(scope="module")
def ae_run():
    return Drill("ae01", brain="offline").run()


def test_offline_drill_meets_targets(cm_run):
    s = cm_run.summary
    assert s["expected_gap_coverage"]["rate"] >= 0.8, s["expected_gap_coverage"]       # T3
    assert s["citations"]["rate"] >= 0.95                                                 # T2
    assert s["ledger"]["ok"]
    assert s["seconds"] < 1200                                                            # T6
    for name in ("report.md", "report.html", "gaps.json", "decisions.json", "scorecard.json", "ledger.jsonl"):
        assert (cm_run.run_dir / name).exists()


def test_key_gaps_found(cm_run):
    gaps = json.loads((cm_run.run_dir / "gaps.json").read_text(encoding="utf-8"))
    kinds = {(g["type"], g["action"]) for g in gaps}
    assert ("G1", "compel_operator_alert") in kinds          # nobody can order operators to relay alerts
    assert ("G8", "validate_ai_forecast") in kinds           # nobody checks the AI forecast
    assert ("G4", "authorise_transfer_abroad") in kinds      # depends on an authority not confirmed ready
    assert ("G5", "access_location_data") in kinds           # conflicting goals
    for g in gaps:
        assert len({p["jurisdiction"] for p in g["precedents"]}) == len(g["precedents"])  # distinct jurisdictions
        assert g["evidence"]


def test_every_seat_sees_only_its_inbox(cm_run):
    entries = read_ledger(cm_run.run_dir / "ledger.jsonl")
    injects = {e["payload"]["event_id"]: set(e["payload"]["to"]) for e in entries if e["type"] == "INJECT"}
    requests = {(e["payload"]["recipient"], e["payload"]["event_id"]) for e in entries
                if e["type"] == "BOARD" and e["payload"]["type"] == "REQUEST"}
    for e in entries:
        if e["type"] == "RETRIEVAL":
            ev = e["payload"]["event_id"]
            assert e["actor"] in injects[ev] or (e["actor"], ev) in requests, "a seat searched for an event it never received"
    decisions = [e for e in entries if e["type"] == "DECISION"]
    for d in decisions:
        p = d["payload"]
        if p["reasoning_summary"].startswith("Accepted request"):
            continue
        assert p["seat"] in injects[p["event_id"]], "a seat decided on an event it never received"


def test_twin_comparison(cm_run, ae_run):
    c = compare_runs(cm_run.run_dir, ae_run.run_dir)
    assert "G2 issue_weather_warning" in c["only_in_a"]       # two bodies issue weather warnings in CM, one in AE
    assert "G2 decide_public_alert" in c["only_in_b"]         # AE: NCEMA and the Ministry of Interior, no lead named
    assert "G1 compel_operator_alert" not in c["only_in_a"]   # nobody can compel operators in either country
    md = compare_markdown(c)
    assert "| G1 |" in md and "Readiness scorecard" in md


def test_replay_snapshot(cm_run):
    snap = snapshot(cm_run.run_dir, 40)
    assert snap.events and snap.seq == 40
    full = snapshot(cm_run.run_dir)
    assert len(full.events) == 15 and full.gaps


def test_french_drill():
    res = Drill("cm01", brain="offline", lang="fr").run()
    md = (res.run_dir / "report.md").read_text(encoding="utf-8")
    assert "Rapport ALERTE" in md and "Personne n'est compétent" in md


def test_human_seat_decision():
    d = Drill("cm01", brain="offline", human_seats=["MET"])
    assert d.pending_humans() == ["MET"]
    d.step({"MET": {"decision": "Issue an orange warning after a forecaster checks the data", "doc_id": "CM-S01",
                    "quote": "The National Risk Observatory collects and disseminates information on risks",
                    "confidence": "medium"}})
    dec = d.decisions[0]
    assert dec.author == "human" and dec.legal_basis[0].verified is True
    d.step()  # event 2: MET is human but gives no input -> AI takes the seat, logged
    assert any(x.author.startswith("ai (human seat") for x in d.decisions if x.seat == "MET")
    assert verify_ledger(d.run_dir / "ledger.jsonl")["ok"]


def test_surprise_event_and_pause():
    d = Drill("cm01", brain="offline")
    d.pause()
    d.resume()
    d.inject_surprise("A dam operator reports cracks.", ["DPC", "CTD"], ["evacuate_zone"])
    res = d.step()
    assert set(res.recipients) == {"DPC", "CTD"}


def test_citation_checker_catches_invented_article():
    s = get_store()
    good = check_citation(Citation(doc_id="GL-S04", article="Section 6", quote="Corporations face a fine"), s)
    assert good.verified
    fake = check_citation(Citation(doc_id="GL-S04", article="Section 99", quote="operators must pay victims"), s)
    assert fake.verified is False
    missing = check_citation(Citation(doc_id="XX-99", article="Article 1"), s)
    assert missing.verified is False


def test_legal_adviser_four_parts():
    a = ask("Who may order mobile operators to send a public alert?", country="CM")
    assert a.national and a.missing and a.recommendation
    assert len({p.jurisdiction for p in a.elsewhere}) >= 2
    assert "lawyer" in a.disclaimer
