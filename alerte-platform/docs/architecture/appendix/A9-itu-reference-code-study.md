> **Annexe — Étude du dépôt de référence cité par le hackathon (CrashingGuru/ITUAIReadiness).**
> Matériau de recherche brut produit le 2026-11-21 par un sous-agent (modèle Haiku 5.5), relu en partie par l'architecte. Les marqueurs « non vérifié » / `[NV]` / `[V]` / `[P]` / `[S]` / `[LU]` / `[SUPPOSÉ]` sont ceux du sous-agent. Pièce justificative, pas une spécification.

---

# 10 - Analyse du dépôt de référence ITU : CrashingGuru/ITUAIReadiness

Date d'analyse : 2026-11-21. Clone superficiel (`--depth 1`) dans `/tmp/claude-1000/-home-rtti-Documents-Github-ALERTE-for-ITUAIReadiness/47bfe664-a298-43d9-bfe6-a48c60d63119/scratchpad/itu-ref/repo`. Aucun code du dépôt n'a été exécuté. Lecture seule (cat, grep, awk sur les JSON de notebooks, WebFetch de l'API GitHub).

Légende de certitude : **[LU]** = lu dans le code ou les fichiers ; **[DÉDUIT]** = inféré d'indices concordants ; **[SUPPOSÉ]** = connaissance générale non vérifiée dans le dépôt.

---

## 0. Identité du dépôt (LU)

- Dépôt : `github.com/CrashingGuru/ITUAIReadiness`, propriétaire `CrashingGuru`, **un seul contributeur** (CrashingGuru, 23 contributions), non-fork, non archivé.
- Description GitHub : « This repo contains code for training for ITU AI Readiness ». README.md : deux lignes, aucune doc d'installation à la racine.
- Créé le 2026-03-22 ; dernier push le 2026-10-20 ; 3 étoiles, 5 forks, 3 issues ouvertes ; taille 163 Mo (API) / 321 Mo (clone de travail).
- HEAD : `84010da` « Change default example country from Ethiopia to UAE » (Vishnu Ram OV, 2026-10-20). Un clone superficiel ne montre qu'un commit : nombre total de commits **non vérifié**.
- Auteurs cités : « Vishnu & Jiaying » (en-tête du notebook racine, 22 mars 2026).
- **Ce n'est pas un dépôt officiel de l'ITU.** Le nom ITU n'apparaît que dans le contenu (cadre, données). La page du hackathon le lie comme « Reference code for KB creation » [LU via WebFetch].
- Maintenance : activité récente (octobre 2026), 1 mainteneur, aucun test (voir section J).

---

## A. Ce que le code réalise réellement (bout en bout)

Deux pipelines distincts coexistent. Seul le premier est un « jeu de simulation » ; le second est un notebook de RAG générique.

### A.1 Pipeline 1 : `simulation/` (serveur FastAPI + ChromaDB + Ollama)

1. **Ingestion (CLI)** : `python -m server.knowledge.ingest [--dir] [--reset] [--framework-only]` [LU, `simulation/server/knowledge/ingest.py`, fonction `main`].
   - `ingest_framework_definitions(kb)` lit `data/framework/dimensions.json` et crée 13 documents « dimension » + 6 documents « factor » dans la collection `kb_framework`. Exécuté **à chaque lancement** de l'ingestion, sans déduplication.
   - `ingest_directory(dir, kb)` parcourt les fichiers du dossier racine (catégorie `general`) et de chaque sous-dossier (catégorie = nom du sous-dossier). Extensions prises en charge : `.pdf .txt .md .csv .html`. `Inputs.md` est ignoré.
   - `ingest_file` : `parse_file` → `chunk_text` → `embed_texts` (Ollama) → `kb.add_documents` (collection `kb_main`).
   - `ingest_usecase_docs` écrit ensuite les fichiers de `AI_Use_Cases/` dans `kb_usecase`.
2. **Parsing** [LU] : `_parse_pdf` tente `docling.document_converter.DocumentConverter` (import optionnel, `try/except ImportError`), puis repli sur PyMuPDF (`fitz`) si docling est absent ou si le texte produit fait moins de 100 caractères. `.txt/.md/.csv` : lecture UTF-8 brute ; `.html` : suppression naïve des balises par regex. **docling n'est pas dans `requirements.txt`** ni dans le Dockerfile : en pratique, PyMuPDF est le parseur utilisé [DÉDUIT].
3. **Chunking** [LU] : `chunk_text(text, chunk_size=settings.chunk_size, overlap=settings.chunk_overlap, max_chars=2000)`. Découpe par **mots** (pas par tokens) : fenêtre de 256 mots, chevauchement de 30 mots (valeurs de `server/config.py`). Plafond dur de 2000 caractères par chunk. Les paragraphes sont lus mais les frontières ne sont pas respectées de façon stricte (les mots sont aplatis).
   - **Incohérence** : la docstring d'`ingest.py` annonce « ~512 tokens, 50 overlap » ; la docstring de `embed_texts` annonce une troncature à 7500 caractères ; le code tronque à 2000. Le code fait foi.
4. **Embeddings** [LU] : `embed_texts` appelle `ollama.Client.embed(model=settings.embed_model)` par lots de 16 ; `embed_model` = `nomic-embed-text` (config). Troncature à 2000 caractères avant envoi. Repli un par un, puis troncature à 4000 caractères en dernier recours.
5. **Stockage** [LU] : `server/knowledge/kb.py`, `chromadb.PersistentClient(path=data/chromadb)`. Collections (cosine) : `kb_main`, `kb_framework`, `kb_decisions`, `kb_usecase`. IDs = `uuid4()`.
6. **Requête (agents)** [LU] : `BaseAgent.run` (`server/agents/base.py`) :
   - embed de la requête ;
   - `_retrieve` : top-3 framework (10 en clarification) ; pour l'évaluation/what-if : `search_by_dimension` par dimension de l'agent (filtre `dimension_id`), top-5 global, top-5 filtré par `country` ; dédoublonnage par les 100 premiers caractères ; plafond 20 ;
   - prompt (system + évidences tronquées à 300 ou 800 caractères) ;
   - appel `ollama.Client.chat(model=llm_model, format="json", options={temperature 0.3, num_predict 8192, num_ctx 12288})` ;
   - parsing JSON → `AgentResponse` (scores 0-5, confiance, lacunes, recommandations). En cas d'échec, repli sur texte brut.
   - **Défaut confirmé** : `search_by_dimension` filtre sur `where={"dimension_id": ...}` dans `kb_main`, or les chunks de `kb_main` n'ont **pas** de métadonnée `dimension_id` (seuls les documents `kb_framework` l'ont). Ces recherches renvoient donc vide, silencieusement (`try/except: pass`). La collection `kb_decisions` n'est jamais interrogée par la recherche.
7. **Routage** [LU] : `server/agents/router.py` : `_DIMENSION_AGENT_MAP` (dimension → agents) et `_KEYWORD_DIMENSION_HINTS` (mots-clés → dimensions). Fusion : pour chaque dimension, le score de plus forte confiance est gardé ; les narratifs sont concaténés (évaluation) ou le plus long est gardé (clarification, what-if).
8. **Flux métier** (`server/game/engine.py`, `GameEngine`) :
   - `register_delegate` → session SQLite (`DelegateSession`) ;
   - `assess_country` → `router.assess` (les 13 dimensions) → `aggregate_agent_responses` (13 scores, dimension non évaluée = score 0, confiance 0) → `save_scenario` (JSON + `DimensionScoreRecord`) ;
   - `clarify` → `router.clarify` (sans contexte pays) ;
   - `whatif` → cache éphémère `KnowledgeCache` (ChromaDB `EphemeralClient`) remplie de 20 documents KB + 10 documents du pays + hypothèse ; agents ; propagation dans le graphe causal (`causal_graph.py`, `apply_propagation`, profondeur 3, décroissance 0,5, seuil 0,01) ; comparaison ; suppression du cache dans `finally` ;
   - `decide` → `router.assess` sur le texte de décision → `DecisionRecord` (SQLite) + `kb.add_decision` (collection `kb_decisions`, **jamais relue**) → nouveau scénario calculé par le LLM → propagation → `AuditLog`. Le champ `applied` n'est jamais mis à `True` (grep).
   - `standardise_usecase` / `usecase_readiness` : `UseCaseAgent` (`server/agents/usecase.py`) : mappe un cas d'usage sur les nœuds Y.3172 (SRC, C, PP, M, P, D, SINK, MLFO, Sandbox), produit exigences et lacunes (LLM, JSON). Recherche dans `kb_usecase` puis `kb_framework`.
9. **Interfaces** : API REST FastAPI (`server/main.py`, routeurs `routes/*.py`, 22 décorateurs de route ; le README annonce 24), WebSocket `/ws/{session_id}` (écho, aucune logique métier), CLI Rich (`cli/app.py`, client HTTP `httpx`), et notebook Colab (voir C et J).

### A.2 Pipeline 2 : `Colab Free Tier LLM Notebook.ipynb` (racine, indépendant)

Notebook RAG autonome (LU, cellules 1 à 12 lues) :
- `pypdf` pour les PDF, lecture brute pour `.txt/.md` ;
- chunks de 800 caractères, chevauchement 120, coupe sur espace, minimum 80 caractères ;
- embeddings `sentence-transformers/all-MiniLM-L6-v2` (normalisés, 384 dimensions [SUPPOSÉ]) ;
- index FAISS `IndexFlatIP` sauvegardé dans Google Drive avec `metadata.pkl` ;
- LLM local GGUF `bartowski/Llama-3.2-1B-Instruct-GGUF` (Q4_K_M, ~700 Mo) via `llama-cpp-python` ;
- `ask_kb(query)` : top-4, prompt « réponds uniquement à partir du contexte », citation des fichiers sources.
Ce pipeline ne produit aucun knowledge record structuré (seulement `source`, `chunk_id`, `text`).

### A.3 Ce qui n'existe PAS dans le dépôt (LU, vérifié par `find`)

- Pas de front-end (aucun React, aucun HTML/JS). Pas de dossier `tests` contenant de vrais tests (seulement `tests/__init__.py`, vide).
- Pas de scraping / extraction par LLM vers un schéma structuré : l'extraction est textuelle + métadonnées par regex sur le nom de fichier.
- Pas de distribution ni d'hébergement de la KB (ChromaDB locale, volumes Docker).

---

## B. Arborescence commentée (LU)

```
ITUAIReadiness/
├── README.md                         2 lignes (« This repo contains code for training for ITU AI Readiness »)
├── LICENSE                           MIT, © 2026 Vishnu Ram OV
├── .gitignore                        standard Python (212 lignes)
├── Colab Free Tier LLM Notebook.ipynb  RAG FAISS + Llama 1B GGUF (pipeline 2, 31 cellules)
└── simulation/                       le jeu (pipeline 1)
    ├── README.md                     doc principale (Docker, CLI, API, config env AIREADY_*)
    ├── PARTICIPANT_GUIDE.md          284 lignes, guide pas-à-pas pour participants (Docker)
    ├── AI_Readiness_Game_Colab.ipynb  notebook Colab qui appelle l'API (cassé, voir J)
    ├── AI_Readiness_Simulation_Game_Plan.docx, AI_Readiness_Game_Slides.pptx  (non lus, binaires)
    ├── requirements.txt              13 dépendances, bornes inférieures seulement
    ├── Dockerfile                    python:3.11-slim, COPY server/ cli/ data/ run_*.py
    ├── docker-compose.yml            services ollama + server, volumes chromadb_data, game_db
    ├── setup.sh                      pull qwen2.5:14b + nomic-embed-text, ingestion
    ├── run_server.py, run_cli.py     lanceurs
    ├── .gitignore, .dockerignore
    ├── data/
    │   └── framework/dimensions.json  13 dimensions, 111 métriques, 6 facteurs (framework ITU v2.0 janv. 2026)
    ├── server/
    │   ├── main.py                   app FastAPI, CORS « * », WebSocket écho, /health, /
    │   ├── config.py                 Settings pydantic (préfixe AIREADY_)
    │   ├── database.py               SQLite via SQLModel (data/game.db)
    │   ├── models.py                 Pydantic + tables SQLModel (DelegateSession, AuditLog, DecisionRecord, DimensionScoreRecord)
    │   ├── agents/
    │   │   ├── base.py               BaseAgent : retrieval RAG + prompt + Ollama JSON + parsing (508 lignes)
    │   │   ├── router.py             mapping dimension→agent, mots-clés, fusion
    │   │   ├── dataset.py            D1, D2 (marketplace de données, contenu généré)
    │   │   ├── opensource.py         D2, D5
    │   │   ├── sandbox.py            D10, D11
    │   │   ├── research.py           D3, D4, D9
    │   │   ├── deployment.py         D5, D12, D13
    │   │   ├── standards.py          D6, D7, D8
    │   │   └── usecase.py            Y.3172 (9 nœuds), kb_usecase
    │   ├── knowledge/
    │   │   ├── kb.py                 ChromaDB persistant, 4 collections
    │   │   ├── cache.py              ChromaDB éphémère pour what-if
    │   │   ├── ingest.py             parsing, chunking, embeddings, ingestion (CLI)
    │   │   ├── dimensions.py         lecture de dimensions.json (lru_cache)
    │   │   └── InputDocs/            corpus (62 fichiers AI_Strategies + 5 AI_Use_Cases + Inputs.md)
    │   ├── game/
    │   │   ├── engine.py             orchestrateur (assess, clarify, whatif, decide, usecase)
    │   │   ├── session.py            CRUD sessions, scénarios, décisions, AuditLog
    │   │   ├── scoring.py            agrégation 13 dimensions, niveaux de maturité, composite
    │   │   └── causal_graph.py       NetworkX DiGraph, 20 arêtes pondérées (poids « dérivés » sans source chiffrée)
    │   └── routes/                   delegates, query, whatif, usecase, decisions, dashboard
    ├── cli/app.py                    client Rich (579 lignes)
    └── tests/__init__.py             vide
```

---

## C. Schéma exact des knowledge records (LU)

Il n'y a **pas de schéma unique**. Chaque collection Chroma a son propre format. Tous les IDs sont des `uuid4` en chaîne (non déterministes). Toutes les métadonnées sont des chaînes (`str(v)`) sauf celles de `add_decision`.

**C.1 `kb_main` / `kb_usecase` : un chunk de document**
| Champ | Type | Source |
|---|---|---|
| `id` | str (uuid4) | `kb.add_documents` |
| `document` | str, ≤ 2000 car., ~256 mots | `chunk_text` |
| `embedding` | float[] (nomic-embed-text, dim. [SUPPOSÉ] 768) | Ollama |
| `metadata.source_file` | str (nom de fichier) | `build_metadata` |
| `metadata.source_type` | str, déduit par regex du nom (`standards_document`, `international_org_report`, `national_strategy`, `policy_document`) | `infer_source_type` |
| `metadata.country` | str, déduit par regex du nom, défaut `global` | `infer_country` |
| `metadata.chunk_index`, `total_chunks` | str | |
| `metadata.ingested_at` | str ISO (`datetime.utcnow`) | |
| `metadata.document_category` | str (`AI_Strategies`, `AI_Use_Cases`, `general`) | `ingest_directory` |
| `metadata.<extra>` | str | `extra_metadata` |

Absents : titre, auteur, année, URL, éditeur, licence, date de publication, page, hash du fichier, version du document, identifiant stable de document.

**C.2 `kb_framework`** : deux familles.
- Dimension : `dimension_id` (str), `dimension_name`, `short_name`, `source_type="framework_definition"`, `entity_type="dimension"`, `factors` (liste séparée par virgules). Document = titre + description + facteurs + liste des métriques.
- Facteur : `factor_id`, `factor_name`, `source_type="framework_definition"`, `entity_type="factor"`.

**C.3 `kb_decisions`** : `document` = `"DECISION by <pays>: <texte>"`, `metadata` = `country`, `session_id`, `affected_dimensions` (liste séparée par virgules), `timestamp`, `entity_type="decision"`. Jamais relue par le code.

**C.4 Cache éphémère** : IDs préfixés `c_<id>`, `hyp_<8 car.>` pour l'hypothèse ; `is_hypothetical=True`.

**C.5 Enregistrements SQLite** (`models.py`, LU) : `DelegateSession(id, country_name, delegate_name, created_at, is_active, scenario_json)`, `DecisionRecord(id, session_id, delegate_id, country_name, decision_text, affected_dimensions, timestamp, applied)`, `DimensionScoreRecord(id, session_id, delegate_id, country_name, dimension_id, score, confidence, evidence_json, timestamp)`, `AuditLog(id, timestamp, action, user_id, entity_type, entity_id, old_value, new_value, source, reason)`.

**C.6 Réponse d'agent** (`AgentResponse`, LU) : `agent_name`, `dimensions_assessed[]`, `scores[]` (`dimension_id`, `dimension_name`, `score` 0-5, `evidence[]`, `metrics{}`, `confidence` 0-1, `gaps[]`, `recommendations[]`), `narrative`, `sources_used[]`, `reasoning_chain[]`.

---

## D. Pile technique et exigences d'exécution

| Élément | Choix (LU) | Remarque |
|---|---|---|
| Langage / web | Python 3.11 (Docker), FastAPI ≥0.115, uvicorn, websockets | pas de front |
| LLM | Ollama, `qwen2.5:14b` par défaut (`AIREADY_LLM_MODEL`) | alt. `llama3.1:8b` dans le guide |
| Embeddings | Ollama `nomic-embed-text` | dimension [SUPPOSÉ] 768 |
| Vector store | ChromaDB ≥0.5 persistant (`data/chromadb`), éphémère pour le what-if | local, non distribué |
| Parsing PDF | docling (optionnel, non packagé), PyMuPDF ≥1.24 | PyMuPDF = AGPL-3.0 ou licence commerciale [SUPPOSÉ] |
| Base relationnelle | SQLite via SQLModel ≥0.0.22 | |
| Graphe | NetworkX ≥3 | |
| Client | httpx, rich | |
| Notebook 2 | FAISS-cpu, pypdf, sentence-transformers, llama-cpp-python, torch, huggingface_hub | |

**Exigences d'exécution (LU, README et PARTICIPANT_GUIDE)** :
- RAM : 16 Go minimum, 24 Go recommandés (`qwen2.5:14b`). Disque : ~15 Go.
- GPU : optionnel (commentaire dans `docker-compose.yml`).
- Clés d'API payantes : **aucune**. Services externes au runtime : **aucun** (sauf téléchargement des modèles Ollama, et Hugging Face / Google Drive pour le notebook 2).
- Taille de téléchargement de `qwen2.5:14b` : le README dit ~4,7 Go, le guide dit ~9 Go : incohérence.
- Premier lancement : 10 à 20 min (README).
- Versions : toutes en bornes inférieures (`>=`), pas de `lock` ; `instructor` et `smolagents` sont mentionnés dans une docstring mais absents de `requirements.txt`.

---

## E. Licences (LU sauf mention)

**E.1 Dépôt** : MIT, © 2026 Vishnu Ram OV (fichier `LICENSE`). Certitude : élevée. Note : le copyright ne mentionne ni CrashingGuru ni l'ITU.

**E.2 Dépendances** : aucune licence n'est indiquée dans le dépôt. Licences usuelles [SUPPOSÉ, à vérifier] :
- chromadb : Apache-2.0 ; fastapi, uvicorn, pydantic, httpx, rich, sqlmodel (MIT ou Apache-2.0), networkx (BSD-3), ollama (client MIT).
- **PyMuPDF : AGPL-3.0 ou licence commerciale Artifex** : point bloquant potentiel pour une plateforme distribuée ou SaaS.
- docling : MIT [SUPPOSÉ].
- Modèles : `qwen2.5:14b` (Apache-2.0 [SUPPOSÉ]), `nomic-embed-text` (Apache-2.0 [SUPPOSÉ]), `llama3.1:8b` et `Llama-3.2-1B` (licence communautaire Llama, restrictions d'usage et de seuil d'utilisateurs [SUPPOSÉ]), `all-MiniLM-L6-v2` (Apache-2.0 [SUPPOSÉ]).

**E.3 Données et documents inclus** (LU) : le dépôt redistribue publiquement environ 67 fichiers : rapports ITU (`T-REC-Y.3172-201906-I!!PDF-E.pdf`, `KSA.T-AI4G-AI4GOOD-2024-2-PDF-E.pdf`, AI for Good Use Cases, Innovate-for-Impact Geneva 2025), rapports ITU (`AI_Ready_Framework_2025.pdf`, `Digital Progress Trends Report 2025.pdf`), UNCTAD, WTO, UN, OMS (`WHO Content 9789240029200.pdf`), G7, G20, GPAI, déclarations diverses, et de nombreuses **stratégies nationales gouvernementales** (Chine, Japon, Inde, Kenya, Arabie saoudite, etc.).
- Aucune licence n'est indiquée pour ces documents. Leurs droits appartiennent aux éditeurs (ITU, gouvernements, OMS, etc.). La présence dans un dépôt MIT ne leur confère aucune licence. Certitude sur le risque : élevée ; sur le statut exact de chaque document : non vérifiée.
- `InputDocs/Inputs.md` affirme : « All documents are used solely for building the knowledge base and are not redistributed. » Cette affirmation est **contredite** par le fait que les PDF sont versionnés dans le dépôt public.
- `sample_national_strategy_ethiopia.txt` et `sample_national_strategy_saudi.txt` : données **synthétiques** (« estimated dimension scores for simulation testing »), à ne pas traiter comme sources.
- `ITU_AI4G_Sandbox_summary.txt`, `ITU-T_Y.3172_summary.txt`, `EU_AI_Act_summary.txt`, `Kenya_..._summary.txt` : résumés rédigés par les auteurs, sans source de référence précise.
- `dimensions.json` : contenu du framework ITU (13 dimensions, 111 métriques, 6 facteurs). Licence du contenu : non indiquée ; attribution ITU à conserver au minimum.
- `List_of_natl_and_multilateral_Initiatives_updated_2026_03_15 (2).docx` : document de travail, non ingéré (voir J).

**E.4 Niveau de certitude global** : fort sur le MIT du code, fort sur l'absence de licence pour les documents, moyen sur les licences des dépendances (non vérifiées dans le dépôt).

---

## F. Classement des composants pour notre plateforme (FastAPI + React, simulation d'exercices de crise, KB par pays, agents, permissions)

**Directement réutilisable (après revue de licence et de qualité)**
- `data/framework/dimensions.json` : structure propre (dimensions, métriques avec identifiants stables `d1_m01`, facteurs). Utile comme référentiel de grille d'évaluation, à condition de vérifier son contenu contre le rapport ITU d'origine.
- Modèle de texte des nœuds Y.3172 (`usecase.py`, `Y3172_PIPELINE_NODES`) : idée réutilisable comme vocabulaire, pas comme code.
- Pattern « KB éphémère par session de simulation » (`cache.py`) : concept utile pour l'isolation des scénarios de crise.

**À adapter**
- `ingest.py` : parsing (remplacer docling/PyMuPDF par notre chaîne, vérifier licence AGPL), chunking (passer aux tokens), métadonnées (ajouter titre, date, pays validé, niveau d'accès, hash, version), **identifiants déterministes** (hash contenu + source) pour rendre l'ingestion idempotente.
- `kb.py` : ajouter filtres de permission et de pays systématiques ; relire `kb_decisions` ; supprimer la confusion `dimension_id` sur `kb_main`.
- `base.py` (`BaseAgent`) : la logique RAG + prompt JSON est réutilisable en squelette ; à refactorer pour injecter nos prompts de crise et une validation de schéma (Pydantic) plutôt que parsing manuel.
- `session.py` / `AuditLog` : bon point de départ, mais l'audit n'est pas écrit pour les mutations de la KB (voir I).
- `scoring.py` / `causal_graph.py` : idée de propagation pondérée utile ; poids non sourcés, à calibrer ou à remplacer.

**À développer séparément**
- Permissions et rôles (aucun dans le dépôt).
- Simulation multi-agents réelle (dans le dépôt, les « agents » sont des appels LLM uniques, sans interaction).
- Front-end React, WebSocket réel (le WebSocket actuel est un écho).
- Gestion des documents et versions (ajout, suppression, retrait d'une KB pays).
- Audit complet et immuable, traçabilité des sources pour chaque affirmation.
- Évaluation de la qualité des sorties LLM (aucune métrique dans le dépôt).

---

## G. Intégration à un pipeline documentaire tiers (adaptateur import/export)

Proposition d'adaptateur fondé sur la structure réelle (LU pour les champs, DÉDUIT pour la conception) :

1. **Export** : écrire un fichier JSON Lines avec un enregistrement par chunk : `{id: sha256(source_file|chunk_index|text), text, embedding (optionnel), metadata: {source_file, source_type, country, document_category, chunk_index, total_chunks, ingested_at}}`. Les champs `country` et `source_type` viennent de la regex sur nom de fichier : à remplacer par nos métadonnées validées.
2. **Import** : lire le même format, recalculer les embeddings si le modèle diffère (ne pas mélanger les dimensions), puis `KnowledgeBase.add_documents` avec `ids` fournis (le paramètre `ids` existe déjà dans `kb.add_documents`).
3. **Schéma cible** : aligner nos champs sur C.1 (ajouter `title`, `publisher`, `year`, `license`, `access_level`, `version`).
4. **Vérification** : comparer le nombre de chunks par fichier, et la somme des `total_chunks` (contrôle de complétude).
5. Ne pas importer `kb_decisions` ni `kb_framework` tels quels : les régénérer à partir de notre propre référentiel.

---

## H. Obligations d'attribution et de licence

- Conserver le fichier `LICENSE` MIT et la mention de copyright (« Copyright (c) 2026 Vishnu Ram OV ») pour tout code réutilisé.
- Citer le dépôt d'origine (`github.com/CrashingGuru/ITUAIReadiness`) et le framework ITU (« ITU AI Ready - Analysis Towards a Standardized Readiness Framework, Report 2.0, janvier 2026 », source citée dans `dimensions.json`).
- Pour les documents tiers : **ne pas redistribuer** les PDF ; référencer les URL officielles des éditeurs et ne pas les versionner dans notre dépôt. À valider juridiquement pour les publications ITU et OMS.
- Pour les dépendances : vérifier l'AGPL de PyMuPDF avant tout déploiement hors usage interne.
- Ne pas utiliser les `sample_national_strategy_*.txt` comme données réelles.

---

## I. Ce que le dépôt NE fait PAS (LU)

- **Pas de permissions** : aucune authentification, aucun rôle, aucun contrôle d'accès ; CORS ouvert à `*` ; l'identifiant de session est la seule protection.
- **Pas d'audit fiable** : `AuditLog` est écrit pour les sessions, scénarios et décisions (SQLite) ; **les mutations de la KB ne sont pas auditées**, malgré la docstring de `kb.py` (« Every mutation is audit-logged »). `applied` n'est jamais mis à jour.
- **Pas de simulation multi-agents réelle** : chaque agent est un appel LLM ; aucun échange entre agents ; pas de temps ni d'événements.
- **Pas de simulation d'exercice de crise** : le jeu concerne l'évaluation de maturité IA des pays, pas la gestion de crise.
- **Pas de KB par pays isolée** : un seul `kb_main` partagé ; le filtre `country` est une métadonnée dérivée du nom de fichier.
- **Pas de versionnement** des documents ni de suppression de chunks (seul `--reset` existe).
- **Pas de distribution** : une seule instance ChromaDB locale.
- **Pas de tests** (`tests/` vide).
- **Pas d'évaluation** des scores (aucun jeu de référence).
- **Pas de front React**, pas de WebSocket fonctionnel.

---

## J. Doutes et éléments non lus

**Défauts observés dans le code (LU) :**
1. `search_by_dimension` filtre sur `dimension_id` dans `kb_main`, où ces métadonnées n'existent pas : retrieval silencieusement vide.
2. Ré-ingestion sans `--reset` : IDs `uuid4` et `ingest_framework_definitions` à chaque exécution : **doublons**.
3. `ingest_directory` parcourt `AI_Use_Cases/` et écrit dans `kb_main` ; `main()` écrit ensuite les mêmes fichiers dans `kb_usecase` : **double indexation** des use cases.
4. Fichiers non supportés ignorés sans erreur : `List_of_natl...docx` (non ingéré).
5. Regex de type de source : `policy|regulation|act|governance` attrape « Impact » (ex. `AI Impact Summit Declaration…`).
6. Notebook Colab `AI_Readiness_Game_Colab.ipynb` : appelle `/delegates/register` avec la clé `country` (le serveur attend `country_name`, `RegisterDelegateRequest`) et des routes `/dashboard/...` qui n'existent pas (les routes sont sous `/game/...`). **Ce notebook ne fonctionne pas tel quel** [LU, par comparaison des routes].
7. `dashboard()` du notebook lit `data["scores"]`, clé absente de la réponse du serveur.
8. Docstrings incohérentes avec le code (chunks 512 tokens vs 256 mots ; troncature 7500 vs 2000).
9. Le README annonce « 27 seed documents » et le code/API « 57+ » ; le manifeste `Inputs.md` annonce « 53 + 4 = 57 » fichiers ; **sur disque : 62 fichiers dans `AI_Strategies/` et 5 dans `AI_Use_Cases/` (67 au total, dont 2 `sample_*.txt` et le PDF Y.3172 absent du manifeste)**. Le chiffre « 57 » provient donc du manifeste, pas d'un comptage effectif. Le notebook dit « Parses all 57 documents ». **Les 57 documents seed mentionnés dans notre projet (ITU-03) ne sont pas une donnée vérifiée : le compte réel sur disque est 67 fichiers (hors Inputs.md), et la liste exacte de ce qui est ingéré dépend des extensions supportées.**
10. Dans `ingest_directory`, le sous-dossier `AI_Use_Cases` est aussi ingéré dans `kb_main` (voir point 3).

**Éléments non lus ou non vérifiés :**
- Contenu des fichiers binaires : `AI_Readiness_Simulation_Game_Plan.docx`, `AI_Readiness_Game_Slides.pptx`, le contenu des PDF (non ouverts, seul leur nom et leur taille ont été vérifiés).
- Les dossiers et fichiers des agents `opensource.py`, `standards.py`, `deployment.py`, `research.py` : seule leur définition (nom, dimensions) a été lue, pas leur prompt complet.
- `causal_graph.py` au-delà de la ligne 150 et `scoring.py` au-delà de la ligne 120 : non lus en détail.
- `cli/app.py` : lu partiellement (client API).
- `PARTICIPANT_GUIDE.md` : lu en partie (début).
- Historique Git complet : non disponible (clone superficiel). Nombre total de commits inconnu.
- Aucune exécution : la reproductibilité, les performances et la qualité des scores ne sont pas évaluées.
- Le lien entre le hackathon et le dépôt est confirmé par la page du hackathon (« Reference code for KB creation »), mais la page ne précise pas que le dépôt est officiel ITU. Certitude : moyenne.
- Dates du hackathon (lu via WebFetch) : soumission le 10 nov. 2026, hackathon le 9 déc. 2026 (Dubai), première évaluation du 11 au 18 nov. 2026. Ces dates sont **incohérentes** entre elles (soumission antérieure au hackathon) : à confirmer sur la page officielle.
