"""API evaluation de bout en bout : ledger fabriqué, lacunes simulées (service `gaps` faux), isolation inter-espaces."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import update

from app.core.db import session_scope
from app.evaluation.fixtures.models import EvalFixture
from app.evaluation.service import compute_t2, compute_t6
from tests.evaluation.fakes import FakeKnowledge, FakeSearch, fp, make_gap, review, seed_ledger

API = "/api/v1"


def run(env, ex, metric, **params):
    return env.client.post(f"{API}/evaluation/exercises/{ex}/run", params={"metric": metric, **params}, headers=env.h)


def test_t2_t6_from_ledger(env):
    ex = env.exercise("EX1")
    seed_ledger(env.ctx, ex, llm_calls=7, minutes=12, citations=(19, 20))
    r = run(env, ex, "T2").json()
    assert r["status"] == "computed" and r["value"] == 0.95 and r["passed"] is True and r["denominator"] == 20
    r = run(env, ex, "t6").json()
    assert r["status"] == "computed" and r["llm_calls"] == 7 and r["passed"] is True
    with session_scope(env.ctx.session_factory) as s:  # signatures du contrat : compute_t2(session, exercise_id)
        assert compute_t2(s, ex)["value"] == 0.95 and compute_t6(s, ex)["llm_calls"] == 7
    g = env.client.get(f"{API}/evaluation/exercises/{ex}", headers=env.h).json()
    assert g["metrics"]["T2"]["status"] == "computed"
    for k in ("T1", "T3", "T4", "T5"):  # jamais lancées : « non calculé », pas 0
        assert g["metrics"][k]["status"] == "not_computed" and g["metrics"][k]["value"] is None


def test_t2_without_ledger_is_not_computed_and_persisted(env):
    ex = env.exercise("EX0")
    r = run(env, ex, "T2").json()
    assert r["status"] == "not_computed" and r["value"] is None and r["run_id"]
    assert run(env, ex, "T9").status_code == 422


def test_t1_questions_import_csv_and_run(env):
    kb = "KB1"
    env.ctx.services["knowledge"] = FakeKnowledge({kb: {"dv1"}})
    plan = {"Qui coordonne les secours ?": [("CM-S01", "Art. 4")], "Quel texte régit les données ?": [("CM-S01", "Art. 9")]}
    search = FakeSearch(plan)
    env.ctx.services["search"] = search
    ex = env.exercise("EX1")
    # sans jeu de questions : non calculé
    assert run(env, ex, "T1", kb_id=kb).json()["status"] == "not_computed"
    csv_bytes = ("question;expected_doc_code;expected_article;lang;category\n"
                 "Qui coordonne les secours ?;CM-S01;Art. 4;fr;national\n"
                 "Quel texte régit les données ?;CM-S02;;fr;national\n").encode("utf-8-sig")
    r = env.client.post(f"{API}/evaluation/kbs/{kb}/questions/import", files={"file": ("q.csv", csv_bytes, "text/csv")}, headers=env.h)
    assert r.status_code == 201 and len(r.json()) == 2
    res = run(env, ex, "T1", kb_id=kb).json()
    assert res["status"] == "computed" and res["recall_at_5"] == 0.5 and res["insufficient_sample"] is True
    assert res["scope_hash"] and res["kb_ids"] == [kb]
    assert search.scopes[0].purpose == "eval" and search.scopes[0].workspace_id == env.ws
    bad = env.client.post(f"{API}/evaluation/kbs/{kb}/questions/import", files={"file": ("q.csv", b"a,b\n1,2\n", "text/csv")}, headers=env.h)
    assert bad.status_code == 422
    # KB d'un autre espace (le service knowledge lève NotFound) -> 404
    assert env.client.post(f"{API}/evaluation/kbs/OTHER/questions", json=[{"question": "abc?", "expected_doc_code": "X"}],
                           headers=env.h).status_code == 404


def seal(env, key, label, scenario="SC1"):
    r = env.client.post(f"{API}/evaluation/fixtures", json={"scenario_code": scenario, "expected_gap_key": key, "label": label}, headers=env.h)
    assert r.status_code == 201, r.text
    return r.json()


def test_t3_sealed_fixtures_found_missed_new(env):
    seal(env, fp("a"), "A")
    seal(env, fp("b"), "B")
    ex = env.exercise("EX3")
    seed_ledger(env.ctx, ex, start=dt.datetime.now(dt.UTC) + dt.timedelta(minutes=5))  # run APRÈS le scellement
    env.gaps.put(env.ws, ex, [make_gap("a"), make_gap("new")])
    r = run(env, ex, "T3", scenario_code="SC1").json()
    assert r["status"] == "computed" and r["value"] == 0.5 and r["sealed_before_run"] is True
    assert [x["label"] for x in r["missed_fixtures"]] == ["B"] and [x["title"] for x in r["new_gaps"]] == ["Lacune new"]
    assert len(r["sealed_sha256"]) == 2
    # une seconde fixture identique est refusée (scellée, immuable)
    assert env.client.post(f"{API}/evaluation/fixtures", json={"scenario_code": "SC1", "expected_gap_key": fp("a"), "label": "A'"},
                           headers=env.h).status_code == 409


def test_t3_not_computed_when_sealed_after_run_or_tampered_or_missing(env):
    ex = env.exercise("EX3")
    seed_ledger(env.ctx, ex, start=dt.datetime.now(dt.UTC) - dt.timedelta(hours=1))  # run AVANT le scellement
    env.gaps.put(env.ws, ex, [make_gap("a")])
    assert run(env, ex, "T3", scenario_code="NOPE").json()["reason"].startswith("aucune fixture")
    assert run(env, ex, "T3").json()["reason"].startswith("scénario inconnu")
    seal(env, fp("a"), "A")
    late = run(env, ex, "T3", scenario_code="SC1").json()
    assert late["status"] == "not_computed" and "APRÈS" in late["reason"] and late["value"] is None
    ex2 = env.exercise("EX4")
    seed_ledger(env.ctx, ex2, start=dt.datetime.now(dt.UTC) + dt.timedelta(minutes=5))
    env.gaps.put(env.ws, ex2, [make_gap("a")])
    with session_scope(env.ctx.session_factory) as s:  # altération directe de la base
        s.execute(update(EvalFixture).values(label="falsifié"))
    t = run(env, ex2, "T3", scenario_code="SC1").json()
    assert t["status"] == "not_computed" and "altérées" in t["reason"]


def test_t4_t5_benchmark_negative_control(env):
    ex = env.exercise("EX5")
    env.gaps.put(env.ws, ex, [make_gap("a", reviews=[review("r1", "real")]), make_gap("b", reviews=[review("r1", "not_real")])])
    r = run(env, ex, "T4").json()
    assert r["value"] == 0.5 and r["denominator"] == 2
    clones = [env.exercise("EX6"), env.exercise("EX7")]
    for c in clones:
        env.gaps.put(env.ws, c, [make_gap("a")])
    assert run(env, ex, "T5").json()["status"] == "not_computed"  # 1 seul exercice
    t5 = run(env, ex, "T5", clone_id=clones).json()
    assert t5["status"] == "computed" and t5["value"] == 0.5 and t5["denominator"] == 2 and t5["numerator"] == 1
    assert run(env, ex, "T5", clone_id=["FOREIGN"]).status_code == 404
    bs = env.client.post(f"{API}/evaluation/benchmark-sets", json={"name": "IFRC", "source": "IFRC CM-12"}, headers=env.h).json()
    env.client.post(f"{API}/evaluation/benchmark-sets/{bs['id']}/items", headers=env.h,
                    json=[{"label": "x", "fingerprint": fp("a")}, {"label": "y", "fingerprint": fp("q")}])
    b = run(env, ex, "benchmark", benchmark_set_id=bs["id"]).json()
    assert b["value"] == 0.5 and b["missed"] == ["y"]
    nc = run(env, ex, "negative_control", max_gaps=5).json()
    assert nc["false_positives"] == 2 and nc["passed"] is True and nc["false_positive_rate"] is None


def test_isolation_between_workspaces(env):
    ex = env.exercise("EX1")
    seed_ledger(env.ctx, ex)
    assert env.client.get(f"{API}/evaluation/exercises/{ex}", headers=env.h2).status_code == 404
    assert env.client.post(f"{API}/evaluation/exercises/{ex}/run", params={"metric": "T2"}, headers=env.h2).status_code == 404
    assert env.client.get(f"{API}/scorecard/exercises/{ex}", headers=env.h2).status_code == 404
    seal(env, fp("a"), "A")
    assert env.client.get(f"{API}/evaluation/fixtures", params={"scenario_code": "SC1"}, headers=env.h2).json() == []
    assert env.client.get(f"{API}/evaluation/fixtures", params={"scenario_code": "SC1"}, headers=env.h).json()[0]["seal_valid"] is True
    assert env.client.get(f"{API}/evaluation/exercises/{ex}").status_code == 401
