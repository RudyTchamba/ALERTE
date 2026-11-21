"""Doublures des autres modules (agents, scenarios, mandates, knowledge, recherche, gap_engine).
Le FakeRuntime est DÉTERMINISTE ; il n'est PAS une preuve d'IA."""
from __future__ import annotations

import copy
import random
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.contracts import ActivationResult, Hit, PostedMessage, SeatContext, ToolEvent
from app.core.errors import NotFound

CHUNKS = {
    "c1": {"chunk_id": "c1", "document_version_id": "dv1", "kb_id": "kb1", "article": "33", "title": "Law A",
           "text": "The national authority shall issue public alerts for imminent hazards."},
    "c2": {"chunk_id": "c2", "document_version_id": "dv2", "kb_id": "kb1", "article": "7", "title": "Decree B",
           "text": "Operators must relay warnings to the population without delay."},
    "c9": {"chunk_id": "c9", "document_version_id": "dvX", "kb_id": "kbX", "article": "1", "title": "Secret",
           "text": "Canary chunk that belongs to another knowledge base entirely."},
}
GOOD_QUOTE = "shall issue public alerts"


@dataclass
class Behavior:
    decision: dict | None = None
    messages: list[PostedMessage] = field(default_factory=list)
    status: str = "ok"
    author: str = "agent"
    llm_calls: int = 2
    events: list[ToolEvent] | None = None
    no_decision: bool = False


def decision(code: str | None = "issue_alert", outcome: str = "act", **kw: Any) -> dict:
    d = {"action": f"{outcome} {code}", "action_code": code, "outcome": outcome, "confidence": "medium",
         "options_considered": ["a", "b"], "gap_flags": [], "rationale": "because", "evidence_tag": "documented",
         "legal_basis": [{"chunk_id": "c1", "article": "33", "quote": GOOD_QUOTE, "check": "pass", "reason": None}]
         if outcome != "no_legal_basis_found" else [], "status": "recorded"}
    d.update(kw)
    return d


class FakeRuntime:
    """`script(ctx) -> Behavior|None` ; défaut : décision `act` citant c1. Enregistre chaque activation."""

    def __init__(self, script: Callable[[SeatContext], Behavior | None] | None = None) -> None:
        self.script = script
        self.calls: list[str] = []
        self.contexts: list[SeatContext] = []
        self.lock = threading.Lock()
        self.rng = random.Random()  # latences non déterministes : doivent être ignorées par le digest

    def activate(self, ctx: SeatContext) -> ActivationResult:
        with self.lock:
            self.calls.append(ctx.step_key)
            self.contexts.append(ctx)
        b = (self.script(ctx) if self.script else None) or Behavior()
        demands = [d.get("action_code") for d in ctx.inject.get("demands", []) if d.get("action_code")]
        dec = None if b.no_decision else b.decision if b.decision is not None else (None if b.status in ("not_recorded", "budget_exhausted")
                                                           else decision(demands[0] if demands else None))
        events = b.events if b.events is not None else [
            ToolEvent("LLM_CALL", {"provider": "fake", "model": "m", "endpoint": "mem://", "step_key": ctx.step_key,
                                   "ms": self.rng.randint(1, 900), "tokens_in": 10, "tokens_out": 5, "valid": True},
                      "audit"),
            ToolEvent("TOOL_CALL", {"tool": "decide", "args": {}, "rationale": "r", "ok": True, "error": None}, "seat"),
            ToolEvent("RETRIEVAL", {"query": "q", "scope_hash": ctx.scope.scope_hash(),
                                    "results": [{"chunk_id": "c1", "score": 0.5, "rank": 1}],
                                    "signals": {"degraded": False}}, "seat")]
        return ActivationResult(decision=dec, messages=list(b.messages), events=list(events), llm_calls=b.llm_calls,
                                status=b.status, author=b.author)


class FakeChecker:
    def check(self, decision: dict, retrieval_set: set[str], scope: Any) -> list[dict]:
        out = []
        for b in decision.get("legal_basis", []):
            c = CHUNKS.get(b["chunk_id"])
            if c is None:
                out.append({"chunk_id": b["chunk_id"], "pass": False, "reason": "unknown_chunk"})
            elif c["document_version_id"] not in scope.document_version_ids:
                out.append({"chunk_id": b["chunk_id"], "pass": False, "reason": "out_of_scope"})
            elif b["chunk_id"] not in retrieval_set:
                out.append({"chunk_id": b["chunk_id"], "pass": False, "reason": "not_retrieved"})
            elif len(b["quote"]) < 20 or b["quote"].lower() not in c["text"].lower():
                out.append({"chunk_id": b["chunk_id"], "pass": False, "reason": "quote_not_in_chunk"})
            else:
                out.append({"chunk_id": b["chunk_id"], "pass": True, "reason": None})
        return out


class FakeAgents:
    def __init__(self, ws: str, runtime: FakeRuntime) -> None:
        self.ws, self._runtime = ws, runtime
        self.agents: dict[str, dict] = {}
        self.grants: dict[str, list[str]] = {}
        self.citation_checker = FakeChecker()
        self.legal_questions: list[str] = []

    def export_agent_snapshot(self, session, workspace_id, agent_id):  # noqa: ANN001
        if workspace_id != self.ws or agent_id not in self.agents:
            raise NotFound("agent introuvable")
        return copy.deepcopy(self.agents[agent_id])

    def kb_grants(self, session, workspace_id, agent_id):  # noqa: ANN001
        return list(self.grants.get(agent_id, []))

    def runtime(self):  # noqa: ANN201
        return self._runtime

    def ask_legal(self, seat_ctx, question):  # noqa: ANN001
        self.legal_questions.append(question)
        return {"what_the_texts_say": [{"claim": "x", "cites": ["c1"]}], "what_they_do_not_say": [],
                "what_others_do": [], "what_to_check": [], "closing": "For exercise purposes only",
                "events": [ToolEvent("LLM_CALL", {"provider": "fake", "model": "m", "ms": 5, "step_key": "legal"}, "audit")],
                "llm_calls": 1}


class FakeScenarios:
    def __init__(self, ws: str) -> None:
        self.ws = ws
        self.scenarios: dict[str, dict] = {}

    def export_scenario_snapshot(self, session, workspace_id, scenario_id):  # noqa: ANN001
        if workspace_id != self.ws or scenario_id not in self.scenarios:
            raise NotFound("scénario introuvable")
        return copy.deepcopy(self.scenarios[scenario_id])

    def readiness_scenario_checks(self, session, workspace_id, scenario_id):  # noqa: ANN001
        return []


class FakeMandates:
    def __init__(self) -> None:
        self.mandates: list[dict] = []
        self.registry = "reviewed_complete"
        self.actions = {"issue_alert": {"code": "issue_alert", "label": "Issue alert", "derivation": "referential",
                                        "justification": "j"},
                        "relay_alert": {"code": "relay_alert", "label": "Relay", "derivation": "scenario_author",
                                        "justification": "j"}}

    def export_active_mandates(self, session, workspace_id, institution_ids, document_version_ids):  # noqa: ANN001
        return [copy.deepcopy(m) for m in self.mandates if m["institution_id"] in institution_ids]

    def registry_state(self, session, workspace_id, institution_id):  # noqa: ANN001
        return self.registry

    def action_exists(self, session, workspace_id, code):  # noqa: ANN001
        return code in self.actions

    def list_actions(self, session, workspace_id):  # noqa: ANN001
        return list(self.actions.values())


class FakeKnowledge:
    def __init__(self) -> None:
        self.versions: dict[str, list[str]] = {"kb1": ["dv1", "dv2"]}

    def published_document_version_ids(self, session, workspace_id, kb_ids):  # noqa: ANN001
        return {v for k in kb_ids for v in self.versions.get(k, [])}

    def kb_overview(self, session, workspace_id, kb_id):  # noqa: ANN001
        return {"code": kb_id.upper(), "name": f"KB {kb_id}"}

    def coverage(self, session, workspace_id, kb_ids):  # noqa: ANN001
        return {"ratio": 1.0, "expected": 2, "present": 2, "missing": []}

    def document_meta(self, session, document_version_id):  # noqa: ANN001
        return {"code": document_version_id, "redistribution": "allowed"}

    def get_chunk(self, session, chunk_id):  # noqa: ANN001
        return CHUNKS.get(chunk_id)


class FakeSearch:
    def __init__(self) -> None:
        self.leak = False
        self.scopes: list[Any] = []

    def search(self, scope, query, k=5, *, filters=None):  # noqa: ANN001
        self.scopes.append(scope)
        out = []
        for c in CHUNKS.values():
            if c["document_version_id"] in scope.document_version_ids or (self.leak and c["chunk_id"] == "c9"):
                out.append(Hit(chunk_id=c["chunk_id"], document_version_id=c["document_version_id"], kb_id=c["kb_id"],
                               doc_code=c["document_version_id"], doc_title=c["title"], article=c["article"], page=1,
                               text=c["text"], score=1.0 - 0.1 * len(out), snippet=c["text"][:60]))
        return out[:k]


class FakeGap:
    def __init__(self) -> None:
        self.closed: list[str] = []
        self.finished = 0
        self.fail = False

    def on_inject_closed(self, session, exercise_id, inject_ref):  # noqa: ANN001
        if self.fail:
            raise RuntimeError("boom")
        self.closed.append(inject_ref)

    def on_exercise_finished(self, session, exercise_id):  # noqa: ANN001
        self.finished += 1
