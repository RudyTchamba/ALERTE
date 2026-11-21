# 11 — Organisation du backend et du frontend

> Arborescence **peu profonde** (pas de couches inutiles) ; un module = un dossier ; contrats entre modules = services publics + schémas Pydantic (doc 05 §5.4–5.5). Rien de ceci n'est créé tant que le dossier n'est pas validé.

## 11.1 Arborescence cible du dépôt

```
alerte-platform/
├── README.md                    # démarrage rapide, liens vers docs/
├── Dockerfile                   # multi-stage : node:22 (build SPA) → python:3.12-slim
├── compose.yaml                 # app + profils optionnels : ollama (dev), vllm (GPU)
├── .env.example                 # toutes les variables ALERTE_* documentées
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini · migrations/        # créés au gel du modèle (ADR 010)
│   ├── app/
│   │   ├── main.py                      # crée l'app, include_router par module, monte le SPA
│   │   ├── core/                        # config, db, ids, errors, auth, jobs, lifespan, blobs, canonical_json, clock
│   │   ├── workspaces/                  # espaces, pays, institutions, domaines, jetons
│   │   ├── mandates/                    # registre de mandats, catalogue d'actions, graphe
│   │   ├── knowledge/                   # KB, documents, ingestion, index, recherche, archive
│   │   │   ├── ingest/                  # extract · ocr · normalize · structure · chunking · quality
│   │   │   ├── index/                   # fts · vectors · embed (port Embedder)
│   │   │   └── archive/                 # export · import_ · manifest · limits
│   │   ├── agents/                      # agents, profils de modèle, droits, runtime, outils, citations
│   │   │   ├── tools/                   # search_kb · ask_legal · post · decide
│   │   │   ├── llm/                     # base (port) · openai_compat · scripted · cassette
│   │   │   └── prompts/                 # modèles de prompts versionnés (fichiers texte)
│   │   ├── scenarios/                   # scénarios, injects, demandes, readiness
│   │   ├── simulation/                  # exercices, snapshot, sièges, état, runner, coord, board, human, stream
│   │   ├── audit/                       # événements (catalogue), ledger, vérification, ancres, trace
│   │   ├── gaps/                        # rules/, signals, negative_search, references, review, fingerprint
│   │   ├── reports/                     # assemble, render/{md,csv,json,pdf,xlsx}, imported, compare, templates/
│   │   └── evaluation/                  # t1…t6, scorecard, benchmark ; fixtures/ (PRIVÉ)
│   ├── tests/
│   │   ├── unit/ · integration/ · security/ · architecture/ · golden/ · fixtures_data/
│   └── scripts/                         # legacy_to_archive.py · verify_ledger.py · seed_demo.py
├── frontend/
│   ├── package.json · vite.config.ts · tsconfig.json · tailwind.config.ts
│   └── src/
│       ├── main.tsx · app/ (routes, providers, layout)
│       ├── api/ (client.ts, schema.d.ts généré, queries/)
│       ├── components/ui/               # primitives accessibles (Radix/shadcn)
│       ├── features/                    # un dossier par espace fonctionnel (voir §11.4)
│       ├── lib/ · i18n/ (en.json, fr.json) · styles/
│       └── tests/
├── docs/ (architecture/, adr/, runbooks/)
└── deploy/ (sandbox/, ollama.md, vllm.sh)
```

Les **données d'exécution** (`/data/db`, `/data/blobs`, `/data/anchors`, `/data/keys`, `/data/exports`) vivent hors du dépôt (volume Docker ; `ALERTE_DATA_DIR`).

## 11.2 Convention interne d'un module backend

| Fichier | Contenu | Règle |
|---|---|---|
| `models.py` | Tables SQLAlchemy du module | Seul le module écrit ses tables |
| `schemas.py` | DTOs Pydantic (entrée/sortie API) | **Source du contrat OpenAPI** ; pas de modèle ORM exposé |
| `service.py` | Cas d'usage (transactions, règles métier) ; reçoit `Session` et `Actor` | Aucune dépendance HTTP ; testable seul |
| `router.py` | `APIRouter` mince : validation, appel service, sérialisation | Pas de logique (BP-02) |
| `__init__.py` | Exporte `service` public et `router` | Les autres modules n'importent que ça |
| sous-dossiers | Sous-domaines volumineux (`ingest/`, `rules/`, `render/`) | Un fichier par responsabilité |

## 11.3 Contrats à figer **avant** le développement parallèle

1. Modèles SQLAlchemy + DTOs Pydantic de `core`, `workspaces`, `knowledge`, `agents`, `scenarios`, `simulation`, `audit`, `gaps`, `reports` (doc 06).
2. **Catalogue d'événements du ledger** : enum des types, schéma de payload par type, visibilité (doc 10 §10.2) — contrat entre moteur, SSE, gaps et rapports.
3. **OpenAPI** généré à partir des schémas (doc 12) → types TS ; le frontend développe contre des réponses *fixtures*.
4. Ports : `LLMProvider.complete(messages, schema, params) -> RawCompletion` ; `Embedder.embed(texts) -> vectors` ; `search(scope, query, k) -> [Hit]` ; `detect(snapshot, registry, demands, events) -> [GapCandidate]` ; `Ledger.append(...)`.
5. Un **run scripted « doré »** (golden) partagé : exercice de référence qui doit toujours produire le même `replay_digest`.

## 11.4 Frontend : espaces fonctionnels et routes

| Espace | Route | Page | Contenu principal | Expérience |
|---|---|---|---|---|
| Accueil | `/` | Workspace Home | Exercices (brouillon/en cours/terminé/archivé), accès rapide, état du fournisseur de modèle, bandeau « Fictional exercise » | Studio |
| Pays & institutions | `/studio/countries` | Country & Institutional Manager | Pays, institutions, domaines, **registre de mandats** (onglet), revue de couverture | Studio |
| Bases de connaissances | `/studio/knowledge`, `/studio/knowledge/:kbId` | Knowledge Base Manager | Liste, détail (documents, chunks, qualité, versions, index, **export/import**) | Studio |
| Agents | `/studio/agents` | Agent Manager | CRUD agent, mission, modèle, outils, limites, aperçu du prompt | Studio |
| Accès | `/studio/access` | Knowledge Access Mapping | **Matrice agents × KB** (cases à cocher accessibles) ; vue d'impact ; vérification « aucun agent sans KB » | Studio |
| Scénarios | `/studio/scenarios`, `/studio/scenarios/:id` | Scenario Builder | Injects ordonnés, destinataires, demandes, étiquettes, pannes, aperçu, lint | Studio |
| Exercice | `/studio/exercises/:id` | Participants & Readiness | Sièges (IA/humain), liens de siège, **contrôles de préparation**, lancement | Studio |
| Salle | `/room/:exerciseId` | **Simulation Room** | Voir §11.5 | Room |
| Joueur | `/play#t=<jeton>` | Player Seat | Fiche de rôle, boîte privée, tableau, recherche, décision | Room |
| Observateur | `/watch#t=<jeton>` | Observer View | Lecture seule | Room |
| Lacunes | `/gaps`, `/gaps/:gapId` | Gap Analysis & Institutional Assessment | Voir doc 09 §9.7 | Transverse |
| Rapports | `/reports`, `/reports/:id` | Report Center | Générés/importés, versions, comparaison, téléchargements | Transverse |
| Audit | `/audit/:exerciseId` | Audit & Replay | Chronologie, vérification, trace de décision, rejeu | Transverse |
| Évaluation | `/evaluation` | Evaluation & Scorecard | T1–T6, scorecard | Transverse |
| Architecture | `/about/architecture` | Mapping Y.3172 | Table de correspondance (critère C5) | Transverse |

### 11.5 Simulation Room (écran de démonstration)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ ▮ Fictional exercise — not a real alert   [SANS IA]?   État: RUNNING   J1 07:10  │
│ [Pause] [Pas à pas] [Vitesse ▾] [Surprise] [Arrêter]      Budget: 41/200 appels  │
├───────────────┬───────────────────────────────────────────┬──────────────────────┤
│ Événements    │  Sièges (une carte par institution)       │ Tableau de           │
│ ▸ 06:00 inject│  ┌MET──────┐ ┌DPC──────┐ ┌OPS──────┐      │ coordination         │
│ ▸ 06:20 inject│  │ dernière │ │ attend  │ │ décision │      │  INFO · REQUEST ·    │
│ ● 07:10 inject│  │ décision │ │ humain  │ │ non      │      │  DECISION · OBJECTION│
│   (courant)   │  │ ✔ vérifiée│ │ ⏳ Marie │ │ vérifiée ⚠│      │  · GAP_FLAG          │
│ ▹ prochain    │  └─────────┘ └─────────┘ └─────────┘      │  (filtre par tour)   │
│               │  Clic = détail : boîte, décisions,        │                      │
│               │  trace (sources, scores, brut), prise     │ Lacunes naissantes   │
│               │  de contrôle                              │  🔴 G1 · 🟠 G2 …      │
└───────────────┴───────────────────────────────────────────┴──────────────────────┘
```

Principes d'interface : couleur **toujours accompagnée d'un mot** (WCAG, spec) ; lisible sur projecteur ; mises à jour par SSE sans rechargement ; un clic sur toute décision ouvre la **trace** ; vocabulaire simple, détails techniques repliés (« afficher les détails »).

## 11.6 Conventions frontend

| Sujet | Règle (BP-15…19) |
|---|---|
| Composition | Composants de **présentation** sans appel réseau ; **conteneurs** de page qui lisent les requêtes ; état au plus proche du parent commun |
| État serveur | TanStack Query, clés centralisées (`api/queries/keys.ts`) ; invalidation sur événements SSE pertinents |
| État local | `useState`/`useReducer` ; **pas de store global** (Redux/Zustand écartés) |
| Flux SSE | Hook `useExerciseStream(exerciseId, filters)` : `EventSource`, reconnexion, `Last-Event-ID`, réducteur d'événements → états dérivés (chronologie, cartes, tableau, lacunes) ; **ne duplique pas** la logique métier |
| Types | `schema.d.ts` généré par `openapi-typescript` à partir de `/api/v1/openapi.json` ; CI vérifie qu'il est à jour |
| Formulaires | `react-hook-form` + validation alignée sur les contraintes OpenAPI ; messages d'erreur serveur affichés par champ |
| Tableaux | `@tanstack/table` ; tri/filtre côté serveur quand > 200 lignes |
| Design | Tailwind + tokens CSS (clair/sombre) ; composants Radix/shadcn copiés dans `components/ui` ; icônes `lucide-react` ; graphiques `recharts` (radar du scorecard) ; Markdown `react-markdown` (aperçu de rapport) |
| i18n (**FR = P1**) | `react-i18next` ; **clés dès le début**, anglais complet en P0, français en P1 (FR/EN exigé par la spec) |
| Accessibilité | WCAG 2.2 AA ; navigation clavier ; focus visible ; `aria-live` pour les événements entrants ; contraste vérifié ; tests `axe` sur les pages clés |
| Responsive | Studio : tablette/desktop ; **Player Seat et Observer : utilisables sur téléphone** (spec) |
| Assistants guidés | Création de KB (nom → pays/domaine → import → revue → publication) ; création d'exercice (scénario → sièges → readiness → lancement) |

## 11.7 Tests par dossier

| Dossier | Contenu |
|---|---|
| `backend/tests/unit` | Règles G, canonisation JSON, chaîne de hachage, citation checker, chunking, RRF, transitions d'état |
| `backend/tests/integration` | API + SQLite temporaire : parcours KB, exercice `scripted`, revue de lacune, génération de rapport |
| `backend/tests/security` | Les 11 tests adversariaux (doc 13) + canaris de fuite |
| `backend/tests/architecture` | Graphe d'imports, fixtures privées, pas de `UPDATE/DELETE` sur tables en ajout seul, aucune constante de pays |
| `backend/tests/golden` | Exercice de référence `scripted` + cassette : **`replay_digest` stable** |
| `frontend/tests` | Composants (Vitest + Testing Library), a11y (axe), un parcours smoke contre une API de test |
