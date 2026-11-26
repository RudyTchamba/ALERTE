"""Contexte applicatif partagé (un seul processus, architecture V1) et dépendances FastAPI."""
from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

from fastapi import Request
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .blobs import BlobStore
from .config import Settings
from .jobs import JobRunner


@dataclass
class AppContext:
    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    blobs: BlobStore
    jobs: JobRunner
    # Services enregistrés par les modules au démarrage (inversion de dépendance : core n'importe pas les modules)
    services: dict[str, Any] = field(default_factory=dict)
    # Résolution d'un jeton en Principal (enregistrée par le module workspaces)
    principal_resolver: Callable[[Session, str], Any] | None = None
    # Faux pour la CLI : un processus d'outil ne doit pas déclarer « interrompus » les traitements d'un serveur qui tourne
    recover_on_start: bool = True

    def service(self, name: str) -> Any:
        try:
            return self.services[name]
        except KeyError as exc:
            raise RuntimeError(f"service '{name}' non enregistré") from exc


def get_ctx(request: Request) -> AppContext:
    return request.app.state.ctx


def get_session(request: Request) -> Iterator[Session]:
    """Une session par requête : commit si succès, rollback sinon."""
    ctx: AppContext = request.app.state.ctx
    session = ctx.session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
