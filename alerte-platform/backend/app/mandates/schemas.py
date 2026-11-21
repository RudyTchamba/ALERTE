from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Derivation = Literal["referential", "scenario_author", "agent_proposed"]
MandateKind = Literal["power", "duty", "lead", "coordination", "information_sharing", "procedure", "human_oversight",
                      "liability", "inclusion", "channel_protection", "international_agreement", "prohibition"]
ProcedureStatus = Literal["specific", "general", "none", "unknown"]
EvidenceTag = Literal["documented", "inferred", "assumed"]
RegistryStatus = Literal["unreviewed", "partial", "reviewed_complete"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ActionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.\-]+$")
    label: str = Field(min_length=1, max_length=300)
    domain: str | None = Field(default=None, max_length=64)
    derivation: Derivation
    justification: str | None = None
    reference_note: str | None = None


class ActionUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=300)
    domain: str | None = None
    derivation: Derivation | None = None
    justification: str | None = None
    reference_note: str | None = None


class ActionOut(ORM):
    id: str
    code: str
    label: str
    domain: str | None
    derivation: str
    justification: str | None
    reference_note: str | None
    presentation: str = ""


class SourceIn(BaseModel):
    document_version_id: str
    chunk_id: str
    article: str | None = None
    page: int | None = None
    quote: str | None = None


class SourceOut(ORM):
    id: str
    document_version_id: str
    chunk_id: str
    article: str | None
    page: int | None
    quote: str | None
    quote_found: bool | None


class MandateCreate(BaseModel):
    institution_id: str
    kind: MandateKind
    action_code: str
    description: str = ""
    procedure_status: ProcedureStatus = "unknown"
    has_deadline: bool = False
    dependency_text: str | None = None
    dependency_ready: Literal["yes", "no", "unknown"] | None = None
    depends_on_id: str | None = None
    conflicts_with_id: str | None = None
    evidence_tag: EvidenceTag = "inferred"
    sources: list[SourceIn] = []


class MandateUpdate(BaseModel):
    institution_id: str | None = None
    kind: MandateKind | None = None
    action_code: str | None = None
    description: str | None = None
    procedure_status: ProcedureStatus | None = None
    has_deadline: bool | None = None
    dependency_text: str | None = None
    dependency_ready: Literal["yes", "no", "unknown"] | None = None
    depends_on_id: str | None = None
    conflicts_with_id: str | None = None
    evidence_tag: EvidenceTag | None = None


class MandateOut(ORM):
    id: str
    institution_id: str
    kind: str
    action_code: str
    description: str
    procedure_status: str
    has_deadline: bool
    dependency_text: str | None
    dependency_ready: str | None
    depends_on_id: str | None
    conflicts_with_id: str | None
    evidence_tag: str
    validation: str
    origin: str
    import_ref: str | None
    notes: str | None
    created_at: dt.datetime
    sources: list[SourceOut] = []
    active: bool = False
    inactive_reason: str | None = None


class ValidateIn(BaseModel):
    note: str | None = None
    corrections: MandateUpdate | None = None


class RejectIn(BaseModel):
    note: str = Field(min_length=1)


class ImportRowError(BaseModel):
    line: int
    import_ref: str | None
    error: str


class ImportReport(BaseModel):
    dry_run: bool
    created: int
    skipped: int
    errors: list[ImportRowError]
    mandate_ids: list[str] = []


class RegistryReviewIn(BaseModel):
    status: RegistryStatus
    note: str | None = None


class RegistryReviewOut(BaseModel):
    institution_id: str
    status: str
    reviewer: str | None = None
    note: str | None = None
    reviewed_at: dt.datetime | None = None


class ImportJson(BaseModel):
    csv_text: str
