"""Moteur d'exécution : gestionnaire de runners (un fil par exercice), boucle du runner, commandes, COORD.

Invariants :
* le moteur est le SEUL écrivain d'événements d'exercice (`ledger.append` dans SA transaction) ;
* une ÉTAPE = une transaction (métier + ledger + ligne `step`) ; `step_key` unique => reprise idempotente ;
* ordre des verrous : verrou d'écriture de l'exercice (ici) -> verrou du ledger -> verrou SQLite ;
* le runtime d'agents est appelé HORS transaction (aucun verrou d'écriture tenu pendant un appel de modèle) ;
* les commandes sont lues entre deux étapes (`checkpoint`) ; en pause le fil se termine (reprise = relance depuis le journal).
"""
from __future__ import annotations

import datetime as dt
import logging
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..contracts import ActivationResult, SeatContext
from ..core.db import session_scope, utcnow
from ..core.errors import Conflict
from ..core.ids import new_id
from . import coord, states
from .common import MAX_ROUNDS, MSG_TYPES, REPLY_STATUSES, activatable, optional_svc, svc
from .models import (
    BoardMessage,
    Command,
    Decision,
    DecisionCitation,
    Exercise,
    HumanTask,
    InboxItem,
    Seat,
    SeatAssignment,
    Step,
)
from .snapshot import load_payload, scope_for_seat, seat_rows

log = logging.getLogger("alerte.simulation")
POLL_INTERVAL = 0.05  # attente (pace manuel, tâche humaine) ; modifiable par les tests
SURPRISE_SEQ_BASE = 10000


class RunnerKilled(Exception):
    """Arrêt brutal simulé (tests) : aucun nettoyage, l'état reste `running`."""


class RunnerAborted(Exception):
    """Arrêt du gestionnaire (fin de processus) : l'état n'est pas modifié."""


class _StopRequested(Exception):
    pass


class _Paused(Exception):
    pass


class _Exit(Exception):
    pass


@dataclass
class Hooks:
    before_step: Callable[[str], None] | None = None   # avant le travail d'une étape
    before_commit: Callable[[str], None] | None = None  # dans la transaction, avant le commit


@dataclass
class SeatInfo:
    id: str
    code: str
    institution_id: str
    agent_id: str | None
    position: int
    agent: dict | None
    activatable: bool


@dataclass
class Unit:
    n: str
    ref: str
    inject: dict
    surprise: bool = False
    cmd_id: str | None = None
    recipient_seats: list[str] = field(default_factory=list)
    in_progress: bool = False


def _iso(d: dt.datetime) -> dt.datetime:
    return d if d.tzinfo else d.replace(tzinfo=dt.UTC)


# =========================================================================== écriture (partagée API / runner)
class Writer:
    """Petites aides d'écriture d'événements ; toutes prennent la session de la transaction courante."""

    def __init__(self, ctx: Any) -> None:
        self.ctx = ctx
        self.ledger = ctx.service("ledger")

    def append(self, s: Session, ex_id: str, type_: str, actor: str, payload: dict, *, seat_id: str | None = None,
               sim_time: str | None = None, visibility: str = "audit") -> int:
        return self.ledger.append(s, ex_id, type_, actor, payload, seat_id=seat_id, sim_time=sim_time,
                                  visibility=visibility)

    def set_state(self, s: Session, ex: Exercise, to: str, reason: str, actor: str = "system") -> None:
        states.assert_transition(ex.state, to)
        src = ex.state
        ex.state = to
        if to == states.RUNNING and ex.started_at is None:
            ex.started_at = utcnow()
        if to in (states.COMPLETED, states.STOPPED):
            ex.ended_at = utcnow()
            ex.substate = None
        if to in (states.PAUSED, states.INTERRUPTED):
            ex.substate = None
        self.append(s, ex.id, "STATE", actor, {"from": src, "to": to, "reason": reason}, visibility="public")

    def facilitator(self, s: Session, ex_id: str, cmd: Command) -> None:
        self.append(s, ex_id, "FACILITATOR", "facilitator",
                    {"command": cmd.kind, "args": cmd.args, "command_id": cmd.id}, visibility="audit")


def normalize_basis(items: list[dict] | None) -> list[dict]:
    out = []
    for b in items or []:
        chk = b.get("check")
        if chk is None:
            chk = "pass" if b.get("pass", True) else "fail"
        out.append({"chunk_id": b.get("chunk_id"), "article": b.get("article"), "quote": b.get("quote"),
                    "check": chk, "reason": b.get("reason")})
    return out


def decision_payload(raw: dict | None, *, seat_code: str, inject_ref: str, rnd: int, author: str) -> dict:
    raw = dict(raw or {})
    outcome = raw.get("outcome")
    status = raw.get("status") or ("recorded" if outcome else "not_recorded")
    return {
        "decision_id": raw.get("decision_id") or new_id(), "seat_code": seat_code, "inject_ref": inject_ref,
        "round": rnd, "action": raw.get("action"), "action_code": raw.get("action_code"), "outcome": outcome,
        "confidence": raw.get("confidence"), "options_considered": list(raw.get("options_considered") or []),
        "gap_flags": list(raw.get("gap_flags") or []), "rationale": raw.get("rationale"),
        "evidence_tag": raw.get("evidence_tag"), "legal_basis": normalize_basis(raw.get("legal_basis")),
        "status": status, "author": raw.get("author") or author}


def persist_decision(ctx: Any, w: Writer, s: Session, ex_id: str, seat: SeatInfo, payload: dict, actor: str,
                     sim_time: str | None) -> int:
    seq = w.append(s, ex_id, "DECISION", actor, payload, seat_id=seat.id, sim_time=sim_time, visibility="public")
    s.add(Decision(id=payload["decision_id"], exercise_id=ex_id, seat_id=seat.id, inject_ref=payload["inject_ref"],
                   round=payload["round"], action=payload["action"], action_code=payload["action_code"],
                   outcome=payload["outcome"], confidence=payload["confidence"],
                   options_considered=payload["options_considered"], gap_flags=payload["gap_flags"],
                   rationale=payload["rationale"], evidence_tag=payload["evidence_tag"], author=payload["author"],
                   status=payload["status"], ledger_seq=seq))
    s.flush()
    knowledge = optional_svc(ctx, "knowledge")
    for b in payload["legal_basis"]:
        dv = None
        if knowledge is not None and hasattr(knowledge, "get_chunk") and b.get("chunk_id"):
            try:
                dv = (knowledge.get_chunk(s, b["chunk_id"]) or {}).get("document_version_id")
            except Exception:  # noqa: BLE001 - métadonnée facultative
                dv = None
        s.add(DecisionCitation(decision_id=payload["decision_id"], chunk_id=str(b.get("chunk_id")),
                               document_version_id=dv, article=b.get("article"), quote=b.get("quote"),
                               check_status=b["check"], check_reason=b.get("reason")))
    return seq


def route_messages(w: Writer, s: Session, ex_id: str, seats: list[SeatInfo], sender: SeatInfo, unit: Unit,
                   rnd: int, messages: list, actor: str, sim_time: str | None) -> int:
    """Valide (défense en profondeur) puis publie les messages ; livre dans la boîte du destinataire (tour r+1)."""
    by_code = {x.code: x for x in seats if x.activatable}
    posted = 0
    for m in messages:
        to, mtype = getattr(m, "to", None), getattr(m, "msg_type", None)
        body = (getattr(m, "body", "") or "").strip()
        reply_to, reply_status = getattr(m, "in_reply_to", None), getattr(m, "reply_status", None)
        err = None
        if to not in by_code or to == sender.code:
            err = "destinataire invalide"
        elif mtype not in MSG_TYPES:
            err = "type de message invalide"
        elif not body or len(body) > 1500:
            err = "corps vide ou trop long"
        elif reply_status is not None and reply_status not in REPLY_STATUSES:
            err = "reply_status invalide"
        if not err and reply_to:
            orig = s.get(BoardMessage, reply_to)
            if orig is None or orig.exercise_id != ex_id or orig.to_seat_id != sender.id or orig.msg_type != "REQUEST":
                if reply_status is not None:
                    err = "reply_status sans REQUEST reçu"
                if orig is None or orig.exercise_id != ex_id:
                    err = "in_reply_to inconnu"
        elif not err and reply_status is not None:
            err = "reply_status sans in_reply_to"
        if err:
            w.append(s, ex_id, "ERROR", "coord", {"component": "coord.routing", "message": f"message rejeté : {err}",
                                                  "next_action": "ignored", "seat": sender.code},
                     seat_id=sender.id, sim_time=sim_time)
            continue
        mid = new_id()
        payload = {"msg_id": mid, "from": sender.code, "to": to, "msg_type": mtype, "body": body,
                   "in_reply_to": reply_to, "reply_status": reply_status, "inject_ref": unit.ref, "round": rnd}
        seq = w.append(s, ex_id, "BOARD", actor, payload, seat_id=sender.id, sim_time=sim_time, visibility="board")
        s.add(BoardMessage(id=mid, exercise_id=ex_id, inject_ref=unit.ref, round=rnd, from_seat_id=sender.id,
                           to_seat_id=by_code[to].id, from_code=sender.code, to_code=to, msg_type=mtype, body=body,
                           in_reply_to=reply_to, reply_status=reply_status, ledger_seq=seq))
        s.add(InboxItem(exercise_id=ex_id, seat_id=by_code[to].id, source="board", ref_id=mid, inject_ref=unit.ref,
                        available_round=rnd + 1, delivered_seq=seq,
                        content={"kind": "board", "msg_id": mid, "from": sender.code, "msg_type": mtype, "body": body,
                                 "in_reply_to": reply_to, "round": rnd}))
        posted += 1
    return posted


def revoke_seat_tokens(ctx: Any, s: Session, ex: Exercise, seat_id: str) -> None:
    from ..core.auth import Principal
    from ..workspaces import service as ws_service
    from ..workspaces.models import AccessToken
    owner = Principal(workspace_id=ex.workspace_id, role="owner", token_id="-")
    for t in s.scalars(select(AccessToken).where(AccessToken.workspace_id == ex.workspace_id,
                                                 AccessToken.exercise_id == ex.id, AccessToken.seat_id == seat_id,
                                                 AccessToken.role == "player", AccessToken.revoked_at.is_(None))):
        ws_service.revoke_token(s, owner, t.id)


# =========================================================================== commandes
def apply_command(ctx: Any, w: Writer, s: Session, ex: Exercise, cmd: Command, runner: ExerciseRunner | None) -> None:
    """Applique une commande (dans la transaction fournie). Re-valide l'état : invalide => `rejected`."""
    def reject(reason: str) -> None:
        cmd.status, cmd.result, cmd.applied_at = "rejected", {"error": reason}, utcnow()

    kind, a = cmd.kind, dict(cmd.args or {})
    if not states.command_allowed(ex.state, kind, ex.pace):
        return reject(f"commande '{kind}' invalide dans l'état '{ex.state}'")
    now = utcnow()
    if kind == "pause":
        w.set_state(s, ex, states.PAUSED, "facilitator", "facilitator")
        w.facilitator(s, ex.id, cmd)
    elif kind == "resume":
        ex.budget_extra += int(a.get("extend_budget") or 0)
        w.set_state(s, ex, states.RUNNING, "facilitator", "facilitator")
        w.facilitator(s, ex.id, cmd)
    elif kind == "step":
        cmd.status = "queued"
        w.facilitator(s, ex.id, cmd)
        return
    elif kind == "speed":
        ex.pace = a.get("pace", ex.pace)
        if "delay_s" in a:
            ex.settings = {**ex.settings, "delay_s": float(a["delay_s"])}
        w.facilitator(s, ex.id, cmd)
    elif kind == "stop":
        w.facilitator(s, ex.id, cmd)
        if runner is not None:
            runner.stop_requested = True
    elif kind == "surprise":
        seats = {x.code for x in seat_rows(s, ex.id)}
        rec = list(a.get("recipients") or [])
        if not rec or any(c not in seats for c in rec):
            return reject("destinataires invalides")
        k = 1 + (s.scalar(select(func.count()).select_from(Command).where(
            Command.exercise_id == ex.id, Command.kind == "surprise", Command.status.in_(("queued", "consumed")))) or 0)
        inject = {"inject_ref": f"surprise-{k}", "seq": SURPRISE_SEQ_BASE + k, "sim_time": a.get("sim_time"),
                  "title": a.get("title", ""), "body": a.get("body", ""), "from_actor": "facilitator",
                  "recipients": [], "tags": list(a.get("tags") or []), "demands": [],
                  "fault_mode": a.get("fault_mode", "none"), "system_output": None}
        cmd.args = {**a, "k": k, "inject": inject}
        cmd.status = "queued"
        w.facilitator(s, ex.id, cmd)
        return
    elif kind == "seat_switch":
        seat = s.scalar(select(Seat).where(Seat.exercise_id == ex.id, Seat.code == a.get("seat")))
        ctrl, name = a.get("controller"), (a.get("human_name") or "").strip() or None
        if seat is None or ctrl not in ("agent", "human", "scripted") or (ctrl == "human" and not name):
            return reject("bascule de siège invalide")
        old, old_name = seat.controller, seat.human_name
        seat.controller, seat.human_name = ctrl, (name if ctrl == "human" else None)
        s.add(SeatAssignment(seat_id=seat.id, controller=ctrl, human_name=seat.human_name,
                             reason=a.get("reason") or "seat_switch", by_actor="facilitator"))
        w.append(s, ex.id, "SEAT", "facilitator",
                 {"seat": seat.code, "from": old, "to": ctrl, "human_name": seat.human_name,
                  "reason": a.get("reason") or "seat_switch"}, seat_id=seat.id, visibility="board")
        if old == "human" and (ctrl != "human" or name != old_name):
            for t in s.scalars(select(HumanTask).where(HumanTask.seat_id == seat.id, HumanTask.status == "pending")):
                t.status = "cancelled"
            revoke_seat_tokens(ctx, s, ex, seat.id)
        w.facilitator(s, ex.id, cmd)
    elif kind == "correction":
        w.append(s, ex.id, "CORRECTION", "facilitator",
                 {"corrects_seq": a.get("corrects_seq"), "reason": a.get("reason"),
                  "replacement": a.get("replacement"), "command_id": cmd.id}, visibility="audit")
    cmd.status, cmd.applied_at = "applied", now


# =========================================================================== gestionnaire
RUNNER_KINDS = ("start", "pause", "resume", "step", "stop")


class SimulationManager:
    def __init__(self, ctx: Any) -> None:
        self.ctx = ctx
        self.w = Writer(ctx)
        self._lock = threading.RLock()
        self._runners: dict[str, ExerciseRunner] = {}
        self._wlocks: dict[str, threading.RLock] = {}
        self._guard = threading.Lock()
        self.hooks = Hooks()
        self.shutdown_event = threading.Event()

    # -- écriture -----------------------------------------------------------------
    def write_lock(self, exercise_id: str) -> threading.RLock:
        with self._guard:
            return self._wlocks.setdefault(exercise_id, threading.RLock())

    @contextmanager
    def write_tx(self, exercise_id: str) -> Iterator[Session]:
        with self.write_lock(exercise_id), session_scope(self.ctx.session_factory) as s:
            yield s

    # -- runners ------------------------------------------------------------------
    def is_active(self, exercise_id: str) -> bool:
        with self._lock:
            r = self._runners.get(exercise_id)
            return bool(r and r.alive)

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for r in self._runners.values() if r.alive)

    def capacity_ok(self, exercise_id: str) -> bool:
        return self.is_active(exercise_id) or self.active_count() < max(1, self.ctx.settings.max_concurrent_exercises)

    def assert_capacity(self, exercise_id: str) -> None:
        if not self.capacity_ok(exercise_id):
            raise Conflict("nombre maximal d'exercices actifs atteint", code="exercise.capacity_reached",
                           details={"max": self.ctx.settings.max_concurrent_exercises})

    def ensure_runner(self, exercise_id: str) -> None:
        with self._lock:
            if self.is_active(exercise_id):
                return
            self.assert_capacity(exercise_id)
            r = ExerciseRunner(self, exercise_id)
            self._runners[exercise_id] = r
            r.thread = threading.Thread(target=r.run_thread, name=f"alerte-ex-{exercise_id[:8]}", daemon=True)
            r.thread.start()

    def join(self, exercise_id: str, timeout: float = 30.0) -> bool:
        with self._lock:
            r = self._runners.get(exercise_id)
        if r is None or r.thread is None:
            return True
        r.thread.join(timeout)
        return not r.thread.is_alive()

    def wait_until(self, exercise_id: str, pred: Callable[[Exercise], bool], timeout: float = 30.0) -> Exercise:
        end = time.monotonic() + timeout
        while True:
            with session_scope(self.ctx.session_factory) as s:
                ex = s.get(Exercise, exercise_id)
                s.expunge(ex)
            if pred(ex) or time.monotonic() > end:
                return ex
            time.sleep(0.02)

    def submit_command(self, exercise_id: str, kind: str, args: dict, issued_by: str | None) -> str:
        """Enregistre la commande ; si un runner vit, il la lira entre deux étapes, sinon application directe
        (commandes sans boucle) ou lancement d'un runner."""
        with self._lock:
            if kind in RUNNER_KINDS and not self.is_active(exercise_id):
                self.assert_capacity(exercise_id)
            with session_scope(self.ctx.session_factory) as s:
                cmd = Command(exercise_id=exercise_id, kind=kind, args=args, issued_by=issued_by)
                s.add(cmd)
                s.flush()
                cid = cmd.id
            if self.is_active(exercise_id):
                return cid
            if kind in RUNNER_KINDS:
                self.ensure_runner(exercise_id)
            else:
                with self.write_tx(exercise_id) as s:
                    apply_command(self.ctx, self.w, s, s.get(Exercise, exercise_id), s.get(Command, cid), None)
            return cid

    def recover_interrupted(self) -> list[str]:
        """Au démarrage : `running` -> `interrupted` (arrêt anormal ; la reprise se fait depuis le journal)."""
        with session_scope(self.ctx.session_factory) as s:
            ids = list(s.scalars(select(Exercise.id).where(Exercise.state == states.RUNNING)))
        for ex_id in ids:
            with self.write_tx(ex_id) as s:
                ex = s.get(Exercise, ex_id)
                if ex.state == states.RUNNING:
                    self.w.set_state(s, ex, states.INTERRUPTED, "startup_recovery")
        return ids

    def shutdown(self, timeout: float = 5.0) -> None:
        self.shutdown_event.set()
        with self._lock:
            runners = list(self._runners.values())
        for r in runners:
            if r.thread is not None:
                r.thread.join(timeout)
        self.shutdown_event.clear()

    def runtime(self) -> Any:
        return svc(self.ctx, "agents").runtime()


# =========================================================================== runner
class ExerciseRunner:
    def __init__(self, mgr: SimulationManager, exercise_id: str) -> None:
        self.mgr, self.ctx, self.w, self.ex_id = mgr, mgr.ctx, mgr.w, exercise_id
        self.alive = True
        self.thread: threading.Thread | None = None
        self.stop_requested = False
        self._stepping = False
        self._done: set[str] = set()
        self.snap: dict = {}
        self.seats: list[SeatInfo] = []

    # ------------------------------------------------------------------ cycle de vie du fil
    def run_thread(self) -> None:
        try:
            while True:
                try:
                    self._loop()
                except (_Paused, _Exit):
                    pass
                except _StopRequested:
                    # Un échec de la finalisation (ex. base verrouillée) ne doit pas tuer le fil : sinon le gestionnaire
                    # croit le moteur vivant et l'exercice reste figé « en cours ». On passe par _on_crash (interrompu,
                    # reprise possible).
                    try:
                        self._finalize(states.STOPPED)
                    except (RunnerKilled, RunnerAborted):
                        raise
                    except Exception as exc:  # noqa: BLE001
                        log.exception("finalisation en échec", extra={"exercise_id": self.ex_id})
                        self._on_crash(exc)
                except (RunnerKilled, RunnerAborted):
                    raise
                except Exception as exc:  # noqa: BLE001 - arrêt anormal : ERROR + interrupted (reprise possible)
                    log.exception("runner en échec", extra={"exercise_id": self.ex_id})
                    self._on_crash(exc)
                with self.mgr._lock:
                    if self._has_work():
                        continue
                    self.mgr._runners.pop(self.ex_id, None)
                    self.alive = False
                    return
        except (RunnerKilled, RunnerAborted):
            with self.mgr._lock:
                self.mgr._runners.pop(self.ex_id, None)
                self.alive = False

    def _has_work(self) -> bool:
        with session_scope(self.ctx.session_factory) as s:
            ex = s.get(Exercise, self.ex_id)
            if ex is None:
                return False
            n_pending = s.scalar(select(func.count()).select_from(Command).where(
                Command.exercise_id == self.ex_id, Command.status == "pending")) or 0
            if n_pending:
                return True
            if ex.state == states.PAUSED:
                return bool(s.scalar(select(func.count()).select_from(Command).where(
                    Command.exercise_id == self.ex_id, Command.kind == "step", Command.status == "queued")))
            return False

    def _on_crash(self, exc: Exception) -> None:
        try:
            with self.mgr.write_tx(self.ex_id) as s:
                ex = s.get(Exercise, self.ex_id)
                self.w.append(s, self.ex_id, "ERROR", "system",
                              {"component": "runner", "message": f"{type(exc).__name__}: {exc}"[:300],
                               "next_action": "interrupted"})
                if ex.state == states.RUNNING:
                    self.w.set_state(s, ex, states.INTERRUPTED, "runner_error")
        except Exception:  # noqa: BLE001
            log.exception("impossible d'enregistrer l'arrêt anormal")

    # ------------------------------------------------------------------ accès d'état
    def _state(self) -> str:
        with session_scope(self.ctx.session_factory) as s:
            return s.scalar(select(Exercise.state).where(Exercise.id == self.ex_id))

    def _pace(self) -> str:
        with session_scope(self.ctx.session_factory) as s:
            return s.scalar(select(Exercise.pace).where(Exercise.id == self.ex_id))

    def _set_substate(self, sub: str | None) -> None:
        with session_scope(self.ctx.session_factory) as s:
            s.execute(update(Exercise).where(Exercise.id == self.ex_id).values(substate=sub))

    def _sleep(self, secs: float) -> None:
        if self.mgr.shutdown_event.wait(secs):
            raise RunnerAborted()

    def _consume_credit(self) -> bool:
        with self.mgr.write_tx(self.ex_id) as s:
            c = s.scalar(select(Command).where(Command.exercise_id == self.ex_id, Command.kind == "step",
                                               Command.status == "queued").order_by(Command.id).limit(1))
            if c is None:
                return False
            c.status = "consumed"
            return True

    def apply_pending_commands(self) -> None:
        while True:
            with self.mgr.write_tx(self.ex_id) as s:
                cmd = s.scalar(select(Command).where(Command.exercise_id == self.ex_id, Command.status == "pending")
                               .order_by(Command.id).limit(1))
                if cmd is None:
                    return
                apply_command(self.ctx, self.w, s, s.get(Exercise, self.ex_id), cmd, self)

    def checkpoint(self) -> None:
        if self.mgr.shutdown_event.is_set():
            raise RunnerAborted()
        self.apply_pending_commands()
        if self.stop_requested:
            raise _StopRequested()
        st = self._state()
        if st == states.PAUSED and not self._stepping:
            if self._consume_credit():
                self._stepping = True
            else:
                raise _Paused()
        elif st not in (states.RUNNING, states.PAUSED):
            raise _Exit()

    # ------------------------------------------------------------------ boucle principale
    def _load(self) -> None:
        with session_scope(self.ctx.session_factory) as s:
            self.snap = load_payload(s, self.ex_id)
            by_id = {x["seat_id"]: x for x in self.snap["seats"]}
            self.seats = [SeatInfo(r.id, r.code, r.institution_id, r.agent_id, r.position,
                                   by_id[r.id].get("agent"), activatable(by_id[r.id].get("agent")))
                          for r in seat_rows(s, self.ex_id)]
            self._done = set(s.scalars(select(Step.step_key).where(Step.exercise_id == self.ex_id)))

    def _loop(self) -> None:
        self._stepping = False
        self.stop_requested = False
        self.apply_pending_commands()
        if self.stop_requested:
            raise _StopRequested()
        if self._state() not in (states.RUNNING, states.PAUSED):
            raise _Exit()
        self._load()
        self.checkpoint()
        while True:
            unit = self._next_unit()
            if unit is None:
                self._finalize(states.COMPLETED)
                return
            self._gate(unit)
            if not unit.in_progress:  # une surprise acceptée pendant l'attente passe en premier
                unit = self._next_unit() or unit
            self._run_unit(unit)
            self._stepping = False
            self._pace_delay()
            self.checkpoint()

    def _units(self) -> tuple[list[Unit], list[Unit]]:
        sched = []
        for i in self.snap["scenario"]["injects"]:
            rec = [x.code for x in self.seats if x.institution_id in i.get("recipients", [])]
            sched.append(Unit(str(i["seq"]), i["inject_ref"], i, False, None, rec))
        sur = []
        with session_scope(self.ctx.session_factory) as s:
            for c in s.scalars(select(Command).where(Command.exercise_id == self.ex_id, Command.kind == "surprise",
                                                     Command.status == "queued").order_by(Command.id)):
                inj = c.args["inject"]
                sur.append(Unit(f"s{c.args['k']}", inj["inject_ref"], inj, True, c.id, list(c.args["recipients"])))
        return sched, sur

    def _next_unit(self) -> Unit | None:
        sched, sur = self._units()
        closed = lambda u: f"inject:{u.n}:close" in self._done  # noqa: E731
        for u in sched + sur:
            if f"inject:{u.n}:release" in self._done and not closed(u):
                u.in_progress = True
                return u
        for u in sur + sched:
            if not closed(u):
                return u
        return None

    def _gate(self, unit: Unit) -> None:
        if unit.in_progress or self._stepping or self._pace() != "manual":
            return
        self._set_substate("idle_between_injects")
        while not self._consume_credit():
            self._sleep(POLL_INTERVAL)
            self.checkpoint()
            if self._stepping or self._pace() != "manual":
                break
        self._set_substate("advancing")

    def _pace_delay(self) -> None:
        with session_scope(self.ctx.session_factory) as s:
            ex = s.get(Exercise, self.ex_id)
            delay = float(ex.settings.get("delay_s") or 0) if ex.pace == "auto_delay" else 0.0
        end = time.monotonic() + delay
        while time.monotonic() < end:
            self._sleep(min(POLL_INTERVAL, max(0.0, end - time.monotonic())))
            self.checkpoint()

    # ------------------------------------------------------------------ une inject
    def _begin(self, key: str) -> bool:
        if key in self._done:
            return False
        if self.mgr.hooks.before_step:
            self.mgr.hooks.before_step(key)
        return True

    def _finish(self, s: Session, key: str, kind: str, *, calls: int = 0, status: str = "done",
                started: dt.datetime | None = None) -> None:
        if self.mgr.hooks.before_commit:
            self.mgr.hooks.before_commit(key)
        s.add(Step(exercise_id=self.ex_id, step_key=key, kind=kind, status=status, llm_calls=calls,
                   started_at=started or utcnow(), finished_at=utcnow()))

    def _run_unit(self, u: Unit) -> None:
        self._set_substate("advancing")
        self._release(u)
        for r in range(1, MAX_ROUNDS + 1):
            seats = self._seats_with_items(u.ref, r)
            if not seats:
                break
            for si in seats:
                self._seat_step(u, r, si)
            self._close_round(u, r)
        self._close_inject(u)

    def _release(self, u: Unit) -> None:
        key = f"inject:{u.n}:release"
        if not self._begin(key):
            return
        inj = u.inject
        with self.mgr.write_tx(self.ex_id) as s:
            targets = [x for x in self.seats if x.code in u.recipient_seats]
            payload = {"inject_ref": u.ref, "seq": inj["seq"], "title": inj.get("title"), "body": inj.get("body"),
                       "recipients": [x.code for x in targets], "tags": list(inj.get("tags") or []),
                       "fault_mode": inj.get("fault_mode", "none"), "surprise": u.surprise}
            seq = self.w.append(s, self.ex_id, "INJECT", "coord", payload, sim_time=inj.get("sim_time"),
                                visibility="public")
            for x in targets:
                s.add(InboxItem(exercise_id=self.ex_id, seat_id=x.id, source="inject", ref_id=u.ref, inject_ref=u.ref,
                                available_round=1, delivered_seq=seq,
                                content={"kind": "inject", "inject_ref": u.ref, "title": inj.get("title"),
                                         "body": inj.get("body"), "from_actor": inj.get("from_actor"),
                                         "sim_time": inj.get("sim_time"), "tags": list(inj.get("tags") or []),
                                         "fault_mode": inj.get("fault_mode", "none"),
                                         "system_output": inj.get("system_output"), "surprise": u.surprise}))
            self._finish(s, key, "inject_release")
        self._done.add(key)

    def _seats_with_items(self, ref: str, rnd: int) -> list[SeatInfo]:
        with session_scope(self.ctx.session_factory) as s:
            ids = set(s.scalars(select(InboxItem.seat_id).where(
                InboxItem.exercise_id == self.ex_id, InboxItem.inject_ref == ref, InboxItem.available_round == rnd)))
        return [x for x in self.seats if x.id in ids and x.activatable]  # ordre déterministe : position des sièges

    def _close_round(self, u: Unit, rnd: int) -> None:
        key = f"inject:{u.n}:round:{rnd}:close"
        if not self._begin(key):
            return
        with self.mgr.write_tx(self.ex_id) as s:
            self.ctx.service("ledger").write_anchor(s, self.ex_id, "round_close")  # aucun événement dans ce tx
            self._finish(s, key, "round_close")
        self._done.add(key)

    def _close_inject(self, u: Unit) -> None:
        key = f"inject:{u.n}:close"
        if not self._begin(key):
            return
        with self.mgr.write_tx(self.ex_id) as s:
            ex = s.get(Exercise, self.ex_id)
            scripted = ex.ai_mode == "scripted"
            sim = u.inject.get("sim_time")
            by_id = {x.id: x.code for x in self.seats}
            msgs = [coord.Msg(m.id, m.from_code, m.to_code, m.msg_type, m.body, m.in_reply_to, m.reply_status, m.round)
                    for m in s.scalars(select(BoardMessage).where(
                        BoardMessage.exercise_id == self.ex_id, BoardMessage.inject_ref == u.ref)
                        .order_by(BoardMessage.ledger_seq))]
            decs = [coord.Dec(d.id, by_id[d.seat_id], d.round, d.action_code, d.outcome, d.status, d.author,
                              tuple(d.gap_flags or ()))
                    for d in s.scalars(select(Decision).where(Decision.exercise_id == self.ex_id,
                                                              Decision.inject_ref == u.ref).order_by(Decision.ledger_seq))]
            recipients = [x.code for x in self.seats if x.code in u.recipient_seats and x.activatable]
            seat_inst = {x.code: x.institution_id for x in self.seats}
            seat_ctrl = {r.code: r.controller for r in seat_rows(s, self.ex_id)}
            signals = coord.evaluate(inject=u.inject, seat_institution=seat_inst, recipients=recipients,
                                     messages=msgs, decisions=decs)
            for sig in signals:
                payload = {"origin_kind": "coordinator_signal", "signal": sig.signal, "inject_ref": u.ref,
                           "action_code": sig.action_code, "institutions": sig.institutions, "evidence": sig.evidence,
                           "scripted": scripted or any(seat_ctrl.get(c) == "scripted" for c in sig.seats)}
                self.w.append(s, self.ex_id, "GAP", "coord", payload, sim_time=sim, visibility="audit")
            self._call_hook(s, "on_inject_closed", u.ref)
            if u.cmd_id:
                s.get(Command, u.cmd_id).status = "consumed"
            self._finish(s, key, "inject_close")
        self._done.add(key)

    def _call_hook(self, s: Session, name: str, *args: Any) -> None:
        gap = optional_svc(self.ctx, "gap_engine")
        fn = getattr(gap, name, None) if gap is not None else None
        if fn is None:
            return
        try:
            with s.begin_nested():
                fn(s, self.ex_id, *args)
        except Exception as exc:  # noqa: BLE001 - un échec du moteur de lacunes ne bloque pas l'exercice
            try:  # consigner l'échec, sans que l'échec de cette écriture (même cause, ex. base verrouillée) ne se propage
                with s.begin_nested():
                    self.w.append(s, self.ex_id, "ERROR", "system", {"component": "gap_engine", "message": str(exc)[:300],
                                                                     "next_action": "continue"})
            except Exception:  # noqa: BLE001
                log.exception("impossible de consigner l'échec du moteur de lacunes", extra={"exercise_id": self.ex_id})

    # ------------------------------------------------------------------ fin
    def _finalize(self, final_state: str) -> None:
        if not self._done and not self.snap:
            self._load()
        key = "final"
        if key not in self._done:
            with self.mgr.write_tx(self.ex_id) as s:
                ex = s.get(Exercise, self.ex_id)
                if ex.state == states.PAUSED and final_state == states.COMPLETED:
                    self.w.set_state(s, ex, states.RUNNING, "all_injects_closed")
                self._call_hook(s, "on_exercise_finished")
                self.w.set_state(s, ex, final_state, "all_injects_closed" if final_state == states.COMPLETED
                                 else "stopped_by_facilitator")
                self._finish(s, key, "final")
            self._done.add(key)
        if "final:anchor" not in self._done:
            with self.mgr.write_tx(self.ex_id) as s:
                self.ctx.service("ledger").write_anchor(s, self.ex_id, "final")
                self._finish(s, "final:anchor", "final_anchor")
            self._done.add("final:anchor")

    # ------------------------------------------------------------------ étape d'un siège
    def _seat_step(self, u: Unit, rnd: int, si: SeatInfo) -> None:
        key = f"inject:{u.n}:round:{rnd}:seat:{si.code}"
        if key in self._done:
            return
        self.checkpoint()
        if not self._begin(key):
            return
        with session_scope(self.ctx.session_factory) as s:
            ctrl = s.scalar(select(Seat.controller).where(Seat.id == si.id))
        if ctrl == "human":
            outcome = self._human_flow(u, rnd, si, key)
            if outcome == "submitted":
                return self._commit_human(u, rnd, si, key)
            if outcome == "skip":
                with self.mgr.write_tx(self.ex_id) as s:
                    self._finish(s, key, "seat_activation", status="skipped")
                self._done.add(key)
                return
        self._agent_step(u, rnd, si, key)

    def _budget_cap(self, s: Session) -> tuple[int, int]:
        ex = s.get(Exercise, self.ex_id)
        return int(ex.settings.get("max_llm_calls") or self.ctx.settings.max_llm_calls) + ex.budget_extra, ex.llm_calls_used

    def _pause_budget(self, key: str, used: int, cap: int) -> None:
        with self.mgr.write_tx(self.ex_id) as s:
            ex = s.get(Exercise, self.ex_id)
            self.w.append(s, self.ex_id, "ERROR", "system",
                          {"component": "budget", "message": f"plafond d'appels atteint ({used}/{cap})",
                           "next_action": "pause", "step_key": key})
            if ex.state == states.RUNNING:
                self.w.set_state(s, ex, states.PAUSED, "budget_exhausted")
        raise _Paused()

    def _agent_step(self, u: Unit, rnd: int, si: SeatInfo, key: str) -> None:
        started = utcnow()
        with session_scope(self.ctx.session_factory) as s:
            cap, used = self._budget_cap(s)
            sctx = build_seat_context(s, self.ex_id, self.snap, self.seats, si, u, rnd, key, cap - used)
        if used >= cap:
            self._pause_budget(key, used, cap)
        result: ActivationResult = self.mgr.runtime().activate(sctx)
        sim = u.inject.get("sim_time")
        actor = f"seat:{si.code}"
        paused = False
        with self.mgr.write_tx(self.ex_id) as s:
            ex = s.get(Exercise, self.ex_id)
            ex.llm_calls_used += int(result.llm_calls or 0)
            skip_types = {"DECISION", "BOARD"}
            has_error = False
            for te in result.events:
                if te.type in skip_types:
                    continue
                has_error |= te.type == "ERROR"
                ev_actor = "legal" if te.payload.get("actor") == "legal" else actor
                self.w.append(s, self.ex_id, te.type, ev_actor, te.payload, seat_id=si.id, sim_time=sim,
                              visibility=te.visibility)
            if result.status == "budget_exhausted":
                self.w.append(s, self.ex_id, "ERROR", "system",
                              {"component": "budget", "message": "plafond d'appels atteint pendant l'activation",
                               "next_action": "pause", "step_key": key}, seat_id=si.id, sim_time=sim)
                if ex.state == states.RUNNING:
                    self.w.set_state(s, ex, states.PAUSED, "budget_exhausted")
                paused = True
            else:
                raw = result.decision or next((e.payload for e in result.events if e.type == "DECISION"), None)
                if raw is None and result.status == "not_recorded":
                    raw = {"status": "not_recorded"}
                if result.status in ("not_recorded", "fallback") and not has_error:
                    self.w.append(s, self.ex_id, "ERROR", "system",
                                  {"component": "agents.runtime", "message": f"activation {result.status}",
                                   "next_action": "fallback decide" if result.status == "fallback" else "not_recorded"},
                                  seat_id=si.id, sim_time=sim)
                route_messages(self.w, s, self.ex_id, self.seats, si, u, rnd, list(result.messages), actor, sim)
                if raw is not None:
                    payload = decision_payload(raw, seat_code=si.code, inject_ref=u.ref, rnd=rnd, author=result.author)
                    persist_decision(self.ctx, self.w, s, self.ex_id, si, payload, actor, sim)
                s.execute(update(InboxItem).where(InboxItem.seat_id == si.id, InboxItem.inject_ref == u.ref,
                                                  InboxItem.available_round == rnd).values(read=True))
                self._finish(s, key, "seat_activation", calls=int(result.llm_calls or 0), started=started)
        if paused:
            raise _Paused()
        self._done.add(key)

    # ------------------------------------------------------------------ siège humain (côté runner)
    def _human_flow(self, u: Unit, rnd: int, si: SeatInfo, key: str) -> str:
        """Ouvre (ou retrouve) la tâche et attend : submitted | takeover | skip."""
        with self.mgr.write_tx(self.ex_id) as s:
            task = s.scalar(select(HumanTask).where(HumanTask.exercise_id == self.ex_id, HumanTask.step_key == key))
            if task is None:
                ex = s.get(Exercise, self.ex_id)
                seat = s.get(Seat, si.id)
                task = HumanTask(exercise_id=self.ex_id, seat_id=si.id, step_key=key, inject_ref=u.ref, round=rnd,
                                 deadline_at=utcnow() + dt.timedelta(seconds=int(ex.settings.get("human_deadline_s", 900))),
                                 fallback=ex.settings.get("human_fallback", "agent_takeover"),
                                 human_name=seat.human_name, usage={})
                s.add(task)
                s.flush()
                self.w.append(s, self.ex_id, "HUMAN", "coord",
                              {"task_id": task.id, "kind": "task_opened", "by": "coord", "inject_ref": u.ref,
                               "round": rnd, "fallback": task.fallback, "seat": si.code},
                              seat_id=si.id, sim_time=u.inject.get("sim_time"), visibility="seat")
            tid = task.id
        self._set_substate("waiting_human")
        try:
            while True:
                with session_scope(self.ctx.session_factory) as s:
                    task = s.get(HumanTask, tid)
                    ctrl = s.scalar(select(Seat.controller).where(Seat.id == si.id))
                    status, deadline, fallback = task.status, _iso(task.deadline_at), task.fallback
                if status == "submitted":
                    return "submitted"
                if status == "cancelled" or ctrl != "human":
                    return "takeover"
                if status == "expired":
                    return "skip" if fallback == "skip" else "takeover"
                if utcnow() >= deadline:
                    return self._expire(tid, si, u)
                self._sleep(POLL_INTERVAL)
                self.checkpoint()
        finally:
            self._set_substate("advancing")

    def _expire(self, task_id: str, si: SeatInfo, u: Unit) -> str:
        with self.mgr.write_tx(self.ex_id) as s:
            task = s.get(HumanTask, task_id)
            if task.status != "pending":
                return "skip" if task.fallback == "skip" else "takeover"
            task.status = "expired"
            sim = u.inject.get("sim_time")
            self.w.append(s, self.ex_id, "HUMAN", "coord",
                          {"task_id": task.id, "kind": "expired", "by": "coord", "fallback": task.fallback,
                           "seat": si.code}, seat_id=si.id, sim_time=sim, visibility="seat")
            if task.fallback != "skip":
                s.add(SeatAssignment(seat_id=si.id, controller="agent", human_name=task.human_name,
                                     reason="deadline_expired (activation seulement)", by_actor="coord"))
                self.w.append(s, self.ex_id, "SEAT", "coord",
                              {"seat": si.code, "from": "human", "to": "agent", "human_name": task.human_name,
                               "reason": "deadline_expired"}, seat_id=si.id, sim_time=sim, visibility="board")
            return "skip" if task.fallback == "skip" else "takeover"

    def _commit_human(self, u: Unit, rnd: int, si: SeatInfo, key: str) -> None:
        sim = u.inject.get("sim_time")
        with self.mgr.write_tx(self.ex_id) as s:
            task = s.scalar(select(HumanTask).where(HumanTask.exercise_id == self.ex_id, HumanTask.step_key == key))
            actor = f"human:{task.human_name}"
            sub = task.submission or {}
            self.w.append(s, self.ex_id, "HUMAN", actor, {"task_id": task.id, "kind": "submitted", "by": actor},
                          seat_id=si.id, sim_time=sim, visibility="seat")
            posts = [_Post(**p) for p in sub.get("posts", [])]
            route_messages(self.w, s, self.ex_id, self.seats, si, u, rnd, posts, actor, sim)
            if sub.get("decision"):
                payload = decision_payload(sub["decision"], seat_code=si.code, inject_ref=u.ref, rnd=rnd, author="human")
                payload["author"] = "human"
                if sub.get("checks"):
                    self.w.append(s, self.ex_id, "CITATION_CHECK", actor,
                                  {"decision_id": payload["decision_id"], "citations": sub["checks"]},
                                  seat_id=si.id, sim_time=sim, visibility="audit")
                persist_decision(self.ctx, self.w, s, self.ex_id, si, payload, actor, sim)
            s.execute(update(InboxItem).where(InboxItem.seat_id == si.id, InboxItem.inject_ref == u.ref,
                                              InboxItem.available_round == rnd).values(read=True))
            self._finish(s, key, "seat_activation")
        self._done.add(key)


@dataclass
class _Post:
    to: str
    msg_type: str
    body: str
    in_reply_to: str | None = None
    reply_status: str | None = None


# =========================================================================== contexte d'un siège
def inbox_dict(i: InboxItem) -> dict:
    return {"item_id": i.id, "source": i.source, "ref_id": i.ref_id, "inject_ref": i.inject_ref,
            "round": i.available_round, **(i.content or {})}


def board_dicts(s: Session, ex_id: str, limit: int | None = 40) -> list[dict]:
    rows = list(s.scalars(select(BoardMessage).where(BoardMessage.exercise_id == ex_id)
                          .order_by(BoardMessage.ledger_seq.desc()).limit(limit or 10000)))[::-1]
    return [{"msg_id": m.id, "from": m.from_code, "to": m.to_code, "msg_type": m.msg_type, "body": m.body,
             "in_reply_to": m.in_reply_to, "reply_status": m.reply_status, "inject_ref": m.inject_ref,
             "round": m.round} for m in rows]


def decision_dicts(s: Session, ex_id: str, seat_id: str) -> list[dict]:
    return [{"decision_id": d.id, "inject_ref": d.inject_ref, "round": d.round, "action": d.action,
             "action_code": d.action_code, "outcome": d.outcome, "confidence": d.confidence, "status": d.status,
             "rationale": d.rationale}
            for d in s.scalars(select(Decision).where(Decision.exercise_id == ex_id, Decision.seat_id == seat_id)
                               .order_by(Decision.ledger_seq))]


def _with_language(inject: dict, snap: dict) -> dict:
    """Copie de l'inject avec la langue du scénario (consigne de langue pour les agents)."""
    out = dict(inject)
    lang = (snap.get("scenario") or {}).get("language")
    if lang and not out.get("language"):
        out["language"] = lang
    return out


def build_seat_context(s: Session, ex_id: str, snap: dict, seats: list[SeatInfo], si: SeatInfo, u: Unit, rnd: int,
                       key: str, budget_left: int | None = None, purpose: str = "agent") -> SeatContext:
    inst = next((i for i in snap["institutions"] if i["id"] == si.institution_id), {"id": si.institution_id})
    agent = dict(si.agent or {})
    if budget_left is not None:
        agent["budget_remaining"] = max(0, budget_left)
    items = list(s.scalars(select(InboxItem).where(
        InboxItem.exercise_id == ex_id, InboxItem.seat_id == si.id, InboxItem.inject_ref == u.ref,
        InboxItem.available_round == rnd).order_by(InboxItem.delivered_seq, InboxItem.id)))
    return SeatContext(
        exercise_id=ex_id, workspace_id=snap["workspace_id"], seat_id=si.id, seat_code=si.code,
        institution={k: inst.get(k) for k in ("id", "code", "name", "kind")}, agent=agent,
        scope=scope_for_seat(snap, si.code, purpose), inject=_with_language(u.inject, snap), round=rnd,
        inbox=[inbox_dict(i) for i in items], board=board_dicts(s, ex_id),
        own_decisions=decision_dicts(s, ex_id, si.id),
        mandates=[m for m in snap["mandates"] if m.get("institution_id") == si.institution_id],
        seat_codes=[x.code for x in seats if x.activatable and x.code != si.code], step_key=key)
