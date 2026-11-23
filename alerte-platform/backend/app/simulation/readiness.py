"""Exercise Readiness (doc 08 §8.9) : contrôles bloquants / avertissements / informations avant lancement."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..core.errors import NotFound
from .common import NON_ACTIVATABLE_ROLES, optional_svc
from .models import Exercise, Seat
from .snapshot import effective_profile

BLOCKING, WARNING, INFO = "blocking", "warning", "info"
DEFAULT_MAX_STEPS = 4
ROUNDS = 2


def _chk(out: list[dict], level: str, code: str, message: str, subject: str | None = None) -> None:
    out.append({"level": level, "code": code, "message": message, "subject": subject})


def compute_readiness(ctx: Any, session: Session, ex: Exercise, seats: list[Seat]) -> dict[str, Any]:
    out: list[dict] = []
    ws = ex.workspace_id
    svcs = {n: optional_svc(ctx, n) for n in ("agents", "scenarios", "mandates", "knowledge", "workspaces")}
    for name, s in svcs.items():
        if s is None:
            _chk(out, BLOCKING, "service.unavailable", f"service '{name}' non enregistré", name)
    if any(s is None for s in svcs.values()):
        return _result(out)
    agents, scenarios, mandates, knowledge, workspaces = (svcs[k] for k in
                                                          ("agents", "scenarios", "mandates", "knowledge", "workspaces"))
    # 1/12 sièges ----------------------------------------------------------------------------
    if not seats:
        _chk(out, BLOCKING, "seats.none", "aucun siège défini")
    institutions: dict[str, Any] = {}
    snaps: dict[str, dict] = {}
    for s in seats:
        try:
            institutions[s.institution_id] = workspaces.get_institution(session, ws, s.institution_id)
        except NotFound:
            _chk(out, BLOCKING, "seat.institution_missing", "institution introuvable", s.code)
        if s.controller not in ("agent", "human", "scripted"):
            _chk(out, BLOCKING, "seat.no_controller", "siège sans contrôleur valide", s.code)
        if s.controller in ("agent", "scripted") and not s.agent_id:
            _chk(out, BLOCKING, "seat.no_controller", "contrôleur agent sans agent affecté", s.code)
        if s.controller == "human" and not (s.human_name or "").strip():
            _chk(out, BLOCKING, "seat.human_unnamed", "siège humain sans humain nommé", s.code)
        if s.controller == "human" and not s.agent_id:
            _chk(out, WARNING, "seat.human_no_agent", "siège humain sans agent : pas de recherche KB ni de reprise", s.code)
        if s.agent_id:
            try:
                snaps[s.agent_id] = agents.export_agent_snapshot(session, ws, s.agent_id)
            except NotFound:
                _chk(out, BLOCKING, "agent.missing", "agent introuvable", s.code)
    # 2 fournisseur --------------------------------------------------------------------------
    if ex.ai_mode == "scripted":
        _chk(out, INFO, "provider.scripted", "fournisseur scripted explicitement choisi : exercice SANS IA")
    for s in seats:
        a = snaps.get(s.agent_id or "")
        if not a:
            continue
        prof = effective_profile(ctx, ex, a.get("model_profile")) or {}
        if ex.ai_mode == "ai":
            if not prof.get("provider") or not prof.get("model"):
                _chk(out, BLOCKING, "agent.no_model_profile", "profil de modèle invalide", s.code)
            elif prof.get("provider") in ("scripted", "cassette"):
                _chk(out, BLOCKING, "provider.not_ai", "fournisseur de test incompatible avec ai_mode=ai", s.code)
            elif hasattr(agents, "test_model_profile"):
                try:
                    ok = agents.test_model_profile(session, ws, s.agent_id)
                except Exception as exc:  # noqa: BLE001
                    ok, _ = False, exc
                if not ok:
                    _chk(out, BLOCKING, "provider.test_failed", "l'appel de test du modèle a échoué", s.code)
    # 3 KB -----------------------------------------------------------------------------------
    all_kbs: set[str] = set()
    for s in seats:
        if not s.agent_id or s.agent_id not in snaps:
            continue
        grants = list(agents.kb_grants(session, ws, s.agent_id))
        if (snaps[s.agent_id].get("role_kind") or "institution") not in NON_ACTIVATABLE_ROLES and not grants:
            _chk(out, BLOCKING, "agent.no_kb_grant", "agent sans base de connaissances accordée", s.code)
        all_kbs.update(grants)
    versions: set[str] = set()
    for kb in sorted(all_kbs):
        v = knowledge.published_document_version_ids(session, ws, [kb])
        if not v:
            _chk(out, BLOCKING, "kb.not_ready", "KB sans version publiée", kb)
        versions |= set(v)
    # 4/5 scénario ---------------------------------------------------------------------------
    scen: dict = {}
    try:
        scen = scenarios.export_scenario_snapshot(session, ws, ex.scenario_id)
    except NotFound:
        _chk(out, BLOCKING, "scenario.missing", "scénario introuvable")
    injects = scen.get("injects", []) if scen else []
    if scen and not injects:
        _chk(out, BLOCKING, "scenario.no_inject", "scénario sans inject")
    seat_inst = {s.institution_id for s in seats}
    for i in injects:
        ref = i.get("inject_ref", "?")
        rec = i.get("recipients", [])
        if not rec:
            _chk(out, BLOCKING, "inject.no_recipient", "inject sans destinataire", ref)
        for r in rec:
            try:
                rinst = workspaces.get_institution(session, ws, r)
            except NotFound:
                _chk(out, BLOCKING, "inject.unknown_recipient", f"destinataire inexistant : {r}", ref)
                continue
            if r not in seat_inst:
                _chk(out, BLOCKING, "inject.recipient_without_seat", f"destinataire sans siège : {getattr(rinst, 'code', r)}", ref)
        for d in i.get("demands", []):
            if d.get("action_code") and not mandates.action_exists(session, ws, d["action_code"]):
                _chk(out, BLOCKING, "inject.unknown_action", f"action inconnue : {d['action_code']}", ref)
    if scen and hasattr(scenarios, "readiness_scenario_checks"):
        cap_ex = int(ex.settings.get("max_llm_calls") or ctx.settings.max_llm_calls)  # le budget de l'EXERCICE prime sur le défaut serveur
        for c in scenarios.readiness_scenario_checks(session, ws, ex.scenario_id, cap_ex):
            if c.get("ok") is True:  # `scenarios` renvoie aussi les contrôles réussis ; seuls les échecs comptent
                continue
            _chk(out, c.get("level", WARNING), c.get("code") or c.get("id", "scenario.check"), c.get("message", ""),
                 c.get("subject"))
    # 6/7 mandats ----------------------------------------------------------------------------
    inst_ids = sorted(seat_inst & set(institutions))
    if inst_ids:
        active = mandates.export_active_mandates(session, ws, inst_ids, sorted(versions))
        have = {m.get("institution_id") for m in active}
        for iid in inst_ids:
            if iid not in have:
                _chk(out, WARNING, "institution.no_mandates", "aucun mandat validé : l'agent n'aura aucune base",
                     institutions[iid].code)
            if str(mandates.registry_state(session, ws, iid)) != "reviewed_complete":
                _chk(out, WARNING, "registry.not_reviewed",
                     "registre non 'reviewed_complete' : les lacunes seront rétrogradées", institutions[iid].code)
    # 9 budget -------------------------------------------------------------------------------
    cap = int(ex.settings.get("max_llm_calls") or ctx.settings.max_llm_calls)
    est = 0
    for i in injects:
        n_seats = sum(1 for s in seats if s.institution_id in i.get("recipients", []) and s.controller != "human"
                      and (snaps.get(s.agent_id or "", {}).get("role_kind") or "institution") not in NON_ACTIVATABLE_ROLES)
        steps = min([(snaps[s.agent_id].get("limits") or {}).get("max_steps", DEFAULT_MAX_STEPS)
                     for s in seats if s.agent_id in snaps] or [DEFAULT_MAX_STEPS])
        est += n_seats * ROUNDS * steps
    if est > cap * 1.5:
        _chk(out, BLOCKING, "budget.exceeds", f"appels estimés {est} > 1,5 x plafond {cap}")
    elif est > cap:
        _chk(out, WARNING, "budget.high", f"appels estimés {est} > plafond {cap}")
    # 8/10 documents -------------------------------------------------------------------------
    if all_kbs and hasattr(knowledge, "coverage"):
        cov = knowledge.coverage(session, ws, sorted(all_kbs))
        if cov.get("ratio") is not None and cov["ratio"] < 1:
            _chk(out, WARNING, "kb.coverage", f"couverture documentaire incomplète : {cov.get('missing')}")
    if hasattr(knowledge, "document_meta"):
        for v in sorted(versions):
            meta = knowledge.document_meta(session, v) or {}
            if meta.get("redistribution") == "unknown":
                _chk(out, INFO, "document.redistribution_unknown", "redistribution inconnue", v)
    res = _result(out)
    res["estimated_llm_calls"] = est
    res["llm_call_cap"] = cap
    return res


def _result(out: list[dict]) -> dict[str, Any]:
    return {"ok": not any(c["level"] == BLOCKING for c in out),
            "blocking": [c for c in out if c["level"] == BLOCKING],
            "warnings": [c for c in out if c["level"] == WARNING],
            "info": [c for c in out if c["level"] == INFO]}
