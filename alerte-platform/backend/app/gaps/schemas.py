from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EvidenceOut(ORM):
    id: str
    kind: str
    role: str
    ref: dict[str, Any]
    excerpt: str | None
    is_agent: bool


class NegativeSearchOut(ORM):
    id: str
    action_code: str | None
    kb_ids: list
    queries: list
    languages: list
    corpus_documents: int
    corpus_coverage: float | None
    coverage_missing: list
    top_hits: list
    verdict: str
    run_at: dt.datetime
    statement: str = ""


class ReviewOut(ORM):
    id: str
    reviewer: str
    action: str
    from_status: str
    to_status: str
    reality_label: str | None
    blind: bool
    comment: str | None
    changes: dict | None
    created_at: dt.datetime


class GapOut(ORM):
    id: str
    exercise_id: str
    fingerprint: str
    code: str
    rule_id: str | None
    category: str
    title: str
    description: str
    domain: str | None
    institution_ids: list
    action_code: str | None
    evidence_basis: str
    confidence: str
    severity: int
    auto_severity: int
    consequence: str | None
    validation_status: str
    origin: str
    registry_state: str | None
    cause: str
    corpus_coverage: float | None
    demand_derivation: str | None
    inject_refs: list
    detail: dict
    is_current: bool
    section: str = "findings"          # findings | hypotheses (règle de promotion, doc 09 §9.3)
    reference_status: dict = {}
    created_at: dt.datetime


class ReferenceOut(ORM):
    id: str
    gap_id: str
    reference_id: str
    fit_note: str | None
    fit_score: float | None
    status: str
    reference: dict | None = None


class GapDetail(GapOut):
    evidence: list[EvidenceOut] = []
    negative_searches: list[NegativeSearchOut] = []
    references: list[ReferenceOut] = []
    reviews: list[ReviewOut] = []
    improvement_actions: list[dict] = []


class ReviewIn(BaseModel):
    action: Literal["confirm", "dispute", "reject", "comment", "reopen"]
    comment: str | None = None
    reality_label: Literal["real", "partially_real", "not_real"] | None = None
    blind: bool = False


class GapPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=400)
    description: str | None = None
    consequence: str | None = None
    severity: int | None = Field(default=None, ge=1, le=3)
    reason: str | None = None


class InternationalReferenceIn(BaseModel):
    jurisdiction: str = Field(min_length=1, max_length=120)
    instrument: str = Field(min_length=1, max_length=400)
    article: str | None = None
    summary: str = ""
    binding: bool = False
    domains: list[str] = []
    gap_codes: list[str] = []
    document_version_id: str | None = None
    chunk_id: str | None = None
    url: str | None = None
    evidence_tag: str | None = None


class InternationalReferenceOut(ORM):
    id: str
    jurisdiction: str
    instrument: str
    article: str | None
    summary: str
    binding: bool
    domains: list
    gap_codes: list
    document_version_id: str | None
    chunk_id: str | None
    url: str | None
    evidence_tag: str


class GapReferenceIn(BaseModel):
    reference_id: str
    fit_note: str | None = None
    fit_score: float | None = None


class GapReferencePatch(BaseModel):
    status: Literal["suggested", "accepted", "rejected"] | None = None
    fit_note: str | None = None
    fit_score: float | None = None


class ImprovementIn(BaseModel):
    description: str = Field(min_length=1)
    owner_institution_id: str | None = None
    due_date: dt.date | None = None
    status: Literal["planned", "in_progress", "done", "dropped"] = "planned"
    kpi: str | None = None


class ImprovementPatch(BaseModel):
    description: str | None = None
    owner_institution_id: str | None = None
    due_date: dt.date | None = None
    status: Literal["planned", "in_progress", "done", "dropped"] | None = None
    kpi: str | None = None


class ImprovementOut(ORM):
    id: str
    gap_id: str
    owner_institution_id: str | None
    description: str
    due_date: dt.date | None
    status: str
    kpi: str | None
