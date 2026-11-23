"""Routes d'évaluation et de scorecard (sans préfixe /api/v1). L'appartenance d'un exercice à l'espace est contrôlée par
`ctx.services["exercise_guard"]` (module simulation) ; un objet d'un autre espace -> 404."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.auth import Principal, require_role
from ..core.context import AppContext, get_ctx, get_session
from ..core.errors import AppError, NotFound
from . import service
from .fixtures import list_fixtures, public_view
from .metrics import THRESHOLDS
from .models import BenchmarkItem, BenchmarkSet
from .schemas import BenchmarkItemIn, BenchmarkSetIn, FixtureIn, QuestionIn, QuestionOut, ScorecardPut
from .scorecard import build_scorecard

router = APIRouter()
Read = require_role("facilitator", "auditor")
Write = require_role("facilitator")


def guard(ctx: AppContext, session: Session, p: Principal, exercise_id: str) -> None:
    g = ctx.services.get("exercise_guard")
    if g is None:
        raise NotFound("exercice introuvable")
    g(session, p, exercise_id)


def _norm_metric(metric: str) -> str:
    m = metric.strip()
    return m.upper() if m[:1] in "tT" and len(m) == 2 else m.lower()


@router.get("/evaluation/exercises/{exercise_id}", tags=["evaluation"])
def get_metrics(exercise_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session),
                ctx: AppContext = Depends(get_ctx)) -> dict[str, Any]:
    guard(ctx, session, p, exercise_id)
    return {"exercise_id": exercise_id, "thresholds": THRESHOLDS,
            "metrics": service.latest_metrics(session, p.workspace_id, exercise_id)}


@router.post("/evaluation/exercises/{exercise_id}/run", tags=["evaluation"])
def run(exercise_id: str, metric: str, kb_id: list[str] = Query(default=[]), scenario_code: str | None = None,
        clone_id: list[str] = Query(default=[]), benchmark_set_id: str | None = None, max_gaps: int = 0,
        p: Principal = Depends(Write), session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)):
    guard(ctx, session, p, exercise_id)
    return service.run_metric(ctx, session, p.workspace_id, exercise_id, _norm_metric(metric),
                              kb_ids=kb_id, scenario_code=scenario_code, clone_ids=clone_id,
                              benchmark_set_id=benchmark_set_id, max_gaps=max_gaps,
                              guard=lambda i: guard(ctx, session, p, i))


# --- T1 : jeu de questions ---------------------------------------------------------------------------------
@router.get("/evaluation/kbs/{kb_id}/questions", response_model=list[QuestionOut], tags=["evaluation"])
def list_questions(kb_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return service.list_questions(session, p.workspace_id, kb_id)


@router.post("/evaluation/kbs/{kb_id}/questions", response_model=list[QuestionOut], status_code=201, tags=["evaluation"])
def add_questions(kb_id: str, body: list[QuestionIn], p: Principal = Depends(Write),
                  session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)):
    return service.add_questions(ctx, session, p.workspace_id, kb_id, [q.model_dump() for q in body])


@router.post("/evaluation/kbs/{kb_id}/questions/import", response_model=list[QuestionOut], status_code=201, tags=["evaluation"])
async def import_questions(kb_id: str, file: UploadFile = File(...), p: Principal = Depends(Write),
                           session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)):
    data = await file.read()
    if len(data) > 2_000_000:
        raise AppError("fichier trop volumineux", status_code=413, code="upload.too_large")
    return service.add_questions(ctx, session, p.workspace_id, kb_id, service.parse_questions_csv(data))


# --- T3 : fixtures scellées (aucune route de mise à jour/suppression) ------------------------------------------
@router.post("/evaluation/fixtures", status_code=201, tags=["evaluation"])
def seal(body: FixtureIn, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    fx = service.add_fixture(session, p.workspace_id, body.scenario_code, body.expected_gap_key, body.label,
                             body.description, p.label or p.token_id)
    return public_view(fx)


@router.get("/evaluation/fixtures", tags=["evaluation"])
def get_fixtures(scenario_code: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return [public_view(f) for f in list_fixtures(session, p.workspace_id, scenario_code)]


# --- benchmark externe --------------------------------------------------------------------------------------
@router.post("/evaluation/benchmark-sets", status_code=201, tags=["evaluation"])
def create_set(body: BenchmarkSetIn, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    b = service.create_benchmark(session, p.workspace_id, body.name, body.source, body.description)
    return {"id": b.id, "name": b.name, "source": b.source}


@router.post("/evaluation/benchmark-sets/{set_id}/items", status_code=201, tags=["evaluation"])
def add_items(set_id: str, body: list[BenchmarkItemIn], p: Principal = Depends(Write), session: Session = Depends(get_session)):
    rows = service.add_benchmark_items(session, p.workspace_id, set_id, [i.model_dump() for i in body])
    return [{"id": r.id, "label": r.label, "fingerprint": r.fingerprint} for r in rows]


@router.get("/evaluation/benchmark-sets", tags=["evaluation"])
def list_sets(p: Principal = Depends(Read), session: Session = Depends(get_session)):
    out = []
    for b in session.scalars(select(BenchmarkSet).where(BenchmarkSet.workspace_id == p.workspace_id).order_by(BenchmarkSet.id)):
        n = len(list(session.scalars(select(BenchmarkItem.id).where(BenchmarkItem.set_id == b.id))))
        out.append({"id": b.id, "name": b.name, "source": b.source, "items": n})
    return out


# --- scorecard ---------------------------------------------------------------------------------------------
@router.get("/scorecard/exercises/{exercise_id}", tags=["evaluation"])
def get_scorecard(exercise_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session),
                  ctx: AppContext = Depends(get_ctx)):
    guard(ctx, session, p, exercise_id)
    return build_scorecard(session, p.workspace_id, exercise_id)


@router.put("/scorecard/exercises/{exercise_id}", tags=["evaluation"])
def put_scorecard(exercise_id: str, body: ScorecardPut, p: Principal = Depends(Write), session: Session = Depends(get_session),
                  ctx: AppContext = Depends(get_ctx)):
    guard(ctx, session, p, exercise_id)
    return service.put_assessments(session, p.workspace_id, exercise_id, [a.model_dump() for a in body.answers],
                                   body.reviewed_by, p.label or p.token_id)


@router.post("/scorecard/exercises/{exercise_id}/assess", status_code=202, tags=["evaluation"])
def assess_llm(exercise_id: str, p: Principal = Depends(Write), session: Session = Depends(get_session),
               ctx: AppContext = Depends(get_ctx)):
    """Juge IA (tâche de fond) : propose une réponse par critère, preuves contrôlées, « à relire » par un humain.
    Les réponses saisies par un humain ne sont jamais écrasées ; les lacunes ne sont jamais lues (indépendance)."""
    guard(ctx, session, p, exercise_id)
    if ctx.services.get("agents") is None:
        raise AppError("module agents indisponible", status_code=503, code="scorecard.llm_judge_unavailable")
    ws = p.workspace_id

    def job(jc: Any) -> dict[str, Any]:
        from . import judge
        with jc.session() as s:
            events = service.read_events(s, exercise_id)
            return judge.run(ctx, s, ws, exercise_id, events, progress=jc.update)

    jid = ctx.jobs.submit("scorecard.assess", job, workspace_id=ws, payload={"exercise_id": exercise_id})
    return {"job": {"id": jid, "status": "queued"}, "job_id": jid}
