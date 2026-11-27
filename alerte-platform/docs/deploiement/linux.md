# Déploiement sur une machine Linux

Testé : le démarrage local sur Linux (Ubuntu, cette machine de développement) ; **les installations Ollama/Docker ci-dessous n'ont pas été rejouées pour ce guide** (marquées NOT TESTED).

## 0. Prérequis
| Élément | Version / commande | Vérification |
|---|---|---|
| Python | 3.12 recommandé (3.11 minimum) | `python3 --version` |
| Node.js | 22 (fichier `.nvmrc`), via nvm | `node --version` |
| Tesseract + langues | `sudo apt install tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng tesseract-ocr-ara` | `tesseract --list-langs` (doit lister `ara eng fra`) |
| Pango (PDF des rapports) | `sudo apt install libpango-1.0-0 libpangoft2-1.0-0` | `python scripts/doctor.py` |
| Git | — | `git --version` |
| Matériel | **minimum** application seule : 2 cœurs, 4 Go RAM, 10 Go disque · **avec Ollama + modèle sur la même machine** : voir [dimensionnement](dimensionnement.md) | [sonde](../runbooks/sonde-materielle.md) |

## 1. Installer l'application (Terminal 1)
```bash
git clone <URL du dépôt> && cd <dépôt>/alerte-platform
git checkout Rudy                       # branche de travail actuelle
python3 scripts/setup.py                # crée backend/.venv, installe les dépendances, copie .env.example -> backend/.env, npm ci
python3 scripts/doctor.py               # lit le résultat : corriger les points BLOQUANT
```
`setup.py` ne remplace jamais un `backend/.env` existant. **Éditez ensuite `backend/.env`** (matrice : [configuration-env.md](../runbooks/configuration-env.md)).

## 2. Serveur de modèles
### Option A — Ollama sur cette machine (NOT TESTED dans ce guide)
```bash
curl -fsSL https://ollama.com/install.sh | sh          # installation officielle ; vérifiez le script avant de l'exécuter si vous le souhaitez
ollama pull bge-m3                                       # embeddings
ollama pull <modèle de génération retenu>                # nom exact : voir `ollama list` ensuite
```
**Contexte** (indispensable) : sans GPU puissant Ollama utilise 4 096 jetons par défaut (doc officielle : « < 24 GiB VRAM: 4k context » — https://docs.ollama.com/context-length) alors qu'un prompt d'agent peut atteindre ~4 000 jetons + 1 024 de sortie. Variable : `OLLAMA_CONTEXT_LENGTH=8192`. Avec le service systemd (https://docs.ollama.com/faq) :
```bash
sudo systemctl edit ollama.service      # ajouter :  [Service]  puis  Environment="OLLAMA_CONTEXT_LENGTH=8192"
sudo systemctl daemon-reload && sudo systemctl restart ollama
```
**Vérification** : `curl http://localhost:11434/v1/models` liste les modèles ; puis dans `backend/.env` :
```
ALERTE_LLM_BASE_URL=http://localhost:11434/v1
ALERTE_LLM_MODEL=<nom exact tel qu'affiché par `ollama list`>
ALERTE_EMBED_BASE_URL=http://localhost:11434/v1
ALERTE_EMBED_MODEL=bge-m3
```
Pour que **d'autres machines** (l'application sur un autre poste) joignent cet Ollama : `Environment="OLLAMA_HOST=0.0.0.0:11434"` dans le même service, **et** ouvrir le port 11434 à ces seules machines dans le pare-feu.

### Option B — vLLM (GPU NVIDIA) (NOT TESTED dans ce guide)
Prérequis : pilote NVIDIA, Docker, `nvidia-container-toolkit`. Doc officielle : vLLM cible Linux, GPU NVIDIA de capacité de calcul ≥ 7.5 (https://docs.vllm.ai/en/latest/getting_started/installation/gpu/).
```bash
VLLM_MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ docker compose -f deploy/compose.models.yml --profile vllm up -d vllm
curl http://127.0.0.1:8001/v1/models
```
Puis `ALERTE_LLM_BASE_URL=http://127.0.0.1:8001/v1` et `ALERTE_LLM_MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ`. L'image est figée en `v0.8.5` (comme `scripts/aws/setup_vllm.sh`) : un modèle plus récent peut exiger une version de vLLM plus récente — **à vérifier avant** (Granite 4.2 : fiche du modèle).

## 3. Démarrer (Terminal 1) et vérifier
```bash
cd alerte-platform && python3 scripts/dev.py          # backend :8000 + interface :5173 ; Ctrl-C arrête les deux
curl http://localhost:8000/api/v1/health              # {"status":"ok",…}
curl http://localhost:5173/api/v1/health              # même réponse via le proxy de l'interface
```
Interface : http://localhost:5173 (création de l'espace : écran `/access`). **Test du modèle** : dans l'application, *Agents → Profils de modèle → Tester la connexion*, ou préparer un exercice en « Modèle réel » : un modèle inaccessible **bloque** la préparation avec un message explicite.

## 4. Variante Docker (application) (NOT TESTED)
```bash
cp deploy/env.app.example deploy/.env.app             # renseigner les URL des modèles
docker compose -f deploy/compose.app.yml --env-file deploy/.env.app up -d --build
curl http://localhost:8000/api/v1/health
```
Depuis le conteneur, Ollama installé sur l'hôte se joint par `http://host.docker.internal:11434/v1` (`extra_hosts` configuré ; sur Linux, Ollama doit écouter sur une adresse accessible depuis le pont Docker : `OLLAMA_HOST=0.0.0.0:11434`).

## 5. Erreurs courantes
| Symptôme | Cause | Correction |
|---|---|---|
| `doctor.py` : modèle absent du serveur | nom différent (`qwen2.5-14b-instruct` ≠ `qwen2.5:14b-instruct`) | `ollama list` puis corriger `ALERTE_LLM_MODEL` |
| OCR « langues absentes » | paquets `tesseract-ocr-*` ou `ALERTE_TESSDATA_DIR` | voir §0 ; chemin absolu |
| Réponses tronquées / JSON invalide | contexte 4k | `OLLAMA_CONTEXT_LENGTH=8192` |
| `connection refused` vers le modèle depuis un conteneur | `localhost` désigne le conteneur | `host.docker.internal` ou l'IP de la machine |
