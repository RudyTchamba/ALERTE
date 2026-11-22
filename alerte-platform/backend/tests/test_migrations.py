"""Alembic : `upgrade head` depuis une base vide crée exactement le schéma des modèles (aucune dérive), avec FTS5 et triggers ;
`downgrade base` fonctionne ; l'application démarre via Alembic."""
from __future__ import annotations

import sqlite3

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.core.config import Settings
from app.core.db import Base, make_engine
from app.migrate import alembic_config, has_revisions
from app.modules import import_all_models


def _env_include_object():  # noqa: ANN202
    src = open("migrations/env.py", encoding="utf-8").read()
    ns: dict = {}
    exec(src[src.index("def include_object"):src.index("if not config.get_main_option")], ns)  # noqa: S102
    return ns["include_object"]


include_object = _env_include_object()


def _settings(tmp_path) -> Settings:
    s = Settings(data_dir=tmp_path / "data", log_json=False, log_level="WARNING")
    s.ensure_dirs()
    return s


def test_upgrade_head_matches_models_and_creates_sqlite_objects(tmp_path):
    assert has_revisions()
    s = _settings(tmp_path)
    command.upgrade(alembic_config(s), "head")
    import_all_models()
    engine = make_engine(s.database_url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True, "include_object": include_object}), Base.metadata)
        assert diff == [], diff
    db = sqlite3.connect(str(s.resolved_data_dir / "db" / "alerte.sqlite"))
    names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type IN ('table','trigger')")}
    assert {"chunk_fts", "gap_review_no_update", "gap_review_no_delete", "trg_report_version_no_update",
            "trg_report_version_no_delete", "alembic_version"} <= names
    db.close()
    command.downgrade(alembic_config(s), "base")


def test_app_starts_through_alembic(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import create_app
    s = Settings(data_dir=tmp_path / "data", log_json=False, log_level="WARNING", llm_mode="scripted", embed_provider="fixture")
    with TestClient(create_app(s)) as c:
        assert c.get("/api/v1/health").status_code == 200
    db = sqlite3.connect(str(s.resolved_data_dir / "db" / "alerte.sqlite"))
    assert db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0002"
