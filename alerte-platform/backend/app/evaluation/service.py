"""Cas d'usage d'evaluation : exécute et enregistre les métriques (eval_run), jeu de questions T1, fixtures T3, benchmark,
scorecard. Lit les autres modules UNIQUEMENT par leurs services (`ledger`, `search`, `knowledge`, `gaps`, snapshot)."""
from __future__ import annotations

import csv
import io
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..contracts import SearchScope
from ..core.errors import NotFound, Unprocessable
from . import gaps_port, metrics
from .fixtures import as_utc, list_fixtures, seal_fixture, seal_ok
from .metrics import not_computed
from .models import Assessment, BenchmarkItem, BenchmarkSet, EvalQuestion, EvalRun, RubricCriterion
from .scorecard import ANSWERS, EVIDENCE_KINDS, build_scorecard

METRICS = ("T1", "T2", "T3", "T4", "T5", "T6", "benchmark", "negative_control")
_CTX: Any = None  # contexte applicatif (posé par setup.register) pour compute_t2/compute_t6(session, exercise_id)


def bind(ctx: Any) -> None:
    global _CTX
    _CTX = ctx


# --------------------------------------------------------------------------- ledger
def read_events(session: Session, exercise_id: str, ledger: Any = None) -> list[dict[str, Any]]:
    ledger = ledger or (_CTX.services.get("ledger") if _CTX else None)
    if ledger is None:
        from ..audit.ledger import Ledger  # repli : lecture seule, sans ancres

        ledger = Ledger()
    out, after = [], 0
    while True:
        batch = ledger.read(session, exercise_id, after_seq=after, limit=2000)
        if not batch:
            return out
        out += [{"seq": e.seq, "type": e.type, "actor": e.actor, "real_time": e.real_time, "payload": e.payload}
                for e in batch]
        after = batch[-1].seq


def compute_t2(session: Session, exercise_id: str, ledger: Any = None) -> dict[str, Any]:
    return metrics.t2_citations(read_events(session, exercise_id, ledger))


def compute_t6(session: Session, exercise_id: str, ledger: Any = None) -> dict[str, Any]:
    return metrics.t6_time_calls(read_events(session, exercise_id, ledger))


# --------------------------------------------------------------------------- jeu de questions T1
def _check_kb(ctx: Any, session: Session, workspace_id: str, kb_id: str) -> None:
    kn = ctx.services.get("knowledge")
    if kn is not None:
        kn.kb_overview(session, workspace_id, kb_id)  # NotFound si la KB n'est pas de cet espace


def add_questions(ctx: Any, session: Session, workspace_id: str, kb_id: str, rows: list[dict[str, Any]]) -> list[EvalQuestion]:
    _check_kb(ctx, session, workspace_id, kb_id)
    out = []
    for r in rows:
        q = (r.get("question") or "").strip()
        doc = (r.get("expected_doc_code") or "").strip()
        if not q or not doc:
            raise Unprocessable("chaque question exige `question` et `expected_doc_code`")
        out.append(EvalQuestion(workspace_id=workspace_id, kb_id=kb_id, question=q, expected_doc_code=doc,
                                expected_article=(r.get("expected_article") or None), lang=(r.get("lang") or None),
                                category=(r.get("category") or None)))
    session.add_all(out)
    session.flush()
    return out


def parse_questions_csv(data: bytes, max_rows: int = 5000) -> list[dict[str, Any]]:
    text = data.decode("utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(text[:2048], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rd = csv.DictReader(io.StringIO(text), dialect=dialect)
    cols = {(c or "").strip().lower() for c in (rd.fieldnames or [])}
    if not {"question", "expected_doc_code"} <= cols:
        raise Unprocessable("CSV : colonnes obligatoires `question` et `expected_doc_code`",
                            details={"found": sorted(cols)})
    rows = []
    for i, raw in enumerate(rd):
        if i >= max_rows:
            raise Unprocessable(f"CSV trop long (> {max_rows} lignes)")
        rows.append({(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()})
    return rows


def list_questions(session: Session, workspace_id: str, kb_id: str) -> list[EvalQuestion]:
    return list(session.scalars(select(EvalQuestion).where(EvalQuestion.workspace_id == workspace_id,
                                                           EvalQuestion.kb_id == kb_id).order_by(EvalQuestion.id)))


# --------------------------------------------------------------------------- exécution d'une métrique
def _persist(session: Session, workspace_id: str, exercise_id: str | None, kb_id: str | None, result: dict[str, Any]) -> dict[str, Any]:
    run = EvalRun(workspace_id=workspace_id, exercise_id=exercise_id, kb_id=kb_id, metric=result["metric"],
                  status=result["status"], result=result)
    session.add(run)
    session.flush()
    return {**result, "run_id": run.id, "run_at": run.run_at.isoformat()}


def _t1(ctx: Any, session: Session, workspace_id: str, exercise_id: str, kb_ids: list[str]) -> tuple[dict[str, Any], str | None]:
    if not kb_ids:
        snap = gaps_port.read_snapshot(ctx, session, exercise_id) or {}
        kb_ids = [k["kb_id"] for k in snap.get("kb", [])]
    if not kb_ids:
        return not_computed("T1", "aucune base de connaissances indiquée (paramètre kb_id ou snapshot)"), None
    qs = [q for kb in kb_ids for q in list_questions(session, workspace_id, kb)]
    if not qs:
        return not_computed("T1", "aucun jeu de questions pour cette base de connaissances", kb_ids=kb_ids), None
    search, kn = ctx.services.get("search"), ctx.services.get("knowledge")
    if search is None or kn is None:
        return not_computed("T1", "service de recherche indisponible", kb_ids=kb_ids), None
    versions = kn.published_document_version_ids(session, workspace_id, set(kb_ids))
    scope = SearchScope(workspace_id=workspace_id, kb_ids=frozenset(kb_ids), document_version_ids=frozenset(versions),
                        purpose="eval")
    if scope.is_empty:
        return not_computed("T1", "aucun document publié dans la portée de ces bases", kb_ids=kb_ids), None

    def do_search(q: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"doc_code": h.doc_code, "article": h.article, "chunk_id": h.chunk_id}
                for h in search.search(scope, q["question"], k=10)]

    res = metrics.t1_retrieval([{"id": q.id, "question": q.question, "expected_doc_code": q.expected_doc_code,
                                 "expected_article": q.expected_article, "category": q.category} for q in qs], do_search)
    res["kb_ids"] = kb_ids
    res["scope_hash"] = scope.scope_hash()  # reproductibilité : version de corpus interrogée
    return res, (kb_ids[0] if len(kb_ids) == 1 else None)


def _t3(ctx: Any, session: Session, workspace_id: str, exercise_id: str, scenario_code: str | None,
        gaps: list[dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, Any]:
    if not scenario_code:
        snap = gaps_port.read_snapshot(ctx, session, exercise_id) or {}
        scenario_code = (snap.get("scenario") or {}).get("code")
    if not scenario_code:
        return not_computed("T3", "scénario inconnu (paramètre scenario_code ou snapshot requis)")
    fxs = list_fixtures(session, workspace_id, scenario_code)
    if not fxs:
        return not_computed("T3", "aucune fixture scellée pour ce scénario", scenario_code=scenario_code)
    bad = [f.id for f in fxs if not seal_ok(f)]
    if bad:
        return not_computed("T3", "fixtures altérées après scellement (SHA-256 invalide) : résultat non fiable",
                            scenario_code=scenario_code, tampered_fixture_ids=bad)
    start = min((metrics._dt(e["real_time"]) for e in events), default=None)
    late = [f.id for f in fxs if start is not None and as_utc(f.sealed_at) > start]
    if late:
        return not_computed("T3", "fixtures scellées APRÈS le début de l'exercice : indépendance non démontrée",
                            scenario_code=scenario_code, late_fixture_ids=late)
    res = metrics.t3_expected_gaps([{"expected_gap_key": f.expected_gap_key, "label": f.label} for f in fxs], gaps)
    res.update(scenario_code=scenario_code, sealed_sha256=[f.sealed_sha256 for f in fxs],
               sealed_before_run=True if start is not None else None)
    return res


def run_metric(ctx: Any, session: Session, workspace_id: str, exercise_id: str, metric: str, *, kb_ids: list[str] | None = None,
               scenario_code: str | None = None, clone_ids: list[str] | None = None, benchmark_set_id: str | None = None,
               max_gaps: int = 0, guard: Any = None) -> dict[str, Any]:
    if metric not in METRICS:
        raise Unprocessable(f"métrique inconnue : {metric}", details={"allowed": list(METRICS)})
    kb_for_run: str | None = None
    if metric == "T2":
        res = compute_t2(session, exercise_id)
    elif metric == "T6":
        res = compute_t6(session, exercise_id)
    elif metric == "T1":
        res, kb_for_run = _t1(ctx, session, workspace_id, exercise_id, kb_ids or [])
    elif metric == "T5":
        ids = list(dict.fromkeys([exercise_id, *(clone_ids or [])]))
        if guard:
            for i in ids:
                guard(i)
        if len(ids) < 3 or not gaps_port.gaps_available(ctx):
            res = not_computed("T5", f"au moins 3 exercices clonés requis ({len(ids)} fourni(s))" if len(ids) < 3
                               else "service des lacunes indisponible", exercises=ids)
        else:
            res = metrics.t5_stability({i: gaps_port.read_gaps(ctx, session, workspace_id, i) for i in ids})
    else:
        if not gaps_port.gaps_available(ctx):
            res = not_computed(metric, "service des lacunes indisponible")
        else:
            gaps = gaps_port.read_gaps(ctx, session, workspace_id, exercise_id)
            if metric == "T3":
                res = _t3(ctx, session, workspace_id, exercise_id, scenario_code, gaps, read_events(session, exercise_id))
            elif metric == "T4":
                res = metrics.t4_not_invented(gaps)
            elif metric == "benchmark":
                bset = session.scalar(select(BenchmarkSet).where(BenchmarkSet.id == (benchmark_set_id or ""),
                                                                 BenchmarkSet.workspace_id == workspace_id))
                if bset is None:
                    raise NotFound("ensemble de référence introuvable")
                items = [{"label": i.label, "fingerprint": i.fingerprint} for i in session.scalars(
                    select(BenchmarkItem).where(BenchmarkItem.set_id == bset.id))]
                res = metrics.benchmark_match(items, gaps)
                res.update(benchmark_set_id=bset.id, source=bset.source)
            else:  # negative_control
                snap = gaps_port.read_snapshot(ctx, session, exercise_id) or {}
                demands = sum(len(i.get("demands") or []) for i in (snap.get("scenario") or {}).get("injects", [])) or None
                res = metrics.negative_control(gaps, demands, max_gaps)
    return _persist(session, workspace_id, exercise_id, kb_for_run, res)


def latest_metrics(session: Session, workspace_id: str, exercise_id: str) -> dict[str, Any]:
    """Dernière exécution par métrique ; une métrique jamais lancée est « non calculé » (jamais 0)."""
    out: dict[str, Any] = {}
    for m in METRICS:
        run = session.scalar(select(EvalRun).where(EvalRun.workspace_id == workspace_id, EvalRun.exercise_id == exercise_id,
                                                   EvalRun.metric == m).order_by(EvalRun.run_at.desc(), EvalRun.id.desc()))
        out[m] = ({**run.result, "run_id": run.id, "run_at": run.run_at.isoformat()} if run
                  else not_computed(m, "non exécuté"))
    return out


# --------------------------------------------------------------------------- fixtures / benchmark
def add_fixture(session: Session, workspace_id: str, scenario_code: str, key: str, label: str, description: str,
                by: str | None):
    return seal_fixture(session, workspace_id, scenario_code, key, label, description, by)


def create_benchmark(session: Session, workspace_id: str, name: str, source: str, description: str | None) -> BenchmarkSet:
    b = BenchmarkSet(workspace_id=workspace_id, name=name, source=source, description=description)
    session.add(b)
    session.flush()
    return b


def add_benchmark_items(session: Session, workspace_id: str, set_id: str, items: list[dict[str, Any]]) -> list[BenchmarkItem]:
    b = session.scalar(select(BenchmarkSet).where(BenchmarkSet.id == set_id, BenchmarkSet.workspace_id == workspace_id))
    if b is None:
        raise NotFound("ensemble de référence introuvable")
    rows = [BenchmarkItem(set_id=b.id, label=i["label"], description=i.get("description"), domain=i.get("domain"),
                          fingerprint=i.get("fingerprint")) for i in items]
    session.add_all(rows)
    session.flush()
    return rows


# --------------------------------------------------------------------------- scorecard
def put_assessments(session: Session, workspace_id: str, exercise_id: str, answers: list[dict[str, Any]],
                    reviewed_by: str | None, assessor: str) -> dict[str, Any]:
    for a in answers:
        crit = session.get(RubricCriterion, a["criterion_id"])
        if crit is None:
            raise Unprocessable(f"critère inconnu : {a['criterion_id']}")
        if a["answer"] not in ANSWERS:
            raise Unprocessable(f"réponse invalide : {a['answer']}", details={"allowed": list(ANSWERS)})
        ev = a.get("evidence") or []
        for e in ev:
            if e.get("kind") not in EVIDENCE_KINDS:
                raise Unprocessable("type de preuve invalide (les lacunes ne peuvent pas servir de preuve : indépendance)",
                                    details={"allowed": list(EVIDENCE_KINDS)})
        if a["answer"] != "not_assessed" and not ev and not (a.get("note") or "").strip():
            raise Unprocessable(f"critère {crit.id} : une réponse oui/partiel/non exige une preuve ou une note")
        row = session.scalar(select(Assessment).where(Assessment.exercise_id == exercise_id,
                                                      Assessment.criterion_id == crit.id))
        if row is None:
            row = Assessment(workspace_id=workspace_id, exercise_id=exercise_id, criterion_id=crit.id, answer=a["answer"])
            session.add(row)
        row.answer, row.evidence, row.note = a["answer"], ev, a.get("note")
        row.assessor, row.reviewed_by = a.get("assessor") or assessor, reviewed_by
    session.flush()
    return build_scorecard(session, workspace_id, exercise_id)


class EvaluationService:
    """`ctx.services["evaluation"]` : lecture des mesures et du scorecard pour le module reports."""

    def __init__(self, ctx: Any) -> None:
        self.ctx = ctx

    def metrics(self, session: Session, workspace_id: str, exercise_id: str) -> dict[str, Any]:
        return latest_metrics(session, workspace_id, exercise_id)

    def scorecard(self, session: Session, workspace_id: str, exercise_id: str) -> dict[str, Any]:
        return build_scorecard(session, workspace_id, exercise_id)

    compute_t2 = staticmethod(compute_t2)
    compute_t6 = staticmethod(compute_t6)
