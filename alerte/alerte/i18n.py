"""French / English strings for the interface, reports and the offline brain."""

from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    "app_title": {"en": "ALERTE: crisis drill simulator", "fr": "ALERTE : simulateur d'exercice de crise"},
    "fictional": {"en": "Fictional exercise. Not a real alert.", "fr": "Exercice fictif. Ceci n'est pas une vraie alerte."},
    "act": {"en": "Act: {label}", "fr": "Agir : {label}"},
    "act_no_proc": {"en": "Act: {label} (no written procedure found; acting on general powers)",
                    "fr": "Agir : {label} (aucune procédure écrite trouvée ; action sur la base de pouvoirs généraux)"},
    "refer": {"en": "Ask {holders} to {label}", "fr": "Demander à {holders} de : {label}"},
    "no_basis": {"en": "No legal basis found to {label}. Flagging a gap.",
                 "fr": "Aucune base légale trouvée pour : {label}. Signalement d'une lacune."},
    "gap_no_holder": {"en": "No institution holds the power or duty to {label}",
                      "fr": "Aucune institution n'a le pouvoir ou le devoir de : {label}"},
    "gap_no_proc": {"en": "No procedure, deadline or form for: {label}", "fr": "Aucune procédure, délai ou forme pour : {label}"},
    "gap_overlap": {"en": "Several institutions hold '{label}' and no text says who leads",
                    "fr": "Plusieurs institutions détiennent « {label} » et aucun texte ne désigne le chef de file"},
    "gap_dependency": {"en": "'{label}' depends on something not confirmed ready: {dep}",
                       "fr": "« {label} » dépend d'un élément dont la disponibilité n'est pas confirmée : {dep}"},
    "gap_conflict": {"en": "'{a}' conflicts with '{b}'", "fr": "« {a} » entre en conflit avec « {b} »"},
    "request_text": {"en": "{sender} asks you to: {label}. Event: {event}", "fr": "{sender} vous demande de : {label}. Événement : {event}"},
    "accept": {"en": "Accepted: we will {label}.", "fr": "Accepté : nous allons {label}."},
    "not_our_role": {"en": "Not our role: we hold no power or duty to {label}.",
                     "fr": "Hors de notre rôle : nous n'avons ni pouvoir ni devoir de : {label}."},
    "ai_output": {"en": "Output produced. HydroSense informs; it does not decide. Validity limits are in its model card.",
                  "fr": "Résultat produit. HydroSense informe ; il ne décide pas. Les limites de validité figurent dans sa fiche modèle."},
    "situation": {"en": "Event {id} at {time}: {text}", "fr": "Événement {id} à {time} : {text}"},
    "unknown_validation": {"en": "Has a human expert validated this information?", "fr": "Un expert humain a-t-il validé cette information ?"},
    "unknown_who": {"en": "Which institution is legally in charge?", "fr": "Quelle institution est juridiquement compétente ?"},
    "no_national": {"en": "No national text in the library addresses this question.",
                    "fr": "Aucun texte national de la bibliothèque ne traite de cette question."},
    "nothing_missing": {"en": "Nothing missing was detected by the rules for this question; check the gap report after a drill.",
                        "fr": "Les règles n'ont détecté aucun manque pour cette question ; consultez le rapport des lacunes après un exercice."},
    "rec_default": {"en": "Consider the options shown by the examples from other jurisdictions; confirm the national legal basis on the official texts before acting.",
                    "fr": "Examinez les options illustrées par les exemples d'autres juridictions ; confirmez la base légale nationale sur les textes officiels avant d'agir."},
    "h_national": {"en": "1. What the national texts say", "fr": "1. Ce que disent les textes nationaux"},
    "h_missing": {"en": "2. What is unclear or missing", "fr": "2. Ce qui est flou ou manquant"},
    "h_elsewhere": {"en": "3. How others handle it", "fr": "3. Comment font les autres"},
    "h_rec": {"en": "4. Recommendation (suggestion only)", "fr": "4. Recommandation (simple suggestion)"},
    "h_sources": {"en": "Sources checked:", "fr": "Sources vérifiées :"},
    "disclaimer": {"en": "For exercise purposes only; confirm with a qualified lawyer.",
                   "fr": "À des fins d'exercice uniquement ; à confirmer par un juriste qualifié."},
}


def t(key: str, lang: str = "en", **kw) -> str:
    entry = STRINGS.get(key, {})
    text = entry.get(lang) or entry.get("en") or key
    try:
        return text.format(**kw)
    except (KeyError, IndexError):
        return text
