from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth

API = "/api/v1"


class FakeKnowledge:
    """Faux service `knowledge` (contrat CONTRACTS.md) : chunks en mémoire."""

    def __init__(self) -> None:
        self.chunks: dict[str, dict] = {}

    def add(self, chunk_id: str, dv: str, text: str = "texte", article: str | None = "Art. 1", kb_id: str = "KB1") -> None:
        self.chunks[chunk_id] = {"id": chunk_id, "document_version_id": dv, "text": text, "article": article, "kb_id": kb_id}

    def get_chunk(self, session, chunk_id):  # noqa: ANN001, ANN201
        return self.chunks.get(chunk_id)


@pytest.fixture
def knowledge(app) -> FakeKnowledge:  # noqa: ANN001
    return FakeKnowledge()


@pytest.fixture
def mclient(app, knowledge):  # noqa: ANN001
    with TestClient(app) as c:
        app.state.ctx.services["knowledge"] = knowledge
        yield c


def ws_headers(client: TestClient, name: str, first: bool = False) -> dict[str, str]:
    r = client.post(f"{API}/workspaces", json={"name": name}, headers=None if first else getattr(client, "_owner", None))
    assert r.status_code == 201, r.text
    return auth(r.json()["owner_token"])


@pytest.fixture
def h(mclient):  # noqa: ANN001
    hd = ws_headers(mclient, "A", first=True)
    mclient._owner = hd
    return hd


@pytest.fixture
def h2(mclient, h):  # noqa: ANN001
    return ws_headers(mclient, "B")


def mk_inst(client: TestClient, hd: dict, code: str, name: str | None = None) -> str:
    r = client.post(f"{API}/institutions", json={"code": code, "name": name or code, "kind": "agency"}, headers=hd)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def mk_action(client: TestClient, hd: dict, code: str, derivation: str = "referential", **kw) -> dict:
    body = {"code": code, "label": f"action {code}", "derivation": derivation, **kw}
    r = client.post(f"{API}/actions", json=body, headers=hd)
    assert r.status_code == 201, r.text
    return r.json()
