"""Tables du module mandates : catalogue d'actions, mandats, sources, revue de registre (doc 06 §6.1)."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base, TimestampMixin, utcnow
from ..core.ids import new_id


class ActionItem(Base, TimestampMixin):
    """« Ce que la situation exige ». `derivation` dit d'où vient l'attente (jamais « obligation officielle » par défaut)."""

    __tablename__ = "action_item"
    __table_args__ = (UniqueConstraint("workspace_id", "code", name="uq_action_item_workspace_code"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    code: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(300))
    domain: Mapped[str | None] = mapped_column(String(64), nullable=True)
    derivation: Mapped[str] = mapped_column(String(20))  # referential|scenario_author|agent_proposed
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Mandate(Base, TimestampMixin):
    __tablename__ = "mandate"
    __table_args__ = (Index("ix_mandate_workspace_institution", "workspace_id", "institution_id"),
                      Index("ix_mandate_workspace_action", "workspace_id", "action_code"))

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institution.id"))
    kind: Mapped[str] = mapped_column(String(24))
    action_code: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    procedure_status: Mapped[str] = mapped_column(String(10), default="unknown")  # specific|general|none|unknown
    has_deadline: Mapped[bool] = mapped_column(Boolean, default=False)
    dependency_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    dependency_ready: Mapped[str | None] = mapped_column(String(8), nullable=True)  # yes|no|unknown (import CSV)
    depends_on_id: Mapped[str | None] = mapped_column(ForeignKey("mandate.id"), nullable=True)
    conflicts_with_id: Mapped[str | None] = mapped_column(ForeignKey("mandate.id"), nullable=True)
    evidence_tag: Mapped[str] = mapped_column(String(12), default="inferred")  # documented|inferred|assumed
    validation: Mapped[str] = mapped_column(String(10), default="proposed")  # proposed|validated|rejected
    origin: Mapped[str] = mapped_column(String(14), default="manual")  # manual|csv_import|llm_proposed
    created_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    import_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)  # identifiant de ligne CSV
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class MandateSource(Base):
    """Un mandat n'est ACTIF que si au moins une source résout vers un chunk réel (vérifié via knowledge.get_chunk)."""

    __tablename__ = "mandate_source"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    mandate_id: Mapped[str] = mapped_column(ForeignKey("mandate.id", ondelete="CASCADE"), index=True)
    document_version_id: Mapped[str] = mapped_column(String(26))
    chunk_id: Mapped[str] = mapped_column(String(26))
    article: Mapped[str | None] = mapped_column(String(100), nullable=True)
    page: Mapped[int | None] = mapped_column(nullable=True)
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    quote_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quote_found: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MandateReview(Base):
    """Journal (ajout seul) des décisions humaines sur les mandats."""

    __tablename__ = "mandate_review"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(String(26), index=True)
    mandate_id: Mapped[str] = mapped_column(String(26), index=True)
    actor: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(16))  # create|validate|correct|reject|reopen|update
    from_status: Mapped[str | None] = mapped_column(String(10), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(10), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RegistryReview(Base, TimestampMixin):
    __tablename__ = "registry_review"
    __table_args__ = (UniqueConstraint("workspace_id", "institution_id", name="uq_registry_review_institution"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institution.id"))
    status: Mapped[str] = mapped_column(String(20), default="unreviewed")  # unreviewed|partial|reviewed_complete
    reviewer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
