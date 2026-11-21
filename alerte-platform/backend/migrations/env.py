"""Environnement Alembic : métadonnées de tous les modules ; URL depuis la configuration de l'application."""
from __future__ import annotations

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.core.db import Base
from app.modules import import_all_models

config = context.config
import_all_models()
target_metadata = Base.metadata



def include_object(obj, name, type_, reflected, compare_to):  # noqa: ANN001, ANN201
    """Les tables virtuelles FTS5 (`chunk_fts*`) sont gérées hors métadonnées : ne jamais les proposer à la suppression."""
    return not (type_ == "table" and name is not None and name.startswith("chunk_fts"))


if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata,
                      literal_binds=True, render_as_batch=True, compare_type=True, include_object=include_object)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.",
                                     poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=True,  # SQLite : ALTER via copie de table
                          compare_type=True, include_object=include_object)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
