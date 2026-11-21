"""DTO Pydantic du module agents."""
from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TOOLS = ("search_kb", "ask_legal", "post", "decide")
RoleKind = Literal["institution", "ai_system", "legal_adviser"]
Provider = Literal["openai_compat", "scripted", "cassette"]
ENV_NAME = r"^[A-Za-z_][A-Za-z0-9_]{0,99}$"
DEFAULT_LIMITS = {"max_steps": 4, "max_search_calls": 3, "max_legal_calls": 2}


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ModelProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    provider: Provider
    endpoint_ref: str | None = Field(default=None, pattern=ENV_NAME, description="NOM d'une variable d'environnement")
    model: str | None = Field(default=None, max_length=200)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=16, le=32768)
    timeout_s: float = Field(default=120.0, gt=0, le=1800)
    extra: dict[str, Any] | None = None


class ModelProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    provider: Provider | None = None
    endpoint_ref: str | None = Field(default=None, pattern=ENV_NAME)
    model: str | None = Field(default=None, max_length=200)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=16, le=32768)
    timeout_s: float | None = Field(default=None, gt=0, le=1800)
    extra: dict[str, Any] | None = None


class ModelProfileOut(ORM):
    id: str
    name: str
    provider: str
    endpoint_ref: str | None
    model: str | None
    temperature: float
    max_tokens: int
    timeout_s: float
    extra: dict[str, Any] | None = None


def _check_tools(v: list[str] | None) -> list[str] | None:
    if v is None:
        return v
    bad = [t for t in v if t not in TOOLS]
    if bad:
        raise ValueError(f"outil(s) inconnu(s) : {bad}")
    return list(dict.fromkeys(v))


def _check_limits(v: dict[str, int] | None) -> dict[str, int] | None:
    if v is None:
        return v
    allowed = {"max_steps": (1, 8), "max_search_calls": (0, 10), "max_legal_calls": (0, 5)}
    out = dict(DEFAULT_LIMITS)
    for k, val in v.items():
        if k == "max_legal_calls_per_inject":
            k = "max_legal_calls"
        if k not in allowed or not isinstance(val, int) or not allowed[k][0] <= val <= allowed[k][1]:
            raise ValueError(f"limite invalide : {k}={val}")
        out[k] = val
    return out


class AgentCreate(BaseModel):
    institution_id: str | None = None
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=300)
    role_kind: RoleKind = "institution"
    mission: str = Field(default="", max_length=4000)
    instructions: str = Field(default="", max_length=8000)
    model_profile_id: str | None = None
    tools: list[str] = Field(default_factory=lambda: list(TOOLS))
    limits: dict[str, int] = Field(default_factory=lambda: dict(DEFAULT_LIMITS))
    is_template: bool = False

    @field_validator("tools")
    @classmethod
    def _t(cls, v):  # noqa: ANN001, ANN206
        return _check_tools(v)

    @field_validator("limits")
    @classmethod
    def _l(cls, v):  # noqa: ANN001, ANN206
        return _check_limits(v)


class AgentUpdate(BaseModel):
    institution_id: str | None = None
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=300)
    role_kind: RoleKind | None = None
    mission: str | None = Field(default=None, max_length=4000)
    instructions: str | None = Field(default=None, max_length=8000)
    model_profile_id: str | None = None
    tools: list[str] | None = None
    limits: dict[str, int] | None = None
    is_template: bool | None = None

    @field_validator("tools")
    @classmethod
    def _t(cls, v):  # noqa: ANN001, ANN206
        return _check_tools(v)

    @field_validator("limits")
    @classmethod
    def _l(cls, v):  # noqa: ANN001, ANN206
        return _check_limits(v)


class AgentOut(ORM):
    id: str
    institution_id: str | None
    code: str
    name: str
    role_kind: str
    mission: str
    instructions: str
    model_profile_id: str | None
    tools: list[str]
    limits: dict[str, int]
    is_template: bool
    cloned_from_id: str | None
    archived_at: dt.datetime | None
    kb_ids: list[str] = Field(default_factory=list)


class AgentClone(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=300)
    institution_id: str | None = None
    copy_grants: bool = True


class KbGrantsIn(BaseModel):
    kb_ids: list[str]
