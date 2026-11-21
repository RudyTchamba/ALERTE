"""Siège humain (doc 08 §8.12) : mêmes validations que l'agent ; la soumission est STAGÉE sur la `human_task`
puis écrite par le runner dans l'étape (un seul écrivain, étape idempotente)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.auth import Principal
from ..core.errors import AppError, Conflict, Forbidden, NotFound, Unprocessable
from ..core.ids import new_id
from . import schemas, states
from .common import MAX_ROUNDS, REPLY_STATUSES, activatable, svc
from .engine import SeatInfo, SimulationManager, Unit, board_dicts, build_seat_context, decision_dicts, inbox_dict
from .models import BoardMessage, Command, Exercise, HumanTask, InboxItem, Seat
from .snapshot import load_payload, scope_for_seat, seat_entry, seat_rows

DEFAULT_LIMITS = {"max_search_calls": 3, "max_legal_calls": 2}
MAX_STAGED_POSTS = 5


def resolve_seat(session: Session, p: Principal) -> tuple[Exercise, Seat]:
    if not p.exercise_id or not p.seat_id:
        raise Conflict("jeton sans siège", code="seat.not_assigned")
    ex = session.scalar(select(Exercise).where(Exercise.id == p.exercise_id, Exercise.workspace_id == p.workspace_id))
    seat = session.get(Seat, p.seat_id)
    if ex is None or seat is None or seat.exercise_id != ex.id:
        raise NotFound("siège introuvable")
    if seat.controller != "human":
        raise Conflict("siège non confié à un humain", code="seat.not_assigned")
    return ex, seat


def _active(ex: Exercise) -> None:
    if ex.state not in (states.RUNNING, states.PAUSED):
        raise Conflict("exercice non actif", code="exercise.not_running", details={"state": ex.state})


def pending_task(session: Session, seat: Seat) -> HumanTask | None:
    return session.scalar(select(HumanTask).where(HumanTask.seat_id == seat.id, HumanTask.status == "pending")
                          .order_by(HumanTask.created_at.desc()).limit(1))


def _need_task(session: Session, ex: Exercise, seat: Seat) -> HumanTask:
    _active(ex)
    t = pending_task(session, seat)
    if t is None:
        raise Conflict("aucune tâche en attente pour ce siège", code="seat.no_pending_task")
    return t


def _infos(session: Session, ex_id: str, snap: dict) -> list[SeatInfo]:
    by_id = {x["seat_id"]: x for x in snap["seats"]}
    return [SeatInfo(r.id, r.code, r.institution_id, r.agent_id, r.position, by_id[r.id].get("agent"),
                     activatable(by_id[r.id].get("agent"))) for r in seat_rows(session, ex_id)]


def _unit(session: Session, ex_id: str, snap: dict, ref: str) -> Unit:
    for i in snap["scenario"]["injects"]:
        if i["inject_ref"] == ref:
            return Unit(str(i["seq"]), ref, i)
    for c in session.scalars(select(Command).where(Command.exercise_id == ex_id, Command.kind == "surprise")):
        if c.args.get("inject", {}).get("inject_ref") == ref:
            return Unit(f"s{c.args['k']}", ref, c.args["inject"])
    raise NotFound("inject introuvable")


def _seat_ctx(session: Session, ex: Exercise, seat: Seat, task: HumanTask):
    snap = load_payload(session, ex.id)
    infos = _infos(session, ex.id, snap)
    me = next(x for x in infos if x.id == seat.id)
    return snap, infos, me, build_seat_context(session, ex.id, snap, infos, me, _unit(session, ex.id, snap, task.inject_ref),
                                               task.round, task.step_key, None, "human_seat")


def _limits(me: SeatInfo) -> dict:
    return {**DEFAULT_LIMITS, **{k: v for k, v in ((me.agent or {}).get("limits") or {}).items()
                                 if k in ("max_search_calls",) or k == "max_legal_calls_per_inject"}}


def seat_card(session: Session, p: Principal) -> dict[str, Any]:
    ex, seat = resolve_seat(session, p)
    snap = load_payload(session, ex.id)
    entry = seat_entry(snap, seat.code)
    agent = entry.get("agent") or {}
    inst = next((i for i in snap["institutions"] if i["id"] == seat.institution_id), {})
    scope = scope_for_seat(snap, seat.code, "human_seat")
    return {"exercise": {"id": ex.id, "code": ex.code, "title": ex.title, "state": ex.state, "ai_mode": ex.ai_mode},
            "seat": {"code": seat.code, "human_name": seat.human_name, "controller": seat.controller},
            "institution": {k: inst.get(k) for k in ("id", "code", "name", "kind")},
            "role": {"mission": agent.get("mission"), "instructions": agent.get("instructions"),
                     "tools": agent.get("tools"), "limits": agent.get("limits")},
            "mandates": [m for m in snap["mandates"] if m.get("institution_id") == seat.institution_id],
            "knowledge_bases": [{"kb_id": k["kb_id"], "code": k["code"], "name": k["name"]}
                                for k in snap["kb"] if k["kb_id"] in scope.kb_ids],
            "seat_codes": [x["code"] for x in snap["seats"] if x["code"] != seat.code]}


def task_view(session: Session, p: Principal) -> dict[str, Any]:
    ex, seat = resolve_seat(session, p)
    t = pending_task(session, seat)
    if t is None:
        return {"task": None, "exercise_state": ex.state}
    snap, _infos_, me, sctx = _seat_ctx(session, ex, seat, t)
    inj = sctx.inject
    return {"exercise_state": ex.state, "task": {
        "id": t.id, "status": t.status, "round": t.round, "inject_ref": t.inject_ref,
        "deadline_at": t.deadline_at.isoformat(), "fallback": t.fallback,
        "inject": {k: inj.get(k) for k in ("inject_ref", "sim_time", "title", "body", "from_actor", "tags")},
        "inbox": sctx.inbox, "board": sctx.board, "own_decisions": sctx.own_decisions,
        "staged_posts": (t.submission or {}).get("posts", []), "usage": t.usage or {}, "limits": _limits(me)}}


def _log(mgr: SimulationManager, s: Session, ex: Exercise, seat: Seat, actor: str, events: list[tuple[str, dict, str]],
         sim: str | None) -> None:
    for typ, payload, vis in events:
        mgr.w.append(s, ex.id, typ, actor, payload, seat_id=seat.id, sim_time=sim, visibility=vis)


def search(ctx: Any, mgr: SimulationManager, p: Principal, query: str) -> dict[str, Any]:
    with mgr.write_tx(p.exercise_id or "-") as s:
        ex, seat = resolve_seat(s, p)
        t = _need_task(s, ex, seat)
        snap, _i, me, _c = _seat_ctx(s, ex, seat, t)
        usage = dict(t.usage or {})
        seen: dict = dict(usage.get("queries", {}))
        q = query.strip()
        if q in seen:
            return {"hits": seen[q], "warning": "requête dupliquée : résultat précédent renvoyé"}
        if usage.get("search_calls", 0) >= _limits(me)["max_search_calls"]:
            raise AppError("limite de recherches atteinte", code="seat.limit_reached", status_code=429)
        scope = scope_for_seat(snap, seat.code, "human_seat")
        raw = [] if scope.is_empty else svc(ctx, "search").search(scope, q, 5)
        actor = f"human:{seat.human_name}"
        sim = _unit(s, ex.id, snap, t.inject_ref).inject.get("sim_time")
        hits = []
        for h in raw:
            if h.document_version_id not in scope.document_version_ids or h.kb_id not in scope.kb_ids:
                s_err = {"component": "scope", "message": "SCOPE_VIOLATION", "next_action": "dropped",
                         "chunk_id": h.chunk_id}
                mgr.w.append(s, ex.id, "ERROR", "system", s_err, seat_id=seat.id, sim_time=sim)
                continue
            hits.append({"chunk_id": h.chunk_id, "title": h.doc_title, "article": h.article, "page": h.page,
                         "excerpt": (h.snippet or h.text)[:400], "score": h.score})
        _log(mgr, s, ex, seat, actor, [
            ("TOOL_CALL", {"tool": "search_kb", "args": {"query": q}, "rationale": None, "ok": True, "error": None}, "seat"),
            ("RETRIEVAL", {"query": q, "scope_hash": scope.scope_hash(), "results": [
                {"chunk_id": h["chunk_id"], "score": h["score"], "rank": i + 1} for i, h in enumerate(hits)],
                "signals": {"degraded": False}}, "seat")], sim)
        usage["search_calls"] = usage.get("search_calls", 0) + 1
        seen[q] = hits
        usage["queries"] = seen
        t.usage = usage
        t.retrieval = sorted(set(t.retrieval or []) | {h["chunk_id"] for h in hits})
        return {"hits": hits}


def ask_legal(ctx: Any, mgr: SimulationManager, p: Principal, question: str) -> dict[str, Any]:
    with mgr.write_tx(p.exercise_id or "-") as s:
        ex, seat = resolve_seat(s, p)
        t = _need_task(s, ex, seat)
        snap, _i, me, sctx = _seat_ctx(s, ex, seat, t)
        usage = dict(t.usage or {})
        lim = (me.agent or {}).get("limits") or {}
        if usage.get("legal_calls", 0) >= lim.get("max_legal_calls_per_inject", DEFAULT_LIMITS["max_legal_calls"]):
            raise AppError("limite de questions au conseiller atteinte", code="seat.limit_reached", status_code=429)
        agents = svc(ctx, "agents")
        if not hasattr(agents, "ask_legal"):
            raise AppError("conseiller juridique indisponible", code="legal.unavailable", status_code=503)
        res = dict(agents.ask_legal(sctx, question))
        events = res.pop("events", [])
        calls = int(res.pop("llm_calls", 0) or 0)
        t.retrieval = sorted(set(t.retrieval or []) | set(res.get("retrieved_chunk_ids") or []))
        actor = f"human:{seat.human_name}"
        sim = sctx.inject.get("sim_time")
        mgr.w.append(s, ex.id, "TOOL_CALL", actor, {"tool": "ask_legal", "args": {"question": question}, "rationale": None,
                                                    "ok": bool(res.get("ok", True)), "error": res.get("reason")}, seat_id=seat.id, sim_time=sim, visibility="seat")
        for te in events:
            mgr.w.append(s, ex.id, te.type, "legal" if te.type == "LLM_CALL" else actor, te.payload, seat_id=seat.id,
                         sim_time=sim, visibility=te.visibility)
        ex.llm_calls_used += calls
        usage["legal_calls"] = usage.get("legal_calls", 0) + 1
        t.usage = usage
        return res


def stage_post(mgr: SimulationManager, p: Principal, body: schemas.PostIn) -> dict[str, Any]:
    with mgr.write_tx(p.exercise_id or "-") as s:
        ex, seat = resolve_seat(s, p)
        t = _need_task(s, ex, seat)
        snap = load_payload(s, ex.id)
        infos = _infos(s, ex.id, snap)
        targets = {x.code for x in infos if x.activatable and x.code != seat.code}
        errs = []
        if body.to not in targets:
            errs.append({"field": "to", "reason": "destinataire invalide (inexistant, soi-même ou non activable)"})
        if t.round > MAX_ROUNDS:
            errs.append({"field": "round", "reason": "tour maximal dépassé"})
        if body.reply_status and body.reply_status not in REPLY_STATUSES:
            errs.append({"field": "reply_status", "reason": "valeur invalide"})
        if body.in_reply_to:
            orig = s.get(BoardMessage, body.in_reply_to)
            if orig is None or orig.exercise_id != ex.id:
                errs.append({"field": "in_reply_to", "reason": "message inconnu"})
            elif body.reply_status and (orig.to_seat_id != seat.id or orig.msg_type != "REQUEST"):
                errs.append({"field": "reply_status", "reason": "ne répond pas à un REQUEST reçu"})
        elif body.reply_status:
            errs.append({"field": "reply_status", "reason": "reply_status exige in_reply_to"})
        sub = dict(t.submission or {})
        posts = list(sub.get("posts", []))
        if len(posts) >= MAX_STAGED_POSTS:
            errs.append({"field": "posts", "reason": "trop de messages pour cette activation"})
        if errs:
            raise Unprocessable("message invalide", code="post.invalid", details={"errors": errs})
        posts.append({"to": body.to, "msg_type": body.msg_type, "body": body.body, "in_reply_to": body.in_reply_to,
                      "reply_status": body.reply_status})
        sub["posts"] = posts
        t.submission = sub
        if body.final and not sub.get("decision"):
            _complete(mgr, s, ex, seat, t)
        return {"staged": len(posts), "task_status": t.status}


def _complete(mgr: SimulationManager, s: Session, ex: Exercise, seat: Seat, t: HumanTask) -> None:
    from ..core.db import utcnow
    t.status, t.submitted_at = "submitted", utcnow()


def citation_check(ctx: Any, decision: dict, retrieval: list[str], scope) -> list[dict]:
    """Adaptateur du CitationChecker exposé par `agents` (`check(decision, retrieval_set, scope)`)."""
    checker = getattr(svc(ctx, "agents"), "citation_checker", None)
    if checker is None:
        raise AppError("contrôle de citation indisponible", code="citation_checker.unavailable", status_code=503)
    if callable(checker) and not hasattr(checker, "check"):
        checker = checker()
    out = []
    for r in checker.check(decision, set(retrieval), scope):
        get = (lambda k, d=None, r=r: r.get(k, d)) if isinstance(r, dict) else (lambda k, d=None, r=r: getattr(r, k, d))
        ok = get("pass", None)
        if ok is None:
            ok = get("passed", get("ok", get("check") == "pass"))
        out.append({"chunk_id": get("chunk_id"), "pass": bool(ok), "reason": get("reason")})
    return out


def submit_decision(ctx: Any, mgr: SimulationManager, p: Principal, body: schemas.DecisionIn) -> dict[str, Any]:
    with mgr.write_tx(p.exercise_id or "-") as s:
        ex, seat = resolve_seat(s, p)
        t = _need_task(s, ex, seat)
        snap = load_payload(s, ex.id)
        errs = []
        if body.action_code is not None and body.action_code not in {a["code"] for a in snap["actions"]}:
            errs.append({"field": "action_code", "reason": "hors catalogue"})
        if body.outcome != "no_legal_basis_found" and not body.legal_basis:
            errs.append({"field": "legal_basis", "reason": "obligatoire sauf outcome=no_legal_basis_found"})
        if errs:
            raise Unprocessable("décision invalide", code="decision.invalid", details={"errors": errs})
        scope = scope_for_seat(snap, seat.code, "human_seat")
        decision = body.model_dump()
        decision["decision_id"] = new_id()
        checks = citation_check(ctx, decision, list(t.retrieval or []), scope) if body.legal_basis else []
        fails = [{"chunk_id": c["chunk_id"], "reason": c["reason"]} for c in checks if not c["pass"]]
        if fails:
            raise Unprocessable("citation non vérifiée", code="decision.citation_failed", details={"failures": fails})
        by_chunk = {c["chunk_id"]: c for c in checks}
        decision["legal_basis"] = [{**b, "check": "pass", "reason": (by_chunk.get(b["chunk_id"]) or {}).get("reason")}
                                   for b in decision["legal_basis"]]
        decision["status"], decision["author"] = "recorded", "human"
        sub = dict(t.submission or {})
        sub["decision"], sub["checks"] = decision, checks
        t.submission = sub
        _complete(mgr, s, ex, seat, t)
        return {"decision_id": decision["decision_id"], "status": "recorded", "task_status": t.status}


def forbidden_other_seat(p: Principal, seat_code: str | None, own: str) -> None:
    if seat_code and seat_code != own:
        raise Forbidden("un joueur ne lit que la boîte de son siège", code="workspace.forbidden")


def own_inbox(session: Session, p: Principal) -> list[dict]:
    ex, seat = resolve_seat(session, p)
    return [inbox_dict(i) for i in session.scalars(select(InboxItem).where(
        InboxItem.exercise_id == ex.id, InboxItem.seat_id == seat.id).order_by(InboxItem.delivered_seq, InboxItem.id))]


__all__ = ["board_dicts", "decision_dicts"]
