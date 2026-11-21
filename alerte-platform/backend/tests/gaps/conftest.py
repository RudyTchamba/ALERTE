from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.audit.events import EventType, Visibility
from app.contracts import Hit
from app.core.canonical_json import canonical_sha256
from app.gaps.commitment import snapshot_hash
from tests.conftest import auth
from tests.gaps import helpers as H

API = "/api/v1"


class FakeKnowledge:
    def __init__(self) -> None:
        self.chunks: dict[str, dict] = {}
        self.kinds: dict[str, str] = {"KB1": "national", "KBG": "global_practices"}
        self.languages = ["fr"]
        self.cov: dict[str, Any] = {"ratio": 1.0, "expected": 2, "present": 2, "missing": []}

    def add(self, chunk_id: str, dv: str, kb_id: str = "KB1", text: str = "t") -> None:
        self.chunks[chunk_id] = {"id": chunk_id, "document_version_id": dv, "kb_id": kb_id, "text": text, "article": "1"}

    def get_chunk(self, session, chunk_id):  # noqa: ANN001, ANN201
        return self.chunks.get(chunk_id)

    def kb_overview(self, session, workspace_id, kb_id):  # noqa: ANN001, ANN201
        return {"kind": self.kinds.get(kb_id, "national"), "languages": self.languages}

    def coverage(self, session, workspace_id, kb_ids):  # noqa: ANN001, ANN201
        return self.cov

    def document_meta(self, session, dv):  # noqa: ANN001, ANN201
        return {"code": dv}


class FakeSearch:
    """Corpus en mémoire : un document répond à une requête si l'un de ses mots-clés y figure ; respecte la portée."""

    def __init__(self) -> None:
        self.docs: list[dict[str, Any]] = []
        self.calls: list[tuple[str, frozenset, str]] = []

    def add(self, chunk_id: str, dv: str, keywords: list[str], score: float = 0.9, kb_id: str = "KB1", lang: str = "fr") -> None:
        self.docs.append({"chunk_id": chunk_id, "dv": dv, "kw": keywords, "score": score, "kb": kb_id, "lang": lang})

    def search(self, scope, query, k=5, *, filters=None):  # noqa: ANN001, ANN201
        assert scope.purpose == "analyst"
        self.calls.append((query, scope.document_version_ids, scope.purpose))
        langs = filters.languages if filters and filters.languages else None
        out = []
        for d in self.docs:
            if d["dv"] not in scope.document_version_ids or d["kb"] not in scope.kb_ids:
                continue
            if langs and d["lang"] not in langs:
                continue
            if any(w in query.lower() for w in d["kw"]):
                out.append(Hit(chunk_id=d["chunk_id"], document_version_id=d["dv"], kb_id=d["kb"], doc_code="DOC", doc_title="t",
                               article="1", page=1, text="texte", score=d["score"], snippet="extrait"))
        return out[:k]


@pytest.fixture
def knowledge() -> FakeKnowledge:
    return FakeKnowledge()


@pytest.fixture
def search() -> FakeSearch:
    return FakeSearch()


class Env:
    """Banc d'essai : client, jetons, snapshot/ledger factices d'exercice."""

    def __init__(self, app, client, owner, knowledge, search):  # noqa: ANN001
        self.app, self.client, self.owner, self.knowledge, self.search = app, client, owner, knowledge, search
        self.ctx = app.state.ctx
        self.ws = client.get(f"{API}/workspaces/current", headers=owner).json()["id"]

    def token(self, role: str) -> dict[str, str]:
        r = self.client.post(f"{API}/tokens", json={"role": role}, headers=self.owner)
        return auth(r.json()["token"])

    def put_exercise(self, exercise_id: str, snap: dict, events: list[tuple[str, dict, dict]] | None = None, *,
                     commitment: str | None = None, sha: str | None = None, ws: str | None = None) -> dict:
        snap = {**snap, "workspace_id": ws or self.ws, "exercise": {**snap["exercise"], "id": exercise_id}}
        snap.setdefault("registry_states", {i: "reviewed_complete" for i in H.INST.values()})
        real_sha = canonical_sha256(snap)
        ev_sha = snapshot_hash(snap)
        with self.ctx.session_factory() as s:
            s.execute(text("DELETE FROM exercise_snapshot WHERE exercise_id = :e"), {"e": exercise_id})
            s.execute(text("INSERT INTO exercise_snapshot (exercise_id, payload, payload_sha256) VALUES (:e, :p, :h)"),
                      {"e": exercise_id, "p": json.dumps(snap), "h": sha or real_sha})
            led = self.ctx.services["ledger"]
            led.append(s, exercise_id, EventType.SNAPSHOT, "system", {"snapshot_sha256": ev_sha,
                                                                     "commitment_sha256": commitment, "ai_mode": "ai", "readiness": {}})
            for typ, payload, kw in events or []:
                led.append(s, exercise_id, typ, kw.get("actor", "coord"), payload, seat_id=kw.get("seat_id"),
                           visibility=kw.get("visibility", Visibility.AUDIT))
            s.commit()
        return snap

    def detect(self, exercise_id: str, headers: dict | None = None):  # noqa: ANN201
        return self.client.post(f"{API}/exercises/{exercise_id}/detect-gaps", headers=self.owner if headers is None else headers)

    def gaps(self, headers: dict | None = None, **params: Any) -> list[dict]:
        r = self.client.get(f"{API}/gaps", params=params, headers=self.owner if headers is None else headers)
        assert r.status_code == 200, r.text
        return r.json()


@pytest.fixture
def env(app, knowledge, search):  # noqa: ANN001
    with TestClient(app) as c:
        r = c.post(f"{API}/workspaces", json={"name": "A"})
        owner = auth(r.json()["owner_token"])
        ctx = app.state.ctx
        ctx.services["knowledge"] = knowledge
        ctx.services["search"] = search
        ctx.services["exercise_guard"] = lambda session, p, ex: None
        # table du module simulation : schéma minimal contractuel (sans FK vers `exercise`) pour ces tests
        with ctx.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
            conn.exec_driver_sql("DROP TABLE IF EXISTS exercise_snapshot")
            conn.exec_driver_sql("CREATE TABLE exercise_snapshot (exercise_id TEXT PRIMARY KEY, payload TEXT, payload_sha256 TEXT)")
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        yield Env(app, c, owner, knowledge, search)
