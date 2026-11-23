"""Juge IA du scorecard : preuves contrôlées, réponses humaines préservées, aucune lacune dans la fiche de faits."""
from __future__ import annotations

import json
import re
import time

from app.contracts import RawCompletion
from app.core.db import session_scope
from tests.evaluation.fakes import seed_ledger

API = "/api/v1"


class Judge:
    """Faux modèle : 1er critère de chaque dimension = yes (preuve E2 valide), 2e = yes avec une preuve inventée."""

    def __init__(self):
        self.calls = []

    def complete(self, messages, *, schema=None, temperature=0.0, max_tokens=None):  # noqa: ANN001, ANN201
        user = messages[-1].content
        self.calls.append(user)
        ids = re.findall(r"^- (d\d+_m\d+):", user, re.M)
        answers = [{"criterion_id": c, "answer": "not_assessed", "refs": [], "justification": "pas dans la fiche"} for c in ids]
        if ids:
            answers[0] = {"criterion_id": ids[0], "answer": "yes", "refs": ["E2", "X:exercise"], "justification": "inject progressif"}
        if len(ids) > 1:
            answers[1] = {"criterion_id": ids[1], "answer": "yes", "refs": ["E999"], "justification": "preuve inventée"}
        return RawCompletion(text=json.dumps({"answers": answers}), model="judge-m", provider="fake", tokens_in=1,
                             tokens_out=1, ms=1, request_sha256="x", endpoint="local")


def wait(env, jid):  # noqa: ANN001, ANN201
    for _ in range(200):
        j = env.client.get(f"{API}/jobs/{jid}", headers=env.h).json()
        if j["status"] in ("done", "failed"):
            return j
        time.sleep(0.05)
    raise AssertionError("job trop long")


def test_llm_judge_grounds_answers_keeps_humans_and_never_reads_gaps(env):
    ex = env.exercise("EXJ")
    seed_ledger(env.ctx, ex)
    with session_scope(env.ctx.session_factory) as s:  # une lacune dans le ledger ne doit JAMAIS entrer dans la fiche
        env.ctx.service("ledger").append(s, ex, "GAP", "system", {"signal": "SECRET_GAP_SIGNAL"})
    sc = env.client.get(f"{API}/scorecard/exercises/{ex}", headers=env.h).json()
    human = sc["dimensions"][1]["criteria"][0]["criterion_id"]
    env.client.put(f"{API}/scorecard/exercises/{ex}", json={"answers": [{"criterion_id": human, "answer": "no", "note": "humain"}]},
                   headers=env.h)
    judge = Judge()
    env.ctx.services["reform_llm"] = judge

    r = env.client.post(f"{API}/scorecard/exercises/{ex}/assess", headers=env.h)
    assert r.status_code == 202, r.text
    j = wait(env, r.json()["job_id"])
    assert j["status"] == "done", j["error"]
    assert j["result"]["model"] == "fake:judge-m" and j["result"]["independent_of_gaps"] is True
    assert len(judge.calls) == 13 and all("SECRET_GAP_SIGNAL" not in c for c in judge.calls)
    assert "[E2]" in judge.calls[0] and "Crue" in judge.calls[0]

    out = env.client.get(f"{API}/scorecard/exercises/{ex}", headers=env.h).json()
    d1 = out["dimensions"][0]["criteria"]
    assert d1[0]["answer"] == "yes" and d1[0]["assessor"] == "llm-judge:fake:judge-m" and d1[0]["reviewed_by"] is None
    assert {"kind": "event", "ref": {"seq": 2}} in d1[0]["evidence"]
    assert d1[1]["answer"] == "not_assessed" and "aucune preuve valide" in d1[1]["note"]  # preuve inventée rejetée
    kept = next(c for c in out["dimensions"][1]["criteria"] if c["criterion_id"] == human)
    assert kept["answer"] == "no" and kept["note"] == "humain"  # jamais écrasé
    assert out["dimensions_assessed"] >= 13 - 1

    # relancer ne crée aucun doublon et remplace seulement les réponses du juge
    j2 = wait(env, env.client.post(f"{API}/scorecard/exercises/{ex}/assess", headers=env.h).json()["job_id"])
    assert j2["status"] == "done"


def test_llm_judge_is_scoped_to_the_workspace(env):
    ex = env.exercise("EXK", ws=env.ws2)
    assert env.client.post(f"{API}/scorecard/exercises/{ex}/assess", headers=env.h).status_code in (403, 404)
