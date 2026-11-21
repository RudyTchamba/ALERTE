from __future__ import annotations

from . import service


def register(ctx) -> None:  # noqa: ANN001
    """Le résolveur de chunks est lié paresseusement au service `knowledge` (peut être enregistré après nous)."""
    def resolve(session, chunk_id):  # noqa: ANN001, ANN202
        knowledge = ctx.services.get("knowledge")
        return knowledge.get_chunk(session, chunk_id) if knowledge is not None else None

    service.set_chunk_resolver(resolve)
    ctx.services["mandates"] = service
