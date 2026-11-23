# Lancement local d'ALERTE — commandes exactes

Toutes les commandes ci-dessous ont été **exécutées** sur Ubuntu 24.04 (Python 3.12.3, Node 22.22.3 via nvm, npm 10.9.8). Les variantes Windows/macOS sont données mais n'ont pas été exécutées. Jamais de `sudo pip`, jamais de `sudo npm`.

## 1. Ce dont vous avez besoin

| Élément | Vérification | Remarque |
|---|---|---|
| Python 3.11+ (3.12 recommandé) | `python3 --version` | l'environnement virtuel `backend/.venv` existe déjà chez vous : ne le recréez pas |
| Node.js 22 et nvm | `. ~/.nvm/nvm.sh && node --version && npm --version && nvm --version` | déjà installés : **ne rien réinstaller** ; `nvm use` lit `.nvmrc` |
| Dépendances backend | `cd backend && .venv/bin/python -m pip check` | déjà installées dans `.venv` |
| Dépendances frontend | `ls frontend/node_modules` | sinon : `cd frontend && npm ci` |
| Ollama (facultatif) | `curl http://localhost:11434/api/tags` | embeddings BGE-M3 réels et petit modèle de génération |

## 2. Votre fichier `backend/.env`

Il est lu **depuis le dossier où vous lancez le backend** (`backend/`). Ne le recréez pas s'il existe : `cp -n ../.env.example .env` (le `-n` n'écrase jamais). Pour la recherche hybride réelle, ajoutez (en retirant le `#` des lignes d'exemple) :

```ini
ALERTE_EMBED_BASE_URL=http://localhost:11434/v1
ALERTE_EMBED_MODEL=bge-m3
```

Sans ces deux lignes l'application fonctionne en recherche **lexicale seule** (signalée « dégradée » partout) : c'est suffisant pour parcourir toute la démonstration. Les lignes `ALERTE_LLM_*` ne servent qu'aux exercices en mode « Modèle réel » ; la démonstration utilise le mode « Scénarisé (SANS IA) ».

## 3. Données : ne rien supprimer, repartir proprement

Par défaut les données sont dans `backend/data/` (jamais effacées par ces commandes). **Pour une démonstration propre sans toucher à vos données existantes**, utilisez un autre dossier :

```bash
cd alerte-platform/backend
ALERTE_DATA_DIR=./data-demo .venv/bin/python -m uvicorn app.main:app_factory --factory --port 8000
# Windows PowerShell :  $env:ALERTE_DATA_DIR=".\data-demo"; .\.venv\Scripts\python -m uvicorn app.main:app_factory --factory --port 8000
```

`data-demo/` est ignoré par Git (règle ajoutée au `.gitignore`). Revenir à vos données = relancer sans `ALERTE_DATA_DIR`.

## 4. Démarrer (deux terminaux)

**Terminal 1 — backend** (depuis `alerte-platform/backend`) :

```bash
source .venv/bin/activate                 # Windows : .\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app_factory --factory --reload --port 8000
```

**Terminal 2 — frontend** (depuis `alerte-platform/frontend`) :

```bash
. ~/.nvm/nvm.sh && nvm use                # nvm n'est chargé que dans les shells interactifs
npm run dev
```

Tout-en-un (un seul terminal, `Ctrl+C` arrête les deux) : `python3 scripts/dev.py` depuis `alerte-platform/` (option `--data-dir ./backend/data-demo`).

## 5. Adresses et vérifications

| À ouvrir | Rôle |
|---|---|
| **http://localhost:5173/access** | l'interface : création/connexion à un espace de travail |
| http://localhost:8000/api/v1/docs · `/redoc` | Swagger · ReDoc |
| http://localhost:8000/api/v1/health | doit répondre `{"status":"ok"}` |
| http://localhost:8000/api/v1/ready | `ready: true` ; `embedder.configured` vaut `true` si vous avez réglé BGE-M3 |

Contrôle de liaison frontend ↔ backend : `curl http://localhost:5173/api/v1/health` (le proxy Vite relaie `/api` vers `:8000`) doit aussi répondre `{"status":"ok"}`.

## 6. Préparer le jeu de données Rising Waters (facultatif mais recommandé)

Les fichiers de démonstration sont **générés** à partir du prototype `alerte/data/` (lecture seule) dans `demo/rising-waters/` :

```bash
cd alerte-platform/backend
.venv/bin/python scripts/rising_waters_pack.py          # scénarios CM/AE, mandats, institutions, actions, agents
.venv/bin/python scripts/seed_rising_waters.py --until 4   # (optionnel) préremplit l'espace jusqu'à l'étape voulue (voir le guide)
```

`seed_rising_waters.py` crée l'espace « ALERTE — Demonstration » et affiche son jeton propriétaire **une seule fois**. Il n'efface rien. Voir [guide-test-complet-interface.md](guide-test-complet-interface.md).

## 7. Arrêter proprement

* `Ctrl+C` dans chaque terminal (backend puis frontend). Les jobs en cours passent à `interrupted` et sont signalés au redémarrage ; un exercice en cours passe à `interrupted` et peut être repris.
* Si vous avez lancé en arrière-plan : `ss -ltnp | grep -E ':(8000|5173) '` puis `kill <pid>`.
* N'arrêtez pas Ollama s'il sert d'autres usages : il peut rester actif.

## 8. Mode « un seul processus »

```bash
cd alerte-platform/frontend && npm run build        # produit frontend/dist
cd ../backend && .venv/bin/python -m uvicorn app.main:app_factory --factory --port 8000
# l'interface est alors servie sur http://localhost:8000/
```

## 9. Problèmes fréquents

| Symptôme | Cause | Correction |
|---|---|---|
| « Un espace existe déjà » à la création | un espace existe dans `ALERTE_DATA_DIR` ; la création d'un autre exige le jeton propriétaire | collez le jeton propriétaire sur `/access` ; **jeton perdu** : il n'est pas récupérable (seul son hash est stocké) → relancez avec un autre `ALERTE_DATA_DIR` (§3), rien n'est supprimé |
| `nvm: command not found` | shell non interactif | `. ~/.nvm/nvm.sh` |
| Port 8000/5173 occupé | processus précédent | `ss -ltnp \| grep :8000` puis `kill` ; ou `--port 8001` + `ALERTE_API_URL=http://localhost:8001 npm run dev` |
| `/ready` → `embedder.configured: false` | lignes `ALERTE_EMBED_*` toujours commentées | §2, puis **redémarrer** le backend (le `.env` n'est lu qu'au démarrage) |
| Page blanche après `npm run build` | `dist` périmé | reconstruire, redémarrer le backend |
| Exercice « Modèle réel » : agents en « Repli (sans modèle) » | `ALERTE_LLM_BASE_URL` absent | utilisez le mode « Scénarisé (SANS IA) » pour la démonstration |
