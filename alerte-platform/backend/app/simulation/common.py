"""Utilitaires partagés : accès aux services des autres modules, paramètres d'exercice."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..contracts import MAX_ROUNDS  # noqa: F401 - ré-exporté (source unique : app/contracts.py)
from ..core.errors import AppError, Unprocessable

NON_ACTIVATABLE_ROLES = ("ai_system", "legal_adviser")
MSG_TYPES = ("INFO", "REQUEST", "DECISION", "OBJECTION", "GAP_FLAG")
REPLY_STATUSES = ("accepted", "refused", "not_our_role")


def svc(ctx: Any, name: str) -> Any:
    try:
        return ctx.services[name]
    except KeyError as exc:
        raise AppError(f"service '{name}' indisponible", code="service.unavailable", status_code=503) from exc


def optional_svc(ctx: Any, name: str) -> Any | None:
    return ctx.services.get(name)


MANDATE_KINDS = Literal["power", "duty", "lead", "coordination", "information_sharing", "procedure", "human_oversight",
                        "liability", "inclusion", "channel_protection", "international_agreement", "prohibition"]


class ReformMandate(BaseModel):
    """Hypothèse de réforme (« Et si… ? ») : un mandat qui N'EXISTE PAS dans le registre réel.

    Il n'est injecté que dans le snapshot de l'exercice qui le porte, marqué `hypothesis`, avec un niveau de preuve
    « supposé » ; le registre réel n'est jamais modifié."""
    model_config = ConfigDict(extra="forbid")
    institution_id: str = Field(min_length=1, max_length=40)
    action_code: str = Field(min_length=1, max_length=120)
    kind: MANDATE_KINDS = "duty"
    description: str = Field(default="", max_length=600)
    has_deadline: bool = False
    procedure_status: Literal["specific", "general", "none", "unknown"] = "specific"


class ExerciseSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_llm_calls: int | None = Field(default=None, ge=1, le=100000)
    human_deadline_s: int = Field(default=900, ge=0, le=7 * 86400)
    human_fallback: Literal["agent_takeover", "skip"] = "agent_takeover"
    delay_s: float = Field(default=0.0, ge=0, le=3600)
    reform_mandates: list[ReformMandate] = Field(default_factory=list, max_length=20)


def resolve_settings(raw: dict | None, default_cap: int) -> dict:
    try:
        s = ExerciseSettings(**(raw or {})).model_dump()
    except ValidationError as exc:
        raise Unprocessable("paramètres d'exercice invalides", code="exercise.invalid_settings",
                            details={"errors": [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]}) from exc
    if s["max_llm_calls"] is None:
        s["max_llm_calls"] = default_cap
    return s


def activatable(agent: dict | None) -> bool:
    return (agent or {}).get("role_kind", "institution") not in NON_ACTIVATABLE_ROLES
