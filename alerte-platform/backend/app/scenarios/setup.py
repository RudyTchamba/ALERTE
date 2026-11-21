from __future__ import annotations

from typing import Any

from sqlalchemy import select

from . import service
from .models import Inject, InjectRecipient, Scenario


class ScenariosService:
    """Objet `ctx.services["scenarios"]` (signatures de CONTRACTS.md)."""

    def __init__(self, ctx: Any) -> None:
        self._ctx = ctx

    def _mandates(self) -> Any:
        return self._ctx.services.get("mandates")

    def export_scenario_snapshot(self, session, workspace_id, scenario_id):  # noqa: ANN001, ANN201
        return service.export_snapshot(session, workspace_id, scenario_id, self._mandates())

    def readiness_scenario_checks(self, session, workspace_id, scenario_id):  # noqa: ANN001, ANN201
        return service.readiness_checks(session, workspace_id, scenario_id, self._mandates(), self._ctx.settings.max_llm_calls)

    def lint(self, session, workspace_id, scenario_id):  # noqa: ANN001, ANN201
        return service.lint(session, workspace_id, scenario_id, self._mandates(), self._ctx.settings.max_llm_calls)


def register(ctx) -> None:  # noqa: ANN001
    ctx.services["scenarios"] = ScenariosService(ctx)
    ws = ctx.services.get("workspaces")
    if ws is not None:
        def guard(session, kind, obj_id):  # noqa: ANN001, ANN202
            if kind == "country":
                return session.scalar(select(Scenario.id).where(Scenario.country_id == obj_id).limit(1)) is not None
            if kind == "institution":
                return session.scalar(select(InjectRecipient.inject_id).where(InjectRecipient.institution_id == obj_id).limit(1)) is not None
            return False
        ws.register_reference_guard(guard)


__all__ = ["register", "ScenariosService", "Inject"]
