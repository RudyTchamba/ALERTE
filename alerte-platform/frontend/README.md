# ALERTE — Frontend (React + TypeScript + Vite)

Interface web d'ALERTE Platform : Exercise Studio (pays/institutions/mandats, bases de connaissances, agents, accès aux connaissances,
scénarios, exercices), Simulation Room (temps réel par SSE), sièges joueur/observateur, analyse des lacunes, rapports, audit & rejeu, évaluation.
Chaque action de l'interface correspond à une vraie opération du backend (aucune donnée factice affichée comme réelle) ; si un module backend
manque, l'écran l'indique explicitement.

> Commandes exécutées et vérifiées sur Ubuntu 24.04 avec Node 22.22.3 / npm 10.9.8 / nvm 0.40.0. Les variantes Windows/macOS n'ont pas été exécutées.

## 1. Stack

| Élément | Choix |
|---|---|
| Framework | React 19 + TypeScript 5.9 (strict ; épinglé car `openapi-typescript` ne supporte pas encore TS 7) |
| Bundler / dev server | Vite 8 (proxy `/api` vers le backend) |
| Données serveur | TanStack Query ; formulaires React Hook Form + Zod |
| Routage | React Router 7 (pages chargées à la demande) |
| Style | Tailwind CSS 4, jetons CSS (thème clair/sombre/système), icônes `lucide-react` |
| i18n | i18next : anglais et français complets (test de parité des clés) ; langue initiale = choix mémorisé sinon langue du navigateur |
| Tests / qualité | Vitest + Testing Library (jsdom), axe-core, oxlint (règles correctness + jsx-a11y), `tsc --noEmit` |

## 2. Node.js et nvm

Node **22** (voir `.nvmrc`, `engines: ">=22"`). Si Node et nvm sont déjà installés, **ne rien réinstaller** : vérifiez seulement.

```bash
node --version      # v22.x attendu
npm --version
nvm --version       # nvm est une fonction du shell : dans un script non interactif, faire d'abord  . ~/.nvm/nvm.sh
nvm use             # lit .nvmrc ; si la version 22 manque :  nvm install
```

Windows : utiliser nvm-windows ou fnm (`nvm use 22`). **N'utilisez jamais `sudo npm`** : tout s'installe dans `frontend/node_modules`, avec votre utilisateur.
Si `npm` se plaint de permissions, c'est qu'un ancien `sudo npm` a laissé des fichiers appartenant à root : `sudo chown -R $USER ~/.npm frontend/node_modules`
(seul usage de `sudo` toléré ici, pour réparer les droits).

## 3. Installation

```bash
cd alerte-platform/frontend
nvm use
npm ci              # installation exacte depuis package-lock.json (reproductible)
```

## 4. Démarrage (développement)

Le backend doit tourner sur `http://localhost:8000` (voir [backend/README.md](../backend/README.md)), puis dans un **second terminal** :

```bash
cd alerte-platform/frontend
npm run dev         # http://localhost:5173
```

Ouvrez `http://localhost:5173/access` : créez un espace de travail (le **jeton propriétaire n'est affiché qu'une fois** : copiez-le) ou collez un jeton existant.
Le jeton vit dans `sessionStorage` (onglet courant) ; il n'apparaît jamais dans une URL ni dans un journal. Arrêt : `Ctrl+C`.

## 5. Connexion au backend

* **Développement** : le navigateur appelle `http://localhost:5173/api/...` ; Vite relaie `/api` vers `http://localhost:8000` (`vite.config.ts`). Pas de CORS à configurer.
* **Backend ailleurs / autre port** : `ALERTE_API_URL=http://machine:8001 npm run dev` (Windows PowerShell : `$env:ALERTE_API_URL="http://machine:8001"; npm run dev`).
* **Production** : `npm run build` crée `dist/` ; FastAPI le sert lui-même sur `http://localhost:8000/` (même origine, pas de proxy).
* `VITE_API_BASE` (optionnelle) change le préfixe d'API dans le build (défaut `/api/v1`).

Contrats : `src/api/schema.d.ts` est **généré** depuis l'OpenAPI réel du backend (`npm run gen:api`, backend démarré) ; ne pas l'éditer.
Certaines réponses du backend n'ont pas de `response_model` : leurs formes sont décrites à la main dans `src/api/loose.ts`. Ce qui n'existe pas côté backend est
listé dans `src/api/pending.ts` (`TODO(api)`), sans appel factice.

## 6. Flux SSE (temps réel)

* **Exercice** (`src/api/sse.ts`, hook `src/features/room/useExerciseStream.ts`) : `POST /exercises/{id}/stream-token` (jeton à usage unique, 60 s) puis `EventSource`
  sur `/exercises/{id}/stream?stream_token=…&after=<dernier seq>`. À la coupure, un **nouveau** jeton est demandé et le flux reprend après le dernier `seq` ; dédoublonnage par `seq`.
  Le jeton de flux est le seul jeton qui apparaît dans une URL.
* **Jobs** (ingestion, embeddings, export, import, rapports) : `GET /jobs/{id}/stream` lu avec `fetch` (en-tête `Authorization`), reprise par `after=<dernier id>`.
* Liens de siège / observateur : `/play#t=…` et `/watch#t=…` — le fragment est lu une fois, retiré de la barre d'adresse et gardé en `sessionStorage`.

Vérification manuelle du flux à travers le proxy Vite (remplacer `<id>` et `<jeton>`) :

```bash
ST=$(curl -s -X POST http://localhost:5173/api/v1/exercises/<id>/stream-token -H "Authorization: Bearer <jeton>" | python3 -c "import sys,json;print(json.load(sys.stdin)['stream_token'])")
curl -N "http://localhost:5173/api/v1/exercises/<id>/stream?stream_token=$ST&after=0"
```

## 7. Scripts npm

| Commande | Rôle |
|---|---|
| `npm run dev` | serveur de développement Vite + proxy `/api` |
| `npm run build` | `tsc -b` puis build de production dans `dist/` |
| `npm run preview` | sert `dist/` localement (sans backend intégré) |
| `npm run typecheck` | TypeScript strict, sans émission |
| `npm run lint` | oxlint (correctness + accessibilité JSX) |
| `npm test` | Vitest (56 tests : client API, SSE, états de la salle, pages, primitives UI + axe, parité i18n, parcours) ; `fetch` et `EventSource` sont simulés **dans les tests uniquement** |
| `npm run test:watch` | Vitest en mode surveillance |
| `npm run gen:api` | régénère `src/api/schema.d.ts` depuis `http://localhost:8000/api/v1/openapi.json` |

Contrôle complet avant de proposer une modification : `npm run typecheck && npm run lint && npm test && npm run build`.

## 8. Organisation

```
src/
  app/          AppShell (navigation, bandeau « exercice fictif »), routes (code-splitting), thème, authentification
  api/          client HTTP, session, SSE, hooks TanStack Query, clés, types
  components/ui/  primitives accessibles maison (Button, Table, Dialog, Tabs, Toast, Badge…)
  features/     un dossier par écran : geo, kb, agents, scenarios, room, gaps, reports, audit, evaluation, access, about, help (glossaire)
  app/journey.ts  le parcours en 3 phases (menu, barre de parcours, Accueil)
  i18n/         en/*.json et fr/*.json (mêmes clés)
  styles/       jetons CSS et Tailwind
```

Principes : couleur toujours accompagnée d'un mot et d'une icône ; focus visible ; lien d'évitement ; régions `aria-live` pour les événements entrants ;
les exercices non réalisés par un vrai modèle affichent en permanence un bandeau « NO AI » ; une lacune n'est jamais présentée comme définitive avant revue humaine.

## 9. Dépannage

| Symptôme | Cause / correction |
|---|---|
| « The server cannot be reached » | backend arrêté ou `ALERTE_API_URL` incorrect ; tester `curl http://localhost:8000/api/v1/health` |
| `nvm: command not found` dans un script | nvm n'est chargé que par les shells interactifs : `. ~/.nvm/nvm.sh` |
| `npm ERR! EACCES` | fichiers créés par un ancien `sudo npm` : `sudo chown -R $USER ~/.npm frontend/node_modules` |
| Version de Node incorrecte | `nvm use` dans `frontend/` (lit `.nvmrc`) |
| 401 en boucle | jeton révoqué/expiré : se reconnecter depuis `/access` |
| Types TypeScript en échec après une mise à jour du backend | `npm run gen:api` (backend démarré) |
| Page blanche après `npm run build` servie par FastAPI | reconstruire (`npm run build`) puis redémarrer le backend |
| Port 5173 occupé | `npm run dev -- --port 5174` |
| Un écran affiche « Backend not available yet » | le module backend correspondant n'est pas chargé : redémarrer le backend |
| Comportement ancien après une mise à jour du backend | redémarrer uvicorn |

Voir aussi `../docs/runbooks/frontend.md` (notes de conception détaillées).
