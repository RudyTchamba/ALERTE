"""Table `eval_fixture` : lacunes ATTENDUES d'un scénario (T3). PRIVÉE : seul `app.evaluation` importe ce paquet.

Ni `gaps`, ni `agents`, ni `simulation`, ni `reports` ne lisent cette table (test d'architecture). Chaque fixture est
SCELLÉE (SHA-256 + date) à sa création ; elle n'a ni mise à jour ni suppression applicatives.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base, utcnow
from ...core.ids import new_id


class EvalFixture(Base):
    __tablename__ = "eval_fixture"
    __table_args__ = (UniqueConstraint("workspace_id", "scenario_code", "expected_gap_key",
                                       name="uq_eval_fixture_scenario_key"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(String(26), index=True)
    scenario_code: Mapped[str] = mapped_column(String(64), index=True)
    expected_gap_key: Mapped[str] = mapped_column(String(64))  # = gap.fingerprint
    label: Mapped[str] = mapped_column(String(400))
    description: Mapped[str] = mapped_column(Text, default="")
    sealed_sha256: Mapped[str] = mapped_column(String(64))
    sealed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
