"""Tables du module evaluation (doc 06 §6.4) : jeu de questions T1, exécutions de métriques, benchmark externe, grille
de scorecard et évaluations. `kb_id`/`exercise_id` ne sont pas des clés étrangères (lecture des autres modules par services)."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base, utcnow
from ..core.ids import new_id
from .fixtures.models import EvalFixture  # noqa: F401  (enregistre la table privée)


class EvalQuestion(Base):
    __tablename__ = "eval_question"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(String(26), index=True)
    kb_id: Mapped[str] = mapped_column(String(26), index=True)
    question: Mapped[str] = mapped_column(Text)
    expected_doc_code: Mapped[str] = mapped_column(String(64))
    expected_article: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lang: Mapped[str | None] = mapped_column(String(8), nullable=True)
    category: Mapped[str | None] = mapped_column(String(24), nullable=True)  # national|uae|global (répartition 20/10/10)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EvalRun(Base):
    """Une mesure (append-only). `status=not_computed` + `reason` : JAMAIS 0 pour une valeur non calculable (I6)."""

    __tablename__ = "eval_run"
    __table_args__ = (Index("ix_eval_run_exercise_metric", "exercise_id", "metric"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(String(26), index=True)
    exercise_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    kb_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    metric: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(12))  # computed|not_computed
    result: Mapped[dict] = mapped_column(JSON)
    run_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BenchmarkSet(Base):
    __tablename__ = "benchmark_set"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(String(26), index=True)
    name: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(400), default="")  # ex. IFRC, EW4All, catégories AI Readiness
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BenchmarkItem(Base):
    __tablename__ = "benchmark_item"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    set_id: Mapped[str] = mapped_column(ForeignKey("benchmark_set.id"), index=True)
    label: Mapped[str] = mapped_column(String(400))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)  # None : non appariable automatiquement


class RubricDimension(Base):
    __tablename__ = "rubric_dimension"

    id: Mapped[str] = mapped_column(String(8), primary_key=True)  # d01..d13
    number: Mapped[int] = mapped_column(Integer, unique=True)
    name: Mapped[str] = mapped_column(String(200))
    short_name: Mapped[str] = mapped_column(String(64))
    factor: Mapped[str | None] = mapped_column(String(200), nullable=True)
    question: Mapped[str] = mapped_column(Text)


class RubricCriterion(Base):
    __tablename__ = "rubric_criterion"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # id de métrique ITU (d1_m01…)
    dimension_id: Mapped[str] = mapped_column(ForeignKey("rubric_dimension.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    weight: Mapped[float] = mapped_column(Float, default=1.0)


class Assessment(Base):
    __tablename__ = "assessment"
    __table_args__ = (UniqueConstraint("exercise_id", "criterion_id", name="uq_assessment_exercise_criterion"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(String(26), index=True)
    exercise_id: Mapped[str] = mapped_column(String(26), index=True)
    criterion_id: Mapped[str] = mapped_column(ForeignKey("rubric_criterion.id"))
    answer: Mapped[str] = mapped_column(String(16))  # yes|partial|no|not_assessed
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    assessor: Mapped[str] = mapped_column(String(200), default="manual")
    reviewed_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
