# Configuration d'ALERTE (`.env`) — matrice des variables et vérification avant démarrage

Le modèle de fichier est [`.env.example`](../../.env.example) (toutes les variables, commentées). Ce document donne, pour chacune, sa
fonction, son caractère obligatoire, la valeur attendue, ses dépendances et **le test qui prouve qu'elle est correcte**. Les valeurs
ci-dessous ont été relevées dans le code (`backend/app/core/config.py` et les modules cités) ; aucune n'est un secret.

## 1. Où est lu le `.env`, et dans quel ordre

1. Le backend lit **`.env` dans le dossier d'où il est lancé** (`backend/` pour `python -m uvicorn …` ou `scripts/dev.py`) : `config.py` (`env_file=".env"`).
2. **Une variable déjà définie dans le shell prime** sur le fichier.
3. Le fichier n'est relu qu'au **démarrage** : après toute modification, redémarrez le backend. (Exception : les noms de variables désignés par
   un *profil de modèle* sont relus à chaud.)
4. `.env` est protégé par `.gitignore` ; seul `.env.example` est suivi. Ne mettez **jamais** une clé dans un README, un guide ou un commit.

## 2. Vérifier avant de démarrer

```bash
cd alerte-platform
python scripts/doctor.py --backend-only      # Linux / macOS     (Windows : python scripts\doctor.py --backend-only)
```
Code de sortie 0 = aucun point bloquant. Le script contrôle : Python et `backend/.venv`, Node, Tesseract et ses langues (`ara`, `fra`, `eng`),
**le chemin `tessdata` (relatif = avertissement)**, le serveur de génération **et que le modèle configuré y est réellement servi**, le serveur
d'embeddings (idem), le dossier de données (inscriptible, espace libre), Docker. Un modèle absent du serveur est **BLOQUANT** (sinon un exercice
« Modèle réel » échouerait à chaque appel).

## 3. Matrice des variables

Légende : **O** obligatoire pour le cas d'usage indiqué · **F** facultative · test = commande ou action qui valide la valeur.

### Application et données
| Variable | Fonction | O/F | Valeur attendue | Dépend de | Test |
|---|---|---|---|---|---|
| `ALERTE_DATA_DIR` | racine des données (SQLite, blobs, vecteurs, ancres, exports) | F (défaut `./data`) | chemin, de préférence absolu | espace disque | `doctor.py` : « inscriptible, N Go libres » |
| `ALERTE_DB_URL` | URL SQLAlchemy | F | vide = SQLite dans `ALERTE_DATA_DIR/db` | architecture V1 (un écrivain) | l'API démarre : `curl localhost:8000/api/v1/health` |
| `ALERTE_UPLOAD_MAX_MB` | taille max d'un fichier importé | F (100) | entier | — | import d'un gros PDF |

### Génération (agents)
| Variable | Fonction | O/F | Valeur attendue | Dépend de | Test |
|---|---|---|---|---|---|
| `ALERTE_LLM_MODE` | `openai_compat` (vrai modèle) · `scripted` (SANS IA) · `cassette` (rejeu) | F (`openai_compat`) | l'une des trois | — | bandeau SANS IA dans l'interface |
| `ALERTE_LLM_BASE_URL` | serveur de génération | **O** pour « Modèle réel » | URL en `/v1` | serveur joignable | `curl "$ALERTE_LLM_BASE_URL/models"` |
| `ALERTE_LLM_MODEL` | nom EXACT du modèle servi | **O** pour « Modèle réel » | Ollama `nom:tag` · vLLM nom HF | modèle installé/servi | `doctor.py` (BLOQUANT si absent) ; préparation de l'exercice |
| `ALERTE_LLM_API_KEY` | clé du serveur | F | secret, seulement dans `backend/.env` | vLLM `--api-key` | `curl -H "Authorization: Bearer …" …/models` |
| `ALERTE_LLM_TIMEOUT_S` | délai d'un appel | F (120) | secondes | taille du modèle, CPU/GPU | un appel de profil : « Tester la connexion » |
| `ALERTE_MAX_LLM_CALLS` | plafond d'appels **par défaut** | F (199) | entier | critère T6 (< 200) | **le budget de l'exercice, saisi dans le formulaire, prime** |

### Embeddings et base vectorielle
| Variable | Fonction | O/F | Valeur attendue | Dépend de | Test |
|---|---|---|---|---|---|
| `ALERTE_EMBED_BASE_URL` | serveur d'embeddings | **O** pour construire une base avec vecteurs | URL en `/v1` | serveur joignable | `curl …/models` |
| `ALERTE_EMBED_MODEL` | modèle d'embeddings | **O** (avec l'URL) | `bge-m3` | modèle installé | `doctor.py` ; `python -m app.cli knowledge status` |
| `ALERTE_EMBED_PROVIDER` | `openai_compat` · `fixture` (tests, vecteurs factices) | F | `openai_compat` | — | jamais `fixture` pour une vraie base |
| `ALERTE_EMBED_API_KEY` | clé du serveur | F | secret | — | — |
| `ALERTE_EMBED_BATCH_SIZE` | extraits par requête | F (16) | 1 à 16 ; bas sur machine lente | RAM/CPU | build sans `ReadTimeout` |
| `ALERTE_EMBED_TIMEOUT_S` | délai d'une requête | F (60) | secondes ; 300 sur CPU seul | longueur des extraits | idem |
| `ALERTE_EMBED_REVISION` / `_RUNTIME` / `_QUANTIZATION` | empreinte de l'embedder | F | texte libre | changer l'une = **revectorisation complète** | `knowledge status` : empreinte |
| `ALERTE_AUTHORITY_SPREAD` | poids d'autorité du classement | F (0 = neutre) | 0 à 1 | évaluation de recherche | `scripts/kb_eval.py` |

### OCR
| Variable | Fonction | O/F | Valeur attendue | Dépend de | Test |
|---|---|---|---|---|---|
| `ALERTE_TESSDATA_DIR` | dossier contenant `ara/fra/eng.traineddata` | F si Tesseract du système a ces langues | **chemin absolu** (un relatif est résolu depuis le dossier courant, `backend/`, la plateforme puis le dépôt) | Tesseract installé | `tesseract --list-langs --tessdata-dir <chemin>` |
| `ALERTE_OCR_LANGS` | langues demandées | F (`ara+fra+eng`) | `+`-séparées | paquets de langues | `doctor.py` : « langues manquantes » |

### Exécution, web et sécurité
| Variable | Fonction | O/F | Valeur attendue | Test |
|---|---|---|---|---|
| `ALERTE_MAX_CONCURRENT_EXERCISES` | exercices simultanés | F (2) | entier | — |
| `ALERTE_JOB_WORKERS` | tâches de fond | F (2) | entier | `knowledge build` |
| `ALERTE_LOG_LEVEL` / `ALERTE_LOG_JSON` | journalisation | F | `INFO` / `true` | — |
| `ALERTE_CORS_ORIGINS` | origines autorisées | F | URL(s) séparées par `,` | navigateur sans erreur CORS |
| `ALERTE_BOOTSTRAP_ENABLED` | création d'espace libre au 1er démarrage | F (false) | `false` en usage normal | — |
| `ALERTE_SIGNING_KEY_PATH` | clé Ed25519 des ancres | F | chemin | `Audit` : vérification de la chaîne |

### Frontend et outils
| Variable | Fonction | Où | Valeur |
|---|---|---|---|
| `ALERTE_API_URL` | cible du proxy de développement Vite | environnement du shell avant `npm run dev` | `http://localhost:8000` (défaut) |
| `VITE_API_BASE` | chemin de l'API vu par le navigateur | build Vite | `/api/v1` (défaut) |
| `ALERTE_ENV_FILE` | fichier lu/écrit par `scripts/llm_target.py` | environnement | `backend/.env` (défaut) |
| `ALERTE_LEGACY_DIR` | dossier `alerte/` (scénarios et rôles seulement) | environnement | auto-détecté |
| `ALERTE_TOKEN` | jeton d'API pour `ledger_tamper_demo.py` | environnement, jamais en argument | jeton |
| `ALERTE_LLM_<NOM>_BASE_URL/_MODEL/_API_KEY` | préréglages de machines d'inférence | écrits par `scripts/llm_target.py` | — |

## 4. Exemples

**Poste local (test de câblage, petit modèle, étiqueté tel)** — `backend/.env` :
```
ALERTE_LLM_BASE_URL=http://localhost:11434/v1
ALERTE_LLM_MODEL=qwen2.5:1.5b-instruct
ALERTE_EMBED_BASE_URL=http://localhost:11434/v1
ALERTE_EMBED_MODEL=bge-m3
ALERTE_TESSDATA_DIR=/chemin/absolu/vers/tessdata
```
Un petit modèle ne valide **pas** la qualité des décisions ni de la coordination : il vérifie seulement que la chaîne technique fonctionne.

**Application sur une machine, modèles sur une autre** — sur la machine applicative, remplacer les deux URL par celles de la machine d'inférence
(`http://<adresse>:11434/v1` pour Ollama, ou l'URL d'un tunnel SSH pour vLLM) ; voir [le déploiement](../deploiement/README.md).

## 5. Erreurs courantes
| Symptôme | Cause | Correction |
|---|---|---|
| Préparation de l'exercice bloquée : « modèle … inaccessible » | nom de modèle faux, serveur arrêté, URL erronée | `doctor.py` ; `curl …/models` ; corriger `ALERTE_LLM_MODEL` ; **redémarrer** le backend |
| OCR : « langues OCR absentes » | `ALERTE_TESSDATA_DIR` faux ou langues non installées | chemin absolu ; `tesseract --list-langs --tessdata-dir …` |
| `ReadTimeout` pendant la construction d'une base | machine lente, extraits longs | `ALERTE_EMBED_BATCH_SIZE=1`, `ALERTE_EMBED_TIMEOUT_S=300` |
| « vecteurs incomplets » à la publication | embeddings non terminés | relancer l'étape `embed` (voir la CLI), puis publier |
| Modification du `.env` sans effet | backend non redémarré, ou variable du shell qui prime | redémarrer ; `env | grep ALERTE_` |
