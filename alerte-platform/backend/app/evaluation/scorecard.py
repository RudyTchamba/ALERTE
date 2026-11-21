"""Scorecard : 13 dimensions de l'AI Readiness ITU (doc 09 §9.11). Évaluation INDÉPENDANTE des lacunes : ce module
n'importe ni ne lit jamais les lacunes. « non évalué » n'est JAMAIS 0.

Score d'une dimension = 5 × Σ(poids × valeur) / Σ(poids des critères évalués), valeur : yes=1, partial=0.5, no=0.
Aucun critère évalué -> score `None` (« non évalué »). Score global = moyenne des dimensions évaluées + couverture."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Assessment, RubricCriterion, RubricDimension

FRAMEWORK_DIR = Path(__file__).resolve().parent / "framework"
ANSWERS = ("yes", "partial", "no", "not_assessed")
VALUE = {"yes": 1.0, "partial": 0.5, "no": 0.0}
EVIDENCE_KINDS = ("chunk", "event", "document", "note", "url")  # jamais « gap » : indépendance


def load_framework() -> dict[str, Any]:
    return json.loads((FRAMEWORK_DIR / "dimensions.json").read_text(encoding="utf-8"))


def seed_rubric(session: Session) -> int:
    """Amorce idempotente des 13 dimensions et de leurs critères (un critère par métrique ITU). Renvoie le nb créé."""
    fw = load_framework()
    factors = {f["id"]: f["name"] for f in fw["factors"]}
    created = 0
    for d in fw["dimensions"]:  # dimensions d'abord (flush) : les critères les référencent par clé étrangère
        did = f"d{int(d['id']):02d}"
        if session.get(RubricDimension, did) is None:
            session.add(RubricDimension(
                id=did, number=int(d["id"]), name=d["name"], short_name=d["short_name"],
                factor=", ".join(factors.get(f, f) for f in d.get("mapped_factors", [])),
                question=d["description"]))
            created += 1
    session.flush()
    for d in fw["dimensions"]:
        did = f"d{int(d['id']):02d}"
        for m in d.get("metrics", []):
            if session.get(RubricCriterion, m["id"]) is None:
                session.add(RubricCriterion(id=m["id"], dimension_id=did, weight=1.0,
                                            text=f"{m['name']} — {m['description']}"))
                created += 1
    session.flush()
    return created


def dimension_score(answers: list[tuple[float, str]]) -> dict[str, Any]:
    """`answers` : (poids, réponse) ; renvoie {score|None, status, assessed, total}."""
    assessed = [(w, VALUE[a]) for w, a in answers if a in VALUE]
    if not assessed:
        return {"score": None, "status": "not_assessed", "assessed": 0, "total": len(answers)}
    wsum = sum(w for w, _ in assessed)
    score = 5.0 * sum(w * v for w, v in assessed) / wsum if wsum > 0 else None
    return {"score": score, "status": "assessed" if score is not None else "not_assessed",
            "assessed": len(assessed), "total": len(answers)}


def build_scorecard(session: Session, workspace_id: str, exercise_id: str) -> dict[str, Any]:
    dims = list(session.scalars(select(RubricDimension).order_by(RubricDimension.number)))
    crits = list(session.scalars(select(RubricCriterion).order_by(RubricCriterion.id)))
    ass = {a.criterion_id: a for a in session.scalars(select(Assessment).where(
        Assessment.workspace_id == workspace_id, Assessment.exercise_id == exercise_id))}
    out_dims = []
    for d in dims:
        rows = []
        for c in (c for c in crits if c.dimension_id == d.id):
            a = ass.get(c.id)
            rows.append({"criterion_id": c.id, "text": c.text, "weight": c.weight,
                         "answer": a.answer if a else "not_assessed", "evidence": a.evidence if a else [],
                         "assessor": a.assessor if a else None, "reviewed_by": a.reviewed_by if a else None,
                         "note": a.note if a else None})
        sc = dimension_score([(r["weight"], r["answer"]) for r in rows])
        out_dims.append({"dimension_id": d.id, "number": d.number, "name": d.name, "short_name": d.short_name,
                         "factor": d.factor, "question": d.question, "criteria": rows, **sc})
    scored = [d["score"] for d in out_dims if d["score"] is not None]
    return {"exercise_id": exercise_id, "scale": "0-5", "independent_of_gaps": True,
            "overall_score": (sum(scored) / len(scored)) if scored else None,
            "overall_status": "assessed" if scored else "not_assessed",
            "dimensions_assessed": len(scored), "dimensions_total": len(out_dims),
            "note": "« non évalué » n'est pas un score de 0 ; le score global ne porte que sur les dimensions évaluées.",
            "dimensions": out_dims}
