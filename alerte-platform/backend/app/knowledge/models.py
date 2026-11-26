"""Tables du module knowledge (doc 06 §6.2). SQLite = source de vérité ; FTS5/Chroma sont reconstructibles.

Immutabilité (ADR 004) : `document_version` (contenu), `chunk` (texte) et `kb_version*` sont en ajout seul ;
des écouteurs ORM refusent toute modification des colonnes de contenu.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base, TimestampMixin, utcnow
from ..core.ids import new_id

KB_KINDS = ("national", "global_practices", "scenario", "prior_reports", "mixed")
RELIABILITY = ("official", "summary", "unofficial", "unknown", "not_found")
VALIDITY = ("in_force", "replaced", "unknown")
REDISTRIBUTION = ("allowed", "restricted", "unknown")
EVIDENCE = ("documented", "inferred", "assumed")
VERSION_STATUS = ("processing", "ready", "needs_review", "failed", "retired")  # état historique (conservé : compatibilité API/archives)
# États de traitement détaillés (un par version de document). `status` en est DÉRIVÉ (LEGACY_STATUS) : jamais deux vérités.
IN_FLIGHT_STATES = ("uploaded", "validating", "queued", "extracting", "ocr_processing", "structuring", "chunking", "embedding", "indexing")
PROCESSING_STATES = IN_FLIGHT_STATES + ("ready", "needs_review", "failed", "retired")
LEGACY_STATUS = {**{st: "processing" for st in IN_FLIGHT_STATES}, "ready": "ready", "needs_review": "needs_review", "failed": "failed", "retired": "retired"}
SCOPE_KINDS = ("country", "global", "organization")  # périmètre d'une base : pays / base globale / organisation (ITU n'est pas un pays)


class KnowledgeBase(Base, TimestampMixin):
    __tablename__ = "knowledge_base"
    __table_args__ = (UniqueConstraint("workspace_id", "code", name="uq_knowledge_base_workspace_code"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    country_id: Mapped[str | None] = mapped_column(ForeignKey("country.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    kind: Mapped[str] = mapped_column(String(24), default="national")
    scope_kind: Mapped[str] = mapped_column(String(16), default="country")  # country | global | organization (voir SCOPE_KINDS)
    languages: Mapped[list | None] = mapped_column(JSON, nullable=True)
    embedder_key: Mapped[str | None] = mapped_column(String(32), nullable=True)
    embedder_fingerprint: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    chunking_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    archived_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Document(Base, TimestampMixin):
    __tablename__ = "document"
    __table_args__ = (UniqueConstraint("kb_id", "code", name="uq_document_kb_code"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    kb_id: Mapped[str] = mapped_column(ForeignKey("knowledge_base.id"), index=True)
    code: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(500))
    doc_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    doc_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    doc_date: Mapped[dt.date | None] = mapped_column(nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    reliability: Mapped[str] = mapped_column(String(16), default="unofficial")
    validity: Mapped[str] = mapped_column(String(16), default="unknown")
    replaced_by_id: Mapped[str | None] = mapped_column(ForeignKey("document.id"), nullable=True)
    license_spdx: Mapped[str | None] = mapped_column(String(100), nullable=True)
    redistribution: Mapped[str] = mapped_column(String(16), default="unknown")
    evidence_default: Mapped[str] = mapped_column(String(16), default="documented")
    accessed_at: Mapped[dt.date | None] = mapped_column(nullable=True)
    current_version_id: Mapped[str | None] = mapped_column(String(26), nullable=True)  # pas de FK (cycle)


class DocumentVersion(Base):
    __tablename__ = "document_version"
    __table_args__ = (UniqueConstraint("document_id", "version_no", name="uq_document_version_no"),
                      Index("ix_document_version_blob", "kb_id", "blob_sha256"))

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    kb_id: Mapped[str] = mapped_column(String(26), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("document.id"), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    blob_sha256: Mapped[str] = mapped_column(String(64))
    mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bytes: Mapped[int] = mapped_column(Integer, default=0)
    original_name: Mapped[str | None] = mapped_column(String(300), nullable=True)  # affichage seul, jamais un chemin
    text_blob_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)  # pages normalisées (aperçu)
    extraction_method: Mapped[str | None] = mapped_column(String(40), nullable=True)
    extraction_quality: Mapped[float | None] = mapped_column(Float, nullable=True)
    pages_to_review: Mapped[list | None] = mapped_column(JSON, nullable=True)
    quality_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="processing")
    # --- stockage physique de référence : <data>/blobs/knowledge_sources/<périmètre>/<nom physique> (chemin RELATIF, jamais absolu)
    storage_path: Mapped[str | None] = mapped_column(String(600), nullable=True)
    migration_filename: Mapped[str | None] = mapped_column(String(300), nullable=True)  # nom du fichier au moment de la migration
    download_name: Mapped[str | None] = mapped_column(String(300), nullable=True)       # nom de téléchargement d'origine, si réellement connu
    provenance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    processing_state: Mapped[str] = mapped_column(String(20), default="uploaded")
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("document_version.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DocumentEvent(Base):
    """Historique de traitement d'une version de document (une ligne par changement d'état ou événement notable)."""

    __tablename__ = "document_event"
    __table_args__ = (Index("ix_document_event_version", "document_version_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    kb_id: Mapped[str] = mapped_column(String(26), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("document.id"), index=True)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_version.id"))
    state: Mapped[str] = mapped_column(String(20))
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    job_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Chunk(Base):
    __tablename__ = "chunk"
    __table_args__ = (Index("ix_chunk_scope", "workspace_id", "kb_id", "document_version_id"),
                      UniqueConstraint("document_version_id", "ordinal", name="uq_chunk_version_ordinal"))

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"))
    kb_id: Mapped[str] = mapped_column(ForeignKey("knowledge_base.id"), index=True)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_version.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    article: Mapped[str | None] = mapped_column(String(100), nullable=True)
    section: Mapped[str | None] = mapped_column(String(300), nullable=True)
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    search_text: Mapped[str] = mapped_column(Text, default="")  # dérivé (analyseur) : modifiable par reindex
    text_sha256: Mapped[str] = mapped_column(String(64))
    char_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doc_title: Mapped[str] = mapped_column(String(500), default="")
    evidence_tag: Mapped[str] = mapped_column(String(16), default="documented")
    topics: Mapped[list | None] = mapped_column(JSON, nullable=True)


class ChunkEmbedding(Base):
    """Vecteurs float32 little-endian (source de vérité ; Chroma en est une copie reconstructible)."""

    __tablename__ = "chunk_embedding"

    chunk_id: Mapped[str] = mapped_column(ForeignKey("chunk.id"), primary_key=True)
    embedder_key: Mapped[str] = mapped_column(String(32), primary_key=True)
    dim: Mapped[int] = mapped_column(Integer)
    vector: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=utcnow)  # date de génération


class KBVersion(Base):
    __tablename__ = "kb_version"
    __table_args__ = (UniqueConstraint("kb_id", "version_no", name="uq_kb_version_no"),)

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    kb_id: Mapped[str] = mapped_column(ForeignKey("knowledge_base.id"), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    manifest_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KBVersionItem(Base):
    __tablename__ = "kb_version_item"

    kb_version_id: Mapped[str] = mapped_column(ForeignKey("kb_version.id"), primary_key=True)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_version.id"), primary_key=True)


class KBExport(Base):
    __tablename__ = "kb_export"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    kb_id: Mapped[str] = mapped_column(ForeignKey("knowledge_base.id"), index=True)
    kb_version_id: Mapped[str | None] = mapped_column(ForeignKey("kb_version.id"), nullable=True)
    mode: Mapped[str] = mapped_column(String(24))
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    job_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    blob_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    filename: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KBImport(Base):
    """Import en deux temps : dry-run (rapport) puis confirmation transactionnelle."""

    __tablename__ = "kb_import"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    blob_sha256: Mapped[str] = mapped_column(String(64))
    manifest_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="validating")  # validating|validated|rejected|confirmed|failed
    report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_kb_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    import_map: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    job_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KBExpectedDocument(Base):
    __tablename__ = "kb_expected_document"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True)
    kb_id: Mapped[str] = mapped_column(ForeignKey("knowledge_base.id"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    jurisdiction: Mapped[str | None] = mapped_column(String(100), nullable=True)
    citation: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="missing")  # present|missing|replaced
    matched_document_id: Mapped[str | None] = mapped_column(ForeignKey("document.id"), nullable=True)


# --------------------------------------------------------------------------- immutabilité
_IMMUTABLE = {
    DocumentVersion: {"document_id", "version_no", "blob_sha256", "kb_id", "workspace_id", "supersedes_id"},
    Chunk: {"text", "text_sha256", "document_version_id", "kb_id", "workspace_id", "ordinal", "page_start",
            "page_end", "article", "char_start", "char_end"},
    KBVersion: {"kb_id", "version_no", "manifest_sha256", "workspace_id"},
}


class ImmutableError(RuntimeError):
    """Tentative de modifier un enregistrement en ajout seul."""


def _guard(cls: type, cols: set[str]) -> None:
    @event.listens_for(cls, "before_update")
    def _before_update(_mapper, _conn, target):  # noqa: ANN001
        from sqlalchemy import inspect
        state = inspect(target)
        for col in cols:
            if state.attrs[col].history.has_changes():
                raise ImmutableError(f"{cls.__tablename__}.{col} est immuable (ajout seul)")


for _cls, _cols in _IMMUTABLE.items():
    _guard(_cls, _cols)


@event.listens_for(KBVersionItem, "before_update")
def _kbv_item_update(_m, _c, _t):  # noqa: ANN001
    raise ImmutableError("kb_version_item est immuable")


@event.listens_for(KBVersionItem, "before_delete")
def _kbv_item_delete(_m, _c, _t):  # noqa: ANN001
    raise ImmutableError("kb_version_item est immuable")


@event.listens_for(KBVersion, "before_delete")
def _kbv_delete(_m, _c, _t):  # noqa: ANN001
    raise ImmutableError("kb_version est immuable")
