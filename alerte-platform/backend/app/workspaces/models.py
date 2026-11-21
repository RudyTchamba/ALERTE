"""Tables du module workspaces : espaces, jetons d'accès, pays, institutions (génériques : aucun pays codé en dur)."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base, TimestampMixin, utcnow
from ..core.ids import new_id


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspace"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    archived_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccessToken(Base):
    """Jeton porteur : seul le hash SHA-256 est stocké. Rôles : owner|facilitator|player|observer|auditor."""

    __tablename__ = "access_token"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    exercise_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    seat_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Country(Base, TimestampMixin):
    __tablename__ = "country"
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_country_workspace_name"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    iso2: Mapped[str | None] = mapped_column(String(2), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    languages: Mapped[list | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Institution(Base, TimestampMixin):
    __tablename__ = "institution"
    __table_args__ = (
        UniqueConstraint("workspace_id", "code", name="uq_institution_workspace_code"),
        Index("ix_institution_workspace_country", "workspace_id", "country_id"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    country_id: Mapped[str | None] = mapped_column(ForeignKey("country.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(300))
    name_local: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # ministry|agency|regulator|operator|local_authority|ai_system|advisory|other
    kind: Mapped[str] = mapped_column(String(24), default="other")
    domains: Mapped[list | None] = mapped_column(JSON, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
