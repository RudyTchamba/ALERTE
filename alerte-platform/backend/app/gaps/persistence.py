"""Persistance idempotente des candidats : (exercise_id, group_key) est l'identité ; l'état humain n'est jamais écrasé."""
from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..core.canonical_json import canonical_sha256
from ..core.db import utcnow
from .constants import ENGINE_VERSION
from .detection import GapCandidate
from .models import Gap, GapEvidence, NegativeSearch
from .negative_search import NegativeResult

CONSEQUENCES = {
    3: {"fr": "Risque pour la vie ou les droits des personnes si la lacune se produit en situation réelle.",
        "en": "Risk to life or rights of people if the gap occurs in a real situation."},
    2: {"fr": "Retard, surcoût ou mauvaise coordination de la réponse.", "en": "Delay, extra cost or poor coordination of the response."},
    1: {"fr": "Gêne opérationnelle limitée.", "en": "Limited operational inconvenience."},
}


def _machine_fields(c: GapCandidate, lang: str) -> dict[str, Any]:
    return {"code": c.code, "rule_id": c.rule_id, "category": c.category, "title": c.title, "description": c.description,
            "domain": c.domain, "institution_ids": c.institutions, "action_code": c.action_code,
            "evidence_basis": c.evidence_basis, "confidence": c.confidence, "auto_severity": c.severity,
            "consequence": CONSEQUENCES[c.severity][lang], "origin": c.origin, "registry_state": c.registry_state,
            "cause": c.cause, "corpus_coverage": c.coverage, "demand_derivation": c.demand_derivation,
            "inject_refs": c.inject_refs, "fingerprint": c.fingerprint}


def persist_candidates(session: Session, snapshot: dict[str, Any], exercise_id: str, cands: list[GapCandidate],
                       neg_rows: dict[str, NegativeResult], integrity: dict[str, Any], final: bool, result: dict[str, Any]) -> None:
    ws = snapshot["workspace_id"]
    lang = ((snapshot.get("scenario") or {}).get("language") or "fr")[:2]
    lang = lang if lang in ("fr", "en") else "en"
    neg_ids: dict[str, str] = {}
    for key, r in neg_rows.items():
        row = session.scalar(select(NegativeSearch).where(NegativeSearch.exercise_id == exercise_id,
                                                          NegativeSearch.query_key == key))
        if row is None:
            row = NegativeSearch(workspace_id=ws, exercise_id=exercise_id, query_key=key)
            session.add(row)
        row.action_code, row.kb_ids, row.queries, row.languages = r.action_code, r.kb_ids, r.queries, r.languages
        row.corpus_documents, row.corpus_coverage, row.coverage_missing = r.corpus_documents, r.coverage, r.coverage_missing
        row.top_hits, row.verdict, row.run_at = r.top_hits, r.verdict, utcnow()
        session.flush()
        neg_ids[key] = row.id
    existing = {g.group_key: g for g in session.scalars(select(Gap).where(Gap.workspace_id == ws, Gap.exercise_id == exercise_id))}
    seen: set[str] = set()
    for c in cands:
        fields = _machine_fields(c, lang)
        detail = {"notes": c.notes, "signals": c.signals, "tags": sorted(c.tags), "scripted": c.scripted,
                  "proposed_mandate": c.proposed_mandate, "neg_status": c.neg_status, "action_key": c.action_key,
                  "demand_derivations": sorted(c.derivations), "commitment": integrity["commitment"],
                  "snapshot_integrity": integrity["snapshot"], "rules_sha256": integrity["rules_sha256"],
                  "engine_version": ENGINE_VERSION, "registry_source": integrity.get("registry_states")}
        evidence = [{"kind": e.kind, "role": e.role, "excerpt": e.excerpt, "is_agent": e.is_agent,
                     "ref": {**e.ref, "negative_search_id": neg_ids.get(e.ref.get("query_key"))} if e.kind == "negative_search" else e.ref}
                    for e in c.evidence]
        h = canonical_sha256({"f": fields, "d": detail, "e": evidence})
        gap = existing.get(c.group_key)
        seen.add(c.group_key)
        if gap is None:
            gap = Gap(workspace_id=ws, exercise_id=exercise_id, group_key=c.group_key, severity=c.severity,
                      validation_status="proposed", **fields)
            gap.detail, gap.engine_hash, gap.is_current, gap.edited_fields = detail, h, True, []
            session.add(gap)
            session.flush()
            change = "created"
            result["created"] += 1
        elif gap.engine_hash == h and gap.is_current:
            change = "unchanged"
            result["unchanged"] += 1
        else:
            edited = set(gap.edited_fields or [])
            for k, v in fields.items():
                if k not in edited:
                    setattr(gap, k, v)
            if "severity" not in edited:
                gap.severity = c.severity
            gap.detail, gap.engine_hash, gap.is_current = detail, h, True
            session.flush()
            change = "updated"
            result["updated"] += 1
        if change != "unchanged":
            session.execute(delete(GapEvidence).where(GapEvidence.gap_id == gap.id))
            for e in evidence:
                session.add(GapEvidence(gap_id=gap.id, **e))
            session.flush()
        result["gaps"].append({"id": gap.id, "fingerprint": gap.fingerprint, "code": gap.code, "action_code": gap.action_code,
                               "evidence_basis": gap.evidence_basis, "confidence": gap.confidence, "severity": gap.severity,
                               "validation_status": gap.validation_status, "origin": gap.origin, "cause": gap.cause,
                               "change": change})
    if final:  # la détection finale marque comme périmés les candidats incrémentaux qui ne tiennent plus
        for key, g in existing.items():
            if key not in seen and g.is_current and g.origin != "imported":
                g.is_current = False
                result["stale"] += 1
        session.flush()
