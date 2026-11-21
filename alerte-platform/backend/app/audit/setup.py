from __future__ import annotations

from .ledger import Ledger


def register(ctx) -> None:  # noqa: ANN001
    ctx.services["ledger"] = Ledger(ctx.settings.anchors_dir)
