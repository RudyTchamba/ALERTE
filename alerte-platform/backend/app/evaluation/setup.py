from __future__ import annotations

import logging

from ..core.db import session_scope
from . import service
from .scorecard import seed_rubric

log = logging.getLogger("alerte.evaluation")


def register(ctx) -> None:  # noqa: ANN001
    service.bind(ctx)
    ctx.services["evaluation"] = service.EvaluationService(ctx)
    try:
        with session_scope(ctx.session_factory) as s:
            seed_rubric(s)  # 13 dimensions + critères (idempotent)
    except Exception:  # noqa: BLE001 - ne jamais empêcher le démarrage de l'application
        log.exception("amorçage de la grille du scorecard impossible : scorecard vide jusqu'au prochain démarrage")
