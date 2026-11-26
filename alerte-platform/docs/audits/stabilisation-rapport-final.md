# Rapport final de stabilisation (2026-11-24)

Étiquettes de preuve : **UI** (navigateur réel piloté), **API** (appels HTTP), **TEST** (suite automatisée), **DOC** (lecture de code/documentation), **ABS** (non fait / non vérifié).

## 1. Organisation du travail — ce qui a réellement été utilisé

* Un coordinateur (cette session, modèle Sonnet 5.5) a fait tout le travail de lecture, d'audit Git, de mesure, de code et de documentation.
* **Un seul sous-agent** a été lancé : un audit **indépendant en lecture seule** (modèle **Haiku**), qui a relu les correctifs non commités, exécuté les tests ciblés (70 backend, 8 frontend, typecheck) et rendu 9 constats (0 bloquant, 2 importants, 7 mineurs) — **tous traités** (§4). Les rôles `search`, `grep` et « conseiller Opus » n'ont **pas** été utilisés. Le découpage en trois membres/worktrees n'a **pas** été appliqué : les modifications ont été faites séquentiellement par le coordinateur, sans conflit de fichiers.

## 2. État initial

Voir [reconciliation-modifications-git.md](reconciliation-modifications-git.md) : fusion incohérente côté frontend (tests en échec), 18 commits de Landry Balekamen non audités, 23 fichiers modifiés non commités, et un guide impossible à suivre à l'étape 7.3.

## 3. Changements conservés / corrigés

* **Conservés** : les 11 groupes de l'équipe (voir la table du rapport de réconciliation). Rien n'a été retiré.
* **Corrigés** : fusion frontend ; N+1 de `GET /gaps` ; régression de requêtes causée par ma barre de parcours ; import CSV du catalogue d'actions (cause du premier blocage du guide) ; **ajout de sources aux mandats importés** (cause du second blocage) ; pays des bases et des institutions ; guide « revu complet » ; décodage UTF-8 → 422.
* **Remplacé** : la liste « Préparation » à 5 compteurs par une checklist à 10 étapes à état réel.

## 4. Audit indépendant : constats et suites

| # | Gravité | Constat (Haiku) | Suite |
|---|---|---|---|
| 1 | important | une requête en erreur (403 d'un observateur) était traitée comme « liste vide » → faux « à faire » | **corrigé** : `unavailable` → message, pas d'étape suivante |
| 2 | important | `?tab=` ignoré quand on est déjà sur la page (état initial seulement) | **corrigé** : onglet dérivé de l'URL (`useSearchParams`) |
| 3 | mineur | tuile « lacunes » affichait 0 en erreur | corrigé (« — ») |
| 4 | mineur | clé `common.replayShort` absente | ajoutée FR/EN |
| 5 | mineur | texte lecteur d'écran « Après : » sans prérequis | corrigé |
| 6 | mineur | boutons « Supprimer » tous en chargement ; non contextuels | corrigé (état par ligne + libellé accessible) ; doublon de nom « Importer un CSV » (mandats/actions) : **ouvert** |
| 7 | mineur | échec partiel d'enregistrement de sources → doublons possibles au 2ᵉ essai | corrigé (chaque source retirée dès enregistrée) ; **pas de contrôle de doublon côté backend** : ouvert |
| 8 | mineur | CSV non UTF-8 → 500 | corrigé (422) |
| 9 | mineur | libellé d'avertissement cité de façon inexacte dans l'aide | corrigé |
| — | réserve | le comportement contrefactuel n'avait pas été exécuté par l'auditeur | il a été exécuté dans une session précédente (**API**) ; la requête de contrôle du jour confirme : sans revue, G1 « transfert à l'étranger » = `inferred`, confiance `low` (**API**) |

## 5. Tests exécutés (résultats réels)

| Niveau | Commande | Résultat | Date |
|---|---|---|---|
| **TEST** backend complet | `pytest -o addopts="" -p no:warnings` | **539 réussis, 2 ignorés** (tests `-m model`), 0 échec (7 min 41 s) | avant les 3 dernières retouches |
| **TEST** backend ciblé, après retouches finales | `pytest tests/mandates tests/gaps tests/simulation` | **290 réussis** | fin de session |
| **TEST** lint backend | `ruff check app tests scripts` | propre | fin de session |
| **TEST** frontend | `vitest run` | **88 réussis** (20 fichiers) | fin de session |
| **TEST** frontend | `tsc --noEmit`, `oxlint src`, `vite build` | OK | fin de session |
| **UI** smoke navigateur | 23 routes (Accueil, Pays [3 onglets], Bases, Agents, Accès, Scénarios, Exercices [liste + page], Salle [+ salle], Carte, Lacunes, Et si…, Rapports, Audit [+ page], Évaluation, Glossaire, Architecture, Jetons, Présentation) sur un espace complet | **23/23** : titre affiché, **0 erreur console**, **0 réponse API ≥ 400** ; rejoué **3 fois sur le build final** (un premier essai avait montré 1 échec différent à chaque passage : course du script qui lisait le titre avant son rendu sur la machine saturée ; script corrigé pour attendre le titre) | build final |
| **UI** parcours neuf | espace → pays → institution → accueil, bar « À faire maintenant » et checklist | conforme ; **0 erreur console** | après audit |
| **UI** étape 7.3 | CM-L10, CM-L13, CM-L14 : refus sans source → Sources → Valider | conforme (3/3) | après audit |
| **API** | `GET /gaps` (42 lacunes), mêmes champs | OK | — |

**Non exécutés** : suite complète backend *après* les toutes dernières retouches (seul le sous-ensemble ci-dessus) ; tests Playwright **versionnés dans le dépôt** (aucun n'existe : les scripts de parcours sont dans le dossier temporaire de session, non commités) ; exercice en **mode modèle réel** (aucun fournisseur disponible dans cette session) ; CI GitHub (3 OS) ; Windows/macOS.

## 6. Performances

Voir [frontend-backend-performance-audit.md](frontend-backend-performance-audit.md). Résumé : `GET /gaps` 74 → 36 ms (N+1 supprimé) ; 4 à 8 requêtes évitées sur les pages hors préparation (Salle 15 → 7, Audit 14 → 6, Évaluation 10 → 3) ; **la machine est saturée** (charge 8–10, swap plein, processus tiers à 85–150 % de CPU) ; le mode développement double le premier chargement de l'accueil (5,2 s contre 2,4 s en production).

## 7. Critères d'acceptation (les 20 de la mission)

| # | Critère | Statut |
|---|---|---|
| 1 | Je sais quelles modifications l'ami a faites | **Atteint** (18 commits, auteur vérifié, table par groupe) |
| 2 | Les modifications pertinentes sont conservées | **Atteint** |
| 3 | Les incompatibles corrigées/remplacées avec justification | **Atteint** (fusion réparée ; une liste remplacée) |
| 4 | Conformité aux spécifications et à V1 | **Atteint avec réserves** : `reform` (G7) et poids d'autorité (G9) à confirmer |
| 5 | Parcours de configuration évident | **Partiel** : checklist + barre ; formulaires non découpés |
| 6 | Relations visibles | **Partiel** : pays ↔ institution/KB, mandat ↔ source ; scénario ↔ pays absent du modèle |
| 7 | Formulaires indiquent ressources obligatoires et prochaines étapes | **Partiel** (institution, KB) |
| 8 | Suivre sans deviner | **Partiel** : guide pas à pas rédigé, étapes 4 et 7–12 **non cliquées** de bout en bout |
| 9 | Comprendre la suite après 7.3 | **Atteint** (UI + guide + aide) |
| 10 | Jamais « registre complet » à tort | **Atteint** (guide, aide, test MD-08 reformulé) |
| 11 | Avertissements de Readiness expliquent la correction | **Partiel** (messages existants ; pas de lien par avertissement) |
| 12 | Lenteurs mesurées, causes identifiées | **Atteint** (avec conditions de mesure dégradées) |
| 13 | Problèmes démontrés corrigés | **Atteint** pour ce qui est démontré côté code ; contention machine **hors périmètre** |
| 14 | Rising Waters préparable et exécutable | **Atteint** (API/script, scripted SANS IA) ; **pas** en modèle réel |
| 15 | Liens principaux persistés | **Atteint** (table du rapport UX) |
| 16 | Tests fonctionnels et de sécurité passent | **Atteint** (539 + 88) ; isolation/rôles vérifiés précédemment (API) |
| 17 | Guide simple compréhensible sans connaissances techniques | **Partiel** : une commande de terminal en étape 0 |
| 18 | Guide complet décrit la version actuelle | **Partiel** : §7 corrigé, reste du guide à relire contre les nouvelles pages |
| 19 | Pas de reconstruction massive de KB | **Atteint** (aucune réingestion, aucun embedding) |
| 20 | Aucun commit/push | **Atteint** |

## 8. Problèmes restants

1. Étapes 4 et 7–12 du guide pas à pas **non rejouées au clic** dans le navigateur ; à faire par l'utilisateur ou lors d'une prochaine session.
2. Pas de test Playwright versionné ; pas de test de composant pour `MandateSourcesDialog`.
3. `GET /gaps/summary` (contrat d'API) à décider ; `readiness` ≈ 216 ms.
4. Pas de dédoublonnage des sources d'un mandat côté backend.
5. Pages de l'équipe non auditées fonctionnellement ; modes de panne non implémentés (13/14 sont des étiquettes), SQLite « database is locked » possible, références internationales vides, aucun modèle de production validé.
6. Les fichiers non commités (≈ 40) attendent la décision de l'utilisateur : `git status` pour la liste.
