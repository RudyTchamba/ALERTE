from __future__ import annotations

from ..workspaces import service as ws_service
from . import service
from .engine import SimulationManager


def register(ctx) -> None:  # noqa: ANN001
    mgr = SimulationManager(ctx)
    ctx.services["simulation"] = mgr
    ctx.services["exercise_guard"] = service.exercise_guard
    ws_service.register_reference_guard(service.reference_guard)
    # arrêt anormal : running -> interrupted ; la reprise (commande `resume`) repart du journal (étapes idempotentes)
    mgr.recover_interrupted()
