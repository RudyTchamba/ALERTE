"""Import / export YAML d'un scénario (confort). Destinataires par CODE d'institution, pays par iso2/nom."""
from __future__ import annotations

from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.errors import Unprocessable
from ..workspaces.models import Country, Institution
from . import service
from .models import Inject
from .schemas import DemandIn, InjectCreate, ScenarioCreate

FORMAT = "alerte-scenario"
FORMAT_VERSION = 1
MAX_BYTES = 1_000_000


def export_yaml(session: Session, ws: str, scenario_id: str) -> str:
    sc = service.get_scenario(session, ws, scenario_id)
    codes = {i.id: i.code for i in session.scalars(select(Institution).where(Institution.workspace_id == ws))}
    injects = []
    for inj in service.list_injects(session, ws, scenario_id):
        rec, tags, dem = service._inject_children(session, inj)
        item: dict[str, Any] = {"seq": inj.seq, "sim_time": inj.sim_time, "title": inj.title, "body": inj.body,
                                "from_actor": inj.from_actor, "fault_mode": inj.fault_mode,
                                "recipients": sorted(codes.get(r, r) for r in rec), "tags": tags,
                                "demands": [{"action_code": d.action_code, "justification": d.justification,
                                             "derivation": d.derivation} for d in dem]}
        if inj.system_output is not None:
            item["system_output"] = inj.system_output
        if inj.source_note:
            item["source_note"] = inj.source_note
        injects.append(item)
    doc = {"format": FORMAT, "format_version": FORMAT_VERSION,
           "scenario": {"code": sc.code, "title": sc.title, "description": sc.description, "language": sc.language,
                        "version": sc.version, "country": service.country_label(session, ws, sc.country_id)},
           "injects": injects}
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, default_flow_style=False)


def import_yaml(session: Session, ws: str, text: str | bytes, mandates: Any = None) -> tuple[Any, list[str]]:
    if len(text) > MAX_BYTES:
        raise Unprocessable("fichier YAML trop volumineux", code="scenario.import_too_large")
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise Unprocessable("YAML invalide", code="scenario.import_invalid", details={"error": str(exc)[:200]}) from exc
    if not isinstance(doc, dict) or doc.get("format") != FORMAT or not isinstance(doc.get("scenario"), dict):
        raise Unprocessable(f"format attendu : {FORMAT}", code="scenario.import_invalid")
    warnings: list[str] = []
    s = doc["scenario"]
    country_id = None
    c = s.get("country")
    if c:
        name, iso = (c.get("name"), c.get("iso2")) if isinstance(c, dict) else (c, c)
        row = session.scalar(select(Country).where(Country.workspace_id == ws, (Country.iso2 == iso) | (Country.name == name)))
        if row is None:
            warnings.append(f"pays introuvable dans l'espace, ignoré : {name or iso}")
        else:
            country_id = row.id
    try:
        data = ScenarioCreate(code=s.get("code"), title=s.get("title"), description=s.get("description") or "",
                              language=s.get("language") or "en", version=int(s.get("version") or 1), country_id=country_id)
    except Exception as exc:  # noqa: BLE001 - erreur de validation Pydantic : message utilisateur
        raise Unprocessable("scénario invalide", code="scenario.import_invalid", details={"error": str(exc)[:300]}) from exc
    by_code = {i.code: i.id for i in session.scalars(select(Institution).where(Institution.workspace_id == ws))}
    sc = service.create_scenario(session, ws, data)  # code existant → 409
    for n, item in enumerate(doc.get("injects") or [], 1):
        try:
            rec_ids = []
            for code in item.get("recipients") or []:
                if code in by_code:
                    rec_ids.append(by_code[code])
                else:
                    warnings.append(f"inject {n} : institution inconnue « {code} », destinataire ignoré")
            dem = [DemandIn(**d) for d in item.get("demands") or []]
            payload = InjectCreate(sim_time=str(item.get("sim_time") or ""), title=item.get("title"),
                                   body=item.get("body") or "", from_actor=item.get("from_actor") or "",
                                   fault_mode=item.get("fault_mode") or "none", system_output=item.get("system_output"),
                                   source_note=item.get("source_note"), tags=item.get("tags") or [])
        except Exception as exc:  # noqa: BLE001
            raise Unprocessable(f"inject {n} invalide", code="scenario.import_invalid", details={"error": str(exc)[:300]}) from exc
        inj, _ = service.create_inject(session, ws, sc.id, payload, mandates)
        service.set_recipients(session, ws, inj, rec_ids)
        warnings += [f"inject {n} : {w}" for w in service.set_demands(session, ws, inj, dem, mandates, strict=False)]
    session.flush()
    return sc, list(dict.fromkeys(warnings))


__all__ = ["export_yaml", "import_yaml", "Inject"]
