"""Métriques pures T1–T6, benchmark, contrôle négatif : « non calculé » n'est jamais 0."""
from __future__ import annotations

import math

import pytest

from app.evaluation import metrics as m
from tests.evaluation.fakes import fp, iso, make_gap, review


def ev(type_, minutes, payload=None, seq=1):
    return {"seq": seq, "type": type_, "real_time": iso(minutes), "payload": payload or {}}


def test_t2_ratio_and_failures():
    events = [ev("CITATION_CHECK", 1, {"citations": [{"chunk_id": "a", "pass": True}, {"chunk_id": "b", "pass": False, "reason": "x"}]}),
              ev("CITATION_CHECK", 2, {"citations": [{"chunk_id": "c", "pass": True}, {"chunk_id": "d", "pass": True}]})]
    r = m.t2_citations(events)
    assert r["status"] == "computed" and r["value"] == 0.75 and r["numerator"] == 3 and r["denominator"] == 4
    assert r["passed"] is False and r["failures"][0]["chunk_id"] == "b"
    assert m.t2_citations([ev("CITATION_CHECK", 1, {"citations": [{"pass": True}] * 19 + [{"pass": False}]})])["passed"] is True


def test_t2_not_computed_is_not_zero():
    r = m.t2_citations([ev("INJECT", 0)])
    assert r["status"] == "not_computed" and r["value"] is None and r["passed"] is None and r["reason"]
    r2 = m.t2_citations([ev("CITATION_CHECK", 1, {"citations": []})])
    assert r2["status"] == "not_computed" and r2["value"] is None


def test_t6_time_and_calls():
    events = [ev("SNAPSHOT", -1, {"ai_mode": "ai"}), ev("INJECT", 0)] + [ev("LLM_CALL", 1)] * 50 + [ev("STATE", 12)]
    r = m.t6_time_calls(events)
    assert r["status"] == "computed" and r["llm_calls"] == 50 and math.isclose(r["wall_seconds"], 720) and r["passed"] is True
    slow = m.t6_time_calls([ev("INJECT", 0), ev("STATE", 25)])
    assert slow["passed"] is False and slow["time_ok"] is False
    many = m.t6_time_calls([ev("INJECT", 0)] + [ev("LLM_CALL", 1)] * 200)
    assert many["passed"] is False and many["calls_ok"] is False
    assert m.t6_time_calls([ev("LLM_CALL", 1)])["status"] == "not_computed"


def test_t6_scripted_note():
    r = m.t6_time_calls([ev("SNAPSHOT", -1, {"ai_mode": "scripted"}), ev("INJECT", 0), ev("STATE", 1)])
    assert r["llm_calls"] == 0 and "sans IA" in r["note"]


def _qs(n):
    return [{"id": str(i), "question": f"q{i}", "expected_doc_code": "DOC", "expected_article": "A1", "category": "national"}
            for i in range(n)]


def test_t1_metrics_values():
    plan = {"q0": [("DOC", "A1")], "q1": [("X", None), ("DOC", "A1")], "q2": [("X", None)] * 6 + [("DOC", "A1")],
            "q3": [("DOC", "A2"), ("Y", None)], "q4": []}
    r = m.t1_retrieval(_qs(5), lambda q: [{"doc_code": c, "article": a} for c, a in plan[q["question"]]])
    assert r["recall_at_5"] == pytest.approx(2 / 5) and r["recall_at_10"] == pytest.approx(3 / 5)
    assert r["mrr"] == pytest.approx((1 + 1 / 2 + 1 / 7) / 5)
    assert r["ndcg_at_10"] == pytest.approx((1 + 1 / math.log2(3) + 1 / math.log2(8)) / 5)
    assert r["insufficient_sample"] is True and r["passed"] is None and r["n_questions"] == 5
    assert len(r["misses"]) == 3 and r["confidence_interval"][0] < 0.4 < r["confidence_interval"][1]


def test_t1_threshold_with_40_questions():
    r = m.t1_retrieval(_qs(40), lambda q: [{"doc_code": "doc", "article": " a1 "}])
    assert r["recall_at_5"] == 1.0 and r["passed"] is True and r["insufficient_sample"] is False


def test_t1_without_questions_not_computed():
    r = m.t1_retrieval([], lambda q: [])
    assert r["status"] == "not_computed" and r["value"] is None


def test_t3_found_missed_new():
    fixtures = [{"expected_gap_key": fp(k), "label": k} for k in "abcd"]
    detected = [make_gap("a"), make_gap("b"), make_gap("c"), make_gap("zz", origin="rule")]
    r = m.t3_expected_gaps(fixtures, detected)
    assert r["value"] == 0.75 and r["passed"] is False
    assert [x["label"] for x in r["missed_fixtures"]] == ["d"]
    assert [x["title"] for x in r["new_gaps"]] == ["Lacune zz"]
    assert m.t3_expected_gaps([], detected)["status"] == "not_computed"


def test_t4_precision_ci_and_kappa():
    gaps = [make_gap("a", reviews=[review("r1", "real"), review("r2", "real")]),
            make_gap("b", reviews=[review("r1", "partially_real"), review("r2", "not_real")]),
            make_gap("c", reviews=[review("r1", "not_real"), review("r2", "not_real")]),
            make_gap("d", reviews=[review("r1", "real"), review("r2", "partially_real")]),
            make_gap("e")]
    r = m.t4_not_invented(gaps)
    assert r["denominator"] == 4 and r["numerator"] == 2 and r["unreviewed"] == 1 and r["value"] == 0.5
    lo, hi = r["confidence_interval"]
    assert 0 < lo < 0.5 < hi < 1
    assert r["kappa"] is not None and -1 <= r["kappa"] <= 1 and "r1" in r["kappa_note"]


def test_t4_single_reviewer_has_no_kappa_and_none_is_not_computed():
    r = m.t4_not_invented([make_gap("a", reviews=[review("r1", "real")])])
    assert r["kappa"] is None and "2 relecteurs" in r["kappa_note"] and r["value"] == 1.0
    z = m.t4_not_invented([make_gap("a", reviews=[review("r1", None, action="comment")])])
    assert z["status"] == "not_computed" and z["value"] is None


def test_kappa_perfect_and_chance():
    assert m.cohen_kappa([("a", "a"), ("b", "b"), ("a", "a")]) == pytest.approx(1.0)
    assert m.cohen_kappa([("a", "b"), ("b", "a")]) == pytest.approx(-1.0)
    assert m.cohen_kappa([("a", "a")]) is None


def test_t5_stability_needs_three_exercises():
    g = lambda *ks: [make_gap(k) for k in ks]  # noqa: E731
    r = m.t5_stability({"e1": g("a", "b", "c"), "e2": g("a", "b", "d"), "e3": g("a", "b", "c")})
    # a,b dans 3/3 ; c dans 2/3 ; d dans 1/3 -> stables : a,b,c sur 4
    assert r["value"] == pytest.approx(3 / 4) and r["found_in_all"] == 2 and r["min_occurrences"] == 2
    two = m.t5_stability({"e1": g("a"), "e2": g("a")})
    assert two["status"] == "not_computed" and two["value"] is None
    assert m.t5_stability({"e1": [], "e2": [], "e3": []})["status"] == "not_computed"


def test_benchmark_and_negative_control():
    r = m.benchmark_match([{"label": "x", "fingerprint": fp("a")}, {"label": "y", "fingerprint": fp("q")},
                           {"label": "z", "fingerprint": None}], [make_gap("a")])
    assert r["value"] == 0.5 and r["not_mappable"] == 1 and r["missed"] == ["y"]
    assert m.benchmark_match([{"label": "z", "fingerprint": None}], [])["status"] == "not_computed"
    nc = m.negative_control([make_gap("a"), make_gap("h", origin="agent_hypothesis"), make_gap("r", status="rejected")], 10)
    assert nc["false_positives"] == 1 and nc["false_positive_rate"] == 0.1 and nc["passed"] is False
    assert m.negative_control([], None)["passed"] is True and m.negative_control([], None)["false_positive_rate"] is None
