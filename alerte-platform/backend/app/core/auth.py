"""Authentification par jetons porteurs à rôle (architecture V1).

Rôles : `owner` (tout dans l'espace), `facilitator`, `player` (un siège), `observer` (lecture), `auditor`.
Le jeton n'est jamais stocké en clair ; il porte un rôle et une portée (espace, éventuellement exercice/siège).
Le flux SSE utilise un jeton de flux à usage unique de courte durée (module simulation).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from .context import AppContext, get_ctx, get_session
from .errors import Forbidden, Unauthorized

ROLES = ("owner", "facilitator", "player", "observer", "auditor")


@dataclass(frozen=True)
class Principal:
    workspace_id: str
    role: str
    token_id: str
    label: str | None = None
    exercise_id: str | None = None
    seat_id: str | None = None

    def has_role(self, *roles: str) -> bool:
        return self.role == "owner" or self.role in roles


def _bearer(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return None


def current_principal(request: Request, session: Session = Depends(get_session),
                      ctx: AppContext = Depends(get_ctx)) -> Principal:
    token = _bearer(request)
    if not token:
        raise Unauthorized("jeton d'accès manquant", code="auth.missing_token")
    if ctx.principal_resolver is None:  # pragma: no cover - configuration
        raise RuntimeError("principal_resolver non enregistré")
    principal = ctx.principal_resolver(session, token)
    if principal is None:
        raise Unauthorized("jeton invalide, expiré ou révoqué", code="auth.invalid_token")
    return principal


def require_role(*roles: str) -> Callable[..., Principal]:
    """Dépendance FastAPI : `Depends(require_role("facilitator"))` ; `owner` est toujours autorisé."""
    for r in roles:
        if r not in ROLES:
            raise ValueError(f"rôle inconnu : {r}")

    def _dep(principal: Principal = Depends(current_principal)) -> Principal:
        if not principal.has_role(*roles):
            raise Forbidden("rôle insuffisant", code="workspace.forbidden", details={"required": list(roles)})
        return principal

    return _dep
