"""DTO Pydantic du module simulation."""
from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CODE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}$"
Controller = Literal["agent", "human", "scripted"]


class ExerciseCreate(BaseModel):
    scenario_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,39}$")
    settings: dict[str, Any] | None = None
    ai_mode: Literal["ai", "scripted", "cassette"] | None = None
    pace: Literal["manual", "auto", "auto_delay"] | None = None


class SeatIn(BaseModel):
    code: str = Field(pattern=CODE_PATTERN)
    institution_id: str
    agent_id: str | None = None
    controller: Controller = "agent"
    human_name: str | None = Field(default=None, max_length=200)


class SeatsPut(BaseModel):
    seats: list[SeatIn]


class InviteIn(BaseModel):
    expires_in_hours: int = Field(default=24, ge=1, le=24 * 30)


class CommandIn(BaseModel):
    kind: Literal["start", "pause", "resume", "step", "speed", "stop", "surprise", "seat_switch", "correction"]
    args: dict[str, Any] = Field(default_factory=dict)


class SurpriseArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=4000)
    recipients: list[str] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    fault_mode: str = "none"
    sim_time: str | None = None


class SeatSwitchArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seat: str
    controller: Controller
    human_name: str | None = None
    reason: str | None = None


class CorrectionArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    corrects_seq: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=1000)
    replacement: dict[str, Any] | None = None


class SpeedArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pace: Literal["manual", "auto", "auto_delay"]
    delay_s: float | None = Field(default=None, ge=0, le=3600)


class ResumeArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    extend_budget: int = Field(default=0, ge=0, le=100000)


class SeatOut(BaseModel):
    code: str
    institution_id: str
    agent_id: str | None = None
    controller: str
    human_name: str | None = None


class ExerciseOut(BaseModel):
    id: str
    code: str
    title: str
    state: str
    substate: str | None = None
    pace: str
    ai_mode: str
    scenario_id: str
    parent_exercise_id: str | None = None
    settings: dict[str, Any]
    started_at: dt.datetime | None = None
    ended_at: dt.datetime | None = None
    snapshot_sha256: str | None = None
    commitment_sha256: str | None = None
    llm_calls_used: int = 0
    seats: list[SeatOut] | None = None


# --------------------------------------------------------------------------- siège humain
class SearchIn(BaseModel):
    query: str = Field(min_length=1, max_length=300)


class AskLegalIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class PostIn(BaseModel):
    to: str
    msg_type: Literal["INFO", "REQUEST", "DECISION", "OBJECTION", "GAP_FLAG"]
    body: str = Field(min_length=1, max_length=1500)
    in_reply_to: str | None = None
    reply_status: Literal["accepted", "refused", "not_our_role"] | None = None
    final: bool = False  # termine l'activation sans décision


class LegalBasisIn(BaseModel):
    chunk_id: str
    article: str | None = None
    quote: str = Field(min_length=1)


class GapFlagIn(BaseModel):
    hint: str | None = None
    text: str = Field(min_length=1, max_length=500)


class DecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(min_length=1, max_length=500)
    action_code: str | None = None
    outcome: Literal["act", "decline", "refer", "no_legal_basis_found"]
    confidence: Literal["low", "medium", "high"]
    legal_basis: list[LegalBasisIn] = Field(default_factory=list)
    options_considered: list[str] = Field(default_factory=list)
    gap_flags: list[GapFlagIn] = Field(default_factory=list)
    evidence_tag: Literal["documented", "inferred", "assumed"]
    rationale: str = Field(min_length=1, max_length=280)
