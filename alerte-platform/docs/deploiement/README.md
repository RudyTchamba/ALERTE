# Déployer ALERTE — Linux, Windows, AWS Sandbox

**Principe.** ALERTE se compose de deux parties qui communiquent **uniquement par des URL configurables** (aucun changement de code d'une machine à l'autre) :

| Partie | Contenu | Machine type |
|---|---|---|
| **Application** | API FastAPI, interface React, base SQLite, stockage des documents et index vectoriel, moteur de simulation | n'importe quelle machine (CPU suffit) |
| **Inférence** | modèle de **génération** (agents), modèle d'**embeddings** (recherche) ; reranker : *non implémenté*, aucune variable à régler | machine avec GPU pour de vrais résultats |

```
 Navigateur ──► [ Application :8000 ] ──ALERTE_LLM_BASE_URL────► [ Inférence : génération (Ollama :11434 | vLLM) ]
                                       └─ALERTE_EMBED_BASE_URL──► [ Inférence : embeddings (Ollama :11434) ]
```
Les deux parties peuvent être sur la **même machine** ou sur **deux machines**. La génération et les embeddings peuvent aussi être sur deux machines différentes (variables indépendantes).
La base de données reste **SQLite, un seul écrivain** (architecture V1) : une seule instance de l'application écrit dans un espace de données.

## Choisir la procédure

| Vous avez… | Procédure |
|---|---|
| une machine **Linux** (poste ou serveur) | [linux.md](linux.md) |
| une machine **Windows** | [windows.md](windows.md) |
| le compte **AWS Sandbox** (par le coéquipier qui détient les accès) | [aws-sandbox.md](aws-sandbox.md) |
| à décider **quelle machine** héberge les modèles | 1) [sonde matérielle](../runbooks/sonde-materielle.md) sur chaque machine, 2) [dimensionnement](dimensionnement.md) |

## Ce qui change d'un environnement à l'autre : seulement la configuration
| Réglage | Variable (voir [`.env.example`](../../.env.example), [matrice](../runbooks/configuration-env.md)) |
|---|---|
| machine de génération | `ALERTE_LLM_BASE_URL`, `ALERTE_LLM_MODEL`, `ALERTE_LLM_API_KEY` ; bascule locale/AWS : `python scripts/llm_target.py` |
| machine d'embeddings | `ALERTE_EMBED_BASE_URL`, `ALERTE_EMBED_MODEL` |
| données | `ALERTE_DATA_DIR` |
| OCR | `ALERTE_TESSDATA_DIR` (chemin absolu), `ALERTE_OCR_LANGS` |

## Ports
| Port | Service | Exposition recommandée |
|---|---|---|
| 8000 | application (API + interface) | le réseau de l'équipe, ou `localhost` + tunnel SSH |
| 5173 | interface en développement (Vite, `scripts/dev.py`) | `localhost` (ou `--host` pour téléphones des joueurs) |
| 11434 | Ollama (génération et/ou embeddings) | `localhost` par défaut ; l'ouvrir au réseau demande `OLLAMA_HOST=0.0.0.0:11434` **et** un pare-feu |
| 8001 (hôte) → 8000 (conteneur) | vLLM (profil `vllm` de `deploy/compose.models.yml`) | **`127.0.0.1` seulement** ; accès distant par tunnel SSH |

Ne jamais exposer un serveur de modèle à Internet sans authentification (clé d'API) et filtrage réseau.

## Fichiers fournis
| Fichier | Rôle | Statut de vérification |
|---|---|---|
| `scripts/hardware_probe.py` | sonde matérielle multiplateforme | exécutée sur Linux ; **Windows/macOS/AWS : NOT TESTED** |
| `scripts/doctor.py` | contrôle de l'environnement et des serveurs de modèles | exécuté sur Linux |
| `deploy/docker/Dockerfile`, `deploy/compose.app.yml`, `deploy/env.app.example` | application en conteneur | syntaxe validée (`docker compose config`) ; **construction de l'image : NOT TESTED** |
| `deploy/compose.models.yml`, `deploy/compose.models.gpu.yml` | Ollama (CPU/GPU) et vLLM (profil `vllm`) | syntaxe validée ; **exécution : NOT TESTED** |
| `scripts/aws/setup_vllm.sh` | vLLM sur une instance EC2 GPU | existant ; **non exécuté ici** |
| `scripts/llm_target.py` | bascule de la machine de génération | existant ; **non exécuté ici (il modifie `backend/.env`)** |
