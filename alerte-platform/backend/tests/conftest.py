from __future__ import annotations

import pathlib

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path: pathlib.Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", log_json=False, log_level="WARNING", llm_mode="scripted",
                    embed_provider="fixture", job_workers=2)


@pytest.fixture
def app(settings: Settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def owner(client: TestClient) -> dict[str, str]:
    """Espace + en-têtes du jeton propriétaire."""
    r = client.post("/api/v1/workspaces", json={"name": "Espace de test"})
    assert r.status_code == 201, r.text
    return auth(r.json()["owner_token"])


def make_workspace(client: TestClient, name: str) -> dict[str, str]:
    owner_token = None
    first = client.post("/api/v1/workspaces", json={"name": name})
    if first.status_code == 201:
        owner_token = first.json()["owner_token"]
    return auth(owner_token) if owner_token else {}
