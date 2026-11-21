"""Assemblage du contenu JSON sur données fabriquées (fonction pure) : séparation constats/hypothèses, étiquettes, limites."""
from __future__ import annotations

from app.reports import assemble as asm
from tests.evaluation.fakes import make_gap, review
from tests.reports.conftest import SNAPSHOT


def inputs(gaps, ai_mode="ai", **kw):
    base = {"report": {"id": "R1", "title": "Rapport", "version_no": 1, "generated_at": "2026-11-21T10:00:00Z",
                       "confidentiality": "internal", "parent_version_no": None},
            "exercise": {"id": "EX1", "code": "EX-001", "title": "Exercice", "ai_mode": ai_mode, "snapshot_sha256": "a" * 64,
                         "commitment_sha256": "b" * 64},
            "snapshot": SNAPSHOT, "ledger": {"head_seq": 9, "head_hash": "c" * 64, "events": 9,
                                             "verify": {"ok": True, "checked": 9}},
            "events": [], "gaps": gaps, "kb": {"inventory": [], "coverage": {"ratio": 0.5, "expected": 4, "present": 2, "missing": ["X"]}},
            "scorecard": None, "metrics": None, "prior_links": []}
    base.update(kw)
    return base


def test_findings_and_hypotheses_are_separated_and_rejected_excluded():
    c = asm.assemble(inputs([make_gap("a", severity=2), make_gap("b", severity=3, status="confirmed"),
                             make_gap("h", basis="hypothesis", origin="agent_hypothesis"), make_gap("x", basis="hypothesis"),
                             make_gap("r", status="rejected")]))
    assert [f["id"] for f in c["findings"]] == ["gap-b", "gap-a"]  # gravité décroissante
    assert {h["id"] for h in c["hypotheses"]} == {"gap-h", "gap-x"}
    assert not ({f["id"] for f in c["findings"]} & {h["id"] for h in c["hypotheses"]})
    assert [g["id"] for g in c["annexes"]["rejected_gaps"]] == ["gap-r"]
    s = c["executive_summary"]
    assert s["findings_count"] == 2 and s["hypotheses_count"] == 2 and s["rejected_count"] == 1
    assert s["findings_by_severity"] == {"3": 1, "2": 1, "1": 0}
    assert c["schema"] == "alerte.report/1" and c["cover"]["ledger"]["head_seq"] == 9


def test_no_ai_label_in_cover_and_content():
    for mode, label in (("scripted", "SANS IA"), ("cassette", "REJEU")):
        c = asm.assemble(inputs([make_gap("a")], ai_mode=mode))
        assert c["banner"] == label and c["cover"]["ai_label"] == label
        assert label in c["methodology"]["ai_notice"] and any(label in x for x in c["limits"])
    ai = asm.assemble(inputs([make_gap("a")], ai_mode="ai"))
    assert ai["banner"] is None and ai["cover"]["ai_label"] is None and ai["methodology"]["ai_notice"] is None
    assert asm.assemble(inputs([], ai_mode=None))["banner"] == "MODE IA NON DÉTERMINÉ"


def test_scripted_observed_signal_is_caveated():
    c = asm.assemble(inputs([make_gap("a", basis="observed")], ai_mode="scripted"))
    assert any("mode sans IA" in x for x in c["findings"][0]["caveats"])


def test_absence_statement_uses_corpus_and_coverage():
    c = asm.assemble(inputs([make_gap("a"), make_gap("c", code="G6", registry_state="partial", negative_searches=[]),
                             make_gap("d", code="X1", negative_searches=[])]))
    by = {f["id"]: f for f in c["findings"]}
    assert by["gap-a"]["absence_statement"] == "non trouvée dans le corpus K (12 documents ; couverture 80 %)"
    assert "non trouvée dans le corpus K" in by["gap-c"]["absence_statement"] and "couverture 80 %" in by["gap-c"]["absence_statement"]
    assert "registre des mandats non entièrement revu" in by["gap-c"]["absence_statement"] and "sans mandat" in by["gap-c"]["absence_statement"]
    assert by["gap-d"]["absence_statement"] is None  # règle non « absence » et pas de recherche négative


def test_references_need_two_jurisdictions():
    one = make_gap("a", references=[{"status": "accepted", "reference": {"jurisdiction": "EU", "instrument": "AI Act"}}])
    two_same = make_gap("b", references=[{"status": "accepted", "reference": {"jurisdiction": "EU"}},
                                         {"status": "suggested", "reference": {"jurisdiction": " eu "}}])
    ok = make_gap("c")
    c = asm.assemble(inputs([one, two_same, ok]))
    refs = {r["gap_id"]: r for r in c["references"]}
    assert refs["gap-a"]["status"] == "insufficient_sources" and "insuffisantes : 1" in refs["gap-a"]["message"]
    assert refs["gap-b"]["status"] == "insufficient_sources"
    assert refs["gap-c"]["status"] == "sufficient" and refs["gap-c"]["message"] is None


def test_plan_is_separate_and_reviews_summarised():
    c = asm.assemble(inputs([make_gap("a", status="disputed", reviews=[review("r1", "partially_real", "dispute", "disputed")])]))
    assert c["improvement_plan"][0]["recommendation"] == "Désigner un responsable" and c["improvement_plan"][0]["owner"].startswith("MET")
    assert "recommendation" not in c["findings"][0]
    assert c["reviews"]["by_reality_label"] == {"partially_real": 1} and c["reviews"]["disputed"] == ["gap-a"]
    assert c["reviews"]["history"][0]["reviewer"] == "r1"


def test_not_assessed_and_not_computed_are_never_zero():
    c = asm.assemble(inputs([make_gap("a")]))
    assert c["scorecard"]["status"] == "not_available" and c["scorecard"]["dimensions"] == []
    assert all(m["status"] == "not_computed" and m["value"] is None and m["text"] == "non calculé" for m in c["metrics"].values())
    assert any("Métrique T3 : non calculée" in x for x in c["limits"])
    sc = {"overall_status": "not_assessed", "overall_score": None, "scale": "0-5", "dimensions_assessed": 0, "dimensions_total": 1,
          "note": "n", "dimensions": [{"number": 1, "name": "D", "score": None, "assessed": 0, "total": 2}]}
    c2 = asm.assemble(inputs([], scorecard=sc, metrics={"T2": {"status": "computed", "value": 0.97, "passed": True}}))
    assert c2["scorecard"]["dimensions"][0]["status"] == "non évalué" and c2["scorecard"]["dimensions"][0]["score"] is None
    assert c2["metrics"]["T2"]["value"] == 0.97 and c2["metrics"]["T1"]["value"] is None
    assert any("non évalué" in x for x in c2["limits"])


def test_limits_cover_corpus_ocr_scripted_fictive_and_integrity():
    c = asm.assemble(inputs([make_gap("a")], ledger={"head_seq": 3, "head_hash": "d" * 64, "events": 3,
                                                       "verify": {"ok": False, "first_bad_seq": 2, "reason": "hash invalide"}}))
    text = " ".join(c["limits"])
    for needle in ("FICTIF", "couverture documentaire attendue/présente 50 %", "OCR", "n'est jamais une preuve d'inexistence",
                   "infalsifiable", "ALERTE INTÉGRITÉ", "n° 2"):
        assert needle in text, needle


def test_gap_service_unavailable_is_not_zero():
    c = asm.assemble(inputs(None))
    assert c["executive_summary"]["gaps_available"] is False and c["executive_summary"]["findings_count"] is None
    assert any("indisponible" in x for x in c["limits"])


def test_content_is_json_safe_and_hashable():
    import datetime as dt

    from app.core.canonical_json import canonical_sha256
    g = make_gap("a", negative_searches=[{"corpus_documents": 3, "corpus_coverage": 0.5, "run_at": dt.datetime(2026, 1, 1, tzinfo=dt.UTC)}])
    c = asm.assemble(inputs([g]))
    assert len(canonical_sha256(c)) == 64
