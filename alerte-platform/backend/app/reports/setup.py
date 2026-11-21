from __future__ import annotations

from . import service


def register(ctx) -> None:  # noqa: ANN001
    ctx.services["reports"] = service
