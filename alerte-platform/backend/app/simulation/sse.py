"""Flux SSE d'exercice (doc 12 §12.4) : jeton de flux à usage unique, filtrage serveur par visibilité."""
from __future__ import annotations

import datetime as dt
import json
import time
from collections.abc import Iterator
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..audit.router import allowed_visibilities
from ..core.auth import Principal
from ..core.db import session_scope, utcnow
from ..core.errors import Unauthorized
from ..core.security import generate_token, hash_token
from . import states
from .models import Exercise, Seat, StreamToken

POLL_INTERVAL = 0.3      # lecture du ledger (modifiable par les tests)
HEARTBEAT_INTERVAL = 15.0
TOKEN_TTL_S = 60
BATCH = 200


def issue_token(session: Session, p: Principal, exercise_id: str) -> dict[str, Any]:
    plain, h = generate_token("str")
    session.add(StreamToken(token_hash=h, workspace_id=p.workspace_id, exercise_id=exercise_id, role=p.role,
                            seat_id=p.seat_id, token_id=p.token_id,
                            expires_at=utcnow() + dt.timedelta(seconds=TOKEN_TTL_S)))
    return {"stream_token": plain, "expires_in": TOKEN_TTL_S, "exercise_id": exercise_id, "role": p.role}


def consume_token(session: Session, plain: str, exercise_id: str) -> Principal:
    """Atomique : un jeton ne sert qu'une fois (UPDATE ... WHERE used_at IS NULL)."""
    bad = Unauthorized("jeton de flux invalide, expiré ou déjà utilisé", code="stream.invalid_token")
    row = session.scalar(select(StreamToken).where(StreamToken.token_hash == hash_token(plain or "")))
    if row is None or row.exercise_id != exercise_id or row.used_at is not None:
        raise bad
    exp = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=dt.UTC)
    if exp <= utcnow():
        raise bad
    res = session.execute(update(StreamToken).where(StreamToken.id == row.id, StreamToken.used_at.is_(None))
                          .values(used_at=utcnow()))
    if res.rowcount != 1:
        raise bad
    return Principal(workspace_id=row.workspace_id, role=row.role, token_id=row.token_id or "-",
                     exercise_id=exercise_id, seat_id=row.seat_id)


def _frame(seq: int | None, event: str, data: dict) -> str:
    head = f"id: {seq}\n" if seq is not None else ""
    return f"{head}event: {event}\ndata: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"


def event_stream(ctx: Any, p: Principal, exercise_id: str, after: int = 0, types: list[str] | None = None) -> Iterator[str]:
    """Générateur SSE. Tous les `seq` > after, dans l'ordre, sans trou ni doublon ; ferme après STATE completed|stopped."""
    ledger = ctx.service("ledger")
    vis = allowed_visibilities(p)
    last, beat = after, time.monotonic()
    codes: dict[str, str] = {}
    yield "retry: 3000\n\n"
    while True:
        with session_scope(ctx.session_factory) as s:
            # l'état terminal est lu AVANT les événements : tout ce qui précède son commit est visible ensuite
            state = s.scalar(select(Exercise.state).where(Exercise.id == exercise_id))
            events = ledger.read(s, exercise_id, after_seq=last, limit=BATCH, types=types, visibilities=vis,
                                 seat_id=p.seat_id)
            if events and any(e.seat_id and e.seat_id not in codes for e in events):
                codes = {x.id: x.code for x in s.scalars(select(Seat).where(Seat.exercise_id == exercise_id))}
            batch = [(e.seq, e.type, {"seq": e.seq, "type": e.type, "actor": e.actor, "seat": codes.get(e.seat_id or ""),
                                      "sim_time": e.sim_time, "real_time": e.real_time, "visibility": e.visibility,
                                      "payload": e.payload}) for e in events]
        for seq, typ, data in batch:
            last, beat = seq, time.monotonic()
            yield _frame(seq, typ, data)
            if typ == "STATE" and data["payload"].get("to") in (states.COMPLETED, states.STOPPED):
                return
        if not batch:
            if state in states.TERMINAL_STATES or state is None:
                return
            if time.monotonic() - beat >= HEARTBEAT_INTERVAL:
                beat = time.monotonic()
                yield _frame(None, "heartbeat", {"ts": utcnow().isoformat()})
            time.sleep(POLL_INTERVAL)
