from __future__ import annotations

import json
from typing import Any

import pytest

from app.contracts import Hit, LLMMessage, RawCompletion, SearchScope, SeatContext
from app.core.blobs import BlobStore
from app.core.config import Settings
from app.core.errors import NotFound

WS = "WS000000000000000000000001"
KB = "KB000000000000000000000001"
KB_OTHER = "KB000000000000000000000002"
DV = "DV000000000000000000000001"

CHUNK_TEXT = ("Le directeur de la protection civile peut ordonner l'évacuation des populations exposées "
              "lorsqu'un danger grave et imminent est constaté.")
QUOTE = "peut ordonner l'évacuation des populations exposées"


class FakeKnowledge:
    def __init__(self) -> None:
        self.chunks: dict[str, dict[str, Any]] = {
            "C1": {"chunk_id": "C1", "text": CHUNK_TEXT, "article": "33", "document_version_id": DV, "kb_id": KB,
                   "validity": "in_force"},
            "C2": {"chunk_id": "C2", "text": "Texte sans article numéroté mais suffisamment long pour être cité.",
                   "article": None, "document_version_id": DV, "kb_id": KB, "validity": "in_force"},
            "OLD": {"chunk_id": "OLD", "text": "Ancienne disposition remplacée par un texte plus récent du pays.",
                    "article": "1", "document_version_id": DV, "kb_id": KB, "validity": "replaced"},
            "SECRET": {"chunk_id": "SECRET", "text": "Contenu confidentiel d'une base non accordée au siège.",
                       "article": "9", "document_version_id": DV, "kb_id": KB_OTHER, "validity": "in_force"},
        }
        self.kbs = {WS: {KB: {"id": KB, "code": "NAT", "name": "National"}, KB_OTHER: {"id": KB_OTHER, "code": "X", "name": "X"}}}

    def get_chunk(self, session, chunk_id):  # noqa: ANN001, ANN201
        return self.chunks.get(chunk_id)

    def chunk_in_scope(self, session, chunk_id, scope):  # noqa: ANN001, ANN201
        c = self.chunks.get(chunk_id)
        return bool(c) and c["kb_id"] in scope.kb_ids

    def kb_overview(self, session, workspace_id, kb_id):  # noqa: ANN001, ANN201
        try:
            return self.kbs[workspace_id][kb_id]
        except KeyError:
            raise NotFound("kb") from None

    def published_document_version_ids(self, session, workspace_id, kb_ids):  # noqa: ANN001, ANN201
        return {DV}


class FakeSearch:
    def __init__(self, knowledge: FakeKnowledge) -> None:
        self.k = knowledge
        self.calls: list[tuple[SearchScope, str]] = []
        self.override: dict[str, str] = {}  # chunk_id -> texte (ex. injection)

    def search(self, scope, query, k=5, *, filters=None):  # noqa: ANN001, ANN201
        self.calls.append((scope, query))
        out = []
        for c in self.k.chunks.values():
            if c["kb_id"] in scope.kb_ids:  # le vrai service filtre dans la requête
                text = self.override.get(c["chunk_id"], c["text"])
                out.append(Hit(c["chunk_id"], c["document_version_id"], c["kb_id"], "LAW-1", "Loi 1", c["article"], 1,
                               text, 1.0 / (len(out) + 1), {"lexical": 1, "dense": 2, "degraded": False}))
        return out[:k]


class FakeMandates:
    def action_exists(self, session, workspace_id, code):  # noqa: ANN001, ANN201
        return code in {"evacuate", "send_mass_alert"}

    def list_actions(self, session, workspace_id):  # noqa: ANN001, ANN201
        return [{"code": "evacuate", "derivation": "referential"}]


class QueueProvider:
    """Modèle factice : rejoue une file de réponses (str ou Exception) et mémorise les prompts."""

    name = "fake"
    ai_involved = True

    def __init__(self, replies: list[Any], repeat_last: bool = False) -> None:
        self.replies, self.repeat_last = list(replies), repeat_last
        self.calls: list[list[LLMMessage]] = []
        self.schemas: list[Any] = []

    def complete(self, messages, *, schema=None, temperature=0.0, max_tokens=None):  # noqa: ANN001, ANN201
        from app.agents.providers import request_sha256
        self.calls.append(list(messages))
        self.schemas.append(schema)
        r = self.replies.pop(0) if len(self.replies) > 1 or not self.repeat_last else self.replies[0]
        if isinstance(r, Exception):
            raise r
        if isinstance(r, dict):
            r = json.dumps(r)
        return RawCompletion(text=r, model="fake-1", provider="fake", tokens_in=10, tokens_out=5, ms=1,
                             request_sha256=request_sha256(messages, schema), endpoint="local:fake")


def decide(basis: list[dict] | None = None, outcome: str = "act", **kw: Any) -> dict[str, Any]:
    d = {"action": "decide", "rationale": "because the text allows it",
         "decision": {"action": "Order evacuation", "action_code": None, "outcome": outcome,
                      "legal_basis": basis if basis is not None else [{"chunk_id": "C1", "article": "33", "quote": QUOTE}],
                      "confidence": "medium", "options_considered": ["wait"], "gap_flags": [], "evidence_tag": "documented"}}
    d["decision"].update(kw)
    return d


SEARCH = {"action": "search_kb", "rationale": "need the text", "query": "evacuation power"}


@pytest.fixture
def knowledge() -> FakeKnowledge:
    return FakeKnowledge()


@pytest.fixture
def services(knowledge):  # noqa: ANN001, ANN201
    return {"knowledge": knowledge, "search": FakeSearch(knowledge), "mandates": FakeMandates()}


@pytest.fixture
def make_runtime(tmp_path, services):  # noqa: ANN001, ANN201
    from app.agents.runtime import AgentRuntime

    def _make(provider, **settings_kw):  # noqa: ANN001, ANN202
        settings = Settings(data_dir=tmp_path / "d", log_json=False, **settings_kw)
        return AgentRuntime(settings, BlobStore(tmp_path / "blobs"), services, provider_factory=lambda p, s: provider)
    return _make


def make_ctx(**kw: Any) -> SeatContext:
    base: dict[str, Any] = dict(
        exercise_id="EX1", workspace_id=WS, seat_id="S1", seat_code="DPC",
        institution={"id": "I1", "code": "DPC", "name": "Civil Protection", "kind": "agency"},
        agent={"id": "A1", "code": "DPC", "name": "DPC agent", "role_kind": "institution", "mission": "Protect people",
               "instructions": "Be concise", "tools": ["search_kb", "ask_legal", "post", "decide"],
               "limits": {"max_steps": 4, "max_search_calls": 3, "max_legal_calls": 2},
               "model_profile": {"provider": "fake", "model": "fake-1", "temperature": 0.0}},
        scope=SearchScope(WS, frozenset({KB}), frozenset({DV}), purpose="agent", seat_id="S1"),
        inject={"inject_ref": "inj-001", "seq": 1, "sim_time": "D1 06:00", "title": "Flood warning",
                "body": "Heavy rain expected.", "from_actor": "MET", "fault_mode": "false_alarm",
                "tags": ["life_risk"], "demands": [{"action_code": "evacuate"}]},
        round=1, inbox=[], board=[], own_decisions=[],
        mandates=[{"kind": "power", "action_code": "evacuate", "description": "Order evacuation of exposed populations", "sources": []}],
        seat_codes=["DPC", "MET", "OPS"], step_key="inject:1:round:1:seat:DPC")
    base.update(kw)
    return SeatContext(**base)
