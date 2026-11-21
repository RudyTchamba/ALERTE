# Installation et exécution d'ALERTE Platform

Le même code tourne sur **Ubuntu/Linux, Windows et macOS** ; Docker et Podman sont **optionnels**. La puissance de la machine n'est pas une contrainte : les modèles et les embeddings tournent sur un **serveur configurable** (votre poste, une machine de l'équipe ou le Sandbox).

## 1. Prérequis

| Outil | Version | Remarque |
|---|---|---|
| Python | 3.11+ (3.12 recommandé) | `python3 --version` ; jamais d'installation globale de paquets |
| Node.js | 22 (`.nvmrc`) | via **nvm** (Linux/macOS) ou **nvm-windows/fnm** ; **jamais `sudo npm`** |
| Tesseract | 5.x avec `ara`, `fra`, `eng` | OCR des PDF scannés (optionnel pour développer) |
| Pango | — | requis par WeasyPrint (PDF) ; repli prévu si absent |
| Git | — | |

Installation des dépendances système :

* **Ubuntu/Debian** : `sudo apt install tesseract-ocr tesseract-ocr-fra tesseract-ocr-ara libpango-1.0-0 libpangoft2-1.0-0`
* **macOS** : `brew install tesseract tesseract-lang pango`
* **Windows** : installeur Tesseract (UB Mannheim) + ajouter au `PATH` ; Pango via MSYS2 (voir la doc WeasyPrint) ou utiliser le rendu de repli ; `ALERTE_TESSDATA_DIR` si les langues sont dans un dossier à part.

## 2. Installation (toutes plateformes)

```bash
git clone <dépôt> && cd <dépôt>/alerte-platform
python scripts/setup.py            # crée backend/.venv, installe requirements-dev.txt avec `python -m pip`, copie .env.example, npm ci
python scripts/doctor.py           # vérifie l'environnement et explique quoi corriger
```

`setup.py` accepte `--python /chemin/python3.12` et `--skip-frontend`. Sous nvm : `nvm install && nvm use` (lit `.nvmrc`) **avant** `setup.py`.

Équivalent manuel (backend) :

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt      # Windows : .venv\Scripts\python
```

## 3. Configuration (`backend/.env`, jamais commité)

Voir `.env.example`. Les deux serveurs sont **indépendants** :

```ini
ALERTE_LLM_BASE_URL=http://machine-equipe:8000/v1     # génération (Ollama, vLLM, API compatible OpenAI)
ALERTE_LLM_MODEL=qwen2.5-14b-instruct
ALERTE_EMBED_BASE_URL=http://machine-equipe:8080/v1   # embeddings (BGE-M3 via TEI/Ollama/vLLM)
ALERTE_EMBED_MODEL=bge-m3
```

## 4. Lancer

```bash
python scripts/dev.py                    # API http://localhost:8000/api/v1/docs + frontend http://localhost:5173
# ou séparément :
cd backend && .venv/bin/python -m uvicorn app.main:app_factory --factory --reload
cd frontend && npm run dev
```

Premier démarrage : créer un espace de travail depuis l'interface (le **jeton propriétaire est affiché une seule fois**).

## 5. Tests

```bash
cd backend
.venv/bin/python -m pytest -m "not model and not gpu"          # tests unitaires et d'intégration (aucun modèle requis)
ALERTE_LLM_BASE_URL=… ALERTE_EMBED_BASE_URL=… .venv/bin/python -m pytest -m model   # tests IA RÉELS (machine adaptée)
cd ../frontend && npm test && npm run typecheck && npm run build
```

Les modes `scripted` et `cassette` servent aux tests déterministes : **ils ne prouvent jamais le fonctionnement de l'IA** ; seuls les tests `-m model` exécutés avec un vrai modèle et de vrais embeddings le font.

## 6. Dépendances : reproductibilité

* Backend : `requirements.in` (directes) → `requirements.txt` (versions épinglées, Python 3.12). Régénération : installer dans un venv propre, `pip freeze`, reporter les versions des dépendances directes.
* Frontend : `package.json` + `package-lock.json` (`npm ci`).
* **PyMuPDF (AGPL) est interdit** (contrôlé en CI).

## 7. Sauvegarde et restauration

Copier le dossier `ALERTE_DATA_DIR` (arrêter l'application, ou utiliser `sqlite3 alerte.sqlite ".backup copie.sqlite"` pour la base) ; les blobs sont adressés par SHA-256. Les bases de connaissances et les rapports s'exportent en archives portables depuis l'interface.
