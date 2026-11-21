"""Schémas Pydantic de l'API knowledge. Les entrées de recherche n'ont AUCUN champ d'identité ou de portée."""
from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

KBKind = Literal["national", "global_practices", "scenario", "prior_reports", "mixed"]
Reliability = Literal["official", "summary", "unofficial", "not_found"]
Validity = Literal["in_force", "replaced", "unknown"]
Redistribution = Literal["allowed", "restricted", "unknown"]
Evidence = Literal["documented", "inferred", "assumed"]


class KBCreate(BaseModel):
    code: str | None = Field(default=None, max_length=64)
    name: str = Field(min_length=1, max_length=300)
    description: str | None = None
    country_id: str | None = None
    domain: str | None = Field(default=None, max_length=100)
    kind: KBKind = "national"
    languages: list[str] = Field(default_factory=list)
    chunking_params: dict[str, Any] | None = None


class KBUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    country_id: str | None = None
    domain: str | None = None
    kind: KBKind | None = None
    languages: list[str] | None = None
    chunking_params: dict[str, Any] | None = None


class DocumentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=500)
    doc_type: str | None = None
    doc_number: str | None = None
    doc_date: dt.date | None = None
    jurisdiction: str | None = None
    language: str | None = None
    source_url: str | None = None
    reliability: Reliability | None = None
    validity: Validity | None = None
    replaced_by_id: str | None = None
    license_spdx: str | None = None
    redistribution: Redistribution | None = None
    evidence_default: Evidence | None = None
    accessed_at: dt.date | None = None


class SearchRequest(BaseModel):
    """Pas de `workspace_id`, `kb_ids`, `scope`… : `extra=forbid` les refuse (422)."""

    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=5, ge=1, le=50)
    article: str | None = Field(default=None, max_length=50)
    languages: list[str] | None = None
    doc_types: list[str] | None = None


class PublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: str | None = Field(default=None, max_length=1000)


class EmbedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reembed: bool = False


class ExportInclude(BaseModel):
    model_config = ConfigDict(extra="forbid")
    originals: bool | None = None
    embeddings: bool = False
    mandates: bool = False
    references: bool = False


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["full_reimportable", "processed_only", "documents_only", "selection", "open_publication"] = \
        "full_reimportable"
    document_ids: list[str] | None = None
    kb_version_id: str | None = None
    include: ExportInclude = Field(default_factory=ExportInclude)
    purpose: Literal["private", "open_publication"] = "private"


class ImportConfirm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["new_kb", "new_version"] = "new_kb"
    target_kb_id: str | None = None
    code: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=300)


class ExpectedCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=500)
    jurisdiction: str | None = None
    citation: str | None = None
    status: Literal["present", "missing", "replaced"] = "missing"
    matched_document_id: str | None = None


class ExpectedUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    jurisdiction: str | None = None
    citation: str | None = None
    status: Literal["present", "missing", "replaced"] | None = None
    matched_document_id: str | None = None
