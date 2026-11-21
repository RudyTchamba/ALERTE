"""Tables du module simulation (doc 06 §6.3). Pas de FK vers les tables des autres modules (hors workspace)."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base, TimestampMixin, utcnow
from ..core.ids import new_id


def _id() -> Mapped[str]:
    return mapped_column(String(26), primary_key=True, default=new_id)


class Exercise(Base, TimestampMixin):
    __tablename__ = "exercise"
    __table_args__ = (UniqueConstraint("workspace_id", "code", name="uq_exercise_workspace_code"),)

    id: Mapped[str] = _id()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    scenario_id: Mapped[str] = mapped_column(String(26), index=True)
    parent_exercise_id: Mapped[str | None] = mapped_column(ForeignKey("exercise.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(300))
    state: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    substate: Mapped[str | None] = mapped_column(String(24), nullable=True)
    pace: Mapped[str] = mapped_column(String(16), default="auto")
    ai_mode: Mapped[str] = mapped_column(String(12), default="ai")  # ai|scripted|cassette
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snapshot_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    commitment_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    llm_calls_used: Mapped[int] = mapped_column(Integer, default=0)
    budget_extra: Mapped[int] = mapped_column(Integer, default=0)


class ExerciseSnapshot(Base):
    __tablename__ = "exercise_snapshot"

    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercise.id"), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    payload_sha256: Mapped[str] = mapped_column(String(64))
    snapshot_sha256: Mapped[str] = mapped_column(String(64))
    commitment_sha256: Mapped[str] = mapped_column(String(64))
    document_version_ids: Mapped[list] = mapped_column(JSON, default=list)
    readiness: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExerciseReference(Base):
    """Objets référencés par un exercice lancé (garde de référence : non supprimables)."""

    __tablename__ = "exercise_reference"
    __table_args__ = (Index("ix_exercise_reference_kind_ref", "kind", "ref_id"),)

    id: Mapped[str] = _id()
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercise.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    ref_id: Mapped[str] = mapped_column(String(128))


class Seat(Base):
    __tablename__ = "seat"
    __table_args__ = (UniqueConstraint("exercise_id", "code", name="uq_seat_exercise_code"),)

    id: Mapped[str] = _id()
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercise.id"), index=True)
    code: Mapped[str] = mapped_column(String(32))
    institution_id: Mapped[str] = mapped_column(String(26))
    agent_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    controller: Mapped[str] = mapped_column(String(12), default="agent")  # agent|human|scripted
    human_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)


class SeatAssignment(Base):
    __tablename__ = "seat_assignment"

    id: Mapped[str] = _id()
    seat_id: Mapped[str] = mapped_column(ForeignKey("seat.id"), index=True)
    controller: Mapped[str] = mapped_column(String(12))
    human_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    by_actor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Step(Base):
    __tablename__ = "step"
    __table_args__ = (UniqueConstraint("exercise_id", "step_key", name="uq_step_exercise_key"),)

    id: Mapped[str] = _id()
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercise.id"), index=True)
    step_key: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(12), default="done")  # done|skipped
    llm_calls: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Command(Base):
    __tablename__ = "command"
    __table_args__ = (Index("ix_command_exercise_status", "exercise_id", "status"),)

    id: Mapped[str] = _id()
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercise.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    args: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending|applied|queued|consumed|rejected
    issued_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    applied_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BoardMessage(Base):
    __tablename__ = "board_message"

    id: Mapped[str] = _id()  # = msg_id
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercise.id"), index=True)
    inject_ref: Mapped[str] = mapped_column(String(64))
    round: Mapped[int] = mapped_column(Integer)
    from_seat_id: Mapped[str] = mapped_column(String(26))
    to_seat_id: Mapped[str] = mapped_column(String(26))
    from_code: Mapped[str] = mapped_column(String(32))
    to_code: Mapped[str] = mapped_column(String(32))
    msg_type: Mapped[str] = mapped_column(String(16))
    body: Mapped[str] = mapped_column(Text)
    in_reply_to: Mapped[str | None] = mapped_column(String(26), nullable=True)
    reply_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ledger_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)


class InboxItem(Base):
    __tablename__ = "inbox_item"
    __table_args__ = (Index("ix_inbox_exercise_seat_inject", "exercise_id", "seat_id", "inject_ref"),)

    id: Mapped[str] = _id()
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercise.id"), index=True)
    seat_id: Mapped[str] = mapped_column(ForeignKey("seat.id"))
    source: Mapped[str] = mapped_column(String(12))  # inject|board
    ref_id: Mapped[str] = mapped_column(String(64))
    inject_ref: Mapped[str] = mapped_column(String(64))
    available_round: Mapped[int] = mapped_column(Integer, default=1)
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    delivered_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)


class Decision(Base):
    __tablename__ = "decision"

    id: Mapped[str] = _id()
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercise.id"), index=True)
    seat_id: Mapped[str] = mapped_column(ForeignKey("seat.id"))
    inject_ref: Mapped[str] = mapped_column(String(64))
    round: Mapped[int] = mapped_column(Integer)
    action: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(24), nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(8), nullable=True)
    options_considered: Mapped[list] = mapped_column(JSON, default=list)
    gap_flags: Mapped[list] = mapped_column(JSON, default=list)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_tag: Mapped[str | None] = mapped_column(String(12), nullable=True)
    author: Mapped[str] = mapped_column(String(10), default="agent")  # agent|human|fallback
    status: Mapped[str] = mapped_column(String(14), default="recorded")  # recorded|not_verified|not_recorded
    ledger_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)


class DecisionCitation(Base):
    __tablename__ = "decision_citation"

    id: Mapped[str] = _id()
    decision_id: Mapped[str] = mapped_column(ForeignKey("decision.id"), index=True)
    chunk_id: Mapped[str] = mapped_column(String(64))
    document_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    article: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    check_status: Mapped[str] = mapped_column(String(8), default="pass")
    check_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)


class HumanTask(Base):
    __tablename__ = "human_task"
    __table_args__ = (UniqueConstraint("exercise_id", "step_key", name="uq_human_task_exercise_step"),)

    id: Mapped[str] = _id()
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercise.id"), index=True)
    seat_id: Mapped[str] = mapped_column(ForeignKey("seat.id"), index=True)
    step_key: Mapped[str] = mapped_column(String(120))
    inject_ref: Mapped[str] = mapped_column(String(64))
    round: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending|submitted|expired|cancelled
    deadline_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    fallback: Mapped[str] = mapped_column(String(16), default="agent_takeover")  # agent_takeover|skip
    human_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    submission: Mapped[dict] = mapped_column(JSON, default=dict)  # {posts:[...], decision:{...}, checks:[...]}
    retrieval: Mapped[list] = mapped_column(JSON, default=list)  # chunk_id récupérés par le joueur
    usage: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    submitted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StreamToken(Base):
    __tablename__ = "stream_token"

    id: Mapped[str] = _id()
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    workspace_id: Mapped[str] = mapped_column(String(26))
    exercise_id: Mapped[str] = mapped_column(String(26), index=True)
    role: Mapped[str] = mapped_column(String(16))
    seat_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    token_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
