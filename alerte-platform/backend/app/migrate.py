"""Migrations Alembic. Tant qu'aucune révision n'existe (phase de conception du modèle), `create_all` est utilisé
sur une base jetable ; dès qu'une révision existe, `upgrade head` est la seule voie."""
from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine

from .core.config import Settings
from .core.db import Base
from .modules import import_all_models

log = logging.getLogger("alerte.migrate")
BACKEND_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = BACKEND_DIR / "migrations"


def alembic_config(settings: Settings) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
    return cfg


def has_revisions() -> bool:
    versions = MIGRATIONS_DIR / "versions"
    return versions.is_dir() and any(p.suffix == ".py" for p in versions.iterdir())


def init_database(settings: Settings, engine: Engine) -> str:
    """Prépare le schéma. Renvoie 'alembic' ou 'create_all'."""
    import_all_models()
    if has_revisions():
        command.upgrade(alembic_config(settings), "head")
        return "alembic"
    Base.metadata.create_all(engine)
    return "create_all"
