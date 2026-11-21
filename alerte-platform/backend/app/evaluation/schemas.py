from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QuestionIn(BaseModel):
    question: str = Field(min_length=3)
    expected_doc_code: str = Field(min_length=1)
    expected_article: str | None = None
    lang: str | None = None
    category: str | None = None


class QuestionOut(QuestionIn):
    id: str
    kb_id: str

    model_config = {"from_attributes": True}


class FixtureIn(BaseModel):
    scenario_code: str = Field(min_length=1, max_length=64)
    expected_gap_key: str = Field(min_length=8, max_length=64)  # = gap.fingerprint
    label: str = Field(min_length=1, max_length=400)
    description: str = ""


class BenchmarkSetIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source: str = ""
    description: str | None = None


class BenchmarkItemIn(BaseModel):
    label: str = Field(min_length=1, max_length=400)
    description: str | None = None
    domain: str | None = None
    fingerprint: str | None = None


class EvidenceIn(BaseModel):
    kind: str
    ref: Any = None
    excerpt: str | None = None


class AnswerIn(BaseModel):
    criterion_id: str
    answer: str
    evidence: list[EvidenceIn] = []
    note: str | None = None
    assessor: str | None = None


class ScorecardPut(BaseModel):
    answers: list[AnswerIn]
    reviewed_by: str | None = None
