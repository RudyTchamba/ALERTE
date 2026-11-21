"""DTO Pydantic du module workspaces (source du contrat OpenAPI)."""
from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["owner", "facilitator", "player", "observer", "auditor"]
InstitutionKind = Literal["ministry", "agency", "regulator", "operator", "local_authority", "ai_system", "advisory", "other"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{1,98}$")


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)


class WorkspaceOut(ORM):
    id: str
    name: str
    slug: str
    created_at: dt.datetime
    archived_at: dt.datetime | None = None


class WorkspaceCreated(BaseModel):
    workspace: WorkspaceOut
    owner_token: str = Field(description="Montré UNE seule fois ; seul son hash est conservé")


class TokenCreate(BaseModel):
    role: Role
    label: str | None = Field(default=None, max_length=200)
    expires_in_hours: int | None = Field(default=None, ge=1, le=24 * 365)
    exercise_id: str | None = None
    seat_id: str | None = None


class TokenOut(ORM):
    id: str
    role: str
    label: str | None
    exercise_id: str | None = None
    seat_id: str | None = None
    created_at: dt.datetime
    expires_at: dt.datetime | None = None
    revoked_at: dt.datetime | None = None


class TokenCreated(BaseModel):
    token: str = Field(description="Montré UNE seule fois")
    info: TokenOut


class CountryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    iso2: str | None = Field(default=None, min_length=2, max_length=2)
    languages: list[str] = Field(default_factory=list)
    notes: str | None = None


class CountryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    iso2: str | None = Field(default=None, min_length=2, max_length=2)
    languages: list[str] | None = None
    notes: str | None = None


class CountryOut(ORM):
    id: str
    name: str
    iso2: str | None
    languages: list[str] | None
    notes: str | None
    created_at: dt.datetime
    archived_at: dt.datetime | None = None


class InstitutionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=300)
    name_local: str | None = None
    country_id: str | None = None
    kind: InstitutionKind = "other"
    domains: list[str] = Field(default_factory=list)
    description: str | None = None


class InstitutionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    name_local: str | None = None
    country_id: str | None = None
    kind: InstitutionKind | None = None
    domains: list[str] | None = None
    description: str | None = None


class InstitutionOut(ORM):
    id: str
    code: str
    name: str
    name_local: str | None
    country_id: str | None
    kind: str
    domains: list[str] | None
    description: str | None
    created_at: dt.datetime
    archived_at: dt.datetime | None = None
