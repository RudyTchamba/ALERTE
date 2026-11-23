"""Scorecard (13 dimensions, « non évalué » ≠ 0, indépendance des lacunes) et isolation des fixtures T3."""
from __future__ import annotations

import ast
import json
import pathlib

from app.evaluation import scorecard
from app.evaluation.scorecard import dimension_score

API = "/api/v1"
APP = pathlib.Path(__file__).resolve().parents[2] / "app"


def test_framework_copy_is_13_dimensions_with_notice():
    fw = scorecard.load_framework()
    assert [d["id"] for d in fw["dimensions"]] == list(range(1, 14))
    assert fw["dimensions"][0]["name"] == "Data/Model Marketplace" and fw["dimensions"][12]["name"] == "Digital Infrastructure"
    notice = (scorecard.FRAMEWORK_DIR / "NOTICE").read_text(encoding="utf-8")
    assert "ITU" in notice and "MIT" in notice and "ne définit NI échelle" in notice
    json.loads((scorecard.FRAMEWORK_DIR / "dimensions.json").read_text(encoding="utf-8"))


def test_dimension_score_not_assessed_is_never_zero():
    assert dimension_score([(1, "not_assessed"), (1, "not_assessed")])["score"] is None
    assert dimension_score([(1, "not_assessed")])["status"] == "not_assessed"
    assert dimension_score([(1, "no"), (1, "not_assessed")])["score"] == 0.0  # un « non » évalué est un vrai 0
    assert dimension_score([(1, "yes"), (1, "no"), (2, "not_assessed")])["score"] == 2.5
    assert dimension_score([(1, "yes"), (3, "partial")])["score"] == 5 * (1 + 1.5) / 4


def test_scorecard_api_defaults_to_not_assessed_then_scores(env):
    ex = env.exercise("EX1")
    sc = env.client.get(f"{API}/scorecard/exercises/{ex}", headers=env.h).json()
    assert len(sc["dimensions"]) == 13 and sc["overall_score"] is None and sc["overall_status"] == "not_assessed"
    assert all(d["score"] is None and d["status"] == "not_assessed" for d in sc["dimensions"])
    crit = sc["dimensions"][0]["criteria"]
    body = {"answers": [{"criterion_id": crit[0]["criterion_id"], "answer": "yes", "evidence": [{"kind": "chunk", "ref": "c1"}]},
                        {"criterion_id": crit[1]["criterion_id"], "answer": "no", "note": "rien dans le corpus"},
                        {"criterion_id": crit[2]["criterion_id"], "answer": "not_assessed"}], "reviewed_by": "revue"}
    out = env.client.put(f"{API}/scorecard/exercises/{ex}", json=body, headers=env.h).json()
    d1 = out["dimensions"][0]
    assert d1["score"] == 2.5 and d1["assessed"] == 2 and out["dimensions"][1]["score"] is None
    assert out["overall_score"] == 2.5 and out["dimensions_assessed"] == 1
    assert d1["criteria"][0]["reviewed_by"] == "revue"
    # mise à jour (upsert)
    body["answers"] = [{"criterion_id": crit[1]["criterion_id"], "answer": "partial", "note": "partiel"}]
    assert env.client.put(f"{API}/scorecard/exercises/{ex}", json=body, headers=env.h).json()["dimensions"][0]["score"] == 3.75


def test_scorecard_validation_and_independence_from_gaps(env):
    ex = env.exercise("EX1")
    cid = env.client.get(f"{API}/scorecard/exercises/{ex}", headers=env.h).json()["dimensions"][0]["criteria"][0]["criterion_id"]

    def put(a):
        return env.client.put(f"{API}/scorecard/exercises/{ex}", json={"answers": [a]}, headers=env.h)

    assert put({"criterion_id": cid, "answer": "yes"}).status_code == 422  # ni preuve ni note
    assert put({"criterion_id": "zzz", "answer": "yes", "note": "n"}).status_code == 422
    assert put({"criterion_id": cid, "answer": "maybe", "note": "n"}).status_code == 422
    assert put({"criterion_id": cid, "answer": "yes", "evidence": [{"kind": "gap", "ref": "g1"}]}).status_code == 422
    assert env.client.post(f"{API}/scorecard/exercises/{ex}/assess", headers=env.h).status_code == 202  # juge IA (tâche)
    # ni le scorecard ni son juge IA ne référencent les lacunes
    for name in ("scorecard.py", "judge.py"):
        src = (APP / "evaluation" / name).read_text(encoding="utf-8")
        assert "gaps" not in {n.module.split(".")[-1] for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ImportFrom) and n.module}
        assert "gaps_port" not in src and "read_gaps" not in src and "FROM gap" not in src


def _imports(path: pathlib.Path) -> list[str]:
    out = []
    for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(n, ast.Import):
            out += [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            out.append(("." * n.level) + (n.module or "") + "|" + ",".join(a.name for a in n.names))
    return out


def test_fixtures_are_private_to_evaluation():
    """Architecture : aucun module hors `app/evaluation` n'importe `evaluation.fixtures` ni ne lit `eval_fixture`."""
    offenders = []
    for py in APP.rglob("*.py"):
        rel = py.relative_to(APP)
        if rel.parts[0] == "evaluation":
            continue
        text = py.read_text(encoding="utf-8")
        if "eval_fixture" in text or "EvalFixture" in text or "evaluation.fixtures" in text:
            offenders.append(str(rel))
        for imp in _imports(py):
            if "evaluation" in imp and "fixtures" in imp:
                offenders.append(f"{rel}: {imp}")
    assert offenders == []
    # et à l'intérieur d'evaluation, seuls service/router/models/fixtures y touchent (pas la grille, ni les métriques pures)
    inside = [p.name for p in (APP / "evaluation").glob("*.py") if any("fixtures" in i for i in _imports(p))]
    assert set(inside) <= {"models.py", "service.py", "router.py"}


def test_reports_module_never_reads_fixtures_table():
    for py in (APP / "reports").rglob("*.py"):
        assert "fixtures" not in py.read_text(encoding="utf-8"), py
