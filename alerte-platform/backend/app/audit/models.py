"""Tables d'audit : ledger chaîné (ajout seul) et ancres de tête. `exercise_id` n'est pas une FK : l'audit ne dépend que de core."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, DateTime, Index, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base, utcnow
from ..core.ids import new_id


class LedgerEvent(Base):
    __tablename__ = "ledger_event"
    __table_args__ = (
        UniqueConstraint("exercise_id", "seq", name="uq_ledger_event_exercise_seq"),
        Index("ix_ledger_event_exercise_type", "exercise_id", "type"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    exercise_id: Mapped[str] = mapped_column(String(26), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(24))
    actor: Mapped[str] = mapped_column(String(64))
    seat_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    sim_time: Mapped[str | None] = mapped_column(String(32), nullable=True)
    real_time: Mapped[str] = mapped_column(String(32))  # ISO 8601 UTC, figé en texte (jamais recalculé)
    visibility: Mapped[str] = mapped_column(String(16))  # public|board|seat|audit
    payload: Mapped[dict] = mapped_column(JSON)
    canonical: Mapped[bytes] = mapped_column(LargeBinary)  # octets canoniques sur lesquels le hash est calculé
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))


class LedgerAnchor(Base):
    """Ancre de tête (seq, hash) écrite à chaque fin de tour : détecte la troncature de fin de journal."""

    __tablename__ = "ledger_anchor"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    exercise_id: Mapped[str] = mapped_column(String(26), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    hash: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(24), default="round_close")
    signature: Mapped[str | None] = mapped_column(String(200), nullable=True)  # Ed25519 (P1)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
