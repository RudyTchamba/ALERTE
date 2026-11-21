from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from ..core.auth import Principal, require_role
from ..core.context import AppContext, get_ctx, get_session
from ..core.errors import Unprocessable
from . import service, yamlio
from .faults import FAULT_MODES
from .schemas import (
    DemandsIn,
    InjectCreate,
    InjectOut,
    InjectUpdate,
    OrderIn,
    RecipientsIn,
    ScenarioClone,
    ScenarioCreate,
    ScenarioOut,
    ScenarioUpdate,
)

router = APIRouter()
Read = require_role("facilitator", "auditor", "observer")
Write = require_role("facilitator")


def _mand(ctx: AppContext):  # noqa: ANN202
    return ctx.services.get("mandates")


def _lint_fn(ctx: AppContext):  # noqa: ANN202
    return lambda s, ws, sid: service.lint(s, ws, sid, _mand(ctx), ctx.settings.max_llm_calls)


@router.get("/fault-modes", tags=["scenarios"])
def fault_modes(p: Principal = Depends(Read)):
    return FAULT_MODES


@router.get("/scenarios", response_model=list[ScenarioOut], tags=["scenarios"])
def list_scenarios(include_archived: bool = False, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return [service.scenario_out(session, s) for s in service.list_scenarios(session, p.workspace_id, include_archived)]


@router.post("/scenarios", response_model=ScenarioOut, status_code=201, tags=["scenarios"])
def create_scenario(body: ScenarioCreate, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return service.scenario_out(session, service.create_scenario(session, p.workspace_id, body))


@router.post("/scenarios/import", response_model=dict, status_code=201, tags=["scenarios"])
async def import_scenario(request: Request, p: Principal = Depends(Write), session: Session = Depends(get_session),
                          ctx: AppContext = Depends(get_ctx)):
    raw = await request.body()
    if not raw.strip():
        raise Unprocessable("corps YAML vide", code="scenario.import_invalid")
    sc, warnings = yamlio.import_yaml(session, p.workspace_id, raw.decode("utf-8", errors="replace"), _mand(ctx))
    return {"scenario": service.scenario_out(session, sc).model_dump(), "warnings": warnings}


@router.get("/scenarios/{scenario_id}", response_model=ScenarioOut, tags=["scenarios"])
def get_scenario(scenario_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return service.scenario_out(session, service.get_scenario(session, p.workspace_id, scenario_id))


@router.patch("/scenarios/{scenario_id}", response_model=ScenarioOut, tags=["scenarios"])
def update_scenario(scenario_id: str, body: ScenarioUpdate, p: Principal = Depends(Write),
                    session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)):
    row = service.update_scenario(session, p.workspace_id, scenario_id, body, _lint_fn(ctx))
    return service.scenario_out(session, row)


@router.delete("/scenarios/{scenario_id}", status_code=204, tags=["scenarios"])
def delete_scenario(scenario_id: str, p: Principal = Depends(Write), session: Session = Depends(get_session)) -> Response:
    service.delete_scenario(session, p.workspace_id, scenario_id)
    return Response(status_code=204)


@router.post("/scenarios/{scenario_id}/archive", response_model=ScenarioOut, tags=["scenarios"])
def archive_scenario(scenario_id: str, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return service.scenario_out(session, service.archive_scenario(session, p.workspace_id, scenario_id))


@router.post("/scenarios/{scenario_id}/clone", response_model=ScenarioOut, status_code=201, tags=["scenarios"])
def clone_scenario(scenario_id: str, body: ScenarioClone | None = None, p: Principal = Depends(Write),
                   session: Session = Depends(get_session)):
    return service.scenario_out(session, service.clone_scenario(session, p.workspace_id, scenario_id, body or ScenarioClone()))


@router.get("/scenarios/{scenario_id}/lint", tags=["scenarios"])
def lint(scenario_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session),
         ctx: AppContext = Depends(get_ctx)):
    return service.lint(session, p.workspace_id, scenario_id, _mand(ctx), ctx.settings.max_llm_calls)


@router.get("/scenarios/{scenario_id}/export.yaml", tags=["scenarios"])
def export_yaml(scenario_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return Response(yamlio.export_yaml(session, p.workspace_id, scenario_id), media_type="application/yaml; charset=utf-8")


@router.get("/scenarios/{scenario_id}/injects", response_model=list[InjectOut], tags=["scenarios"])
def list_injects(scenario_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return [service.inject_out(session, i) for i in service.list_injects(session, p.workspace_id, scenario_id)]


@router.post("/scenarios/{scenario_id}/injects", response_model=InjectOut, status_code=201, tags=["scenarios"])
def create_inject(scenario_id: str, body: InjectCreate, p: Principal = Depends(Write),
                  session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)):
    inj, warnings = service.create_inject(session, p.workspace_id, scenario_id, body, _mand(ctx))
    return service.inject_out(session, inj, warnings)


@router.put("/scenarios/{scenario_id}/injects/order", response_model=list[InjectOut], tags=["scenarios"])
def reorder(scenario_id: str, body: OrderIn, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return [service.inject_out(session, i) for i in service.reorder_injects(session, p.workspace_id, scenario_id, body.inject_ids)]


@router.get("/injects/{inject_id}", response_model=InjectOut, tags=["scenarios"])
def get_inject(inject_id: str, p: Principal = Depends(Read), session: Session = Depends(get_session)):
    return service.inject_out(session, service.get_inject(session, p.workspace_id, inject_id))


@router.patch("/injects/{inject_id}", response_model=InjectOut, tags=["scenarios"])
def update_inject(inject_id: str, body: InjectUpdate, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    return service.inject_out(session, service.update_inject(session, p.workspace_id, inject_id, body))


@router.delete("/injects/{inject_id}", status_code=204, tags=["scenarios"])
def delete_inject(inject_id: str, p: Principal = Depends(Write), session: Session = Depends(get_session)) -> Response:
    service.delete_inject(session, p.workspace_id, inject_id)
    return Response(status_code=204)


@router.put("/injects/{inject_id}/recipients", response_model=InjectOut, tags=["scenarios"])
def put_recipients(inject_id: str, body: RecipientsIn, p: Principal = Depends(Write), session: Session = Depends(get_session)):
    inj = service.get_inject(session, p.workspace_id, inject_id)
    service._editable(service.get_scenario(session, p.workspace_id, inj.scenario_id))
    service.set_recipients(session, p.workspace_id, inj, body.institution_ids)
    return service.inject_out(session, inj)


@router.put("/injects/{inject_id}/demands", response_model=InjectOut, tags=["scenarios"])
def put_demands(inject_id: str, body: DemandsIn, p: Principal = Depends(Write), session: Session = Depends(get_session),
                ctx: AppContext = Depends(get_ctx)):
    inj = service.get_inject(session, p.workspace_id, inject_id)
    service._editable(service.get_scenario(session, p.workspace_id, inj.scenario_id))
    warnings = service.set_demands(session, p.workspace_id, inj, body.demands, _mand(ctx))
    return service.inject_out(session, inj, warnings)
