from __future__ import annotations

from .engine import GapEngine


def register(ctx) -> None:  # noqa: ANN001
    ctx.services["gap_engine"] = GapEngine(ctx)
