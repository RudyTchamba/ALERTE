from __future__ import annotations

import pathlib
import time
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.ids import new_id
from app.simulation import engine, sse
from app.simulation.engine import SimulationManager
from tests.conftest import auth
from tests.simulation.fakes import (
    FakeAgents,
    FakeGap,
    FakeKnowledge,
    FakeMandates,
    FakeRuntime,
    FakeScenarios,
    FakeSearch,
)

API = "/api/v1"
INST = ("MET", "OPS", "DPC")


@pytest.fixture(autouse=True)
def _fast(monkeypatch):
    monkeypatch.setattr(engine, "POLL_INTERVAL", 0.01)
    monkeypatch.setattr(sse, "POLL_INTERVAL", 0.02)


@pytest.fixture
def settings(tmp_path: pathlib.Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", log_json=False, log_level="CRITICAL", llm_mode="scripted",
                    embed_provider="fixture", job_workers=2, max_concurrent_exercises=3)


def make_scenario(inst: dict[str, str]) -> dict:
    def inj(ref, seq, rec, demands):
        return {"inject_ref": ref, "seq": seq, "sim_time": f"D1 0{seq}:00", "title": f"Inject {seq}", "body": "body",
                "from_actor": "event", "recipients": [inst[c] for c in rec], "tags": ["life_risk"],
                "demands": [{"action_code": d, "derivation": "referential", "justification": "j"} for d in demands],
                "fault_mode": "none", "system_output": None}
    return {"id": new_id(), "code": "SC1", "title": "Scenario", "language": "en",
            "injects": [inj("inj-001", 1, ["MET", "OPS"], ["issue_alert"]), inj("inj-002", 2, ["DPC"], ["relay_alert"])]}


@dataclass
class World:
    client: TestClient
    ctx: Any
    mgr: SimulationManager
    owner: dict
    fac: dict
    aud: dict
    obs: dict
    ws: str
    inst: dict[str, str]
    agent: dict[str, str]
    scenario_id: str
    runtime: FakeRuntime
    agents: FakeAgents
    scenarios: FakeScenarios
    mandates: FakeMandates
    knowledge: FakeKnowledge
    search: FakeSearch
    gap: FakeGap
    extra: dict = field(default_factory=dict)

    def seats(self, controllers: dict[str, str] | None = None, codes=INST) -> list[dict]:
        controllers = controllers or {}
        out = []
        for c in codes:
            ctrl = controllers.get(c, "agent")
            out.append({"code": c, "institution_id": self.inst[c], "agent_id": self.agent[c], "controller": ctrl,
                        "human_name": f"Human {c}" if ctrl == "human" else None})
        return out

    def new_exercise(self, controllers=None, settings=None, ai_mode="scripted", pace=None, codes=INST) -> str:
        body: dict = {"scenario_id": self.scenario_id, "title": "Ex", "ai_mode": ai_mode}
        if settings:
            body["settings"] = settings
        if pace:
            body["pace"] = pace
        r = self.client.post(f"{API}/exercises", json=body, headers=self.fac)
        assert r.status_code == 201, r.text
        ex_id = r.json()["id"]
        r = self.client.put(f"{API}/exercises/{ex_id}/seats", json={"seats": self.seats(controllers, codes)},
                            headers=self.fac)
        assert r.status_code == 200, r.text
        return ex_id

    def cmd(self, ex_id: str, kind: str, args: dict | None = None, who=None):
        return self.client.post(f"{API}/exercises/{ex_id}/commands", json={"kind": kind, "args": args or {}},
                                headers=who or self.fac)

    def start(self, ex_id: str):
        r = self.cmd(ex_id, "start")
        assert r.status_code == 202, r.text
        return r

    def wait(self, ex_id: str, states_: set[str], timeout: float = 20.0) -> str:
        ex = self.mgr.wait_until(ex_id, lambda e: e.state in states_, timeout)
        assert ex.state in states_, f"état {ex.state} (attendu {states_})"
        self.mgr.join(ex_id, 10)
        return ex.state

    def run(self, ex_id: str) -> str:
        self.start(ex_id)
        return self.wait(ex_id, {"completed", "stopped", "paused", "interrupted"})

    def ledger(self, ex_id: str, who=None) -> list[dict]:
        r = self.client.get(f"{API}/exercises/{ex_id}/ledger?limit=5000", headers=who or self.aud)
        assert r.status_code == 200, r.text
        return r.json()

    def verify(self, ex_id: str) -> dict:
        return self.client.get(f"{API}/exercises/{ex_id}/ledger/verify", headers=self.aud).json()

    def digest(self, ex_id: str) -> str:
        return self.client.get(f"{API}/exercises/{ex_id}/replay-digest", headers=self.aud).json()["replay_digest"]

    def token(self, role: str, **kw) -> dict:
        r = self.client.post(f"{API}/tokens", json={"role": role, **kw}, headers=self.owner)
        assert r.status_code == 201, r.text
        return auth(r.json()["token"])


@pytest.fixture
def world(client: TestClient, app, owner) -> World:
    ctx = app.state.ctx
    ws = client.get(f"{API}/workspaces/current", headers=owner).json()["id"]
    inst = {}
    for code in INST:
        r = client.post(f"{API}/institutions", json={"code": code, "name": f"Inst {code}", "kind": "agency"}, headers=owner)
        assert r.status_code == 201, r.text
        inst[code] = r.json()["id"]
    runtime = FakeRuntime()
    agents, scenarios = FakeAgents(ws, runtime), FakeScenarios(ws)
    agent = {}
    for code in INST:
        aid = new_id()
        agent[code] = aid
        agents.agents[aid] = {"id": aid, "code": f"AG-{code}", "role_kind": "institution", "mission": f"mission {code}",
                              "instructions": "be brief", "tools": ["search_kb", "ask_legal", "post", "decide"],
                              "limits": {"max_steps": 4, "max_search_calls": 2, "max_legal_calls_per_inject": 1},
                              "model_profile": {"provider": "scripted", "model": "s"}, "institution_id": inst[code]}
        agents.grants[aid] = ["kb1"]
    scen = make_scenario(inst)
    scenarios.scenarios[scen["id"]] = scen
    mandates, knowledge, search, gap = FakeMandates(), FakeKnowledge(), FakeSearch(), FakeGap()
    mandates.mandates = [{"id": f"m-{c}", "institution_id": inst[c], "kind": "duty", "action_code": "issue_alert",
                          "description": "d", "procedure_status": "validated", "sources": []} for c in INST]
    ctx.services.update({"agents": agents, "scenarios": scenarios, "mandates": mandates, "knowledge": knowledge,
                         "search": search, "gap_engine": gap})
    w = World(client, ctx, ctx.service("simulation"), owner, {}, {}, {}, ws, inst, agent, scen["id"], runtime, agents,
              scenarios, mandates, knowledge, search, gap)
    w.fac, w.aud, w.obs = w.token("facilitator"), w.token("auditor"), w.token("observer")
    yield w
    w.mgr.shutdown(5)


def wait_for(pred, timeout: float = 10.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        v = pred()
        if v:
            return v
        time.sleep(0.02)
    raise AssertionError("condition non atteinte")
