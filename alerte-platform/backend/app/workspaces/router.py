from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from ..core.auth import Principal, require_role
from ..core.context import AppContext, get_ctx, get_session
from ..core.errors import Forbidden
from . import service
from .schemas import (
    CountryCreate,
    CountryOut,
    CountryUpdate,
    InstitutionCreate,
    InstitutionOut,
    InstitutionUpdate,
    TokenCreate,
    TokenCreated,
    TokenOut,
    WorkspaceCreate,
    WorkspaceCreated,
    WorkspaceOut,
    WorkspaceUpdate,
)

router = APIRouter()
Any_ = require_role("facilitator", "player", "observer", "auditor")  # lecture : tout rôle authentifié
Write = require_role("facilitator")  # `owner` est toujours autorisé


@router.post("/workspaces", response_model=WorkspaceCreated, status_code=status.HTTP_201_CREATED, tags=["workspaces"])
def create_workspace(body: WorkspaceCreate, request: Request, session: Session = Depends(get_session),
                     ctx: AppContext = Depends(get_ctx)) -> WorkspaceCreated:
    """Premier démarrage (aucun espace) ou `ALERTE_BOOTSTRAP_ENABLED=true` ; sinon, un jeton propriétaire est requis."""
    allowed = service.workspace_count(session) == 0 or ctx.settings.bootstrap_enabled
    if not allowed:
        header = request.headers.get("authorization", "")
        token = header[7:].strip() if header.lower().startswith("bearer ") else ""
        principal = service.resolve_principal(session, token) if token else None
        if principal is None or principal.role != "owner":
            raise Forbidden("création d'espace non autorisée", code="workspace.bootstrap_disabled")
    ws, plain = service.create_workspace(session, body.name, body.slug)
    return WorkspaceCreated(workspace=WorkspaceOut.model_validate(ws), owner_token=plain)


@router.get("/workspaces/current", response_model=WorkspaceOut, tags=["workspaces"])
def current_workspace(p: Principal = Depends(Any_), session: Session = Depends(get_session)) -> WorkspaceOut:
    return WorkspaceOut.model_validate(service.get_workspace(session, p.workspace_id))


@router.patch("/workspaces/current", response_model=WorkspaceOut, tags=["workspaces"])
def update_workspace(body: WorkspaceUpdate, p: Principal = Depends(require_role()), session: Session = Depends(get_session)):
    ws = service.get_workspace(session, p.workspace_id)
    if body.name:
        ws.name = body.name
    return WorkspaceOut.model_validate(ws)


@router.get("/tokens", response_model=list[TokenOut], tags=["workspaces"])
def list_tokens(p: Principal = Depends(require_role()), session: Session = Depends(get_session)):
    return [TokenOut.model_validate(t) for t in service.list_tokens(session, p.workspace_id)]


@router.post("/tokens", response_model=TokenCreated, status_code=201, tags=["workspaces"])
def create_token(body: TokenCreate, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    plain, row = service.create_token(session, p, body)
    return TokenCreated(token=plain, info=TokenOut.model_validate(row))


@router.delete("/tokens/{token_id}", status_code=204, tags=["workspaces"])
def revoke_token(token_id: str, p: Principal = Depends(Write), session: Session = Depends(get_session)) -> Response:
    service.revoke_token(session, p, token_id)
    return Response(status_code=204)


# --- pays ---------------------------------------------------------------------------------------
@router.get("/countries", response_model=list[CountryOut], tags=["workspaces"])
def list_countries(include_archived: bool = False, p: Principal = Depends(Any_), session: Session = Depends(get_session)):
    return [CountryOut.model_validate(c) for c in service.list_countries(session, p.workspace_id, include_archived)]


@router.post("/countries", response_model=CountryOut, status_code=201, tags=["workspaces"])
def create_country(body: CountryCreate, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return CountryOut.model_validate(service.create_country(session, p.workspace_id, body))


@router.get("/countries/{country_id}", response_model=CountryOut, tags=["workspaces"])
def get_country(country_id: str, p: Principal = Depends(Any_), session: Session = Depends(get_session)):
    return CountryOut.model_validate(service.get_country(session, p.workspace_id, country_id))


@router.patch("/countries/{country_id}", response_model=CountryOut, tags=["workspaces"])
def update_country(country_id: str, body: CountryUpdate, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return CountryOut.model_validate(service.update_country(session, p.workspace_id, country_id, body))


@router.post("/countries/{country_id}/archive", response_model=CountryOut, tags=["workspaces"])
def archive_country(country_id: str, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return CountryOut.model_validate(service.archive_country(session, p.workspace_id, country_id))


@router.delete("/countries/{country_id}", status_code=204, tags=["workspaces"])
def delete_country(country_id: str, p: Principal = Depends(Write), session: Session = Depends(get_session)) -> Response:
    service.delete_country(session, p.workspace_id, country_id)
    return Response(status_code=204)


# --- institutions ---------------------------------------------------------------------------------
@router.get("/institutions", response_model=list[InstitutionOut], tags=["workspaces"])
def list_institutions(country_id: str | None = None, include_archived: bool = False,
                      p: Principal = Depends(Any_), session: Session = Depends(get_session)):
    return [InstitutionOut.model_validate(i) for i in service.list_institutions(session, p.workspace_id, country_id, include_archived)]


@router.post("/institutions", response_model=InstitutionOut, status_code=201, tags=["workspaces"])
def create_institution(body: InstitutionCreate, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return InstitutionOut.model_validate(service.create_institution(session, p.workspace_id, body))


@router.get("/institutions/{institution_id}", response_model=InstitutionOut, tags=["workspaces"])
def get_institution(institution_id: str, p: Principal = Depends(Any_), session: Session = Depends(get_session)):
    return InstitutionOut.model_validate(service.get_institution(session, p.workspace_id, institution_id))


@router.patch("/institutions/{institution_id}", response_model=InstitutionOut, tags=["workspaces"])
def update_institution(institution_id: str, body: InstitutionUpdate, p: Principal = Depends(Write),
                       session: Session = Depends(get_session)):
    return InstitutionOut.model_validate(service.update_institution(session, p.workspace_id, institution_id, body))


@router.post("/institutions/{institution_id}/archive", response_model=InstitutionOut, tags=["workspaces"])
def archive_institution(institution_id: str, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return InstitutionOut.model_validate(service.archive_institution(session, p.workspace_id, institution_id))


@router.delete("/institutions/{institution_id}", status_code=204, tags=["workspaces"])
def delete_institution(institution_id: str, p: Principal = Depends(Write), session: Session = Depends(get_session)) -> Response:
    service.delete_institution(session, p.workspace_id, institution_id)
    return Response(status_code=204)
