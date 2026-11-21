from __future__ import annotations

from . import service


def register(ctx) -> None:  # noqa: ANN001
    ctx.principal_resolver = service.resolve_principal
    ctx.services["workspaces"] = service
