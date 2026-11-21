"""Markdown canonique : dérivé du JSON structuré (déterministe, jamais édité à la main)."""
from __future__ import annotations

from typing import Any

SEV = {3: "3 (vie/droits)", 2: "2 (retard/coordination)", 1: "1 (gêne)"}


def _c(v: Any) -> str:
    """Cellule de tableau : une ligne, `|` échappé."""
    return ("" if v is None else str(v)).replace("|", "\\|").replace("\n", " ").strip()


def _pct(v: Any) -> str:
    return "non calculé" if v is None else f"{v:.3f}" if isinstance(v, float) else str(v)


def _finding(f: dict[str, Any], out: list[str], n: str) -> None:
    out += [f"### {n} {f['title']}", "",
            f"- **Identifiant** : `{f['id']}` · **empreinte** : `{(f.get('fingerprint') or '')[:16]}` · **code** : {f.get('code')} · "
            f"**catégorie** : {f.get('category')} · **domaine** : {f.get('domain') or '—'}",
            f"- **Gravité** : {SEV.get(f.get('severity'), f.get('severity'))} · **confiance** : {f.get('confidence')} · "
            f"**base de preuve** : {f.get('evidence_basis')} · **statut** : {f.get('validation_status')} · **origine** : {f.get('origin')}",
            f"- **Institutions** : {', '.join(f.get('institutions') or []) or '—'}", "", f.get("description") or ""]
    if f.get("consequence"):
        out += ["", f"**Conséquence** : {f['consequence']}"]
    if f.get("absence_statement"):
        out += ["", f"**Absence** : {f['absence_statement']}"]
    for cav in f.get("caveats") or []:
        out += [f"> Réserve : {cav}"]
    for label, key in (("Sources", "sources"), ("Événements, messages, décisions", "trace"), ("Contre-preuves", "counter_evidence")):
        if f.get(key):
            out += ["", f"**{label}**", ""]
            out += [f"- [{e.get('kind')}] {_c(e.get('ref'))} — « {_c(e.get('excerpt'))} »" for e in f[key]]
    out.append("")


def render_markdown(c: dict[str, Any]) -> str:
    cv, led = c["cover"], c["cover"]["ledger"]
    ver = led.get("verify") or {}
    out: list[str] = []
    if c.get("banner"):
        out += [f"> **{c['banner']}** — exercice sans modèle d'IA vivant ; lecture à adapter (voir §3 et §11).", ""]
    out += [f"# {c['title']}", "",
            "## 0. Page de garde et intégrité", "",
            f"- **Exercice** : {cv['exercise'].get('code')} — {cv['exercise'].get('title')} (`{cv['exercise'].get('id')}`)",
            f"- **Rapport** : `{cv.get('report_id')}` · **version** : {cv['version_no']}"
            + (f" (précédente : {cv['parent_version_no']})" if cv.get("parent_version_no") else ""),
            f"- **Généré le** : {cv['generated_at']} · **confidentialité** : {cv.get('confidentiality')} · **générateur** : {c['generator_version']}",
            f"- **Mode IA** : {cv.get('ai_mode')}" + (f" — **{cv['ai_label']}**" if cv.get("ai_label") else ""),
            f"- **Empreinte du snapshot** : `{cv.get('snapshot_sha256')}`",
            f"- **Tête du ledger** : seq {led.get('head_seq')} · hash `{led.get('head_hash')}` ({led.get('events')} événements)",
            f"- **Vérification du ledger** : {'intact' if ver.get('ok') else 'ÉCHEC'} ({ver.get('checked')} entrées vérifiées)"
            + ("" if ver.get("ok") else f" — première entrée altérée n° {ver.get('first_bad_seq')} : {ver.get('reason')}"), ""]
    s = c["executive_summary"]
    out += ["## 1. Résumé exécutif", ""]
    if not s["gaps_available"]:
        out += ["Service des lacunes indisponible : constats non évalués.", ""]
    else:
        out += [f"- Constats : **{s['findings_count']}** (gravité 3 : {s['findings_by_severity']['3']}, 2 : {s['findings_by_severity']['2']}, 1 : {s['findings_by_severity']['1']})",
                f"- Statuts : {', '.join(f'{k} {v}' for k, v in sorted(s['findings_by_status'].items())) or '—'}",
                f"- Hypothèses non confirmées : {s['hypotheses_count']} · lacunes rejetées (hors résumé) : {s['rejected_count']}"]
    out += [f"- Décisions enregistrées : {s['decisions_count']} · {s['citations_text']}", ""]
    out += [f"  - {h}" for h in s["highlights"]] + [""]
    x = c["context"]
    out += ["## 2. Contexte de l'exercice", "",
            f"- Scénario : {x['scenario'].get('code')} — {x['scenario'].get('title')} ({x['scenario'].get('injects')} injects, langue {x['scenario'].get('language')})",
            f"- Modèles : {', '.join(x['models']) or '—'}", "",
            "| Siège | Institution | Pilotage |", "|---|---|---|"]
    out += [f"| {_c(s_['code'])} | {_c(s_['institution'])} | {_c(s_['controller'])} |" for s_ in x["seats"]]
    out += ["", "Bases de connaissances : " + (", ".join(f"{k['code']} ({k['documents']} doc.)" for k in x["knowledge_bases"]) or "—"), ""]
    m = c["methodology"]
    out += ["## 3. Méthodologie", "", "Règles : " + " ; ".join(m["rules"]) + ".", "", "Niveaux de preuve :", ""]
    out += [f"- `{k}` : {v}" for k, v in m["evidence_levels"].items()]
    out += ["", m["negative_search"], "", m["findings_vs_hypotheses"], "", m["demand_derivation_note"]]
    if m["demand_derivation"]:
        out += ["Dérivation des demandes : " + ", ".join(f"{k} = {v}" for k, v in m["demand_derivation"].items()) + "."]
    if m.get("ai_notice"):
        out += ["", f"**{m['ai_notice']}**"]
    out += ["", "## 4. Constats (observations)", ""]
    out += [""] if c["findings"] else ["Aucun constat.", ""]
    for i, f in enumerate(c["findings"], 1):
        _finding(f, out, f"4.{i}")
    out += ["## 5. Hypothèses non confirmées (agents)", "", "Ces éléments ne sont PAS des constats : aucune preuve indépendante d'un agent.", ""]
    out += [] if c["hypotheses"] else ["Aucune hypothèse.", ""]
    for i, f in enumerate(c["hypotheses"], 1):
        _finding(f, out, f"5.{i}")
    out += ["## 6. Références et précédents internationaux", ""]
    for r in c["references"]:
        out += [f"### {r['gap_title']}", ""]
        if r["message"]:
            out += [f"**{r['message']}**", ""]
        out += [f"- {_c(x_['jurisdiction'])} — {_c(x_['instrument'])} {_c(x_['article'])} : {_c(x_['summary'])} {_c(x_['url'])}" for x_ in r["references"]] + [""]
    out += ["## 7. Plan d'amélioration (recommandations, distinct des constats)", "",
            "| Lacune | Recommandation | Propriétaire | Échéance | Statut | KPI |", "|---|---|---|---|---|---|"]
    out += [f"| {_c(a['gap_title'])} | {_c(a['recommendation'])} | {_c(a['owner'])} | {_c(a['due_date'])} | {_c(a['status'])} | {_c(a['kpi'])} |"
            for a in c["improvement_plan"]]
    r_ = c["reviews"]
    out += ["", "## 8. Validations et contestations humaines", "",
            "Synthèse : " + (", ".join(f"{k} {v}" for k, v in sorted(r_["by_status"].items())) or "aucune lacune") + ".",
            "Libellés de réalité : " + (", ".join(f"{k} {v}" for k, v in sorted(r_["by_reality_label"].items())) or "aucun") + ".", "",
            "| Lacune | Relecteur | Action | De → À | Réalité | Commentaire |", "|---|---|---|---|---|---|"]
    out += [f"| {_c(h['gap_title'])} | {_c(h['reviewer'])} | {_c(h['action'])} | {_c(h['from_status'])} → {_c(h['to_status'])} | {_c(h['reality_label'])} | {_c(h['comment'])} |"
            for h in r_["history"]]
    sc = c["scorecard"]
    out += ["", "## 9. Scorecard (13 dimensions ITU AI Readiness)", ""]
    if sc["status"] == "not_available":
        out += ["Scorecard non disponible.", ""]
    else:
        out += [f"Score global : {'non évalué' if sc['overall_score'] is None else round(sc['overall_score'], 2)} "
                f"({sc['dimensions_assessed']}/{sc['dimensions_total']} dimensions évaluées). « non évalué » n'est pas 0.", "",
                "| N° | Dimension | Score (0–5) | État |", "|---|---|---|---|"]
        out += [f"| {d['number']} | {_c(d['name'])} | {'non évalué' if d['score'] is None else round(d['score'], 2)} | {d['status']} |" for d in sc["dimensions"]]
    out += ["", "## 10. Métriques d'évaluation T1–T6", "", "| Métrique | État | Valeur | Réussite | Détail |", "|---|---|---|---|---|"]
    for k, v in c["metrics"].items():
        out += [f"| {k} | {'calculée' if v['status'] == 'computed' else 'non calculé'} | {_pct(v['value'])} | "
                f"{'—' if v['passed'] is None else ('oui' if v['passed'] else 'non')} | {_c(v.get('reason') or v.get('note') or '')} |"]
    pa = c["prior_analyses"]
    if pa["links"]:
        out += ["", "### Rapprochement avec des analyses antérieures (origine : analyse antérieure)", ""]
        out += [f"- {_c(x_['relation'])} : lacune `{x_['gap_id']}` ↔ « {_c(x_['finding_title'])} » ({_c(x_.get('report_title'))}, p. {x_.get('source_page')})" for x_ in pa["links"]]
    out += ["", "## 11. Limites de l'analyse", ""] + [f"- {x_}" for x_ in c["limits"]]
    a = c["annexes"]
    out += ["", "## Annexes", "", "### A1. Index des preuves", ""]
    out += [f"- `{e['gap_id']}` [{e['kind']}/{e['role']}] {_c(e['ref'])}" for e in a["evidence_index"]]
    out += ["", "### A2. Inventaire des bases de connaissances", ""]
    for kb in a["kb_inventory"]:
        out += [f"- **{kb.get('code')}** {kb.get('name')}"] + [f"  - {d.get('code')} — {d.get('title')} ({d.get('jurisdiction')}, licence {d.get('license')})" for d in kb.get("documents", [])]
    cov = a["kb_coverage"] or {}
    out += ["", f"Couverture documentaire : {cov.get('present')}/{cov.get('expected')}" + (f" (manquants : {', '.join(cov.get('missing') or [])})" if cov.get("missing") else ""), "",
            "### A3. Vérification du ledger", "", f"- Résultat : {'intact' if ver.get('ok') else 'échec'} ; tête seq {led.get('head_seq')} `{led.get('head_hash')}`",
            "", "### A4. Lacunes rejetées (hors résumé)", ""] + [f"- `{g['id']}` {g['title']}" for g in a["rejected_gaps"]]
    out += ["", "---", f"Rendu dérivé du JSON structuré (version {cv['version_no']}). Tête du ledger : seq {led.get('head_seq')} `{led.get('head_hash')}`.", ""]
    return "\n".join(out)
