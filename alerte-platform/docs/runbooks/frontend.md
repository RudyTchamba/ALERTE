# Runbook — Frontend (React + TypeScript + Vite)

Dossier : `alerte-platform/frontend/`. Node 22 (`.nvmrc` à la racine du projet). Aucun script bash n'est nécessaire :
tout passe par les scripts npm (Windows, macOS, Linux).

## Démarrage

```bash
# Linux/macOS avec nvm (sinon : installer Node 22 par tout autre moyen)
export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"; nvm use      # lit .nvmrc

# 1. Backend (autre terminal) — données de dev hors du dépôt
cd backend && ALERTE_DATA_DIR=/tmp/alerte-dev .venv/bin/python -m uvicorn app.main:app_factory --factory --port 8000
#    (Windows : set ALERTE_DATA_DIR=%TEMP%\alerte-dev puis .venv\Scripts\python -m uvicorn ...)

# 2. Frontend
cd frontend && npm ci && npm run dev        # http://localhost:5173 ; /api est proxifié vers :8000
```

Variable optionnelle : `ALERTE_API_URL` (cible du proxy de dev, défaut `http://localhost:8000`).

Premier lancement : l'écran `/access` propose de **créer un espace** (le jeton propriétaire est affiché UNE fois) ou de coller un jeton.
Le jeton vit dans `sessionStorage` (onglet courant), jamais dans une URL ni un journal.

## Scripts

| Script | Rôle |
|---|---|
| `npm run dev` | Serveur Vite + proxy `/api` |
| `npm run build` | `tsc` puis build de production dans `frontend/dist` (servi par FastAPI : `app.main` monte `frontend/dist`) |
| `npm run typecheck` | TypeScript strict, sans émission |
| `npm run lint` | oxlint (règles `correctness` + jsx-a11y ; config `.oxlintrc.json`) |
| `npm test` | Vitest + Testing Library (jsdom) ; `fetch` et `EventSource` sont simulés **dans les tests uniquement** |
| `npm run gen:api` | Régénère `src/api/schema.d.ts` depuis `http://localhost:8000/api/v1/openapi.json` (backend démarré) |

## Contrats API

* `src/api/schema.d.ts` est **généré** (ne pas l'éditer). `src/api/types.ts` n'en expose que des alias.
* Plusieurs routes du backend renvoient des `dict` sans `response_model` : leurs formes sont écrites à la main dans
  `src/api/loose.ts` (dérivées du code backend) — à remplacer par des alias dès que le backend déclare les modèles.
* Ce qui n'existe pas encore côté backend est listé dans `src/api/pending.ts` (`TODO(api)`) : trace de décision serveur,
  blobs prompt/réponse, rejeu serveur, échange de session, rôle de l'appelant. L'UI contourne sans inventer de données
  (trace et rejeu reconstruits depuis le ledger ; rôle propriétaire détecté par `GET /tokens`).
* Un module backend absent donne un état explicite « Backend not available yet » (route 404 `http.404`), jamais de données factices.
* Après chaque évolution du backend : démarrer le backend, `npm run gen:api`, `npm run typecheck`.

## Flux SSE

* Exercice : `POST /exercises/{id}/stream-token` (jeton à usage unique, 60 s) puis `EventSource ?stream_token=…&after=<dernier seq>`.
  Sur coupure, un **nouveau** jeton est demandé et le flux repart de `after=<dernier seq>` ; dédoublonnage par `seq`
  (`src/api/sse.ts`, hook `src/features/room/useExerciseStream.ts`). Le jeton de flux est le seul jeton qui apparaît dans une URL.
* Jobs (ingestion, export, import, rapport) : `GET /jobs/{id}/stream` lu par `fetch` avec l'en-tête `Authorization` (pas de jeton dans l'URL),
  reprise par `after=<dernier id>`.
* Liens de siège / observateur : `/play#t=…`, `/watch#t=…`. Le fragment est lu une fois, retiré de la barre d'adresse
  (`history.replaceState`) et conservé en `sessionStorage` ; il n'est jamais envoyé en query ni en chemin.

## Accessibilité et i18n

* Couleur toujours accompagnée d'un mot et d'une icône (`Badge`, `StatusBadge`) ; focus visible ; lien d'évitement ; `aria-live`
  pour les événements entrants de la salle ; matrice d'accès = cases à cocher natives dans un tableau à en-têtes.
* Anglais complet (`src/i18n/en/*.json`) ; français prévu (P1) : `src/i18n/fr/*.json` ne contient que le cadre, le reste retombe sur l'anglais.
* Thème clair/sombre (jetons CSS dans `src/styles/index.css`), responsive : Studio tablette/bureau, Player/Observer téléphone.

## Dépendances ajoutées au projet pré-créé

`tailwindcss`, `@tailwindcss/vite`, `vitest`, `jsdom`, `@testing-library/{react,user-event,jest-dom,dom}`, `openapi-typescript`,
`axe-core` (tests d'accessibilité), `i18next`, `react-i18next`. **TypeScript est épinglé en 5.9** : TypeScript 7 n'expose plus
l'API JavaScript dont `openapi-typescript` a besoin. Écartés volontairement : `@tanstack/table` (tableaux simples maison),
`recharts` (radar SVG maison), `react-markdown` (aperçu JSON structuré), Radix (primitives accessibles maison : dialogue, onglets, toasts).

## Dépannage

* « The server cannot be reached » : le backend ne tourne pas sur `:8000` (ou `ALERTE_API_URL` est faux).
* 401 en boucle : jeton révoqué/expiré — se reconnecter depuis `/access`.
* Types TypeScript en échec après une mise à jour du backend : `npm run gen:api`.
* Un serveur backend démarré avant une mise à jour du code garde l'ancien comportement : le redémarrer.
