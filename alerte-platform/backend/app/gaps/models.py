"""Tables du module gaps (doc 06 §6.4). `exercise_id` n'est pas une FK : la table `exercise` appartient à simulation."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    DDL,
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base, TimestampMixin, utcnow
from ..core.ids import new_id


class Gap(Base, TimestampMixin):
    __tablename__ = "gap"
    __table_args__ = (UniqueConstraint("exercise_id", "group_key", name="uq_gap_exercise_group"),
                      Index("ix_gap_fingerprint", "fingerprint"), Index("ix_gap_workspace_exercise", "workspace_id", "exercise_id"))

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"))
    exercise_id: Mapped[str] = mapped_column(String(26))
    group_key: Mapped[str] = mapped_column(String(200))  # identité intra-exercice (code|action|…) stable entre détections
    fingerprint: Mapped[str] = mapped_column(String(64))  # sha256(code|action|institutions|domaine) : comparaison inter-exercices
    code: Mapped[str] = mapped_column(String(8))
    rule_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    category: Mapped[str] = mapped_column(String(48))
    title: Mapped[str] = mapped_column(String(400))
    description: Mapped[str] = mapped_column(Text, default="")
    domain: Mapped[str | None] = mapped_column(String(64), nullable=True)
    institution_ids: Mapped[list] = mapped_column(JSON, default=list)
    action_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_basis: Mapped[str] = mapped_column(String(12))  # documented|observed|inferred|hypothesis
    confidence: Mapped[str] = mapped_column(String(8))  # high|medium|low
    severity: Mapped[int] = mapped_column(Integer)
    auto_severity: Mapped[int] = mapped_column(Integer)
    consequence: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(10), default="proposed")  # proposed|confirmed|disputed|rejected
    origin: Mapped[str] = mapped_column(String(20))  # rule|coordinator_signal|agent_hypothesis|imported
    registry_state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cause: Mapped[str] = mapped_column(String(14), default="undetermined")  # institutional|documentary|artifact|undetermined
    corpus_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
    demand_derivation: Mapped[str | None] = mapped_column(String(16), nullable=True)
    inject_refs: Mapped[list] = mapped_column(JSON, default=list)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)  # notes, signaux, étiquettes, drapeaux (scripted…)
    edited_fields: Mapped[list] = mapped_column(JSON, default=list)
    engine_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)


class GapEvidence(Base):
    __tablename__ = "gap_evidence"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    gap_id: Mapped[str] = mapped_column(ForeignKey("gap.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(24))  # mandate|chunk|event|message|decision|negative_search|coordinator_signal
    role: Mapped[str] = mapped_column(String(10))  # supports|counter|context
    ref: Mapped[dict] = mapped_column(JSON, default=dict)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_agent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class NegativeSearch(Base):
    __tablename__ = "negative_search"
    __table_args__ = (UniqueConstraint("exercise_id", "query_key", name="uq_negative_search_key"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(String(26), index=True)
    exercise_id: Mapped[str] = mapped_column(String(26), index=True)
    query_key: Mapped[str] = mapped_column(String(64))
    action_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kb_ids: Mapped[list] = mapped_column(JSON, default=list)
    queries: Mapped[list] = mapped_column(JSON, default=list)
    languages: Mapped[list] = mapped_column(JSON, default=list)
    corpus_documents: Mapped[int] = mapped_column(Integer, default=0)
    corpus_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
    coverage_missing: Mapped[list] = mapped_column(JSON, default=list)
    top_hits: Mapped[list] = mapped_column(JSON, default=list)
    verdict: Mapped[str] = mapped_column(String(12))  # no_hit|weak_hit|strong_hit
    run_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GapReview(Base):
    """AJOUT SEUL : triggers SQLite + garde ORM interdisent UPDATE/DELETE (doc 06 §6.5)."""

    __tablename__ = "gap_review"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    gap_id: Mapped[str] = mapped_column(ForeignKey("gap.id"), index=True)
    reviewer: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(12))  # confirm|dispute|reject|comment|reopen|edit
    from_status: Mapped[str] = mapped_column(String(10))
    to_status: Mapped[str] = mapped_column(String(10))
    reality_label: Mapped[str | None] = mapped_column(String(16), nullable=True)  # real|partially_real|not_real
    blind: Mapped[bool] = mapped_column(Boolean, default=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    changes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


@event.listens_for(GapReview, "before_update")
@event.listens_for(GapReview, "before_delete")
def _gap_review_append_only(*_a) -> None:  # noqa: ANN002
    raise RuntimeError("gap_review est en ajout seul (aucun UPDATE/DELETE)")


for _op in ("UPDATE", "DELETE"):
    event.listen(GapReview.__table__, "after_create", DDL(
        f"CREATE TRIGGER IF NOT EXISTS gap_review_no_{_op.lower()} BEFORE {_op} ON gap_review "
        f"BEGIN SELECT RAISE(ABORT, 'gap_review est en ajout seul'); END").execute_if(dialect="sqlite"))


class InternationalReference(Base, TimestampMixin):
    __tablename__ = "international_reference"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    jurisdiction: Mapped[str] = mapped_column(String(120))
    instrument: Mapped[str] = mapped_column(String(400))
    article: Mapped[str | None] = mapped_column(String(100), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    binding: Mapped[bool] = mapped_column(Boolean, default=False)
    domains: Mapped[list] = mapped_column(JSON, default=list)
    gap_codes: Mapped[list] = mapped_column(JSON, default=list)
    document_version_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    chunk_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    evidence_tag: Mapped[str] = mapped_column(String(12), default="documented")


class GapReference(Base, TimestampMixin):
    __tablename__ = "gap_reference"
    __table_args__ = (UniqueConstraint("gap_id", "reference_id", name="uq_gap_reference_pair"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    gap_id: Mapped[str] = mapped_column(ForeignKey("gap.id", ondelete="CASCADE"), index=True)
    reference_id: Mapped[str] = mapped_column(ForeignKey("international_reference.id"))
    fit_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    fit_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="suggested")  # suggested|accepted|rejected


class ImprovementAction(Base, TimestampMixin):
    __tablename__ = "improvement_action"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(String(26), index=True)
    gap_id: Mapped[str] = mapped_column(ForeignKey("gap.id", ondelete="CASCADE"), index=True)
    owner_institution_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    due_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="planned")  # planned|in_progress|done|dropped
    kpi: Mapped[str | None] = mapped_column(Text, nullable=True)
