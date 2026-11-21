"""Point d'entrée FastAPI : `python -m uvicorn app.main:app` ou `app.main.create_app(settings)` (tests)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import modules
from .core.blobs import BlobStore
from .core.config import Settings, get_settings
from .core.context import AppContext
from .core.db import assert_foreign_keys_enabled, make_engine, make_sessionmaker
from .core.errors import install_error_handlers
from .core.jobs import JobRunner
from .core.logging_setup import setup_logging
from .migrate import init_database

log = logging.getLogger("alerte")
API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level, settings.log_json)
    settings.ensure_dirs()

    engine = make_engine(settings.database_url)
    factory = make_sessionmaker(engine)
    ctx = AppContext(settings=settings, engine=engine, session_factory=factory,
                     blobs=BlobStore(settings.blobs_dir), jobs=JobRunner(factory, settings.job_workers))

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # noqa: ANN202
        mode = init_database(settings, engine)
        assert_foreign_keys_enabled(engine)
        interrupted = ctx.jobs.mark_interrupted_on_startup()
        done = modules.run_setups(ctx)
        log.info("démarrage : schéma=%s, jobs interrompus=%s, modules=%s", mode, interrupted, done)
        yield
        ctx.jobs.shutdown(wait=False)
        engine.dispose()

    app = FastAPI(title="ALERTE Platform API", version="0.1.0", lifespan=lifespan,
                  openapi_url=f"{API_PREFIX}/openapi.json", docs_url=f"{API_PREFIX}/docs")
    app.state.ctx = ctx
    install_error_handlers(app)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=False,
                       allow_methods=["*"], allow_headers=["*"], expose_headers=["x-request-id"])

    from .core.health import router as health_router
    app.include_router(health_router, prefix=API_PREFIX)
    for name, router in modules.routers():
        app.include_router(router, prefix=API_PREFIX, tags=[name])

    # SPA construite (si présente) servie par le même processus
    dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):  # noqa: ANN202
            candidate = dist / full_path
            if full_path and candidate.is_file() and dist in candidate.resolve().parents:
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    return app


def app_factory() -> FastAPI:
    """Lancement : `python -m uvicorn app.main:app_factory --factory` (config lue dans l'environnement)."""
    return create_app()
