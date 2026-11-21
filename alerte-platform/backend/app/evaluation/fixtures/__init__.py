"""Fixtures T3 privées et scellées (doc 09 §9.9 #7). NE JAMAIS importer ce paquet hors de `app.evaluation`."""
from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.canonical_json import canonical_sha256
from ...core.db import utcnow
from ...core.errors import Conflict
from .models import EvalFixture

SEAL_VERSION = "alerte-fixture-seal-v1"


def _iso(d: dt.datetime) -> str:
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.UTC)
    return d.astimezone(dt.UTC).isoformat(timespec="microseconds")


def compute_seal(workspace_id: str, scenario_code: str, expected_gap_key: str, label: str, description: str,
                 sealed_at: dt.datetime) -> str:
    return canonical_sha256({"v": SEAL_VERSION, "workspace_id": workspace_id, "scenario_code": scenario_code,
                             "expected_gap_key": expected_gap_key, "label": label, "description": description,
                             "sealed_at": _iso(sealed_at)})


def seal_fixture(session: Session, workspace_id: str, scenario_code: str, expected_gap_key: str, label: str,
                 description: str = "", created_by: str | None = None) -> EvalFixture:
    exists = session.scalar(select(EvalFixture.id).where(
        EvalFixture.workspace_id == workspace_id, EvalFixture.scenario_code == scenario_code,
        EvalFixture.expected_gap_key == expected_gap_key))
    if exists:
        raise Conflict("fixture déjà scellée pour ce scénario et cette empreinte (immuable)", code="fixture.sealed")
    at = utcnow()
    fx = EvalFixture(workspace_id=workspace_id, scenario_code=scenario_code, expected_gap_key=expected_gap_key,
                     label=label, description=description, sealed_at=at, created_by=created_by,
                     sealed_sha256=compute_seal(workspace_id, scenario_code, expected_gap_key, label, description, at))
    session.add(fx)
    session.flush()
    return fx


def list_fixtures(session: Session, workspace_id: str, scenario_code: str) -> list[EvalFixture]:
    return list(session.scalars(select(EvalFixture).where(
        EvalFixture.workspace_id == workspace_id, EvalFixture.scenario_code == scenario_code)
        .order_by(EvalFixture.id)))


def seal_ok(fx: EvalFixture) -> bool:
    return fx.sealed_sha256 == compute_seal(fx.workspace_id, fx.scenario_code, fx.expected_gap_key, fx.label,
                                            fx.description or "", fx.sealed_at)


def as_utc(d: dt.datetime) -> dt.datetime:
    return d.replace(tzinfo=dt.UTC) if d.tzinfo is None else d.astimezone(dt.UTC)


def public_view(fx: EvalFixture) -> dict[str, Any]:
    return {"id": fx.id, "scenario_code": fx.scenario_code, "expected_gap_key": fx.expected_gap_key, "label": fx.label,
            "sealed_sha256": fx.sealed_sha256, "sealed_at": _iso(fx.sealed_at), "seal_valid": seal_ok(fx)}
