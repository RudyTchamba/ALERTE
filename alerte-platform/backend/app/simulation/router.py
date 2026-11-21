"""Routes du module simulation (sans préfixe /api/v1)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..audit.router import allowed_visibilities
from ..core.auth import Principal, require_role
from ..core.context import AppContext, get_ctx, get_session
from ..core.errors import Forbidden
from . import human, schemas, service, sse
from .engine import SimulationManager

router = APIRouter()
FAC = require_role("facilitator")
ANY = require_role("facilitator", "player", "observer", "auditor")
READERS = require_role("facilitator", "observer", "auditor")
AUDITOR = require_role("auditor")
PLAYER = require_role("player")


def mgr_of(ctx: AppContext) -> SimulationManager:
    return ctx.service("simulation")


# --------------------------------------------------------------------------- exercices
@router.post("/exercises", status_code=201, tags=["simulation"])
def create_exercise(body: schemas.ExerciseCreate | None = None, from_: str | None = Query(default=None, alias="from"),
                    p: Principal = Depends(FAC), session: Session = Depends(get_session),
                    ctx: AppContext = Depends(get_ctx)) -> dict[str, Any]:
    ex_id = service.create_exercise(ctx, mgr_of(ctx), p, body, from_)
    return service.exercise_out(session, service.exercise_guard(session, p, ex_id), with_seats=True)


@router.get("/exercises", tags=["simulation"])
def list_exercises(state: str | None = None, p: Principal = Depends(ANY), session: Session = Depends(get_session)):
    return [service.exercise_out(session, e, full=p.role != "player") for e in service.list_exercises(session, p, state)]


@router.get("/exercises/{exercise_id}", tags=["simulation"])
def get_exercise(exercise_id: str, p: Principal = Depends(ANY), session: Session = Depends(get_session)):
    ex = service.exercise_guard(session, p, exercise_id)
    return service.exercise_out(session, ex, with_seats=True, full=p.role in ("owner", "facilitator", "auditor"))


@router.delete("/exercises/{exercise_id}", status_code=204, tags=["simulation"])
def delete_exercise(exercise_id: str, p: Principal = Depends(FAC), ctx: AppContext = Depends(get_ctx)) -> Response:
    service.delete_exercise(mgr_of(ctx), p, exercise_id)
    return Response(status_code=204)


@router.post("/exercises/{exercise_id}/archive", tags=["simulation"])
def archive_exercise(exercise_id: str, p: Principal = Depends(FAC), session: Session = Depends(get_session),
                     ctx: AppContext = Depends(get_ctx)):
    service.archive_exercise(mgr_of(ctx), p, exercise_id)
    session.expire_all()
    return service.exercise_out(session, service.exercise_guard(session, p, exercise_id))


@router.put("/exercises/{exercise_id}/seats", tags=["simulation"])
def put_seats(exercise_id: str, body: schemas.SeatsPut, p: Principal = Depends(FAC),
              session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)):
    service.put_seats(ctx, mgr_of(ctx), p, exercise_id, body)
    session.expire_all()
    return service.exercise_out(session, service.exercise_guard(session, p, exercise_id), with_seats=True)


@router.post("/exercises/{exercise_id}/seats/{seat}/invite", status_code=201, tags=["simulation"])
def invite(exercise_id: str, seat: str, body: schemas.InviteIn | None = None, p: Principal = Depends(FAC),
           ctx: AppContext = Depends(get_ctx)):
    return service.invite_seat(mgr_of(ctx), p, exercise_id, seat, (body or schemas.InviteIn()).expires_in_hours)


@router.get("/exercises/{exercise_id}/readiness", tags=["simulation"])
def readiness(exercise_id: str, p: Principal = Depends(FAC), session: Session = Depends(get_session),
              ctx: AppContext = Depends(get_ctx)):
    return service.readiness(ctx, session, p, exercise_id)


@router.post("/exercises/{exercise_id}/ready", tags=["simulation"])
def mark_ready(exercise_id: str, p: Principal = Depends(FAC), ctx: AppContext = Depends(get_ctx)):
    return service.mark_ready(ctx, mgr_of(ctx), p, exercise_id)


@router.post("/exercises/{exercise_id}/commands", status_code=202, tags=["simulation"])
def post_command(exercise_id: str, body: schemas.CommandIn, p: Principal = Depends(FAC),
                 session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)):
    mgr = mgr_of(ctx)
    if body.kind == "start":
        service.exercise_guard(session, p, exercise_id)
        if body.args:
            from ..core.errors import Unprocessable
            raise Unprocessable("start n'accepte pas d'arguments", code="command.invalid_args")
        cid = service.start_exercise(ctx, mgr, p, exercise_id)
        session.expire_all()
        return {"id": cid, "kind": "start", "status": "applied",
                "exercise_state": service.exercise_guard(session, p, exercise_id).state}
    return service.post_command(mgr, session, p, exercise_id, body)


@router.get("/exercises/{exercise_id}/snapshot", tags=["simulation"])
def snapshot(exercise_id: str, p: Principal = Depends(AUDITOR), session: Session = Depends(get_session)):
    return service.snapshot_view(session, p, exercise_id)


@router.get("/exercises/{exercise_id}/board", tags=["simulation"])
def board(exercise_id: str, p: Principal = Depends(ANY), session: Session = Depends(get_session)):
    if not service.can_see_board(p):
        raise Forbidden("le tableau n'est pas visible pour ce rôle", code="workspace.forbidden")
    return service.board_view(session, p, exercise_id)


@router.get("/exercises/{exercise_id}/decisions", tags=["simulation"])
def decisions(exercise_id: str, seat: str | None = None, inject_ref: str | None = None, p: Principal = Depends(ANY),
              session: Session = Depends(get_session)):
    return service.decisions_view(session, p, exercise_id, seat, inject_ref)


@router.get("/exercises/{exercise_id}/inbox", tags=["simulation"])
def inbox(exercise_id: str, seat: str | None = None, p: Principal = Depends(ANY),
          session: Session = Depends(get_session)):
    ex = service.exercise_guard(session, p, exercise_id)
    if p.role == "observer":
        raise Forbidden("boîtes privées non visibles", code="workspace.forbidden")
    if p.role == "player":
        own, other = human.resolve_seat(session, p)
        human.forbidden_other_seat(p, seat, other.code)
        return service.inbox_view(session, ex, other.code)
    if not seat:
        from ..core.errors import Unprocessable
        raise Unprocessable("paramètre 'seat' requis", code="inbox.seat_required")
    return service.inbox_view(session, ex, seat)


# --------------------------------------------------------------------------- flux SSE
@router.post("/exercises/{exercise_id}/stream-token", tags=["simulation"])
def stream_token(exercise_id: str, p: Principal = Depends(ANY), ctx: AppContext = Depends(get_ctx)):
    with mgr_of(ctx).write_tx("stream-token") as s:
        service.exercise_guard(s, p, exercise_id)
        return sse.issue_token(s, p, exercise_id)


@router.get("/exercises/{exercise_id}/stream", tags=["simulation"])
def stream(exercise_id: str, request: Request, stream_token: str = "", after: int | None = None,
           types: str | None = None, last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
           ctx: AppContext = Depends(get_ctx)):
    with mgr_of(ctx).write_tx("stream-token") as s:
        p = sse.consume_token(s, stream_token, exercise_id)
    start = after if after is not None else (int(last_event_id) if (last_event_id or "").isdigit() else 0)
    gen = sse.event_stream(ctx, p, exercise_id, start, [t for t in (types or "").split(",") if t] or None)
    return StreamingResponse(gen, media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# --------------------------------------------------------------------------- siège humain
@router.get("/seats/me", tags=["seats"])
def seat_me(p: Principal = Depends(PLAYER), session: Session = Depends(get_session)):
    return human.seat_card(session, p)


@router.get("/seats/me/task", tags=["seats"])
def seat_task(p: Principal = Depends(PLAYER), session: Session = Depends(get_session)):
    return human.task_view(session, p)


@router.post("/seats/me/search", tags=["seats"])
def seat_search(body: schemas.SearchIn, p: Principal = Depends(PLAYER), ctx: AppContext = Depends(get_ctx)):
    return human.search(ctx, mgr_of(ctx), p, body.query)


@router.post("/seats/me/ask-legal", tags=["seats"])
def seat_ask_legal(body: schemas.AskLegalIn, p: Principal = Depends(PLAYER), ctx: AppContext = Depends(get_ctx)):
    return human.ask_legal(ctx, mgr_of(ctx), p, body.question)


@router.post("/seats/me/post", tags=["seats"])
def seat_post(body: schemas.PostIn, p: Principal = Depends(PLAYER), ctx: AppContext = Depends(get_ctx)):
    return human.stage_post(mgr_of(ctx), p, body)


@router.post("/seats/me/decision", tags=["seats"])
def seat_decision(body: schemas.DecisionIn, p: Principal = Depends(PLAYER), ctx: AppContext = Depends(get_ctx)):
    return human.submit_decision(ctx, mgr_of(ctx), p, body)


__all__ = ["router", "allowed_visibilities", "READERS"]
