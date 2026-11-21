from __future__ import annotations

import pathlib
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from tests.conftest import auth
from tests.evaluation.fakes import FakeGaps, FakeGuard


@pytest.fixture
def settings(tmp_path: pathlib.Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", log_json=False, log_level="WARNING", llm_mode="scripted",
                    embed_provider="fixture", job_workers=2, bootstrap_enabled=True)


@dataclass
class Env:
    client: TestClient
    ctx: object
    h: dict[str, str]        # espace A
    ws: str
    h2: dict[str, str]       # espace B
    ws2: str
    gaps: FakeGaps
    guard: FakeGuard

    def exercise(self, ex_id: str, ws: str | None = None) -> str:
        self.guard.owners[ex_id] = ws or self.ws
        return ex_id


@pytest.fixture
def env(client: TestClient) -> Env:
    ctx = client.app.state.ctx

    def mk(name: str):
        r = client.post("/api/v1/workspaces", json={"name": name})
        assert r.status_code == 201, r.text
        return auth(r.json()["owner_token"]), r.json()["workspace"]["id"]

    h, ws = mk("A")
    h2, ws2 = mk("B")
    gaps, guard = FakeGaps(), FakeGuard()
    ctx.services["gaps"] = gaps
    ctx.services["exercise_guard"] = guard  # remplace le garde réel (aucun exercice réel dans ces tests)
    return Env(client, ctx, h, ws, h2, ws2, gaps, guard)
