"""Import CSV (colonnes du prototype) : toujours `proposed`, sans source (les anciens `source_doc` ne résolvent plus).

Colonnes : line_id,country,institution,kind,action,description,source_doc,article,procedure,depends_on,
dependency_ready,evidence,assumed_by. `institution` = code d'institution de l'espace ; le `source_doc` d'origine est
conservé en note pour re-liaison manuelle.
"""
from __future__ import annotations

import csv
import io
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.errors import AppError
from ..workspaces.models import Institution
from . import service
from .models import Mandate
from .schemas import ImportReport, ImportRowError, MandateCreate


def _row_to_create(row: dict[str, str], institutions: dict[str, str]) -> tuple[MandateCreate, str]:
    code = (row.get("institution") or "").strip()
    if code not in institutions:
        raise ValueError(f"institution inconnue : {code!r}")
    procedure = (row.get("procedure") or "").strip()
    ready = (row.get("dependency_ready") or "").strip().lower() or None
    evidence = (row.get("evidence") or "inferred").strip().lower()
    notes = [f"procédure d'origine : {procedure}" if procedure else "", f"source_doc d'origine (à re-lier) : "
             f"{(row.get('source_doc') or '').strip()} {(row.get('article') or '').strip()}".strip(),
             f"assumé par : {row['assumed_by'].strip()}" if (row.get("assumed_by") or "").strip() else ""]
    data = MandateCreate(
        institution_id=institutions[code], kind=(row.get("kind") or "").strip().lower(),
        action_code=(row.get("action") or "").strip(), description=(row.get("description") or "").strip(),
        procedure_status="general" if procedure else "none",
        dependency_text=(row.get("depends_on") or "").strip() or None,
        dependency_ready=ready if ready in ("yes", "no", "unknown") else None,
        evidence_tag=evidence if evidence in ("documented", "inferred", "assumed") else "inferred")
    return data, "; ".join(n for n in notes if n)


def import_csv(session: Session, workspace_id: str, text: str, principal: Any = None, *, dry_run: bool = False) -> ImportReport:
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    institutions = {i.code: i.id for i in session.scalars(select(Institution).where(Institution.workspace_id == workspace_id))}
    existing = {r for r in session.scalars(select(Mandate.import_ref).where(Mandate.workspace_id == workspace_id,
                                                                            Mandate.import_ref.is_not(None)))}
    rep = ImportReport(dry_run=dry_run, created=0, skipped=0, errors=[])
    for n, row in enumerate(reader, start=2):
        ref = (row.get("line_id") or "").strip() or None
        if ref and ref in existing:
            rep.skipped += 1
            continue
        try:
            data, notes = _row_to_create(row, institutions)
            if not service.action_exists(session, workspace_id, data.action_code):
                raise ValueError(f"action absente du catalogue : {data.action_code!r} (créez-la d'abord : « Catalogue d'actions », bouton « Importer un CSV »)")
        except (ValueError, ValidationError) as exc:
            rep.errors.append(ImportRowError(line=n, import_ref=ref, error=str(exc).splitlines()[0][:300]))
            continue
        if not dry_run:
            try:
                with session.begin_nested():
                    m = service.create_mandate(session, workspace_id, data, principal, origin="csv_import",
                                               import_ref=ref, notes=notes)
            except AppError as exc:
                rep.errors.append(ImportRowError(line=n, import_ref=ref, error=exc.message))
                continue
            rep.mandate_ids.append(m.id)
        if ref:
            existing.add(ref)
        rep.created += 1
    return rep


ACTION_COLUMNS = ("code", "label", "domain", "derivation", "justification", "reference_note")


def import_actions_csv(session: Session, workspace_id: str, text: str, *, dry_run: bool = False) -> ImportReport:
    """Import CSV du catalogue d'actions (colonnes : code,label,domain,derivation,justification,reference_note).

    Idempotent : un code déjà présent est ignoré. Une dérivation `scenario_author` exige une justification."""
    from .schemas import ActionCreate
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    rep = ImportReport(dry_run=dry_run, created=0, skipped=0, errors=[])
    seen: set[str] = set()
    for n, row in enumerate(reader, start=2):
        code = (row.get("code") or "").strip()
        if not code:
            rep.errors.append(ImportRowError(line=n, import_ref=None, error="colonne « code » vide"))
            continue
        if code in seen or service.action_exists(session, workspace_id, code):
            rep.skipped += 1
            continue
        try:
            data = ActionCreate(code=code, label=(row.get("label") or "").strip(), domain=(row.get("domain") or "").strip() or None,
                                derivation=(row.get("derivation") or "scenario_author").strip(),
                                justification=(row.get("justification") or "").strip() or None,
                                reference_note=(row.get("reference_note") or "").strip() or None)
            service._check_action(data.derivation, data.justification)  # mêmes règles en essai à blanc et en réel
            if not dry_run:
                with session.begin_nested():
                    service.create_action(session, workspace_id, data)
        except (ValueError, ValidationError, AppError) as exc:
            rep.errors.append(ImportRowError(line=n, import_ref=code, error=str(getattr(exc, "message", exc)).splitlines()[0][:300]))
            continue
        seen.add(code)
        rep.created += 1
    return rep
