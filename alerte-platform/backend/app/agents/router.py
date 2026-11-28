from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ..core.auth import Principal, require_role
from ..core.context import AppContext, get_ctx, get_session
from . import service
from .schemas import (
    AgentClone,
    AgentCreate,
    AgentOut,
    AgentUpdate,
    KbGrantsIn,
    ModelProfileCreate,
    ModelProfileOut,
    ModelProfileUpdate,
)

router = APIRouter()
Read = require_role("facilitator", "auditor")
Write = require_role("facilitator")


def _out(session: Session, ws: str, a) -> AgentOut:  # noqa: ANN001
    out = AgentOut.model_validate(a)
    out.kb_ids = service.kb_grants(session, ws, a.id)
    return out


# --- profils de modèle
@router.get("/model-profiles", response_model=list[ModelProfileOut], tags=["agents"])
def list_profiles(p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return [ModelProfileOut.model_validate(x) for x in service.list_profiles(session, p.workspace_id)]


@router.post("/model-profiles", response_model=ModelProfileOut, status_code=201, tags=["agents"])
def create_profile(body: ModelProfileCreate, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return ModelProfileOut.model_validate(service.create_profile(session, p.workspace_id, body))


@router.get("/model-profiles/{profile_id}", response_model=ModelProfileOut, tags=["agents"])
def get_profile(profile_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return ModelProfileOut.model_validate(service.get_profile(session, p.workspace_id, profile_id))


@router.patch("/model-profiles/{profile_id}", response_model=ModelProfileOut, tags=["agents"])
def update_profile(profile_id: str, body: ModelProfileUpdate, p: Principal = Depends(Write),
                   session: Session = Depends(get_session)):
    return ModelProfileOut.model_validate(service.update_profile(session, p.workspace_id, profile_id, body))


@router.delete("/model-profiles/{profile_id}", status_code=204, tags=["agents"])
def delete_profile(profile_id: str, p: Principal = Depends(Write), session: Session = Depends(get_session)) -> Response:
    service.delete_profile(session, p.workspace_id, profile_id)
    return Response(status_code=204)


@router.post("/model-profiles/{profile_id}/test", tags=["agents"])
def test_profile(profile_id: str, p: Principal = Depends(Write), session: Session = Depends(get_session),
                 ctx: AppContext = Depends(get_ctx)):
    return service.test_profile(service.get_profile(session, p.workspace_id, profile_id), ctx.settings, ctx.blobs)


# --- agents
@router.get("/agents", response_model=list[AgentOut], tags=["agents"])
def list_agents(institution_id: str | None = None, role_kind: str | None = None, include_archived: bool = False,
                p: Principal = Depends(Read), session: Session = Depends(get_session)):
    rows = service.list_agents(session, p.workspace_id, institution_id=institution_id, role_kind=role_kind,
                               include_archived=include_archived)
    return [_out(session, p.workspace_id, a) for a in rows]


@router.post("/agents", response_model=AgentOut, status_code=201, tags=["agents"])
def create_agent(body: AgentCreate, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return _out(session, p.workspace_id, service.create_agent(session, p.workspace_id, body))


@router.get("/access-matrix", tags=["agents"])
def access_matrix(include_archived: bool = False, p: Principal = Depends(Read), session: Session = Depends(get_session),
                  ctx: AppContext = Depends(get_ctx)):
    return service.access_matrix(session, p.workspace_id, ctx.services.get("knowledge"), include_archived)


@router.get("/agents/{agent_id}", response_model=AgentOut, tags=["agents"])
def get_agent(agent_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return _out(session, p.workspace_id, service.get_agent(session, p.workspace_id, agent_id))


@router.patch("/agents/{agent_id}", response_model=AgentOut, tags=["agents"])
def update_agent(agent_id: str, body: AgentUpdate, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return _out(session, p.workspace_id, service.update_agent(session, p.workspace_id, agent_id, body))


@router.delete("/agents/{agent_id}", status_code=204, tags=["agents"])
def delete_agent(agent_id: str, p: Principal = Depends(Write), session: Session = Depends(get_session)) -> Response:
    service.delete_agent(session, p.workspace_id, agent_id)
    return Response(status_code=204)


@router.post("/agents/{agent_id}/archive", response_model=AgentOut, tags=["agents"])
def archive_agent(agent_id: str, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return _out(session, p.workspace_id, service.archive_agent(session, p.workspace_id, agent_id))


@router.post("/agents/{agent_id}/clone", response_model=AgentOut, status_code=201, tags=["agents"])
def clone_agent(agent_id: str, body: AgentClone | None = None, p: Principal = Depends(Write),
                session: Session = Depends(get_session)):
    return _out(session, p.workspace_id, service.clone_agent(session, p.workspace_id, agent_id, body or AgentClone()))


@router.put("/agents/{agent_id}/kb-grants", tags=["agents"])
def put_kb_grants(agent_id: str, body: KbGrantsIn, p: Principal = Depends(Write), session: Session = Depends(get_session),
                  ctx: AppContext = Depends(get_ctx)):
    return {"agent_id": agent_id, "kb_ids": service.set_kb_grants(session, p.workspace_id, agent_id, body.kb_ids,
                                                                  ctx.services.get("knowledge"))}


@router.get("/agents/{agent_id}/prompt-preview", tags=["agents"])
def prompt_preview(agent_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session),
                   ctx: AppContext = Depends(get_ctx)):
    return service.prompt_preview(session, p.workspace_id, agent_id, ctx.services)
