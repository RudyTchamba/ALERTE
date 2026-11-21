"""Cas d'usage du module scenarios. Toute requête est filtrée par `workspace_id` (autre espace → 404)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.db import utcnow
from ..core.errors import Conflict, NotFound, Unprocessable
from ..workspaces import service as ws_service
from ..workspaces.models import Country, Institution
from .models import Inject, InjectDemand, InjectRecipient, InjectTag, Scenario
from .schemas import (
    DemandIn,
    InjectCreate,
    InjectOut,
    InjectUpdate,
    ScenarioClone,
    ScenarioCreate,
    ScenarioOut,
    ScenarioUpdate,
)

# --------------------------------------------------------------------------- scénarios


def get_scenario(session: Session, ws: str, scenario_id: str) -> Scenario:
    row = session.scalar(select(Scenario).where(Scenario.id == scenario_id, Scenario.workspace_id == ws))
    if row is None:
        raise NotFound("scénario introuvable", code="scenario.not_found")
    return row


def _editable(row: Scenario) -> Scenario:
    if row.archived_at is not None or row.status == "archived":
        raise Conflict("scénario archivé : non modifiable", code="scenario.archived")
    return row


def scenario_out(session: Session, row: Scenario) -> ScenarioOut:
    out = ScenarioOut.model_validate(row)
    out.inject_count = session.scalar(select(func.count()).select_from(Inject).where(Inject.scenario_id == row.id)) or 0
    return out


def list_scenarios(session: Session, ws: str, include_archived: bool = False) -> list[Scenario]:
    q = select(Scenario).where(Scenario.workspace_id == ws).order_by(Scenario.code)
    if not include_archived:
        q = q.where(Scenario.archived_at.is_(None))
    return list(session.scalars(q))


def _check_country(session: Session, ws: str, country_id: str | None) -> None:
    if country_id:
        ws_service.get_country(session, ws, country_id)


def create_scenario(session: Session, ws: str, data: ScenarioCreate) -> Scenario:
    _check_country(session, ws, data.country_id)
    row = Scenario(workspace_id=ws, **data.model_dump())
    session.add(row)
    try:
        session.flush()
    except IntegrityError as exc:
        raise Conflict("un scénario de ce code existe déjà", code="scenario.duplicate") from exc
    return row


def update_scenario(session: Session, ws: str, scenario_id: str, data: ScenarioUpdate, lint_fn: Any = None) -> Scenario:
    row = _editable(get_scenario(session, ws, scenario_id))
    ch = data.model_dump(exclude_unset=True)
    if "country_id" in ch:
        _check_country(session, ws, ch["country_id"])
    if ch.get("status") == "ready" and lint_fn is not None:
        errors = [i for i in lint_fn(session, ws, scenario_id)["issues"] if i["severity"] == "error"]
        if errors:
            raise Unprocessable("le scénario a des erreurs de lint : impossible de le déclarer prêt",
                                code="scenario.lint_errors", details={"errors": errors})
    for k, v in ch.items():
        if v is None and k in ("code", "title", "description", "language", "version", "status", "is_template"):
            continue
        setattr(row, k, v)
    try:
        session.flush()
    except IntegrityError as exc:
        raise Conflict("un scénario de ce code existe déjà", code="scenario.duplicate") from exc
    return row


def archive_scenario(session: Session, ws: str, scenario_id: str) -> Scenario:
    row = get_scenario(session, ws, scenario_id)
    row.status, row.archived_at = "archived", row.archived_at or utcnow()
    return row


def delete_scenario(session: Session, ws: str, scenario_id: str) -> None:
    row = get_scenario(session, ws, scenario_id)
    if ws_service.is_referenced(session, "scenario", scenario_id):
        raise Conflict("ce scénario est utilisé par un exercice : archivez-le", code="scenario.in_use")
    for inj in list(session.scalars(select(Inject).where(Inject.scenario_id == scenario_id))):
        _delete_inject_rows(session, inj)
    session.flush()
    session.delete(row)


# --------------------------------------------------------------------------- injects


def _inject_children(session: Session, inj: Inject) -> tuple[list[str], list[str], list[InjectDemand]]:
    rec = list(session.scalars(select(InjectRecipient.institution_id).where(InjectRecipient.inject_id == inj.id)
                               .order_by(InjectRecipient.institution_id)))
    tags = list(session.scalars(select(InjectTag.tag).where(InjectTag.inject_id == inj.id).order_by(InjectTag.tag)))
    dem = list(session.scalars(select(InjectDemand).where(InjectDemand.inject_id == inj.id).order_by(InjectDemand.position)))
    return rec, tags, dem


def inject_out(session: Session, inj: Inject, warnings: list[str] | None = None) -> InjectOut:
    rec, tags, dem = _inject_children(session, inj)
    return InjectOut(id=inj.id, scenario_id=inj.scenario_id, seq=inj.seq, sim_time=inj.sim_time, title=inj.title,
                     body=inj.body, from_actor=inj.from_actor, fault_mode=inj.fault_mode, system_output=inj.system_output,
                     source_note=inj.source_note, recipients=rec, tags=tags, warnings=warnings or [],
                     demands=[{"action_code": d.action_code, "justification": d.justification, "derivation": d.derivation}
                              for d in dem])


def get_inject(session: Session, ws: str, inject_id: str) -> Inject:
    row = session.scalar(select(Inject).where(Inject.id == inject_id, Inject.workspace_id == ws))
    if row is None:
        raise NotFound("inject introuvable", code="inject.not_found")
    return row


def list_injects(session: Session, ws: str, scenario_id: str) -> list[Inject]:
    get_scenario(session, ws, scenario_id)
    return list(session.scalars(select(Inject).where(Inject.scenario_id == scenario_id, Inject.workspace_id == ws)
                                .order_by(Inject.seq)))


def _renumber(session: Session, scenario_id: str) -> None:
    rows = list(session.scalars(select(Inject).where(Inject.scenario_id == scenario_id).order_by(Inject.seq, Inject.created_at)))
    for i, r in enumerate(rows, 1):
        r.seq = i
    session.flush()


def set_recipients(session: Session, ws: str, inj: Inject, institution_ids: list[str]) -> None:
    ids = list(dict.fromkeys(institution_ids))
    for i in ids:
        ws_service.get_institution(session, ws, i)  # autre espace → 404
    session.execute(delete(InjectRecipient).where(InjectRecipient.inject_id == inj.id))
    session.flush()
    for i in ids:
        session.add(InjectRecipient(inject_id=inj.id, institution_id=i))
    session.flush()


def set_tags(session: Session, inj: Inject, tags: list[str]) -> None:
    session.execute(delete(InjectTag).where(InjectTag.inject_id == inj.id))
    session.flush()
    for t in dict.fromkeys(tags):
        session.add(InjectTag(inject_id=inj.id, tag=t))
    session.flush()


def set_demands(session: Session, ws: str, inj: Inject, demands: list[DemandIn], mandates: Any = None,
                strict: bool = True) -> list[str]:
    """Remplace les demandes. Avec le service mandates : action inconnue → 422 (strict) ; sans : avertissement."""
    warnings: list[str] = []
    if mandates is None or not hasattr(mandates, "action_exists"):
        if demands:
            warnings.append("catalogue d'actions indisponible : les actions n'ont pas été vérifiées")
    else:
        for d in demands:
            if not mandates.action_exists(session, ws, d.action_code):
                if strict:
                    raise Unprocessable(f"action inconnue du catalogue : {d.action_code}", code="inject.unknown_action",
                                        details={"action_code": d.action_code})
                warnings.append(f"action inconnue du catalogue : {d.action_code}")
    session.execute(delete(InjectDemand).where(InjectDemand.inject_id == inj.id))
    session.flush()
    for pos, d in enumerate(demands):
        session.add(InjectDemand(inject_id=inj.id, action_code=d.action_code, justification=d.justification,
                                 derivation=d.derivation, position=pos))
    session.flush()
    return warnings


def create_inject(session: Session, ws: str, scenario_id: str, data: InjectCreate, mandates: Any = None) -> tuple[Inject, list[str]]:
    sc = _editable(get_scenario(session, ws, scenario_id))
    n = session.scalar(select(func.count()).select_from(Inject).where(Inject.scenario_id == sc.id)) or 0
    seq = min(data.seq or n + 1, n + 1)
    for other in session.scalars(select(Inject).where(Inject.scenario_id == sc.id, Inject.seq >= seq)):
        other.seq += 1
    session.flush()
    inj = Inject(workspace_id=ws, scenario_id=sc.id, seq=seq, **data.model_dump(include={
        "sim_time", "title", "body", "from_actor", "fault_mode", "system_output", "source_note"}))
    session.add(inj)
    session.flush()
    set_recipients(session, ws, inj, data.recipients)
    set_tags(session, inj, data.tags)
    warnings = set_demands(session, ws, inj, data.demands, mandates)
    return inj, warnings


def update_inject(session: Session, ws: str, inject_id: str, data: InjectUpdate) -> Inject:
    inj = get_inject(session, ws, inject_id)
    _editable(get_scenario(session, ws, inj.scenario_id))
    ch = data.model_dump(exclude_unset=True)
    tags = ch.pop("tags", None)
    for k, v in ch.items():
        if v is None and k not in ("system_output", "source_note"):
            continue
        setattr(inj, k, v)
    if tags is not None:
        set_tags(session, inj, tags)
    session.flush()
    return inj


def _delete_inject_rows(session: Session, inj: Inject) -> None:
    for model in (InjectRecipient, InjectTag, InjectDemand):
        session.execute(delete(model).where(model.inject_id == inj.id))
    session.flush()
    session.delete(inj)


def delete_inject(session: Session, ws: str, inject_id: str) -> None:
    inj = get_inject(session, ws, inject_id)
    _editable(get_scenario(session, ws, inj.scenario_id))
    sid = inj.scenario_id
    _delete_inject_rows(session, inj)
    session.flush()
    _renumber(session, sid)


def reorder_injects(session: Session, ws: str, scenario_id: str, ids: list[str]) -> list[Inject]:
    sc = _editable(get_scenario(session, ws, scenario_id))
    rows = {r.id: r for r in list_injects(session, ws, sc.id)}
    if len(ids) != len(set(ids)) or set(ids) != set(rows):
        raise Unprocessable("l'ordre doit être une permutation exacte des injects du scénario", code="scenario.bad_order",
                            details={"expected": sorted(rows)})
    for i, iid in enumerate(ids, 1):
        rows[iid].seq = i
    session.flush()
    return [rows[i] for i in ids]


# --------------------------------------------------------------------------- clone


def clone_scenario(session: Session, ws: str, scenario_id: str, data: ScenarioClone) -> Scenario:
    src = get_scenario(session, ws, scenario_id)
    existing = set(session.scalars(select(Scenario.code).where(Scenario.workspace_id == ws)))
    code, n = data.code, 1
    if not code:
        code = f"{src.code}-copy"
        while code in existing:
            n += 1
            code = f"{src.code}-copy{n}"
    new = create_scenario(session, ws, ScenarioCreate(code=code, title=data.title or f"{src.title} (copy)",
                                                      description=src.description, language=src.language,
                                                      country_id=src.country_id))
    new.cloned_from_id = src.id
    for inj in list_injects(session, ws, src.id):
        rec, tags, dem = _inject_children(session, inj)
        c = Inject(workspace_id=ws, scenario_id=new.id, seq=inj.seq, sim_time=inj.sim_time, title=inj.title, body=inj.body,
                   from_actor=inj.from_actor, fault_mode=inj.fault_mode, system_output=inj.system_output,
                   source_note=inj.source_note)
        session.add(c)
        session.flush()
        for r in rec:
            session.add(InjectRecipient(inject_id=c.id, institution_id=r))
        for t in tags:
            session.add(InjectTag(inject_id=c.id, tag=t))
        for d in dem:
            session.add(InjectDemand(inject_id=c.id, action_code=d.action_code, justification=d.justification,
                                     derivation=d.derivation, position=d.position))
    session.flush()
    return new


# --------------------------------------------------------------------------- lint / readiness

ROUNDS, STEPS = 2, 4  # doc 08 §8.9 n°9 : injects × destinataires × tours × pas


def _action_exists(mandates: Any, session: Session, ws: str, code: str) -> bool | None:
    if mandates is None or not hasattr(mandates, "action_exists"):
        return None
    return bool(mandates.action_exists(session, ws, code))


def lint(session: Session, ws: str, scenario_id: str, mandates: Any = None, max_llm_calls: int = 199) -> dict[str, Any]:
    from .faults import MIN_FAULT_MODES, VALID_FAULT_MODES
    sc = get_scenario(session, ws, scenario_id)
    injects = list_injects(session, ws, scenario_id)
    q = select(Institution).where(Institution.workspace_id == ws, Institution.archived_at.is_(None))
    if sc.country_id:
        q = q.where(Institution.country_id == sc.country_id)
    active = {i.id for i in session.scalars(q)}
    known = {i.id: i for i in session.scalars(select(Institution).where(Institution.workspace_id == ws))}
    issues: list[dict[str, Any]] = []

    def add(sev: str, code: str, msg: str, inj: Inject | None = None, **extra: Any) -> None:
        issues.append({"severity": sev, "code": code, "message": msg, "inject_id": inj.id if inj else None,
                       "seq": inj.seq if inj else None, **extra})

    if not injects:
        add("error", "scenario.no_injects", "le scénario ne contient aucun inject")
    checked_actions = False
    est_max, faults, recipients_total = 0, set(), 0
    for inj in injects:
        rec, _tags, dem = _inject_children(session, inj)
        recipients_total += len(rec)
        est_max += len(rec) * ROUNDS * STEPS
        if not rec:
            add("error", "inject.no_recipient", f"inject {inj.seq} sans destinataire", inj)
        for r in rec:
            if r not in known:
                add("error", "inject.unknown_recipient", f"inject {inj.seq} : destinataire inconnu", inj, institution_id=r)
            elif known[r].archived_at is not None:
                add("error", "inject.unknown_recipient", f"inject {inj.seq} : institution archivée ({known[r].code})", inj, institution_id=r)
        if len(active) >= 2 and rec and active <= set(rec):
            add("warning", "inject.all_recipients", f"inject {inj.seq} adressé à toutes les institutions : "
                "inégalité d'information impossible à observer (tous reçoivent la même chose)", inj)
        for d in dem:
            ok = _action_exists(mandates, session, ws, d.action_code)
            if ok is None:
                checked_actions = checked_actions or False
            elif not ok:
                add("error", "inject.unknown_action", f"inject {inj.seq} : action inconnue « {d.action_code} »", inj,
                    action_code=d.action_code)
        if dem and (mandates is None or not hasattr(mandates, "action_exists")) and not checked_actions:
            add("warning", "scenario.actions_unchecked", "catalogue d'actions indisponible : demandes non vérifiées")
            checked_actions = True
        if inj.fault_mode not in VALID_FAULT_MODES:
            add("error", "inject.unknown_fault_mode", f"inject {inj.seq} : mode de panne inconnu « {inj.fault_mode} »", inj)
        elif inj.fault_mode != "none":
            faults.add(inj.fault_mode)
        if not inj.body.strip():
            add("warning", "inject.empty_body", f"inject {inj.seq} sans texte", inj)
    if injects and len(faults) < MIN_FAULT_MODES:
        add("warning", "scenario.few_fault_modes", f"{len(faults)} mode(s) de panne distinct(s) ; au moins {MIN_FAULT_MODES} "
            "recommandés pour couvrir les défaillances")
    if est_max > max_llm_calls:
        add("warning", "scenario.budget_estimate",  # bloquant seulement dans la readiness (> plafond × 1,5)
            
            f"estimation maximale de {est_max} appels LLM (plafond {max_llm_calls})")
    return {"scenario_id": scenario_id, "ok": not any(i["severity"] == "error" for i in issues), "issues": issues,
            "stats": {"injects": len(injects), "recipients_total": recipients_total, "fault_modes": sorted(faults),
                      "distinct_fault_modes": len(faults),
                      "estimated_llm_calls": {"max": est_max, "typical": recipients_total * 2 * 2, "cap": max_llm_calls,
                                              "formula": f"injects × destinataires × {ROUNDS} tours × {STEPS} pas"}}}


def readiness_checks(session: Session, ws: str, scenario_id: str, mandates: Any = None, max_llm_calls: int = 199) -> list[dict[str, Any]]:
    """Contrôles d'Exercise Readiness portés par le scénario (doc 08 §8.9 n°4 et n°9)."""
    rep = lint(session, ws, scenario_id, mandates, max_llm_calls)
    iss = rep["issues"]

    def pick(*codes: str) -> list[dict[str, Any]]:
        return [i for i in iss if i["code"] in codes]

    est = rep["stats"]["estimated_llm_calls"]
    over = est["max"] > max_llm_calls
    bad_budget = est["max"] > max_llm_calls * 1.5
    return [
        {"id": "scenario.has_injects", "readiness_check": 4, "level": "blocking", "ok": not pick("scenario.no_injects"),
         "message": "le scénario contient des injects", "details": pick("scenario.no_injects")},
        {"id": "scenario.recipients", "readiness_check": 4, "level": "blocking",
         "ok": not pick("inject.no_recipient", "inject.unknown_recipient"),
         "message": "chaque inject a ≥ 1 destinataire existant", "details": pick("inject.no_recipient", "inject.unknown_recipient")},
        {"id": "scenario.actions", "readiness_check": 4, "level": "blocking", "ok": not pick("inject.unknown_action"),
         "message": "chaque demande référence une action du catalogue", "details": pick("inject.unknown_action")},
        {"id": "scenario.fault_modes", "readiness_check": 4, "level": "blocking", "ok": not pick("inject.unknown_fault_mode"),
         "message": "modes de panne valides", "details": pick("inject.unknown_fault_mode")},
        {"id": "scenario.information_equality", "readiness_check": 4, "level": "warning", "ok": not pick("inject.all_recipients"),
         "message": "aucun inject adressé à toutes les institutions", "details": pick("inject.all_recipients")},
        {"id": "scenario.budget", "readiness_check": 9, "level": "blocking" if bad_budget else "warning", "ok": not over,
         "message": f"budget estimé {est['max']} appels pour un plafond de {max_llm_calls}", "details": [est]},
    ]


# --------------------------------------------------------------------------- snapshot


def export_snapshot(session: Session, ws: str, scenario_id: str, mandates: Any = None) -> dict[str, Any]:
    """Partie `scenario` du snapshot d'exercice (CONTRACTS.md)."""
    sc = get_scenario(session, ws, scenario_id)
    deriv: dict[str, str] = {}
    if mandates is not None and hasattr(mandates, "list_actions"):
        deriv = {a["code"]: a.get("derivation", "") for a in mandates.list_actions(session, ws)}
    out = []
    for inj in list_injects(session, ws, scenario_id):
        rec, tags, dem = _inject_children(session, inj)
        out.append({"inject_ref": f"inj-{inj.seq:03d}", "seq": inj.seq, "sim_time": inj.sim_time, "title": inj.title,
                    "body": inj.body, "from_actor": inj.from_actor, "recipients": rec, "tags": tags,
                    "demands": [{"action_code": d.action_code, "derivation": deriv.get(d.action_code) or d.derivation,
                                 "justification": d.justification} for d in dem],
                    "fault_mode": inj.fault_mode, "system_output": inj.system_output})
    return {"id": sc.id, "code": sc.code, "title": sc.title, "language": sc.language, "injects": out}


def country_label(session: Session, ws: str, country_id: str | None) -> dict[str, Any] | None:
    if not country_id:
        return None
    c = session.scalar(select(Country).where(Country.id == country_id, Country.workspace_id == ws))
    return None if c is None else {"iso2": c.iso2, "name": c.name}
