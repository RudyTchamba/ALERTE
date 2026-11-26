"""Enregistrement du module : services de recherche, de connaissance et d'embeddings ; FTS5 (SQL brut) ; readiness."""
from __future__ import annotations

import os

from .embedders import build_embedder
from .indexes import create_fts
from .runtime import KnowledgeRuntime


def register(ctx) -> None:  # noqa: ANN001
    create_fts(ctx.engine)  # vérifie FTS5 (RuntimeError sinon) et crée `chunk_fts` si absente
    embedder = build_embedder(ctx.settings, revision=os.environ.get("ALERTE_EMBED_REVISION", ""),
                              runtime=os.environ.get("ALERTE_EMBED_RUNTIME", ""),
                              quantization=os.environ.get("ALERTE_EMBED_QUANTIZATION", ""))
    ws = ctx.services.get("workspaces")
    lookup = getattr(ws, "get_country", None)
    rt = KnowledgeRuntime(ctx.settings, ctx.session_factory, ctx.blobs, ctx.jobs, embedder, country_lookup=lookup)
    rt.signer = getattr(ctx.services.get("ledger"), "signer", None)  # signe les archives exportées (Ed25519)
    from .services.pipeline import recover_interrupted
    if ctx.recover_on_start:
        recover_interrupted(ctx.session_factory)  # versions restées « en cours » après un arrêt : failed, relançables
    ctx.services["knowledge"] = rt
    ctx.services["search"] = rt.search
    ctx.services["embedder"] = embedder
