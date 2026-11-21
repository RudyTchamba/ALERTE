"""Cas d'usage : exercices, sièges, lancement, commandes, lectures, gardes."""
from __future__ import annotations

import copy
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.events import Visibility
from ..core.auth import Principal
from ..core.db import utcnow
from ..core.errors import Conflict, Forbidden, NotFound, Unprocessable
from ..core.ids import new_id
from ..workspaces import service as ws_service
from ..workspaces.schemas import TokenCreate
from . import schemas, states
from .common import resolve_settings, svc
from .engine import SimulationManager, board_dicts, revoke_seat_tokens
from .models import (
    Command,
    Decision,
    DecisionCitation,
    Exercise,
    ExerciseReference,
    ExerciseSnapshot,
    InboxItem,
    Seat,
    SeatAssignment,
)
from .readiness import compute_readiness
from .snapshot import build_snapshot, commitment_hash, payload_hash, reference_rows, seat_rows, snapshot_hash

MODE_FROM_LLM = {"openai_compat": "ai", "scripted": "scripted", "cassette": "cassette"}
KIND_ALIASES = {"kb": "knowledge_base", "document": "document_version", "version": "document_version"}


# --------------------------------------------------------------------------- gardes
def exercise_guard(session: Session, principal: Principal, exercise_id: str) -> Exercise:
    """NotFound si l'exercice n'appartient pas à l'espace ; Forbidden si le jeton est lié à un autre exercice."""
    ex = session.scalar(select(Exercise).where(Exercise.id == exercise_id,
                                               Exercise.workspace_id == principal.workspace_id))
    if ex is None:
        raise NotFound("exercice introuvable")
    if principal.exercise_id and principal.exercise_id != ex.id:
        raise Forbidden("jeton lié à un autre exercice", code="workspace.forbidden")
    return ex


def reference_guard(session: Session, kind: str, obj_id: str) -> bool:
    """Garde de référence : un objet référencé par un exercice LANCÉ ne peut qu'être archivé."""
    kind = KIND_ALIASES.get(kind, kind)
    return session.scalar(select(ExerciseReference.id).where(ExerciseReference.kind == kind,
                                                             ExerciseReference.ref_id == obj_id).limit(1)) is not None


def _require_mutable(ex: Exercise) -> None:
    if ex.state not in (states.DRAFT, states.READY):
        raise Conflict("exercice lancé : configuration figée", code="exercise.immutable", details={"state": ex.state})


# --------------------------------------------------------------------------- sorties
def seat_out(s: Seat, full: bool = True) -> schemas.SeatOut:
    return schemas.SeatOut(code=s.code, institution_id=s.institution_id, agent_id=s.agent_id if full else None,
                           controller=s.controller, human_name=s.human_name if full else None)


def exercise_out(session: Session, ex: Exercise, *, with_seats: bool = False, full: bool = True) -> dict[str, Any]:
    out = schemas.ExerciseOut.model_validate({
        **{k: getattr(ex, k) for k in schemas.ExerciseOut.model_fields if k != "seats"},
        "seats": [seat_out(x, full) for x in seat_rows(session, ex.id)] if with_seats else None})
    return out.model_dump(mode="json", exclude_none=not with_seats and False)


# --------------------------------------------------------------------------- création / lecture
def _next_code(session: Session, ws: str) -> str:
    n = len(list(session.scalars(select(Exercise.id).where(Exercise.workspace_id == ws)))) + 1
    while session.scalar(select(Exercise.id).where(Exercise.workspace_id == ws, Exercise.code == f"EX-{n:03d}")):
        n += 1
    return f"EX-{n:03d}"


def create_exercise(ctx: Any, mgr: SimulationManager, p: Principal, body: schemas.ExerciseCreate | None,
                    from_id: str | None) -> str:
    body = body or schemas.ExerciseCreate()
    default_cap = ctx.settings.max_llm_calls
    with mgr.write_tx("create") as s:
        parent = exercise_guard(s, p, from_id) if from_id else None
        scenario_id = body.scenario_id or (parent.scenario_id if parent else None)
        if not scenario_id:
            raise Unprocessable("scenario_id requis", code="exercise.scenario_required")
        # le scénario doit exister dans l'espace (isolation) : le service lève NotFound sinon
        svc(ctx, "scenarios").export_scenario_snapshot(s, p.workspace_id, scenario_id)
        raw_settings = body.settings if body.settings is not None else (parent.settings if parent else None)
        settings = resolve_settings(raw_settings, default_cap)
        ex = Exercise(
            workspace_id=p.workspace_id, scenario_id=scenario_id, parent_exercise_id=parent.id if parent else None,
            code=body.code or _next_code(s, p.workspace_id),
            title=body.title or (parent.title if parent else f"Exercice {scenario_id[:8]}"),
            pace=body.pace or (parent.pace if parent else "auto"),
            ai_mode=body.ai_mode or (parent.ai_mode if parent else MODE_FROM_LLM.get(ctx.settings.llm_mode, "ai")),
            settings=settings)
        s.add(ex)
        try:
            s.flush()
        except Exception as exc:  # noqa: BLE001 - code dupliqué
            raise Conflict("code d'exercice déjà utilisé", code="exercise.duplicate_code") from exc
        if parent:
            for r in seat_rows(s, parent.id):
                seat = Seat(exercise_id=ex.id, code=r.code, institution_id=r.institution_id, agent_id=r.agent_id,
                            controller=r.controller, human_name=r.human_name, position=r.position)
                s.add(seat)
                s.flush()
                s.add(SeatAssignment(seat_id=seat.id, controller=seat.controller, human_name=seat.human_name,
                                     reason="clone", by_actor=f"token:{p.token_id}"))
        return ex.id


def list_exercises(session: Session, p: Principal, state: str | None = None) -> list[Exercise]:
    q = select(Exercise).where(Exercise.workspace_id == p.workspace_id).order_by(Exercise.created_at, Exercise.id)
    if p.exercise_id:
        q = q.where(Exercise.id == p.exercise_id)
    if state:
        q = q.where(Exercise.state == state)
    return list(session.scalars(q))


def delete_exercise(mgr: SimulationManager, p: Principal, ex_id: str) -> None:
    with mgr.write_tx(ex_id) as s:
        ex = exercise_guard(s, p, ex_id)
        if ex.state not in (states.DRAFT, states.READY) or s.get(ExerciseSnapshot, ex.id) is not None:
            raise Conflict("un exercice lancé ne peut qu'être archivé", code="exercise.started")
        for seat in seat_rows(s, ex.id):
            revoke_seat_tokens(None, s, ex, seat.id)
            s.query(SeatAssignment).filter(SeatAssignment.seat_id == seat.id).delete()
            s.delete(seat)
        s.query(Command).filter(Command.exercise_id == ex.id).delete()
        s.flush()
        s.delete(ex)


def archive_exercise(mgr: SimulationManager, p: Principal, ex_id: str) -> None:
    with mgr.write_tx(ex_id) as s:
        ex = exercise_guard(s, p, ex_id)
        mgr.w.set_state(s, ex, states.ARCHIVED, "archived_by_facilitator", "facilitator")


# --------------------------------------------------------------------------- sièges
def put_seats(ctx: Any, mgr: SimulationManager, p: Principal, ex_id: str, body: schemas.SeatsPut) -> None:
    codes = [x.code for x in body.seats]
    if len(set(codes)) != len(codes):
        raise Unprocessable("codes de siège dupliqués", code="seat.duplicate_code")
    with mgr.write_tx(ex_id) as s:
        ex = exercise_guard(s, p, ex_id)
        _require_mutable(ex)
        for x in body.seats:
            ws_service.get_institution(s, p.workspace_id, x.institution_id)  # NotFound hors espace
            if x.agent_id:
                svc(ctx, "agents").export_agent_snapshot(s, p.workspace_id, x.agent_id)
            if x.controller == "human" and not (x.human_name or "").strip():
                raise Unprocessable("siège humain : humain nommé requis", code="seat.human_unnamed",
                                    details={"seat": x.code})
        existing = {r.code: r for r in seat_rows(s, ex.id)}
        for code, r in existing.items():
            if code not in codes:
                revoke_seat_tokens(ctx, s, ex, r.id)
                s.query(SeatAssignment).filter(SeatAssignment.seat_id == r.id).delete()
                s.delete(r)
        s.flush()
        for pos, x in enumerate(body.seats):
            row = existing.get(x.code)
            name = (x.human_name or "").strip() or None
            if row is None:
                row = Seat(exercise_id=ex.id, code=x.code, institution_id=x.institution_id, agent_id=x.agent_id,
                           controller=x.controller, human_name=name if x.controller == "human" else None, position=pos)
                s.add(row)
                s.flush()
                changed = True
            else:
                changed = (row.controller, row.human_name, row.agent_id) != (
                    x.controller, name if x.controller == "human" else None, x.agent_id)
                if row.controller == "human" and changed:
                    revoke_seat_tokens(ctx, s, ex, row.id)
                row.institution_id, row.agent_id, row.position = x.institution_id, x.agent_id, pos
                row.controller, row.human_name = x.controller, name if x.controller == "human" else None
            if changed:
                s.add(SeatAssignment(seat_id=row.id, controller=row.controller, human_name=row.human_name,
                                     reason="setup", by_actor=f"token:{p.token_id}"))
        if ex.state == states.READY:
            states.assert_transition(ex.state, states.DRAFT)
            ex.state = states.DRAFT


def invite_seat(mgr: SimulationManager, p: Principal, ex_id: str, seat_code: str, hours: int) -> dict[str, Any]:
    with mgr.write_tx(ex_id) as s:
        ex = exercise_guard(s, p, ex_id)
        if ex.state in states.TERMINAL_STATES:
            raise Conflict("exercice terminé", code="exercise.invalid_transition")
        seat = s.scalar(select(Seat).where(Seat.exercise_id == ex.id, Seat.code == seat_code))
        if seat is None:
            raise NotFound("siège introuvable")
        if seat.controller != "human" or not seat.human_name:
            raise Conflict("siège non confié à un humain nommé", code="seat.not_assigned")
        plain, row = ws_service.create_token(s, p, TokenCreate(
            role="player", label=f"{seat.human_name} ({seat.code})", exercise_id=ex.id, seat_id=seat.id,
            expires_in_hours=hours))
        return {"token": plain, "link": f"/play#t={plain}", "seat": seat.code, "human_name": seat.human_name,
                "expires_at": row.expires_at.isoformat() if row.expires_at else None, "token_id": row.id}


# --------------------------------------------------------------------------- readiness / lancement
def readiness(ctx: Any, session: Session, p: Principal, ex_id: str) -> dict[str, Any]:
    ex = exercise_guard(session, p, ex_id)
    return compute_readiness(ctx, session, ex, seat_rows(session, ex.id))


def mark_ready(ctx: Any, mgr: SimulationManager, p: Principal, ex_id: str) -> dict[str, Any]:
    with mgr.write_tx(ex_id) as s:
        ex = exercise_guard(s, p, ex_id)
        res = compute_readiness(ctx, s, ex, seat_rows(s, ex.id))
        if not res["ok"]:
            raise Conflict("contrôles bloquants", code="exercise.readiness_blocked", details={"blocking": res["blocking"]})
        states.assert_transition(ex.state, states.READY)
        ex.state = states.READY
        return res


def start_exercise(ctx: Any, mgr: SimulationManager, p: Principal, ex_id: str) -> str:
    with mgr.write_tx(ex_id) as s:
        ex = exercise_guard(s, p, ex_id)
        states.assert_command_allowed(ex.state, "start")
        mgr.assert_capacity(ex_id)
        seats = seat_rows(s, ex.id)
        res = compute_readiness(ctx, s, ex, seats)
        if not res["ok"]:
            raise Conflict("lancement refusé : contrôles bloquants", code="exercise.readiness_blocked",
                           details={"blocking": res["blocking"], "warnings": res["warnings"]})
        payload, registry = build_snapshot(ctx, s, ex, seats)
        sha, commit = snapshot_hash(payload), commitment_hash(payload, registry)
        if ex.state == states.DRAFT:
            states.assert_transition(states.DRAFT, states.READY)
            ex.state = states.READY
        ex.snapshot_sha256, ex.commitment_sha256 = sha, commit
        versions = sorted({v for k in payload["kb"] for v in k["document_version_ids"]})
        s.add(ExerciseSnapshot(exercise_id=ex.id, payload=copy.deepcopy(payload), payload_sha256=payload_hash(payload),
                               snapshot_sha256=sha, commitment_sha256=commit, document_version_ids=versions,
                               readiness=res))
        s.add_all([ExerciseReference(exercise_id=ex.id, kind=k, ref_id=r) for k, r in reference_rows(payload)])
        cmd = Command(exercise_id=ex.id, kind="start", args={}, status="applied", issued_by=f"token:{p.token_id}",
                      applied_at=utcnow())
        s.add(cmd)
        mgr.w.append(s, ex.id, "SNAPSHOT", "system", {"snapshot_sha256": sha, "commitment_sha256": commit,
                                                       "ai_mode": ex.ai_mode, "readiness": res}, visibility="audit")
        mgr.w.set_state(s, ex, states.RUNNING, "start", "facilitator")
        cid = cmd.id
    mgr.ensure_runner(ex_id)
    return cid


# --------------------------------------------------------------------------- commandes
_ARG_MODELS = {"surprise": schemas.SurpriseArgs, "seat_switch": schemas.SeatSwitchArgs,
               "correction": schemas.CorrectionArgs, "speed": schemas.SpeedArgs, "resume": schemas.ResumeArgs}


def post_command(mgr: SimulationManager, session: Session, p: Principal, ex_id: str,
                 body: schemas.CommandIn) -> dict[str, Any]:
    from ..audit.models import LedgerEvent
    ex = exercise_guard(session, p, ex_id)
    kind = body.kind
    states.assert_command_allowed(ex.state, kind, ex.pace)  # 409 avant toute validation d'arguments
    if kind == "start":
        raise Conflict("utiliser le lancement", code="exercise.invalid_transition")
    model = _ARG_MODELS.get(kind)
    try:
        args = model(**body.args).model_dump(exclude_none=True) if model else {}
    except Exception as exc:  # noqa: BLE001 - ValidationError pydantic
        raise Unprocessable("arguments de commande invalides", code="command.invalid_args",
                            details={"errors": str(exc)[:500]}) from exc
    if not model and body.args:
        raise Unprocessable("cette commande n'accepte pas d'arguments", code="command.invalid_args")
    seats = {x.code for x in seat_rows(session, ex.id)}
    if kind == "surprise" and any(c not in seats for c in args["recipients"]):
        raise Unprocessable("destinataire(s) inconnu(s)", code="command.invalid_args")
    if kind == "seat_switch":
        if args["seat"] not in seats:
            raise NotFound("siège introuvable")
        if args["controller"] == "human" and not (args.get("human_name") or "").strip():
            raise Unprocessable("humain nommé requis", code="seat.human_unnamed")
    if kind == "correction" and session.scalar(select(LedgerEvent.seq).where(
            LedgerEvent.exercise_id == ex.id, LedgerEvent.seq == args["corrects_seq"])) is None:
        raise Unprocessable("seq à corriger inexistant", code="command.invalid_args")
    cid = mgr.submit_command(ex.id, kind, args, f"token:{p.token_id}")
    session.expire_all()
    cmd = session.get(Command, cid)
    return {"id": cid, "kind": kind, "status": cmd.status, "exercise_state": session.get(Exercise, ex.id).state}


# --------------------------------------------------------------------------- lectures
def snapshot_view(session: Session, p: Principal, ex_id: str) -> dict[str, Any]:
    ex = exercise_guard(session, p, ex_id)
    snap = session.get(ExerciseSnapshot, ex.id)
    if snap is None:
        raise Conflict("exercice non lancé : pas de snapshot", code="exercise.not_started")
    return {"exercise_id": ex.id, "snapshot_sha256": snap.snapshot_sha256, "commitment_sha256": snap.commitment_sha256,
            "payload_sha256": snap.payload_sha256, "hash_scope": "snapshot_sha256 exclut exercise.id/code et seat_id",
            "payload": snap.payload, "readiness": snap.readiness, "document_version_ids": snap.document_version_ids}


def board_view(session: Session, p: Principal, ex_id: str, after: int = 0) -> list[dict]:
    ex = exercise_guard(session, p, ex_id)
    return [m for m in board_dicts(session, ex.id, None)]


def decisions_view(session: Session, p: Principal, ex_id: str, seat: str | None, inject_ref: str | None) -> list[dict]:
    ex = exercise_guard(session, p, ex_id)
    codes = {s.id: s.code for s in seat_rows(session, ex.id)}
    q = select(Decision).where(Decision.exercise_id == ex.id).order_by(Decision.ledger_seq)
    if inject_ref:
        q = q.where(Decision.inject_ref == inject_ref)
    out = []
    for d in session.scalars(q):
        if seat and codes.get(d.seat_id) != seat:
            continue
        cites = session.scalars(select(DecisionCitation).where(DecisionCitation.decision_id == d.id))
        out.append({"decision_id": d.id, "seat_code": codes.get(d.seat_id), "inject_ref": d.inject_ref,
                    "round": d.round, "action": d.action, "action_code": d.action_code, "outcome": d.outcome,
                    "confidence": d.confidence, "options_considered": d.options_considered,
                    "gap_flags": d.gap_flags, "rationale": d.rationale, "evidence_tag": d.evidence_tag,
                    "author": d.author, "status": d.status, "seq": d.ledger_seq,
                    "legal_basis": [{"chunk_id": c.chunk_id, "article": c.article, "quote": c.quote,
                                     "check": c.check_status, "reason": c.check_reason} for c in cites]})
    return out


def inbox_view(session: Session, ex: Exercise, seat_code: str) -> list[dict]:
    seat = session.scalar(select(Seat).where(Seat.exercise_id == ex.id, Seat.code == seat_code))
    if seat is None:
        raise NotFound("siège introuvable")
    from .engine import inbox_dict
    return [inbox_dict(i) for i in session.scalars(select(InboxItem).where(
        InboxItem.exercise_id == ex.id, InboxItem.seat_id == seat.id).order_by(InboxItem.delivered_seq, InboxItem.id))]


def can_see_board(p: Principal) -> bool:
    from ..audit.router import allowed_visibilities
    return Visibility.BOARD in allowed_visibilities(p)


def new_code() -> str:
    return new_id()[-6:]
