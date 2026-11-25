# Audit de performance — frontend et backend (mesures réelles)

Date : 2026-11-24. Toutes les durées ci-dessous sont **mesurées** (Chrome 1440×900 piloté par Playwright, `curl`/`httpx`, `uptime`). Aucune donnée existante n'a été supprimée ou modifiée : les données de l'utilisateur ont été **copiées** (`backend/data` → dossier temporaire, 27 Mo) et un jeton de test a été posé **dans la copie** ; les originaux sont intacts.

## 1. Conditions de mesure — à lire d'abord

| Constat | Valeur mesurée |
|---|---|
| Charge de la machine pendant les mesures | `load average` **8 à 10** (puis 5 au repos relatif) |
| Mémoire | 13,8 Go au total, **1 Go libre**, **swap 3,9 Go / 4 Go utilisé** |
| Processus étranger à ALERTE | un conteneur d'un autre projet (`/app/volunteer.py --n-volunteers 5`) à **85–150 % de CPU** pendant toute la session ; non touché |
| Autre conséquence | un serveur Django d'un autre projet occupe le port 8003 (les tests ALERTE ont utilisé 8001, 8002, 8013) |

**Conclusion intermédiaire** : cette machine est saturée. Une requête API qui prend **4–11 ms** seule (mesure `httpx` séquentielle) prend **60–210 ms** quand 10 requêtes arrivent ensemble (le navigateur en envoie 8 à 15 par page) : la lenteur ressentie vient d'abord de la **contention CPU/mémoire de la machine** et du **mode développement**, pas d'un algorithme défaillant du backend. Les chiffres absolus ci-dessous seraient plus bas sur une machine libre ; les **comparaisons avant/après** (mêmes conditions) restent valides.

## 2. Conditions A–D demandées

| Condition | Réalisé ? | Données |
|---|---|---|
| **A. Espace propre** (vide) | **Parcours GUI** mesuré fonctionnellement (création espace → pays → institution : aucune erreur console) ; pas de tableau de temps page par page | — |
| **A′. Espace de démonstration complet** (Rising Waters CM : 11 institutions, 25 actions, 14 mandats, 9 agents, 2 bases / 3 980 chunks, 1 exercice terminé de 15 injects, 42 lacunes, ledger) | **Oui** | §3–§4 |
| **B. Copie des données de l'utilisateur** (11 institutions, 25 actions, 14 mandats, 2 bases, 0 agent/scénario/exercice) | **Oui** | §3 |
| **C. À froid** (premier accès à chaque page, nouveau contexte navigateur) | **Oui** | §3 |
| **D. À chaud** (second accès) | **Oui** (nouvelle page, cache HTTP du navigateur) ; navigation **dans l'application** (clic menu) mesurée à part | §3 |

Pages mesurées : Accueil, Pays et institutions, Bases de connaissances, Agents, Accès, Scénarios, Exercices, Salle (picker et salle), Carte des responsabilités, Lacunes, Et si…, Rapports, Audit (picker et page), Évaluation, Glossaire. L'« Espace de travail » n'est pas une page distincte (c'est l'Accueil).

## 3. Frontend (production, bundle `npm run build` servi par le backend)

Mesure : `h1` = délai jusqu'au titre de la page ; `idle` = jusqu'à l'inactivité réseau.

**B — copie des données utilisateur, 1er accès (froid)**

| Page | h1 (ms) | idle (ms) | Requêtes API | Plus lente |
|---|---|---|---|---|
| Accueil | 2 406 | 2 417 | 6 | `/agents` 428 ms |
| Pays et institutions | 1 225 | 1 772 | 3 | `/workspaces/current` 128 |
| Bases de connaissances | 1 281 | 1 870 | 3 | 247 |
| Agents | 1 411 | 2 025 | 8 | 266 |
| Accès | 1 231 | 1 889 | 8 | `/knowledge-bases` 252 |
| Scénarios | 1 498 | 1 990 | 9 (1 doublon) | 216 |
| Exercices | 1 713 | 1 714 | 3 | `/auth/me` 440 |
| Salle (picker) | 1 177 | 1 861 | 7 | 335 |
| Carte des responsabilités | 1 052 | 1 731 | 9 | 263 |
| Lacunes | 1 751 | 2 518 | 9 (1 doublon) | `/gaps` 560 |
| Rapports / Audit / Évaluation | 1 688 / 1 492 / 1 985 | 2 161 / 2 295 / 1 986 | 8 / 7 / 3 | ≤ 423 |

Navigation **dans l'application** (clic dans le menu, après le premier chargement, 15 pages) : **262 à 728 ms**, **0 à 6 requêtes** (cache TanStack Query) ; la plupart des pages ne refont aucune requête.

**Mode développement (Vite, `npm run dev`) vs production** — comparaison sur la même machine :

| | Accueil à froid | Autres pages à froid |
|---|---|---|
| Dev (Vite, dépendances pré-bundlées au 1er accès) | **5 206 ms** | 1 407–2 442 ms (`networkidle`, inclut ~500 ms d'attente d'inactivité) |
| Prod (bundle) | 2 406 ms | 1 052–1 985 ms |

→ en développement, **le premier chargement de l'accueil est ~2,2× plus lent** ; les pages suivantes sont du même ordre. Les chunks de production sont paresseux par page (le plus gros : `index` 373 ko / 123 ko gzip, `ui` 183 ko / 60 ko gzip).

## 4. Backend

| Endpoint (espace complet A′) | 1er appel | Médian (25 appels) | Octets |
|---|---|---|---|
| `GET /gaps` (42 lacunes) | 141 ms | **74 ms → 36 ms** après correction | 78 412 |
| `GET /agents` | 111 | 38 | 6 920 |
| `GET /exercises/{id}/readiness` (9 sièges) | — | **216 ms** (p90 448) | 7 142 |
| `GET /exercises/{id}/decisions` | — | 128 (1 appel) | 24 159 |
| autres listes (`/institutions`, `/mandates`, `/actions`, `/knowledge-bases`…) | 8–106 | 4–38 | 0,2–10 ko |

Sur la copie des données utilisateur (séquentiel, idle) : toutes les listes répondent en **4 à 11 ms** à chaud (première réponse 8 à 106 ms).

## 5. Causes démontrées et corrections

| # | Élément | Page(s) | Temps initial | Cause démontrée | Fichiers | Correction | Temps final | Vérification |
|---|---|---|---|---|---|---|---|---|
| 1 | **N+1 SQL** : une requête `reference_status` **par lacune** | Accueil, Lacunes, Et si… (`GET /gaps`) | médian **74 ms**, p90 193 ms (42 lacunes → 43 requêtes) | `_gap_out` appelait `reference_status(session, g.id)` dans une boucle | `backend/app/gaps/service.py`, `router.py` | `reference_statuses()` : **1** requête `IN (…)` pour toutes les lacunes ; même format de sortie | médian **36 ms**, p90 63 ms | tests `tests/gaps` (58) + audit indépendant : mêmes champs |
| 2 | **Requêtes ajoutées par ma propre barre « À faire maintenant »** (8 requêtes sur *toutes* les pages) | Salle, Lacunes, Rapports, Audit, Évaluation | Salle 15 requêtes, Audit 14, Évaluation 10, Lacunes 12, Rapports 11 | `JourneyBar` appelait `useSetup()` partout ; mesuré avant correction | `frontend/src/components/JourneyBar.tsx` | la barre n'est montée que dans la phase **Préparer** (`NextAction`) | Salle **7**, Audit **6**, Évaluation **3**, Lacunes **9**, Rapports **8** ; `h1` Audit 1 584 → 503 ms, Évaluation 1 027 → 440 ms, Lacunes 1 085 → 552 ms, Rapports 999 → 503 ms (même charge machine ±) | re-mesure ; 88 tests frontend |
| 3 | `GET /gaps` complet (78 ko, preuves incluses) chargé par l'Accueil **uniquement pour afficher un compteur** | Accueil | 78 ko, 36–93 ms | pas de paramètre de pagination ni de résumé dans l'API | `HomePage.tsx`, `gaps/router.py` | **Non corrigé** (voir §6) | — | — |
| 4 | Contention machine (CPU/swap) | toutes | 60–210 ms par requête sous charge 10 requêtes parallèles | `load average` 8–10, swap plein, processus tiers à 85–150 % CPU | hors dépôt | **Hors du périmètre ALERTE** ; recommandation : arrêter les processus tiers, libérer la mémoire | — | `uptime`, `top`, `ps` |

## 6. Ce qui reste (honnêtement)

* **Résumé des lacunes pour l'Accueil** : un endpoint `GET /gaps/summary` (compteurs) éviterait 78 ko ; non fait car cela ajoute un **contrat d'API** (à valider centralement) — recommandé.
* **`/exercises/{id}/readiness` ≈ 216 ms** : calculé à chaque appel (export des snapshots d'agents et contrôles) ; non optimisé faute de mesure de gain sûr ; la page ne l'appelle qu'à l'ouverture d'un exercice.
* **SQLite sous écritures simultanées** (exercices en parallèle) : `busy_timeout` passé à 30 s par l'équipe ; « database is locked » reste possible.
* **Aucun cache ajouté** : les données de permissions et de statuts doivent rester fraîches.
* **React Profiler** non utilisé (aucune page ne montre de rendu bloquant mesurable dans ces mesures ; la contention machine domine). **SSE** : pas de surcharge mesurée sur les pages hors salle ; la salle a 2 requêtes dupliquées (pré-existant).
* Chaque mesure ci-dessus est **ponctuelle** sur une machine bruitée : ordres de grandeur, pas des seuils garantis.

## 7. Ce qu'il faut faire pour retrouver des pages rapides

1. Utiliser la **production** pour la démonstration : `npm run build`, puis servir `frontend/dist` par le backend (`http://localhost:8000`).
2. Libérer la machine (processus tiers, swap) avant la démonstration.
3. Ne pas mesurer `networkidle` comme « temps de chargement » : il inclut ~500 ms d'attente.
