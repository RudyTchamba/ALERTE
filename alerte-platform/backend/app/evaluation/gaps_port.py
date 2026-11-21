"""Lecture des lacunes d'un exercice par le module evaluation/reports (lecture seule).

Priorité : `ctx.services["gaps"].list_gaps(session, workspace_id, exercise_id) -> list[dict]`.
Repli (tant que le moteur de lacunes n'expose pas ce service) : lecture via `app.gaps.service` (fonctions de lecture)
et conversion en dictionnaires. Forme d'un dict (toutes les clés sont facultatives hormis `id`) :
  id, fingerprint, code, rule_id, category, title, description, domain, institution_ids, action_code, evidence_basis,
  confidence, severity, consequence, cause, corpus_coverage, validation_status, origin, registry_state, detail,
  evidence:[{id,kind,role,ref,excerpt,is_agent}], negative_searches:[{queries,languages,corpus_documents,
  corpus_coverage,verdict,statement}], references:[{status,fit_note,reference:{jurisdiction,instrument,article,
  summary,binding,url,chunk_id}}], reviews:[{reviewer,action,from_status,to_status,reality_label,comment,created_at}],
  improvement_actions:[{id,description,owner_institution_id,due_date,status,kpi}]
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy.orm import Session

GAP_FIELDS = ("id", "fingerprint", "code", "rule_id", "category", "title", "description", "domain", "institution_ids",
              "action_code", "evidence_basis", "confidence", "severity", "consequence", "cause", "corpus_coverage",
              "validation_status", "origin", "registry_state", "detail", "inject_refs")


def _iso(v: Any) -> Any:
    return v.isoformat() if isinstance(v, (dt.datetime, dt.date)) else v


def _plain(obj: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    return {f: _iso(getattr(obj, f, None)) for f in fields}


def gaps_available(ctx: Any) -> bool:
    if ctx.services.get("gaps") is not None:
        return True
    try:
        import app.gaps.service  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def read_gaps(ctx: Any, session: Session, workspace_id: str, exercise_id: str) -> list[dict[str, Any]]:
    svc = ctx.services.get("gaps")
    if svc is not None:
        return [dict(g) for g in svc.list_gaps(session, workspace_id, exercise_id)]
    from app.gaps import service as gs  # repli documenté : lecture seule

    out = []
    for g in gs.list_gaps(session, workspace_id, "owner", exercise=exercise_id):
        parts = gs.gap_detail_parts(session, g)
        d = _plain(g, GAP_FIELDS)
        d["evidence"] = [_plain(e, ("id", "kind", "role", "ref", "excerpt", "is_agent")) for e in parts["evidence"]]
        d["negative_searches"] = parts["negative_searches"]
        d["references"] = parts["references"]
        d["reviews"] = [_plain(r, ("reviewer", "action", "from_status", "to_status", "reality_label", "comment",
                                   "created_at")) for r in parts["reviews"]]
        d["improvement_actions"] = [{**a, "due_date": _iso(a.get("due_date"))} for a in parts["improvement_actions"]]
        out.append(d)
    return out


def read_snapshot(ctx: Any, session: Session, exercise_id: str) -> dict[str, Any] | None:
    """Snapshot figé de l'exercice (JSON canonique de CONTRACTS.md) ou None. Sources : `ctx.services["snapshot_loader"]`
    (fn(session, exercise_id) -> (payload, sha)), sinon `gap_engine.load_snapshot`."""
    for name, attr in (("snapshot_loader", None), ("gap_engine", "load_snapshot")):
        svc = ctx.services.get(name)
        if svc is None:
            continue
        fn = svc if attr is None else getattr(svc, attr, None)
        if fn is None:
            continue
        try:
            payload, _sha = fn(session, exercise_id)
        except Exception:  # noqa: BLE001 - snapshot absent : traité comme inconnu
            continue
        return payload
    return None
