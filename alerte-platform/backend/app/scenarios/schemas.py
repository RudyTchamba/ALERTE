"""DTO Pydantic du module scenarios."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .faults import VALID_FAULT_MODES

TAG_PATTERN = r"^[a-z][a-z0-9_]{1,46}$"
Derivation = Literal["referential", "scenario_author", "agent_proposed"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DemandIn(BaseModel):
    action_code: str = Field(min_length=1, max_length=100)
    justification: str = Field(default="", max_length=2000)
    derivation: Derivation = "scenario_author"


class DemandOut(DemandIn):
    pass


class ScenarioCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=8000)
    language: str = Field(default="en", min_length=2, max_length=8)
    version: int = Field(default=1, ge=1)
    country_id: str | None = None
    is_template: bool = False


class ScenarioUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=8000)
    language: str | None = Field(default=None, min_length=2, max_length=8)
    version: int | None = Field(default=None, ge=1)
    status: Literal["draft", "ready"] | None = None
    country_id: str | None = None
    is_template: bool | None = None


class ScenarioClone(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    title: str | None = Field(default=None, min_length=1, max_length=300)


class ScenarioOut(ORM):
    id: str
    code: str
    title: str
    description: str
    language: str
    version: int
    status: str
    country_id: str | None
    is_template: bool
    cloned_from_id: str | None
    inject_count: int = 0


class _InjectFields(BaseModel):
    sim_time: str = Field(default="", max_length=40)
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(default="", max_length=8000)
    from_actor: str = Field(default="", max_length=200)
    fault_mode: str = "none"
    system_output: dict[str, Any] | None = None
    source_note: str | None = Field(default=None, max_length=2000)

    @field_validator("fault_mode")
    @classmethod
    def _fm(cls, v: str) -> str:
        if v not in VALID_FAULT_MODES:
            raise ValueError(f"mode de panne inconnu : {v}")
        return v


class InjectCreate(_InjectFields):
    seq: int | None = Field(default=None, ge=1)
    recipients: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    demands: list[DemandIn] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def _tags(cls, v: list[str]) -> list[str]:
        import re
        for t in v:
            if not re.match(TAG_PATTERN, t):
                raise ValueError(f"étiquette invalide : {t}")
        return list(dict.fromkeys(v))


class InjectUpdate(BaseModel):
    sim_time: str | None = Field(default=None, max_length=40)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    body: str | None = Field(default=None, max_length=8000)
    from_actor: str | None = Field(default=None, max_length=200)
    fault_mode: str | None = None
    system_output: dict[str, Any] | None = None
    source_note: str | None = Field(default=None, max_length=2000)
    tags: list[str] | None = None

    @field_validator("fault_mode")
    @classmethod
    def _fm(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_FAULT_MODES:
            raise ValueError(f"mode de panne inconnu : {v}")
        return v

    @field_validator("tags")
    @classmethod
    def _tags(cls, v: list[str] | None) -> list[str] | None:
        return v if v is None else InjectCreate._tags(v)  # type: ignore[attr-defined]


class InjectOut(BaseModel):
    id: str
    scenario_id: str
    seq: int
    sim_time: str
    title: str
    body: str
    from_actor: str
    fault_mode: str
    system_output: dict[str, Any] | None
    source_note: str | None
    recipients: list[str]
    tags: list[str]
    demands: list[DemandOut]
    warnings: list[str] = Field(default_factory=list)


class OrderIn(BaseModel):
    inject_ids: list[str]


class RecipientsIn(BaseModel):
    institution_ids: list[str]


class DemandsIn(BaseModel):
    demands: list[DemandIn]
