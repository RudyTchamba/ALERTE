from __future__ import annotations

import time
from typing import Any

import pytest

import tests.evaluation.conftest as _ec
from tests.evaluation.conftest import Env
from tests.evaluation.fakes import FakeKnowledge, make_gap, review, seed_ledger

API = "/api/v1"
settings = _ec.settings  # fixtures partagées (réexportées pour pytest)
env = _ec.env

SNAPSHOT: dict[str, Any] = {
    "workspace_id": "w", "exercise": {"id": "EX1", "code": "EX-001", "title": "Exercice crue", "ai_mode": "ai", "settings": {}},
    "scenario": {"id": "s", "code": "SC1", "title": "Crue éclair", "language": "fr", "injects": [
        {"inject_ref": "inj-001", "seq": 1, "sim_time": "D1 06:00", "title": "Crue", "body": "...", "recipients": ["i1"], "tags": [],
         "demands": [{"action_code": "act_a", "derivation": "referential"}, {"action_code": "act_b", "derivation": "scenario_author"}],
         "fault_mode": "none", "system_output": None}]},
    "institutions": [{"id": "inst-1", "code": "MET", "name": "Météo nationale", "kind": "agency", "country_id": "c", "domains": []},
                     {"id": "inst-2", "code": "DPC", "name": "Protection civile", "kind": "ministry", "country_id": "c", "domains": []}],
    "seats": [{"seat_id": "x", "code": "MET", "institution_id": "inst-1", "controller": "agent", "agent": {}}],
    "kb": [{"kb_id": "KB1", "code": "NAT", "name": "Corpus national", "document_version_ids": ["dv1"]}],
    "grants": {}, "mandates": [], "actions": []}


@pytest.fixture
def rep(env: Env) -> Env:
    """Environnement reports : snapshot, KB, ledger et lacunes fabriqués (aucun vrai modèle)."""
    env.ctx.services["snapshot_loader"] = lambda session, ex: (SNAPSHOT, "a" * 64)
    env.ctx.services["knowledge"] = FakeKnowledge({"KB1": {"dv1"}}, coverage=0.75)
    ex = env.exercise("EX1")
    seed_ledger(env.ctx, ex, ai_mode="ai", citations=(19, 20))
    env.gaps.put(env.ws, ex, [
        make_gap("a", severity=3, status="confirmed", reviews=[review("r1", "real")]),
        make_gap("b", code="G3", severity=2),
        make_gap("h", basis="hypothesis", origin="agent_hypothesis", severity=1),
        make_gap("rej", status="rejected", reviews=[review("r1", "not_real", "reject", "rejected")]),
    ])
    return env


def generate(env: Env, ex: str = "EX1", **body: Any) -> dict[str, Any]:
    r = env.client.post(f"{API}/exercises/{ex}/reports", json=body, headers=env.h)
    assert r.status_code == 202, r.text
    jid = r.json()["job_id"]
    for _ in range(300):
        job = env.ctx.jobs.get(jid)
        if job["status"] in ("done", "failed"):
            break
        time.sleep(0.05)
    assert job["status"] == "done", job
    return job["result"]


def version(env: Env, vid: str) -> dict[str, Any]:
    r = env.client.get(f"{API}/report-versions/{vid}", headers=env.h)
    assert r.status_code == 200, r.text
    return r.json()
