"""Jeu de démonstration : les 11 lacunes de la section 6 du rapport technique ALERTE v2 (6 lacunes de politique + 5 de
standards), saisies comme `imported_finding` (titres/résumés rédigés ici, aucun PDF copié). Usage (script-like) :
`seed(client, headers, report_id)` ou `python -m tests.reports.demo_prior_findings` n'est PAS prévu (saisie via l'API)."""
from __future__ import annotations

from typing import Any

POLICY = [  # (code probable, titre, résumé, page du rapport v2)
    ("G1", "Aucun devoir déclaré des opérateurs de relayer les alertes publiques", "Aucun texte trouvé obligeant les opérateurs à relayer une alerte.", 3),
    ("G2", "Autorité qui autorise et émet une alerte peu claire", "Plusieurs autorités citées, sans règle publiée sur qui autorise chaque alerte.", 4),
    ("G3", "Aucune vérification avant diffusion d'une alerte rédigée par une IA", "Pas de validation humaine ni de journalisation de l'approbation.", 4),
    ("G6", "Personne ne répond du préjudice d'une fausse alerte produite par une IA", "Aucun texte n'attribue la responsabilité des sorties d'IA utilisées dans l'alerte publique.", 4),
    ("G7", "Aucun devoir sur les langues et la couverture des alertes", "Seules l'anglais et l'arabe sont exigés ; pas d'obligation pour les autres langues.", 4),
    ("G9", "Canal d'alerte non protégé contre l'usurpation", "Aucun texte sur qui peut bloquer et corriger une fausse alerte.", 4),
]
STANDARDS = [
    ("Nœud de politique Y.3172 pour les services publics", "Aucune indication sur l'expression des mandats légaux, de l'approbation humaine et de la journalisation."),
    ("Conditions de validité déclarées", "Aucune norme n'exige qu'un modèle déclare ses entrées minimales et signale leur absence."),
    ("Provenance des alertes", "Aucun profil commun ne marque un contenu généré par IA ou validé par un humain."),
    ("Métriques de préparation", "Le rapport 2.0 n'a pas de métrique sur la clarté des mandats ou de la responsabilité."),
    ("Journaux d'audit des agents", "Aucun format commun de traces de raisonnement et d'attribution des sources."),
]


def findings() -> list[dict[str, Any]]:
    rows = [{"title": t, "body": b, "code_hint": c, "severity_hint": 3 if c in ("G1", "G3", "G6") else 2, "source_page": p}
            for c, t, b, p in POLICY]
    rows += [{"title": t, "body": b, "code_hint": "STD", "severity_hint": 1, "source_page": 5} for t, b in STANDARDS]
    return rows


def seed(client: Any, headers: dict[str, str], report_id: str, api: str = "/api/v1") -> list[dict[str, Any]]:
    r = client.post(f"{api}/reports/{report_id}/findings", json=findings(), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()
