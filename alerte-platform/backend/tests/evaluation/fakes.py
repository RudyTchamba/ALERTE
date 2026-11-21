"""Faux services et données fabriquées partagés par les tests reports/evaluation (aucun vrai modèle, aucune IA)."""
from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import dataclass, field
from typing import Any

from app.contracts import Hit
from app.core.db import session_scope
from app.core.errors import NotFound


def fp(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def make_gap(label: str, *, code: str = "G1", severity: int = 3, status: str = "proposed", basis: str = "documented",
             origin: str = "rule", reviews: list[dict] | None = None, **kw: Any) -> dict[str, Any]:
    d = {"id": f"gap-{label}", "fingerprint": fp(label), "code": code, "rule_id": code, "category": "mandate_absent",
         "title": f"Lacune {label}", "description": f"Aucune institution n'est chargée de {label}.", "domain": "alerting",
         "institution_ids": ["inst-1"], "action_code": f"act_{label}", "evidence_basis": basis, "confidence": "medium",
         "severity": severity, "consequence": "retard de l'alerte", "cause": "institutional", "corpus_coverage": 0.8,
         "validation_status": status, "origin": origin, "registry_state": "reviewed_complete",
         "evidence": [{"id": f"ev-{label}", "kind": "mandate", "role": "supports", "ref": {"article": "Art. 3", "page": 4},
                       "excerpt": "extrait du mandat", "is_agent": False}],
         "negative_searches": [{"queries": ["alerte publique"], "languages": ["fr"], "corpus_documents": 12,
                                "corpus_coverage": 0.8, "verdict": "no_hit"}],
         "references": [{"status": "accepted", "fit_note": "adéquation", "reference": {
             "jurisdiction": j, "instrument": f"Instrument {j}", "article": "Art. 1", "summary": "résumé", "binding": True,
             "url": f"https://example.org/{j}"}} for j in ("EU", "US")],
         "reviews": reviews or [], "improvement_actions": [
             {"id": f"imp-{label}", "description": "Désigner un responsable", "owner_institution_id": "inst-1",
              "due_date": "2027-01-31", "status": "planned", "kpi": "délai d'alerte < 10 min"}]}
    d.update(kw)
    return d


def review(reviewer: str, label: str | None, action: str = "confirm", to: str = "confirmed") -> dict[str, Any]:
    return {"reviewer": reviewer, "action": action, "from_status": "proposed", "to_status": to,
            "reality_label": label, "comment": "relu", "created_at": "2026-11-21T10:00:00+00:00"}


@dataclass
class FakeGaps:
    data: dict[tuple[str, str], list[dict]] = field(default_factory=dict)

    def put(self, workspace_id: str, exercise_id: str, gaps: list[dict]) -> None:
        self.data[(workspace_id, exercise_id)] = gaps

    def list_gaps(self, session: Any, workspace_id: str, exercise_id: str) -> list[dict]:
        return [dict(g) for g in self.data.get((workspace_id, exercise_id), [])]


class FakeGuard:
    """exercise_guard(session, principal, exercise_id) : NotFound hors de l'espace propriétaire."""

    def __init__(self) -> None:
        self.owners: dict[str, str] = {}

    def __call__(self, session: Any, principal: Any, exercise_id: str) -> None:
        if self.owners.get(exercise_id) != principal.workspace_id:
            raise NotFound("exercice introuvable")


class FakeKnowledge:
    def __init__(self, docs: dict[str, set[str]] | None = None, coverage: float | None = 0.75) -> None:
        self.docs = docs or {}
        self._cov = coverage

    def published_document_version_ids(self, session: Any, workspace_id: str, kb_ids: Any) -> set[str]:
        return {d for k in kb_ids for d in self.docs.get(k, set())}

    def kb_overview(self, session: Any, workspace_id: str, kb_id: str) -> dict:
        if kb_id not in self.docs:
            raise NotFound("base introuvable")
        return {"id": kb_id}

    def coverage(self, session: Any, workspace_id: str, kb_ids: Any) -> dict:
        return {"ratio": self._cov, "expected": 4, "present": 3, "missing": ["Loi X"]}

    def document_meta(self, session: Any, document_version_id: str) -> dict | None:
        return {"code": "CM-S01", "title": "Loi 2011", "type": "law", "jurisdiction": "CM", "license": "open",
                "redistribution": True}


class FakeSearch:
    """Renvoie, par question, des hits fabriqués : `plan[question] = [(doc_code, article), ...]`."""

    def __init__(self, plan: dict[str, list[tuple[str, str | None]]]) -> None:
        self.plan = plan
        self.scopes: list[Any] = []

    def search(self, scope: Any, query: str, k: int = 5, *, filters: Any = None) -> list[Hit]:
        self.scopes.append(scope)
        return [Hit(chunk_id=f"c{i}", document_version_id="dv", kb_id="kb", doc_code=c, doc_title=c, article=a, page=1,
                    text="t", score=1.0 / (i + 1)) for i, (c, a) in enumerate(self.plan.get(query, [])[:k])]


T0 = dt.datetime(2026, 11, 21, 8, 0, 0, tzinfo=dt.UTC)


def iso(minutes: float) -> str:
    return (T0 + dt.timedelta(minutes=minutes)).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def seed_ledger(ctx: Any, exercise_id: str, *, ai_mode: str = "ai", llm_calls: int = 5, minutes: float = 12.0,
                citations: tuple[int, int] = (19, 20), start: dt.datetime | None = None) -> None:
    """SNAPSHOT, INJECT, LLM_CALL×n, DECISION, CITATION_CHECK (pass/total), STATE final — au format de CONTRACTS.md."""
    led = ctx.service("ledger")
    base = start or T0

    def t(m: float) -> str:
        return (base + dt.timedelta(minutes=m)).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    ok, total = citations
    with session_scope(ctx.session_factory) as s:
        led.append(s, exercise_id, "SNAPSHOT", "system", {"snapshot_sha256": "a" * 64, "commitment_sha256": "b" * 64,
                                                          "ai_mode": ai_mode, "readiness": {}}, real_time=t(-1))
        led.append(s, exercise_id, "INJECT", "coord", {"inject_ref": "inj-001", "seq": 1, "title": "Crue", "body": "...",
                                                      "recipients": ["MET"], "tags": [], "fault_mode": "none",
                                                      "surprise": False}, visibility="public", sim_time="D1 06:00", real_time=t(0))
        for i in range(llm_calls):
            led.append(s, exercise_id, "LLM_CALL", "seat:MET", {"provider": "p", "model": "m", "endpoint": "http://x",
                                                               "step_key": f"s{i}", "tokens_in": 1, "tokens_out": 1,
                                                               "ms": 5, "valid": True, "retried": False}, real_time=t(1 + i * 0.01))
        led.append(s, exercise_id, "DECISION", "seat:MET", {"decision_id": "d1", "seat_code": "MET", "outcome": "act"},
                   visibility="public", real_time=t(2))
        cites = [{"chunk_id": f"c{i}", "pass": i < ok, "reason": None if i < ok else "citation introuvable"}
                 for i in range(total)]
        led.append(s, exercise_id, "CITATION_CHECK", "system", {"decision_id": "d1", "citations": cites}, real_time=t(3))
        led.append(s, exercise_id, "STATE", "system", {"from": "running", "to": "finished", "reason": "fin"},
                   visibility="public", real_time=t(minutes))
