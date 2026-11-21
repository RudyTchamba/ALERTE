"""Tables du module reports (doc 06 §6.4). Une `report_version` publiée est IMMUABLE : triggers SQLite (défense en
profondeur) + refus applicatif. `exercise_id`, `gap_id` ne sont pas des clés étrangères (lecture par services)."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DDL, JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base, utcnow
from ..core.ids import new_id


class Report(Base):
    __tablename__ = "report"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(String(26), index=True)
    exercise_id: Mapped[str | None] = mapped_column(String(26), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(10))  # generated|imported
    title: Mapped[str] = mapped_column(String(400))
    confidentiality: Mapped[str] = mapped_column(String(16), default="internal")  # public|internal|restricted
    # rapport importé : original conservé (blob adressé par contenu) + provenance
    document_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    document_filename: Mapped[str | None] = mapped_column(String(300), nullable=True)
    document_media_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    document_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provenance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReportVersion(Base):
    __tablename__ = "report_version"
    __table_args__ = (UniqueConstraint("report_id", "version_no", name="uq_report_version_no"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(String(26), index=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("report.id"), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), default="draft")  # draft|published
    content: Mapped[dict] = mapped_column(JSON)  # source unique de tous les rendus
    content_sha256: Mapped[str] = mapped_column(String(64))
    ledger_head_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ledger_head_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    generator_version: Mapped[str] = mapped_column(String(32))
    parent_version_id: Mapped[str | None] = mapped_column(ForeignKey("report_version.id"), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# Immuabilité (SQLite) : toute modification/suppression d'une version DÉJÀ publiée est refusée ; la transition
# draft -> published (OLD.status = 'draft') reste permise.
event.listen(ReportVersion.__table__, "after_create", DDL(
    "CREATE TRIGGER IF NOT EXISTS trg_report_version_no_update BEFORE UPDATE ON report_version "
    "WHEN OLD.status = 'published' BEGIN SELECT RAISE(ABORT, 'report_version publiée : immuable'); END;"
).execute_if(dialect="sqlite"))
event.listen(ReportVersion.__table__, "after_create", DDL(
    "CREATE TRIGGER IF NOT EXISTS trg_report_version_no_delete BEFORE DELETE ON report_version "
    "WHEN OLD.status = 'published' BEGIN SELECT RAISE(ABORT, 'report_version publiée : immuable'); END;"
).execute_if(dialect="sqlite"))


class ReportArtifact(Base):
    __tablename__ = "report_artifact"
    __table_args__ = (UniqueConstraint("report_version_id", "format", name="uq_report_artifact_format"),
                      Index("ix_report_artifact_version", "report_version_id"))

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(String(26), index=True)
    report_version_id: Mapped[str] = mapped_column(ForeignKey("report_version.id"))
    format: Mapped[str] = mapped_column(String(8))  # md|json|csv|pdf|xlsx|html
    content_sha256: Mapped[str] = mapped_column(String(64))  # empreinte du JSON dont l'artefact est dérivé
    blob_sha256: Mapped[str] = mapped_column(String(64))
    bytes: Mapped[int] = mapped_column(Integer)
    renderer: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ImportedFinding(Base):
    """Constat d'une analyse ANTÉRIEURE (rapport importé). Origine toujours « analyse antérieure »."""

    __tablename__ = "imported_finding"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(String(26), index=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("report.id"), index=True)
    title: Mapped[str] = mapped_column(String(400))
    body: Mapped[str] = mapped_column(Text, default="")
    code_hint: Mapped[str | None] = mapped_column(String(16), nullable=True)
    severity_hint: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="extracted")  # extracted|validated|rejected
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GapPriorLink(Base):
    __tablename__ = "gap_prior_link"
    __table_args__ = (UniqueConstraint("gap_id", "imported_finding_id", name="uq_gap_prior_link"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(String(26), index=True)
    gap_id: Mapped[str] = mapped_column(String(26), index=True)
    gap_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    exercise_id: Mapped[str] = mapped_column(String(26))
    imported_finding_id: Mapped[str] = mapped_column(ForeignKey("imported_finding.id"))
    relation: Mapped[str] = mapped_column(String(24))  # previously_identified|newly_emerged|contradicts
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
