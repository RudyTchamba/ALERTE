"""Cas d'usage du module workspaces. Toute requête est filtrée par `workspace_id` (isolation)."""
from __future__ import annotations

import datetime as dt
import re
import unicodedata
from collections.abc import Callable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.auth import Principal
from ..core.db import utcnow
from ..core.errors import Conflict, Forbidden, NotFound
from ..core.security import generate_token, hash_token
from .models import AccessToken, Country, Institution, Workspace
from .schemas import CountryCreate, CountryUpdate, InstitutionCreate, InstitutionUpdate, TokenCreate

# Garde de référence : un objet utilisé par un exercice lancé ne peut qu'être archivé (jamais supprimé).
ReferenceGuard = Callable[[Session, str, str], bool]  # (session, kind, id) -> est référencé
_guards: list[ReferenceGuard] = []


def register_reference_guard(fn: ReferenceGuard) -> None:
    if fn not in _guards:
        _guards.append(fn)


def is_referenced(session: Session, kind: str, obj_id: str) -> bool:
    return any(g(session, kind, obj_id) for g in _guards)


def slugify(name: str) -> str:
    norm = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", norm).strip("-")
    return slug[:80] or "espace"


# --------------------------------------------------------------------------- espaces / jetons

def workspace_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Workspace)) or 0


def create_workspace(session: Session, name: str, slug: str | None) -> tuple[Workspace, str]:
    base = slug or slugify(name)
    candidate, n = base, 1
    while session.scalar(select(Workspace.id).where(Workspace.slug == candidate)):
        n += 1
        candidate = f"{base}-{n}"[:100]
    ws = Workspace(name=name, slug=candidate)
    session.add(ws)
    session.flush()
    plain, h = generate_token("own")
    session.add(AccessToken(workspace_id=ws.id, role="owner", label="Propriétaire", token_hash=h))
    session.flush()
    return ws, plain


def resolve_principal(session: Session, plain: str) -> Principal | None:
    row = session.scalar(select(AccessToken).where(AccessToken.token_hash == hash_token(plain)))
    if row is None or row.revoked_at is not None:
        return None
    now = utcnow()
    expires = row.expires_at
    if expires is not None:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=dt.UTC)
        if expires <= now:
            return None
    ws = session.get(Workspace, row.workspace_id)
    if ws is None or ws.archived_at is not None:
        return None
    return Principal(workspace_id=row.workspace_id, role=row.role, token_id=row.id, label=row.label,
                     exercise_id=row.exercise_id, seat_id=row.seat_id)


def get_workspace(session: Session, workspace_id: str) -> Workspace:
    ws = session.get(Workspace, workspace_id)
    if ws is None:
        raise NotFound("espace de travail introuvable")
    return ws


def create_token(session: Session, p: Principal, data: TokenCreate) -> tuple[str, AccessToken]:
    if data.role == "owner" and p.role != "owner":
        raise Forbidden("seul un propriétaire peut créer un jeton propriétaire")
    plain, h = generate_token(data.role[:3])
    expires = utcnow() + dt.timedelta(hours=data.expires_in_hours) if data.expires_in_hours else None
    row = AccessToken(workspace_id=p.workspace_id, role=data.role, label=data.label, token_hash=h,
                      exercise_id=data.exercise_id, seat_id=data.seat_id, expires_at=expires)
    session.add(row)
    session.flush()
    return plain, row


def list_tokens(session: Session, workspace_id: str) -> list[AccessToken]:
    return list(session.scalars(select(AccessToken).where(AccessToken.workspace_id == workspace_id)
                                .order_by(AccessToken.created_at.desc())))


def revoke_token(session: Session, p: Principal, token_id: str) -> None:
    row = session.scalar(select(AccessToken).where(AccessToken.id == token_id, AccessToken.workspace_id == p.workspace_id))
    if row is None:
        raise NotFound("jeton introuvable")
    if row.id == p.token_id:
        raise Conflict("impossible de révoquer le jeton utilisé pour cette requête", code="token.self_revoke")
    row.revoked_at = utcnow()


# --------------------------------------------------------------------------- pays

def _get_country(session: Session, workspace_id: str, country_id: str) -> Country:
    row = session.scalar(select(Country).where(Country.id == country_id, Country.workspace_id == workspace_id))
    if row is None:
        raise NotFound("pays introuvable")
    return row


def list_countries(session: Session, workspace_id: str, include_archived: bool = False) -> list[Country]:
    q = select(Country).where(Country.workspace_id == workspace_id).order_by(Country.name)
    if not include_archived:
        q = q.where(Country.archived_at.is_(None))
    return list(session.scalars(q))


def create_country(session: Session, workspace_id: str, data: CountryCreate) -> Country:
    row = Country(workspace_id=workspace_id, name=data.name, iso2=(data.iso2 or None) and data.iso2.upper(),
                  languages=data.languages, notes=data.notes)
    session.add(row)
    try:
        session.flush()
    except IntegrityError as exc:
        raise Conflict("un pays de ce nom existe déjà dans l'espace", code="country.duplicate") from exc
    return row


def get_country(session: Session, workspace_id: str, country_id: str) -> Country:
    return _get_country(session, workspace_id, country_id)


def update_country(session: Session, workspace_id: str, country_id: str, data: CountryUpdate) -> Country:
    row = _get_country(session, workspace_id, country_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(row, k, v.upper() if k == "iso2" and v else v)
    session.flush()
    return row


def archive_country(session: Session, workspace_id: str, country_id: str) -> Country:
    row = _get_country(session, workspace_id, country_id)
    row.archived_at = utcnow()
    return row


def delete_country(session: Session, workspace_id: str, country_id: str) -> None:
    row = _get_country(session, workspace_id, country_id)
    in_use = session.scalar(select(func.count()).select_from(Institution)
                            .where(Institution.workspace_id == workspace_id, Institution.country_id == country_id))
    if in_use or is_referenced(session, "country", country_id):
        raise Conflict("ce pays est utilisé : archivez-le au lieu de le supprimer", code="country.in_use")
    session.delete(row)


# --------------------------------------------------------------------------- institutions

def _get_institution(session: Session, workspace_id: str, institution_id: str) -> Institution:
    row = session.scalar(select(Institution).where(Institution.id == institution_id,
                                                   Institution.workspace_id == workspace_id))
    if row is None:
        raise NotFound("institution introuvable")
    return row


def list_institutions(session: Session, workspace_id: str, country_id: str | None = None,
                      include_archived: bool = False) -> list[Institution]:
    q = select(Institution).where(Institution.workspace_id == workspace_id).order_by(Institution.code)
    if country_id:
        q = q.where(Institution.country_id == country_id)
    if not include_archived:
        q = q.where(Institution.archived_at.is_(None))
    return list(session.scalars(q))


def create_institution(session: Session, workspace_id: str, data: InstitutionCreate) -> Institution:
    if data.country_id:
        _get_country(session, workspace_id, data.country_id)  # le pays doit appartenir au même espace
    row = Institution(workspace_id=workspace_id, **data.model_dump())
    session.add(row)
    try:
        session.flush()
    except IntegrityError as exc:
        raise Conflict("une institution de ce code existe déjà dans l'espace", code="institution.duplicate") from exc
    return row


def get_institution(session: Session, workspace_id: str, institution_id: str) -> Institution:
    return _get_institution(session, workspace_id, institution_id)


def update_institution(session: Session, workspace_id: str, institution_id: str, data: InstitutionUpdate) -> Institution:
    row = _get_institution(session, workspace_id, institution_id)
    changes: dict[str, Any] = data.model_dump(exclude_unset=True)
    if changes.get("country_id"):
        _get_country(session, workspace_id, changes["country_id"])
    for k, v in changes.items():
        setattr(row, k, v)
    session.flush()
    return row


def archive_institution(session: Session, workspace_id: str, institution_id: str) -> Institution:
    row = _get_institution(session, workspace_id, institution_id)
    row.archived_at = utcnow()
    return row


def delete_institution(session: Session, workspace_id: str, institution_id: str) -> None:
    row = _get_institution(session, workspace_id, institution_id)
    if is_referenced(session, "institution", institution_id):
        raise Conflict("cette institution est utilisée : archivez-la au lieu de la supprimer", code="institution.in_use")
    session.delete(row)
