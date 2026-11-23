from __future__ import annotations

import logging

from .ledger import Ledger

log = logging.getLogger("alerte")


def register(ctx) -> None:  # noqa: ANN001
    signer = None
    try:
        from .signing import AnchorSigner
        path = ctx.settings.signing_key_path or (ctx.settings.resolved_data_dir / "keys" / "ledger-ed25519.pem")
        signer = AnchorSigner.load_or_create(path)
    except Exception:  # noqa: BLE001 - sans clé, les ancres restent valides mais non signées
        log.exception("clé de signature Ed25519 indisponible : ancres non signées")
    ctx.services["ledger"] = Ledger(ctx.settings.anchors_dir, signer=signer)
