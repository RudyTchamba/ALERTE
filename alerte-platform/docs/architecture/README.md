# ALERTE Platform — Dossier d'architecture technique et fonctionnelle

> **Statut : architecture V1 validée (fondations), corrections ciblées appliquées le 2026-11-21 ; développement en cours dans `alerte-platform/`.** Aucun code n'a été écrit ; seuls ces documents existent dans `alerte-platform/`. L'ancien dossier `alerte/` est intact. Rédigé le 2026-11-20 (Claude Sonnet 5.5, coordinateur ; recherches par sous-agents Haiku 5.5 ; revue critique d'Opus 5.5).

## Résumé en dix lignes

1. **ALERTE Platform** simule des exercices de crise où des agents (ou des humains) jouent des **institutions réelles** bornées par leurs mandats et leurs sources ; les **lacunes institutionnelles émergent** des documents, du registre de mandats, des événements du scénario et des interactions — jamais d'une liste pré-écrite.
2. **Monolithe modulaire** FastAPI + SQLAlchemy 2.0 + SQLite (WAL), SPA React/TypeScript/Vite servie par le même conteneur ; dix modules aux dépendances **vérifiées par test**.
3. **Plateforme générique** : espaces de travail, pays, institutions, KB, agents, droits, scénarios et sièges se configurent **dans l'interface** ; aucun pays dans le code.
4. **Bases de connaissances** versionnées, **exportables/réimportables** (ZIP + manifest SHA-256, droits et licences contrôlés) ; recherche hybride (BM25 d'abord, vecteurs ensuite) avec **permissions dans le SQL**, pas dans les prompts.
5. **Agents** : boucle contrôlée par le backend, 4 outils (`search_kb`, `ask_legal`, `post`, `decide`), sorties JSON contraintes, **contrôle de citation déterministe**, coordinateur **en code**.
6. **Exercices** : snapshot figé, machine à états (pause/reprise/reprise après arrêt), **siège humain**, flux **SSE** lisant le ledger.
7. **Audit** : ledger SHA-256 sur JSON canonique, ancre de tête contre la troncature, rejeu **sans rappeler les modèles** (cassette), **trace de décision** (réponse au critère « chain-of-thought traces »).
8. **Gap Analysis** : règles G1–G10 exécutables + signaux observés + recherche négative + références internationales sourcées (≥ 2 juridictions ou « insuffisant ») + revue humaine à trois axes ; **test contrefactuel** comme preuve d'intégrité.
9. **Rapports** versionnés (MD/CSV/JSON, PDF, XLSX), comparaison, import de rapports antérieurs ; structure inspirée HSEEP (observations ≠ recommandations).
10. **Calendrier réaliste** : P0 pour le mercredi 25 (parcours complet), P1 avant le 28, ordre de coupe défini ; démo de Dubaï **indépendante** de la Sandbox (cassettes).

## Index

| # | Document | Contenu |
|---|---|---|
| 01 | [Vision et périmètre](01-vision-and-scope.md) | Finalité, principes d'intégrité I1–I7, 7 niveaux de généricité, parcours, démonstration |
| 02 | [Exigences et arbitrages](02-requirements-and-arbitration.md) | Registre consolidé FR-xx, arbitrage Simple/Spec, ambiguïtés résolues |
| 03 | [Conformité hackathon](03-hackathon-conformance.md) | Critères officiels, matrice C1–C5/E1–E11, correspondance Y.3172 |
| 04 | [Bonnes pratiques](04-best-practices-registry.md) | 38 pratiques sourcées (URL, vérification, limites) + pratiques écartées |
| 05 | [Architecture globale](05-architecture-overview.md) | C4 (contexte, conteneurs, composants), modules, exécution, pile, ADR |
| 06 | [Modèle de données](06-data-model.md) | ERD Mermaid (4 vues) + règles d'intégrité |
| 07 | [Connaissances et RAG](07-knowledge-and-rag.md) | Pipeline documentaire, recherche, permissions, export/import, licences |
| 08 | [Agents et simulation](08-agents-and-simulation.md) | Outils, boucle, citations, scénarios, états, COORD, humain, rejeu |
| 09 | [Lacunes et rapports](09-gap-analysis-and-reports.md) | Typologie, règles, preuves, références, revue, rapports, scorecard |
| 10 | [Audit et évaluation](10-audit-and-evaluation.md) | Ledger, chaîne, ancres, trace, T1–T6 |
| 11 | [Organisation backend/frontend](11-backend-frontend-organization.md) | Arborescence, conventions, routes, Simulation Room |
| 12 | [Contrats API et SSE](12-api-and-sse-contracts.md) | Endpoints, exemples, flux SSE, erreurs |
| 13 | [Sécurité, tests, déploiement](13-security-testing-deployment.md) | Menaces, 11 tests adversariaux, Docker, Sandbox A/B/C |
| 14 | [Plan d'implémentation](14-implementation-plan.md) | Calendrier jour par jour, chemin critique, flux parallèles, risques, agents Claude |
| 15 | [Décisions à valider](15-decisions-to-validate.md) | V1–V18, questions de fond, ce qui n'est pas vérifié |
| A1–A8 | [Annexes](appendix/A1-spec-requirements-register.md) (A1…A8 dans `appendix/`) | Registres d'exigences (321 + ≈ 200), inventaire du corpus, recherches brutes |

Diagrammes : Mermaid (rendu natif sur GitHub, VS Code avec extension). Les 30 livrables demandés par le brief sont couverts : 1 → doc 01 ; 2 → 02 + A1/A2 ; 3 → 03 ; 4 → 04 ; 5 → 05 ; 6 → 05 ; 7 → 06 ; 8 → 07, 08, 09 (séquences) ; 9 → 08 §8.10 ; 10 → 07 §7.1 ; 11 → 07 §7.6 ; 12-14 → 07/08 ; 15 → 08 §8.8-8.9 ; 16 → 08 §8.11 ; 17 → 08 §8.12 ; 18-19 → 09 + 06 ; 20 → 09 §9.10 ; 21 → 10 ; 22-23 → 11 ; 24-25 → 12 ; 26-27 → 13 ; 28 → 13 §13.4 ; 29 → 14 ; 30 → 15.
