# ALERTE — Backend (FastAPI)

API REST + SSE d'ALERTE Platform : bases de connaissances (RAG hybride), mandats, agents, scénarios, simulation d'exercices,
détection de lacunes, rapports, audit (ledger chaîné) et évaluation. Un seul processus FastAPI (monolithe modulaire) ; SQLite
(WAL) est la source de vérité.

> Les commandes ci-dessous sont celles qui ont été exécutées sur Ubuntu 24.04 (Python 3.12.3). Les variantes **Windows PowerShell**
> et **macOS** sont fournies mais **n'ont pas été exécutées** sur ces systèmes (la CI GitHub Actions est écrite pour les trois,
> mais n'a pas encore tourné). Voir « État de validation » dans le [README général](../README.md).

## 1. Prérequis

| Élément | Version | Remarque |
|---|---|---|
| Python | **3.11 ou 3.12** (testé : 3.12.3) | `requires-python = ">=3.11"` ; 3.12 recommandé (`.python-version`) |
| SQLite | avec **FTS5** | présent dans les Python officiels Linux/macOS/Windows ; vérifié au démarrage (`/ready`) |
| Tesseract 5 (optionnel) | langues `ara`, `fra`, `eng` | OCR des PDF scannés ; sans lui, l'ingestion des PDF « texte » fonctionne et les scans sont signalés |
| Pango (optionnel) | — | rendu PDF (WeasyPrint) ; polices arabes/latines embarquées dans le dépôt |
| Serveur d'embeddings | BGE-M3 | **requis pour la recherche hybride réelle** (voir §6) ; sans lui : mode lexical dégradé, signalé |
| Serveur de génération | API compatible OpenAI | requis pour les agents « réels » (voir §7) ; sans lui : exercices `scripted` (SANS IA) |

Paquets système (Ubuntu/Debian) : `sudo apt install python3-venv tesseract-ocr tesseract-ocr-fra tesseract-ocr-ara libpango-1.0-0 libpangoft2-1.0-0`
(`sudo` n'est utilisé **que** pour les paquets système, jamais pour `pip`). macOS : `brew install tesseract tesseract-lang pango`.
Windows : installeur Tesseract (UB Mannheim) dans le `PATH` ; Pango est optionnel.

## 2. Environnement virtuel dédié

Toutes les dépendances Python vivent dans `backend/.venv/` (jamais de `pip` global, jamais de `sudo pip`).

**Ubuntu / macOS**

```bash
cd alerte-platform/backend
python3 --version                 # 3.11+ requis
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

**Windows (PowerShell)**

```powershell
cd alerte-platform\backend
py --version
py -m venv .venv
.\.venv\Scripts\Activate.ps1      # si l'exécution de scripts est bloquée : Set-ExecutionPolicy -Scope Process RemoteSigned
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Sans activer le venv, appelez directement son interpréteur : `.venv/bin/python …` (Linux/macOS) ou `.venv\Scripts\python …` (Windows).
`requirements.txt` (versions épinglées, exécution) et `requirements-dev.txt` (+ pytest, ruff) sont générés à partir de `requirements.in` /
`requirements-dev.in`. **PyMuPDF (AGPL) est interdit** (contrôlé en CI).

Raccourci multiplateforme depuis la racine : `python scripts/setup.py` (crée le venv, installe, copie `.env.example`, lance `npm ci`).

## 3. Configuration (`backend/.env`)

Toute la configuration passe par des variables `ALERTE_*` (12-factor). Le fichier `backend/.env` est lu depuis le dossier courant
(**lancez les commandes depuis `backend/`**) ; il est ignoré par Git. Partez de l'exemple :

```bash
cp -n ../.env.example .env         # -n : ne remplace pas un .env existant. Windows : if not exist .env copy ..\.env.example .env
```

| Variable | Défaut | Rôle |
|---|---|---|
| `ALERTE_DATA_DIR` | `./data` | racine des données : `db/`, `blobs/`, `vector/`, `anchors/`, `exports/` |
| `ALERTE_DB_URL` | SQLite dans `data/db/alerte.sqlite` | URL SQLAlchemy (SQLite seulement validé) |
| `ALERTE_UPLOAD_MAX_MB` | 100 | taille maximale d'un upload |
| `ALERTE_LLM_MODE` | `openai_compat` | `openai_compat` \| `scripted` \| `cassette` (les deux derniers : tests, **SANS IA**) |
| `ALERTE_LLM_BASE_URL`, `ALERTE_LLM_MODEL`, `ALERTE_LLM_API_KEY`, `ALERTE_LLM_TIMEOUT_S` | — / — / — / 120 | serveur de génération |
| `ALERTE_MAX_LLM_CALLS` | 199 | budget d'appels modèle par exercice |
| `ALERTE_EMBED_BASE_URL`, `ALERTE_EMBED_MODEL`, `ALERTE_EMBED_API_KEY` | — | serveur d'embeddings (indépendant du précédent) |
| `ALERTE_EMBED_PROVIDER` | `openai_compat` | `fixture` = tests uniquement (vecteurs déterministes, **pas de l'IA**) |
| `ALERTE_JOB_WORKERS` | 2 | threads de la file de tâches (ingestion, export, rapports) |
| `ALERTE_MAX_CONCURRENT_EXERCISES` | 2 | exercices simultanés |
| `ALERTE_CORS_ORIGINS` | `http://localhost:5173` | origines autorisées (séparées par des virgules) |
| `ALERTE_BOOTSTRAP_ENABLED` | `false` | `POST /workspaces` libre au premier démarrage uniquement |
| `ALERTE_TESSDATA_DIR`, `ALERTE_OCR_LANGS` | — / `ara+fra+eng` | OCR |
| `ALERTE_LOG_LEVEL`, `ALERTE_LOG_JSON` | `INFO` / `true` | journaux (secrets masqués) |

Cette table est un résumé : **toutes** les variables (y compris `ALERTE_EMBED_BATCH_SIZE`, `ALERTE_EMBED_TIMEOUT_S`, `ALERTE_EMBED_REVISION/RUNTIME/QUANTIZATION`, `ALERTE_AUTHORITY_SPREAD`, `ALERTE_SIGNING_KEY_PATH`), leur caractère obligatoire, leur valeur attendue et le test de chacune sont dans [docs/runbooks/configuration-env.md](../docs/runbooks/configuration-env.md) ; le modèle de fichier est [`.env.example`](../.env.example). Vérification avant démarrage : `python ../scripts/doctor.py --backend-only`.

**OCR / Tesseract** : `ALERTE_TESSDATA_DIR` doit être un chemin **absolu** vers un dossier contenant `ara.traineddata`, `fra.traineddata`, `eng.traineddata` (un chemin relatif est résolu depuis le dossier courant, `backend/`, la plateforme puis le dépôt, mais ne vous y fiez pas). Une page image-dominante (scan avec cachet ou numéro) pour laquelle l'OCR est indisponible est **marquée « à relire »** ; elle n'est jamais acceptée en silence. Test : `tesseract --list-langs --tessdata-dir <chemin>`.

**Budget d'appels** : `ALERTE_MAX_LLM_CALLS` (199) n'est que le défaut ; le **budget de l'exercice** saisi dans le formulaire (réglage `max_llm_calls`) fait foi, côté moteur *et* côté runtime des agents.

Les secrets (clés d'API) ne vont que dans `.env` ou l'environnement : ils ne sont jamais écrits en base, dans les journaux ni dans le ledger.

## 4. Base de données et migrations (Alembic)

SQLite en mode WAL, clés étrangères actives (pragmas posés à chaque connexion). Le schéma est géré par Alembic
(`migrations/versions/0001_baseline.py` : 63 tables + table virtuelle FTS5 `chunk_fts` + triggers d'immuabilité).

* **Au démarrage**, l'application exécute automatiquement `upgrade head` (le journal affiche `schéma=alembic`).
* Manuellement (depuis `backend/`, venv actif) :

```bash
python -m alembic upgrade head          # appliquer
python -m alembic current               # révision courante
python -m alembic downgrade base        # tout défaire (base de test uniquement !)
python -m alembic revision --autogenerate -m "description"   # après modification d'un modèle ; relire le fichier généré
```

Les tables FTS5 (`chunk_fts*`) sont gérées hors métadonnées SQLAlchemy et ignorées par l'autogénération (`migrations/env.py`).
Sauvegarde : arrêter l'application puis copier `ALERTE_DATA_DIR`, ou `sqlite3 data/db/alerte.sqlite ".backup copie.sqlite"`.

## 5. Stockage

| Dossier (`ALERTE_DATA_DIR`) | Contenu |
|---|---|
| `db/alerte.sqlite` | données relationnelles, ledger, index lexical FTS5, embeddings (source de vérité) |
| `blobs/` | fichiers adressés par contenu (SHA-256) : documents importés, rendus de rapports, prompts/réponses |
| `vector/` | index vectoriel ChromaDB persistant (reconstructible depuis la base) |
| `anchors/` | ancres du ledger (fichier `jsonl` hors base) |
| `exports/` | archives d'export de bases de connaissances |

## 6. Recherche : moteur vectoriel et embeddings

* **Vectoriel** : ChromaDB persistant (HNSW), **lexical** : SQLite FTS5, **fusion** : RRF (k = 60) — recherche **hybride** dès la première version.
* **Embeddings** : modèle **BGE-M3** servi par n'importe quel serveur compatible OpenAI `/v1/embeddings` (Ollama, TEI, vLLM…), sur n'importe quelle machine.
  Une **empreinte d'embedder** (modèle, révision, runtime, quantification, dimension) est enregistrée : on ne mélange jamais deux empreintes.
* **Sans serveur d'embeddings** : recherche lexicale seule, marquée `degraded`.
* **Permissions** : le périmètre de recherche est construit **uniquement par le backend** ; chaque chunk retourné est re-vérifié en SQL.

Exemple avec Ollama installé localement :

```bash
ollama pull bge-m3
# backend/.env
ALERTE_EMBED_BASE_URL=http://localhost:11434/v1
ALERTE_EMBED_MODEL=bge-m3
```

Vérification : `curl localhost:8000/api/v1/ready` doit afficher `"embedder": {"configured": true, "model": "bge-m3", "fixture": false}`.

## 7. Fournisseurs de modèles de génération

Un **profil de modèle** (API `/model-profiles`, écran « Agents ») désigne un fournisseur par **nom de variable** (`endpoint_ref`), jamais par URL ni clé.
`ai_mode` d'un exercice : `ai` (vrai modèle ; profil de l'agent, sinon `ALERTE_LLM_BASE_URL`/`ALERTE_LLM_MODEL`), `scripted` ou `cassette` (**SANS IA**, étiquetés
dans l'interface, les rapports et le ledger). Les fournisseurs `scripted`/`cassette` servent aux tests et aux démonstrations ; **ils ne prouvent rien sur la qualité d'un modèle**.

```bash
# backend/.env — exemple avec un serveur Ollama (même machine ou machine d'équipe)
ALERTE_LLM_MODE=openai_compat
ALERTE_LLM_BASE_URL=http://localhost:11434/v1
ALERTE_LLM_MODEL=qwen2.5:1.5b-instruct
```

L'état réel de validation avec de vrais modèles est détaillé dans le [README général](../README.md#18-état-réel-de-validation).

## 8. Tâches en arrière-plan

Pas de worker séparé : un pool de threads (`ALERTE_JOB_WORKERS`) exécute les jobs (`/jobs/{id}`, flux SSE `/jobs/{id}/stream`) ; au redémarrage,
les jobs en cours passent à `interrupted`. Les simulations ont leur propre moteur (threads) ; leurs événements sont lus dans le ledger par SSE.

## 9. Démarrage

Depuis `backend/`, venv actif :

```bash
python -m uvicorn app.main:app_factory --factory --reload --timeout-graceful-shutdown 3 --port 8000     # développement (rechargement automatique)
python -m uvicorn app.main:app_factory --factory --port 8000              # sans rechargement
```

Windows PowerShell : identique (`python` du venv activé). Arrêt : `Ctrl+C`. Le premier démarrage crée `data/` et applique la migration.
Si `../frontend/dist` existe (après `npm run build`), FastAPI sert aussi l'interface sur `http://localhost:8000/` (un seul processus).

| URL | Rôle |
|---|---|
| `http://localhost:8000/api/v1/health` | vivacité : `{"status":"ok"}` |
| `http://localhost:8000/api/v1/ready` | disponibilité : base, dossier de données, FTS5, embedder (503 si un contrôle échoue) |
| `http://localhost:8000/api/v1/docs` | Swagger UI |
| `http://localhost:8000/api/v1/redoc` | ReDoc |
| `http://localhost:8000/api/v1/openapi.json` | schéma OpenAPI (source des types TypeScript du frontend) |

**Premier espace de travail** : `POST /api/v1/workspaces {"name": "..."}` renvoie le **jeton propriétaire, affiché une seule fois** (seul son hash est stocké).
L'interface le fait depuis `/access`. Pour un jeu de données de démonstration Rising Waters : [catalogue des commandes](../docs/runbooks/catalogue-commandes-et-fichiers.md) (`rising_waters_pack.py` puis `seed_rising_waters.py`).

## 10. Scripts

| Script | Rôle |
|---|---|
| `scripts/rising_waters_pack.py` | génère dans `../demo/rising-waters/` le pack **Rising Waters** : scénarios, institutions, actions, agents (avec les fiches `knowledge_bases/curation/agent-briefs.CM.json`) et mandats de la **nouvelle** base (`mandates.CM.json`) ; lit `alerte/data/scenarios` (rôles et scénarios, lecture seule) ; **remplace** les fichiers du pack |
| `scripts/seed_rising_waters.py` | prépare l'espace « ALERTE — Demonstration » par étapes : `--from/--until`, `--ai-mode scripted\|ai`, `--pace`, `--max-calls`, `--allow-missing-kbs`, `--fix-agents`. Échoue (message explicite) si un fichier est périmé, une base manque ou un agent diffère du pack. **`scripted` = SANS IA** ; n'efface rien |
| `scripts/seed_demo.py` | ancien espace de démonstration (« Démo ALERTE ») ; **hérité**, non documenté dans les guides ; `--ai-mode ai` appelle un vrai modèle |
| `scripts/ledger_tamper_demo.py` | prouve qu'une altération du ledger est détectée, **sur une copie isolée** |
| `scripts/legacy_to_archive.py` | **hérité** : convertit l'ancien prototype `alerte/` (45 documents, codes `CM-S01…`) en archives ; ne pas utiliser pour la démonstration |
| `scripts/kb_eval.py` | évalue la recherche (Recall@k, MRR) ; **toujours passer `--api http://localhost:8000`** (le port par défaut du script, 8020, est ancien) |

## 11. Tests

```bash
python -m pytest -m "not model and not gpu"        # 539 réussis, 2 ignorés (mesuré le 2026-11-24) ; aucun serveur de modèle requis
python -m pytest tests/knowledge -q                # un module
python -m ruff check app tests                     # lint
```

* `tests/test_e2e_chain.py` : chaîne complète avec les vrais modules (upload → indexation → mandats → agents → scénario → simulation → ledger → lacunes → rapport PDF/XLSX/CSV/MD/JSON → export de KB).
* `tests/test_migrations.py` : `upgrade head` = schéma des modèles (aucune dérive).
* **Tests de modèle réel** (`-m model`) : `ALERTE_EMBED_BASE_URL=http://localhost:11434/v1 ALERTE_EMBED_MODEL=bge-m3 python -m pytest -m model tests/knowledge`.
* Les tests utilisent `scripted` et `fixture` (déterministes, **sans IA**) : ils prouvent l'intégration, pas la qualité d'un modèle.

## 12. Organisation du code

```
backend/
  app/
    main.py             create_app(), app_factory(), servir frontend/dist
    core/               config, db, erreurs, logs, blobs, jobs, sécurité (jetons), santé
    contracts.py        ports et dataclasses partagés entre modules
    modules.py          découverte des modules (models/router/setup)
    workspaces/         espaces, jetons, pays, institutions
    audit/              ledger SHA-256 chaîné, ancres, vérification, export
    knowledge/          ingestion (PDF/OCR/DOCX/MD/TXT/CSV), RAG hybride, versions, archives d'export/import
    mandates/           catalogue d'actions, mandats validés, revue de registre
    agents/             agents, profils de modèle, runtime (boucle, outils, citations vérifiées)
    scenarios/          scénarios, injects, modes de panne, lint
    simulation/         exercices, moteur, tableau de coordination, sièges humains, SSE
    gaps/               détection de lacunes par règles explicites, preuves, revue
    evaluation/         mesures T1–T6, scorecard
    reports/            rapports versionnés immuables, rendus MD/JSON/CSV/XLSX/PDF
  migrations/           Alembic
  tests/                541 tests
  CONTRACTS.md          contrats entre modules
```

## 13. Problèmes courants

| Symptôme | Cause / correction |
|---|---|
| `unable to open database file` | `ALERTE_DATA_DIR` non inscriptible (les dossiers sont créés automatiquement au démarrage et par `alembic upgrade head`) |
| `SQLite sans FTS5` | Python/SQLite compilé sans FTS5 : utiliser un Python officiel ou celui de la distribution |
| `/ready` → `embedder.configured: false` ; recherche `degraded` | `ALERTE_EMBED_BASE_URL`/`ALERTE_EMBED_MODEL` non définis ou serveur injoignable (`curl $ALERTE_EMBED_BASE_URL/models`) |
| Agents en « Fallback (no model) », erreur `endpoint non configuré` | exercice en `ai_mode=ai` sans `ALERTE_LLM_BASE_URL` : configurez-le, ou créez l'exercice en `scripted` (démo SANS IA) |
| OCR : langue manquante | installer `tesseract-ocr-fra`/`-ara` ou définir `ALERTE_TESSDATA_DIR` |
| PDF : erreur Pango | installer `libpango-1.0-0 libpangoft2-1.0-0` |
| 401 en boucle | jeton révoqué ou expiré ; en recréer un depuis l'espace propriétaire |
| Port 8000 occupé | `--port 8001` (et `ALERTE_API_URL=http://localhost:8001` côté frontend) |
| Comportement ancien après une mise à jour du code | redémarrer uvicorn (sans `--reload`) |
