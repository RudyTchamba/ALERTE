"""Tables du module scenarios : scénarios, injects, destinataires, étiquettes, demandes."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base, TimestampMixin
from ..core.ids import new_id


class Scenario(Base, TimestampMixin):
    __tablename__ = "scenario"
    __table_args__ = (UniqueConstraint("workspace_id", "code", name="uq_scenario_workspace_code"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    country_id: Mapped[str | None] = mapped_column(ForeignKey("country.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(8), default="en")
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft|ready|archived
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    cloned_from_id: Mapped[str | None] = mapped_column(ForeignKey("scenario.id"), nullable=True)
    archived_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Inject(Base, TimestampMixin):
    __tablename__ = "inject"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    sim_time: Mapped[str] = mapped_column(String(40), default="")
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text, default="")
    from_actor: Mapped[str] = mapped_column(String(200), default="")
    fault_mode: Mapped[str] = mapped_column(String(40), default="none")
    system_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class InjectRecipient(Base):
    __tablename__ = "inject_recipient"

    inject_id: Mapped[str] = mapped_column(ForeignKey("inject.id"), primary_key=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institution.id"), primary_key=True)


class InjectTag(Base):
    __tablename__ = "inject_tag"

    inject_id: Mapped[str] = mapped_column(ForeignKey("inject.id"), primary_key=True)
    tag: Mapped[str] = mapped_column(String(48), primary_key=True)


class InjectDemand(Base):
    __tablename__ = "inject_demand"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    inject_id: Mapped[str] = mapped_column(ForeignKey("inject.id"), index=True)
    action_code: Mapped[str] = mapped_column(String(100))
    justification: Mapped[str] = mapped_column(Text, default="")
    derivation: Mapped[str] = mapped_column(String(20), default="scenario_author")
    position: Mapped[int] = mapped_column(Integer, default=0)
