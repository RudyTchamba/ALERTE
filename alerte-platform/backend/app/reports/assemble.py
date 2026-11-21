"""Assemblage du contenu JSON structuré d'un rapport (doc 09 §9.10) : fonction PURE (aucun accès base/service).

Principes : constats ≠ hypothèses ; « non évalué »/« non calculé » ≠ 0 ; toute absence est formulée « non trouvée dans le
corpus K (couverture c %) » ; recommandations (plan) ≠ observations ; étiquette SANS IA / REJEU quand `ai_mode != ai`."""
from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Any

SCHEMA = "alerte.report/1"
GENERATOR_VERSION = "reports-1.0"
ABSENCE_CODES = {"G1", "G3", "G6", "G7", "G8", "G9", "G10"}
MIN_JURISDICTIONS = 2
AI_LABELS = {"scripted": "SANS IA", "cassette": "REJEU"}
SEVERITY_LABEL = {3: "risque pour la vie ou les droits", 2: "retard, surcoût ou mauvaise coordination", 1: "gêne"}
METRIC_ORDER = ("T1", "T2", "T3", "T4", "T5", "T6")
EVIDENCE_LEVELS = {
    "documented": "documenté : règle + registre revu + recherche négative sans contre-preuve",
    "observed": "observé : signal du coordinateur en simulation",
    "inferred": "inféré : règle sur registre incomplet/proposé, ou signal seul",
    "hypothesis": "hypothèse : proposée par un agent seul, non confirmée",
}


def jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, (dt.datetime, dt.date)):
        return obj.isoformat()
    if isinstance(obj, float) and obj != obj:  # NaN
        return None
    return obj


def ai_label(ai_mode: str | None) -> str | None:
    if ai_mode == "ai":
        return None
    return AI_LABELS.get(ai_mode or "", "MODE IA NON DÉTERMINÉ")


def pct(v: float | None) -> str:
    return "non renseignée" if v is None else f"{round(v * 100)} %"


def absence_statement(g: dict[str, Any]) -> str | None:
    """« non trouvée dans le corpus K (couverture c %) » — avec réserve si le registre n'est pas entièrement revu."""
    negs = g.get("negative_searches") or []
    if g.get("code") not in ABSENCE_CODES and not negs:
        return None
    docs = next((n.get("corpus_documents") for n in negs if n.get("corpus_documents") is not None), None)
    cov = next((n.get("corpus_coverage") for n in negs if n.get("corpus_coverage") is not None), g.get("corpus_coverage"))
    size = f"{docs} documents ; " if docs is not None else ""
    text = f"non trouvée dans le corpus K ({size}couverture {pct(cov)})"
    reg = g.get("registry_state")
    if reg and reg != "reviewed_complete":
        text += f" — registre des mandats non entièrement revu (état : {reg}) : à ne pas lire comme « sans mandat »"
    return text


def _names(ids: list[str], inst: dict[str, str]) -> list[str]:
    return [inst.get(i, i) for i in ids or []]


def finding_view(g: dict[str, Any], inst: dict[str, str], ai_mode: str | None) -> dict[str, Any]:
    ev = g.get("evidence") or []
    refs = [r for r in g.get("references") or [] if r.get("status") != "rejected"]
    jur = sorted({(r.get("reference") or {}).get("jurisdiction", "").strip().lower() for r in refs} - {""})
    caveats = []
    if ai_mode == "scripted" and g.get("evidence_basis") == "observed":
        caveats.append("signal issu d'un mode sans IA : non indépendant d'un agent, à ne pas lire comme observation d'un modèle")
    if g.get("cause") in ("documentary", "artifact"):
        caveats.append("cause " + ("documentaire (couverture insuffisante)" if g["cause"] == "documentary"
                                   else "artefact de recherche (document dans la portée non récupéré) : pas une lacune institutionnelle"))
    return {
        "id": g.get("id"), "fingerprint": g.get("fingerprint"), "code": g.get("code"), "category": g.get("category"),
        "title": g.get("title"), "description": g.get("description"), "domain": g.get("domain"),
        "institutions": _names(g.get("institution_ids"), inst), "institution_ids": g.get("institution_ids") or [],
        "action_code": g.get("action_code"), "severity": g.get("severity"), "confidence": g.get("confidence"),
        "evidence_basis": g.get("evidence_basis"), "validation_status": g.get("validation_status"),
        "origin": g.get("origin"), "registry_state": g.get("registry_state"), "cause": g.get("cause"),
        "consequence": g.get("consequence"), "corpus_coverage": g.get("corpus_coverage"),
        "sources": [e for e in ev if e.get("kind") in ("mandate", "chunk") and e.get("role") != "counter"],
        "trace": [e for e in ev if e.get("kind") in ("event", "message", "decision", "coordinator_signal")],
        "counter_evidence": [e for e in ev if e.get("role") == "counter"],
        "absence_statement": absence_statement(g), "caveats": caveats,
        "references_status": "sufficient" if len(jur) >= MIN_JURISDICTIONS else "insufficient_sources",
        "references_jurisdictions": jur,
    }


def _metric_view(m: dict[str, Any] | None) -> dict[str, Any]:
    if not m or m.get("status") != "computed":
        return {"status": "not_computed", "value": None, "passed": None,
                "reason": (m or {}).get("reason") or "non exécuté", "text": "non calculé"}
    out = {k: m.get(k) for k in ("value", "passed", "numerator", "denominator", "threshold", "llm_calls", "wall_seconds",
                                 "kappa", "confidence_interval", "recall_at_5", "recall_at_10", "mrr", "ndcg_at_10",
                                 "n_questions", "note")}
    return {"status": "computed", "reason": None, **out,
            "text": "valeur calculée" if m.get("value") is not None else "non calculé"}


def assemble(inp: dict[str, Any]) -> dict[str, Any]:
    """`inp` : report{title,version_no,id,confidentiality,generated_at,parent_version_no}, exercise{id,code,title,ai_mode,
    snapshot_sha256,commitment_sha256}, snapshot, ledger{head_seq,head_hash,verify,events}, events, gaps (None = service
    indisponible), kb{inventory,coverage}, scorecard, metrics, prior_links."""
    rp, ex, led = inp["report"], inp["exercise"], inp["ledger"]
    snap = inp.get("snapshot") or {}
    ai_mode = ex.get("ai_mode")
    label = ai_label(ai_mode)
    inst = {i["id"]: f"{i.get('code', '')} — {i.get('name', '')}".strip(" —") for i in snap.get("institutions", [])}
    events = inp.get("events") or []
    gaps = inp.get("gaps")
    verify = led.get("verify") or {}

    all_f: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for g in gaps or []:
        if g.get("validation_status") == "rejected":
            rejected.append({"id": g.get("id"), "title": g.get("title"), "fingerprint": g.get("fingerprint")})
            continue
        all_f.append(g)
    is_hyp = lambda g: g.get("evidence_basis") == "hypothesis" or g.get("origin") == "agent_hypothesis"  # noqa: E731
    key = lambda v: (-(v.get("severity") or 0), v.get("code") or "", v.get("id") or "")  # noqa: E731
    findings = sorted((finding_view(g, inst, ai_mode) for g in all_f if not is_hyp(g)), key=key)
    hyps = sorted((finding_view(g, inst, ai_mode) for g in all_f if is_hyp(g)), key=key)

    # --- métriques d'exécution tirées du ledger
    decisions = [e for e in events if e["type"] == "DECISION"]
    cites = [c for e in events if e["type"] == "CITATION_CHECK" for c in (e.get("payload") or {}).get("citations") or []]
    llm = [e["payload"] for e in events if e["type"] == "LLM_CALL"]
    models = sorted({f"{p.get('provider')}/{p.get('model')}" for p in llm if p.get("model")})
    cover_unavail = gaps is None

    summary = {
        "gaps_available": not cover_unavail,
        "findings_count": None if cover_unavail else len(findings),
        "hypotheses_count": None if cover_unavail else len(hyps),
        "rejected_count": None if cover_unavail else len(rejected),
        "findings_by_severity": {str(s): sum(1 for f in findings if f["severity"] == s) for s in (3, 2, 1)},
        "findings_by_status": dict(Counter(f["validation_status"] for f in findings)),
        "decisions_count": len(decisions),
        "citations_checked": len(cites),
        "citations_verified": sum(1 for c in cites if c.get("pass") is True) if cites else None,
        "citations_text": (f"{sum(1 for c in cites if c.get('pass') is True)} / {len(cites)} citations vérifiées" if cites
                           else "non calculé (aucune citation vérifiée)"),
        "highlights": [f"{f['code']} · {f['title']} (gravité {f['severity']}, {f['validation_status']})" for f in findings[:5]],
    }

    injects = (snap.get("scenario") or {}).get("injects", [])
    derivations = Counter(d.get("derivation") for i in injects for d in i.get("demands") or [])
    kb = inp.get("kb") or {}
    cov = kb.get("coverage") or {}
    context = {
        "exercise": {"id": ex.get("id"), "code": ex.get("code"), "title": ex.get("title")},
        "scenario": {k: (snap.get("scenario") or {}).get(k) for k in ("code", "title", "language")} | {"injects": len(injects)},
        "institutions": [{"code": i.get("code"), "name": i.get("name"), "kind": i.get("kind")} for i in snap.get("institutions", [])],
        "seats": [{"code": s.get("code"), "institution": inst.get(s.get("institution_id"), s.get("institution_id")),
                   "controller": s.get("controller")} for s in snap.get("seats", [])],
        "knowledge_bases": [{"code": k.get("code"), "name": k.get("name"), "documents": len(k.get("document_version_ids") or [])}
                            for k in snap.get("kb", [])],
        "models": models, "ai_mode": ai_mode,
    }
    methodology = {
        "evidence_levels": EVIDENCE_LEVELS,
        "rules": ["G1 responsabilité orpheline", "G2 mandats chevauchants", "G3 procédure absente", "G4 dépendance manquante",
                  "G5 conflit d'objectifs", "G6 responsabilité (liability)", "G7 inclusion", "G8 supervision de l'IA",
                  "G9 sécurité du canal", "G10 transfrontalier"],
        "negative_search": "Une absence est testée par recherche sur le corpus de l'exercice ; formulation imposée : "
                           "« non trouvée dans le corpus K (couverture c %) ». Une absence dans un corpus incomplet n'est pas une preuve d'inexistence.",
        "findings_vs_hypotheses": "Un constat exige au moins une preuve non-agent ; une proposition d'agent seule reste une hypothèse (section séparée).",
        "demand_derivation": {str(k): v for k, v in derivations.items()},
        "demand_derivation_note": "Les demandes `scenario_author` sont des attentes fixées par le concepteur du scénario, jamais des obligations officielles.",
        "ai_notice": (f"Exercice étiqueté {label} : les agents ne sont pas des modèles d'IA vivants." if label else None),
    }
    plan = []
    for g in all_f:
        for a in g.get("improvement_actions") or []:
            plan.append({"gap_id": g.get("id"), "gap_title": g.get("title"), "action_id": a.get("id"),
                         "recommendation": a.get("description"), "owner": inst.get(a.get("owner_institution_id"), a.get("owner_institution_id")),
                         "due_date": a.get("due_date"), "status": a.get("status"), "kpi": a.get("kpi")})
    plan.sort(key=lambda a: (a["due_date"] or "9999", a["gap_id"] or ""))
    history = [{"gap_id": g.get("id"), "gap_title": g.get("title"), **{k: r.get(k) for k in (
        "reviewer", "action", "from_status", "to_status", "reality_label", "comment", "created_at")}}
        for g in gaps or [] for r in g.get("reviews") or []]
    history.sort(key=lambda r: (r.get("created_at") or "", r["gap_id"] or ""))
    reviews = {"history": history, "by_status": dict(Counter(f["validation_status"] for f in findings + hyps)),
               "by_reality_label": dict(Counter(r["reality_label"] for r in history if r.get("reality_label"))),
               "disputed": [f["id"] for f in findings if f["validation_status"] == "disputed"]}

    sc = inp.get("scorecard")
    scorecard = ({"status": "not_available", "note": "scorecard non disponible", "dimensions": []} if sc is None else {
        "status": sc.get("overall_status"), "overall_score": sc.get("overall_score"), "scale": sc.get("scale"),
        "dimensions_assessed": sc.get("dimensions_assessed"), "dimensions_total": sc.get("dimensions_total"),
        "note": sc.get("note"),
        "dimensions": [{"number": d["number"], "name": d["name"], "score": d["score"],
                        "status": "non évalué" if d["score"] is None else "évalué", "assessed": d["assessed"], "total": d["total"]}
                       for d in sc.get("dimensions", [])]})
    mets = inp.get("metrics") or {}
    metrics = {m: _metric_view(mets.get(m)) for m in METRIC_ORDER}

    limits = [
        "Exercice FICTIF : les événements, chiffres et décisions du scénario sont simulés ; ce n'est pas une alerte réelle.",
        f"Corpus : couverture documentaire attendue/présente {pct(cov.get('ratio'))} ; une absence n'est jamais une preuve d'inexistence.",
        "La recherche négative est lexicale/hybride : un synonyme ou un document hors corpus peut manquer ; revue humaine requise.",
        "Documents numérisés : la qualité de l'OCR peut dégrader l'extraction ; les langues traitées sont celles des bases de l'exercice.",
        "Les recommandations du plan d'amélioration sont des propositions, distinctes des constats observés.",
        "Intégrité : toute modification ou suppression de fin du ledger est détectable à partir de la dernière tête exportée ou publiée ; "
        "un administrateur contrôlant base, ancres et clé de signature pourrait réécrire le journal (non « infalsifiable »).",
    ]
    if label:
        limits.insert(0, f"Étiquette {label} : exercice sans modèle d'IA vivant (mode {ai_mode}) ; "
                         "les signaux d'un mode sans IA ne comptent jamais comme observation d'agents.")
    if cover_unavail:
        limits.append("Le service des lacunes était indisponible : constats, hypothèses et plan d'amélioration non évalués (jamais 0).")
    if verify and not verify.get("ok", True):
        limits.append(f"ALERTE INTÉGRITÉ : la vérification du ledger a échoué ({verify.get('reason')}, première entrée n° {verify.get('first_bad_seq')}).")
    if any(f["registry_state"] not in (None, "reviewed_complete") for f in findings + hyps):
        limits.append("Registre de mandats non entièrement revu pour certaines institutions : leurs absences restent des candidats.")
    if sc is None or sc.get("overall_status") != "assessed":
        limits.append("Scorecard : dimensions « non évalué » (≠ 0).")
    for m in METRIC_ORDER:
        if metrics[m]["status"] != "computed":
            limits.append(f"Métrique {m} : non calculée ({metrics[m]['reason']}) — jamais comptée comme 0.")

    def _ref_block(f: dict[str, Any], g: dict[str, Any]) -> dict[str, Any]:
        rows = [{"jurisdiction": (r.get("reference") or {}).get("jurisdiction"), "instrument": (r.get("reference") or {}).get("instrument"),
                 "article": (r.get("reference") or {}).get("article"), "summary": (r.get("reference") or {}).get("summary"),
                 "binding": (r.get("reference") or {}).get("binding"), "url": (r.get("reference") or {}).get("url"),
                 "status": r.get("status"), "fit_note": r.get("fit_note")}
                for r in g.get("references") or [] if r.get("status") != "rejected"]
        n = len(f["references_jurisdictions"])
        return {"gap_id": f["id"], "gap_title": f["title"], "status": f["references_status"], "references": rows,
                "message": None if n >= MIN_JURISDICTIONS else f"sources internationales insuffisantes : {n} juridiction(s) trouvée(s) (minimum {MIN_JURISDICTIONS})"}

    by_id = {g.get("id"): g for g in all_f}
    refs = [_ref_block(f, by_id[f["id"]]) for f in findings]
    annex_ev = [{"gap_id": f["id"], "kind": e.get("kind"), "role": e.get("role"), "ref": e.get("ref"), "excerpt": e.get("excerpt")}
                for f in findings + hyps for e in (f["sources"] + f["trace"] + f["counter_evidence"])]
    return jsonable({
        "schema": SCHEMA, "generator_version": GENERATOR_VERSION, "language": "fr",
        "banner": label, "title": rp["title"],
        "cover": {
            "report_id": rp.get("id"), "version_no": rp["version_no"], "parent_version_no": rp.get("parent_version_no"),
            "generated_at": rp["generated_at"], "confidentiality": rp.get("confidentiality"),
            "exercise": {"id": ex.get("id"), "code": ex.get("code"), "title": ex.get("title")},
            "ai_mode": ai_mode, "ai_label": label, "snapshot_sha256": ex.get("snapshot_sha256"),
            "commitment_sha256": ex.get("commitment_sha256"),
            "ledger": {"head_seq": led.get("head_seq"), "head_hash": led.get("head_hash"), "events": led.get("events"),
                       "verify": {k: verify.get(k) for k in ("ok", "checked", "first_bad_seq", "reason", "anchor_mismatch",
                                                             "truncated_after_anchor")}},
        },
        "executive_summary": summary, "context": context, "methodology": methodology,
        "findings": findings, "hypotheses": hyps, "references": refs, "improvement_plan": plan,
        "reviews": reviews, "scorecard": scorecard, "metrics": metrics,
        "prior_analyses": {"origin": "analyse antérieure", "links": inp.get("prior_links") or []},
        "limits": limits,
        "annexes": {"evidence_index": annex_ev, "kb_inventory": kb.get("inventory") or [], "kb_coverage": cov,
                    "rejected_gaps": rejected, "ledger_verification": verify},
    })
