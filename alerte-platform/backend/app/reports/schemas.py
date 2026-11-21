from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Confidentiality = Literal["public", "internal", "restricted"]


class ReportCreate(BaseModel):
    kind: Literal["generated", "imported"] = "generated"
    title: str = Field(min_length=1, max_length=400)
    exercise_id: str | None = None
    confidentiality: Confidentiality = "internal"


class GenerateIn(BaseModel):
    title: str | None = Field(default=None, max_length=400)
    report_id: str | None = None  # nouvelle version d'un rapport existant
    confidentiality: Confidentiality = "internal"


class ContentPut(BaseModel):
    content: dict[str, Any]


class FindingIn(BaseModel):
    title: str = Field(min_length=1, max_length=400)
    body: str = ""
    code_hint: str | None = Field(default=None, max_length=16)
    severity_hint: int | None = Field(default=None, ge=1, le=3)
    source_page: int | None = Field(default=None, ge=1)
    status: Literal["extracted", "validated", "rejected"] = "extracted"


class FindingOut(FindingIn):
    id: str
    report_id: str
    origin: str = "analyse antérieure"


class LinkIn(BaseModel):
    gap_id: str
    exercise_id: str
    relation: Literal["previously_identified", "newly_emerged", "contradicts"]
    note: str | None = None
