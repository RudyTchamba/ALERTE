from __future__ import annotations

from typing import Any

from sqlalchemy import select

from . import service
from .citations import check_citations
from .models import Agent
from .runtime import AgentRuntime


class CitationChecker:
    """CitationChecker déterministe exposé aux autres modules : `check(decision, retrieval_set, scope)`."""

    def __init__(self, ctx: Any) -> None:
        self._ctx = ctx

    def check(self, decision: dict, retrieval_set, scope):  # noqa: ANN001, ANN201
        from ..core.db import session_scope
        with session_scope(self._ctx.session_factory) as s:
            return check_citations(self._ctx.services["knowledge"], s, list(decision.get("legal_basis") or []),
                                   scope=scope, retrieval_set=None if retrieval_set is None else set(retrieval_set))


class AgentsService:
    """Objet `ctx.services["agents"]` (signatures de CONTRACTS.md)."""

    def __init__(self, ctx: Any) -> None:
        self._ctx = ctx
        self._runtime = AgentRuntime(ctx.settings, ctx.blobs, ctx.services, ctx.session_factory)

    def export_agent_snapshot(self, session, workspace_id, agent_id):  # noqa: ANN001, ANN201
        return service.export_agent_snapshot(session, workspace_id, agent_id)

    def kb_grants(self, session, workspace_id, agent_id):  # noqa: ANN001, ANN201
        return service.kb_grants(session, workspace_id, agent_id)

    def runtime(self) -> AgentRuntime:
        return self._runtime

    def ask_legal(self, seat_ctx, question):  # noqa: ANN001, ANN201
        """Conseiller juridique pour un siège humain (voir `AgentRuntime.ask_legal`)."""
        return self._runtime.ask_legal(seat_ctx, question)

    def draft_completion(self, messages, *, schema=None, max_tokens: int = 1500):  # noqa: ANN001, ANN201
        """Appel de rédaction (hors simulation, ex. projet de texte) avec le modèle configuré de l'espace.
        Fournisseur injectable pour les tests via `ctx.services["reform_llm"]`. Modèle indisponible -> 503."""
        from ..core.errors import AppError
        from .providers import ProviderUnavailable, provider_for
        try:
            prov = self._ctx.services.get("reform_llm") or provider_for(
                {"provider": "openai_compat", "max_tokens": max_tokens}, self._ctx.settings, blobs=self._ctx.blobs)
            return prov.complete(messages, schema=schema, temperature=0.0, max_tokens=max_tokens)
        except ProviderUnavailable as exc:
            raise AppError(f"modèle indisponible : {exc}", code="reform.model_unavailable", status_code=503) from exc

    @property
    def citation_checker(self) -> CitationChecker:
        return CitationChecker(self._ctx)


def register(ctx) -> None:  # noqa: ANN001
    ctx.services["agents"] = AgentsService(ctx)
    ws = ctx.services.get("workspaces")
    if ws is not None:
        def guard(session, kind, obj_id):  # noqa: ANN001, ANN202
            return kind == "institution" and session.scalar(
                select(Agent.id).where(Agent.institution_id == obj_id).limit(1)) is not None
        ws.register_reference_guard(guard)
