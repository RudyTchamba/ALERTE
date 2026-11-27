# Déploiement sur une machine Windows

**Statut : écrit à partir des documentations officielles citées et des scripts du dépôt ; aucune commande de ce guide n'a été exécutée sous Windows (NOT TESTED).** Si une étape échoue, notez le message exact : c'est un résultat de test utile.

## 0. Ce que Windows permet réellement
| Composant | Windows natif | Source |
|---|---|---|
| **Ollama** (génération et embeddings) | **Oui** : « Ollama runs as a native Windows application, including NVIDIA and AMD Radeon GPU support » ; Windows 10 22H2 ou plus ; NVIDIA : pilote ≥ 551.61 | https://docs.ollama.com/windows |
| **vLLM** | **Non** : « vLLM does not support Windows natively » ; la doc suggère WSL (Windows Subsystem for Linux) avec une distribution Linux | https://docs.vllm.ai/en/latest/getting_started/installation/gpu/ |
| **Docker Desktop + GPU NVIDIA** | Oui, **avec le backend WSL 2** : pilotes NVIDIA à jour, noyau WSL 2 à jour (`wsl --update`) | https://docs.docker.com/desktop/features/gpu/ |
| Application ALERTE (API + interface) | Python et Node tournent sous Windows ; `scripts/*.py` sont écrits pour Windows ; le rendu PDF des rapports (WeasyPrint) demande GTK/Pango (voir [install.md](../runbooks/install.md), repli prévu) | dépôt |

**Recommandation de chemin le plus simple** : *Ollama natif* pour les modèles + *application en Python natif* (ou en Docker). Ne choisissez vLLM sous Windows que via WSL 2 et si vous avez une raison (voir [dimensionnement](dimensionnement.md)).

## 1. Prérequis
| Élément | Installation | Vérification (PowerShell) |
|---|---|---|
| Python 3.12 | python.org (cocher « Add to PATH ») | `python --version` |
| Node 22 | nvm-windows ou fnm, puis `nvm use` dans `frontend/` | `node --version` |
| Git | git-scm.com | `git --version` |
| Tesseract + langues | installeur UB Mannheim (cocher *French*, *Arabic*), ajouter au `PATH` | `tesseract --list-langs` |
| Ollama | installeur depuis https://ollama.com (application native) | `ollama --version` |
| (option) Docker Desktop, WSL 2 | docker.com ; `wsl --install` | `docker --version` ; `wsl --status` |

Sonde matérielle : [sonde-materielle.md](../runbooks/sonde-materielle.md) (`python scripts\hardware_probe.py`).

## 2. Installer l'application (PowerShell, dossier `alerte-platform`)
```powershell
git clone <URL du dépôt> ; cd <dépôt>\alerte-platform
git checkout Rudy
python scripts\setup.py          # crée backend\.venv, installe les dépendances, copie .env.example -> backend\.env, npm ci
python scripts\doctor.py         # corriger les points BLOQUANT
```
Éditez `backend\.env` (Bloc-notes ou VS Code). **Chemins Windows** : utilisez des barres obliques ou des guillemets, par ex. `ALERTE_TESSDATA_DIR=C:/Program Files/Tesseract-OCR/tessdata` (chemin absolu).

## 3. Ollama natif
1. Installez Ollama ; il écoute sur `http://localhost:11434` (doc officielle).
2. Modèles : `ollama pull bge-m3` puis `ollama pull <modèle de génération retenu>` ; `ollama list` donne le **nom exact** à mettre dans `ALERTE_LLM_MODEL`.
3. **Contexte 8 192** (sans GPU puissant, le défaut est 4k) : variable d'environnement utilisateur `OLLAMA_CONTEXT_LENGTH=8192` (https://docs.ollama.com/context-length). Variables : Paramètres Windows → « Modifier les variables d'environnement de votre compte » ; **quittez Ollama (icône de la barre des tâches) puis relancez-le** (https://docs.ollama.com/faq).
4. Les modèles sont stockés par défaut dans `C:\Users\<vous>\.ollama\models` ; `OLLAMA_MODELS` les déplace vers un autre disque (même FAQ).
5. Pour que l'application d'**une autre machine** joigne cet Ollama : variable `OLLAMA_HOST=0.0.0.0:11434`, puis ouvrir le port 11434 dans le Pare-feu Windows **pour ces machines seulement**.

`backend\.env` : `ALERTE_LLM_BASE_URL=http://localhost:11434/v1`, `ALERTE_LLM_MODEL=<nom exact>`, `ALERTE_EMBED_BASE_URL=http://localhost:11434/v1`, `ALERTE_EMBED_MODEL=bge-m3`.

## 4. Démarrer et vérifier
```powershell
python scripts\dev.py                                    # backend :8000 + interface :5173
curl.exe http://localhost:8000/api/v1/health             # curl.exe (et non l'alias PowerShell `curl`)
curl.exe http://localhost:5173/api/v1/health
curl.exe http://localhost:11434/v1/models                # modèles servis par Ollama
```
Test du modèle dans l'application : *Agents → Profils de modèle → Tester la connexion*.

## 5. Variante vLLM via WSL 2 (GPU NVIDIA) — avancé, NOT TESTED
1. `wsl --install` (Ubuntu), pilote NVIDIA Windows à jour, `wsl --update` ; dans Ubuntu : suivre [linux.md](linux.md) option B (Docker + toolkit, ou installation vLLM dans WSL).
2. Depuis Windows, le service WSL est joignable en `localhost` (comportement par défaut de WSL 2 *à vérifier sur votre version*) : `curl.exe http://localhost:8001/v1/models`.

## 6. Variante Docker Desktop (application et/ou Ollama) — NOT TESTED
```powershell
Copy-Item deploy\env.app.example deploy\.env.app        # renseigner les URL des modèles
docker compose -f deploy\compose.app.yml --env-file deploy\.env.app up -d --build
# Ollama en conteneur avec GPU (conditions : Docker Desktop + WSL 2 + pilote NVIDIA) :
docker compose -f deploy\compose.models.yml -f deploy\compose.models.gpu.yml up -d ollama
docker run --rm -it --gpus=all nvcr.io/nvidia/k8s/cuda-sample:nbody nbody -gpu -benchmark   # test GPU proposé par la doc Docker
```
Docker Desktop fournit `host.docker.internal` : `ALERTE_LLM_BASE_URL=http://host.docker.internal:11434/v1` pour joindre un Ollama installé en natif.

## 7. Erreurs courantes
| Symptôme | Cause probable | Correction |
|---|---|---|
| `python` introuvable | PATH | réinstaller en cochant « Add to PATH » ; ou `py -3` |
| OCR « langues absentes » | langues non installées / tessdata | réinstaller Tesseract avec *French* et *Arabic* ; chemin absolu |
| PDF des rapports indisponible (Pango) | GTK absent | voir `install.md` : le rendu de repli s'applique |
| Modèle introuvable | nom (`:` du tag Ollama) | `ollama list` |
| Réponses tronquées | contexte 4k | `OLLAMA_CONTEXT_LENGTH=8192`, relancer Ollama |
| Machine très lente | pas de GPU | CPU seul : test de câblage uniquement |
