"""Sondes : /health (processus) et /ready (base, dossiers, services enregistrés)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text

from .context import AppContext, get_ctx

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(response: Response, ctx: AppContext = Depends(get_ctx)) -> dict:
    checks: dict[str, dict] = {}
    try:
        with ctx.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = {"ok": True}
    except Exception as exc:  # noqa: BLE001
        checks["database"] = {"ok": False, "error": str(exc)[:200]}
    checks["data_dir"] = {"ok": ctx.settings.resolved_data_dir.is_dir()}
    for name, svc in ctx.services.items():
        probe = getattr(svc, "readiness", None)
        if callable(probe):
            try:
                checks[name] = probe()
            except Exception as exc:  # noqa: BLE001
                checks[name] = {"ok": False, "error": str(exc)[:200]}
    ok = all(c.get("ok", False) for c in checks.values())
    if not ok:
        response.status_code = 503
    return {"ready": ok, "checks": checks}
