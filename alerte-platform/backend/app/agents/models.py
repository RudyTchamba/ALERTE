"""Tables du module agents : profils de modèle, agents, droits agent → KB (la KB est vérifiée via le service knowledge)."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base, TimestampMixin, utcnow
from ..core.ids import new_id


class ModelProfile(Base, TimestampMixin):
    __tablename__ = "model_profile"
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_model_profile_workspace_name"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    provider: Mapped[str] = mapped_column(String(16))  # openai_compat|scripted|cassette
    endpoint_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)  # NOM d'une variable de configuration
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.0)
    max_tokens: Mapped[int] = mapped_column(Integer, default=1024)
    timeout_s: Mapped[float] = mapped_column(Float, default=120.0)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Agent(Base, TimestampMixin):
    __tablename__ = "agent"
    __table_args__ = (UniqueConstraint("workspace_id", "code", name="uq_agent_workspace_code"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    institution_id: Mapped[str | None] = mapped_column(ForeignKey("institution.id"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(300))
    role_kind: Mapped[str] = mapped_column(String(16), default="institution")
    mission: Mapped[str] = mapped_column(Text, default="")
    instructions: Mapped[str] = mapped_column(Text, default="")
    model_profile_id: Mapped[str | None] = mapped_column(ForeignKey("model_profile.id"), nullable=True)
    tools: Mapped[list] = mapped_column(JSON, default=list)
    limits: Mapped[dict] = mapped_column(JSON, default=dict)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    cloned_from_id: Mapped[str | None] = mapped_column(ForeignKey("agent.id"), nullable=True)
    archived_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentKbGrant(Base):
    __tablename__ = "agent_kb_grant"

    agent_id: Mapped[str] = mapped_column(ForeignKey("agent.id"), primary_key=True)
    kb_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    mode: Mapped[str] = mapped_column(String(8), default="read")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
