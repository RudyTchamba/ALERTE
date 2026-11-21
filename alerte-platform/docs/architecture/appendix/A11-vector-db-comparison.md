> **Note de l'architecte (2026-11-21).** Ce comparatif recommande Qdrant en premier choix pour un déploiement partagé. **L'architecture V1 (processus unique, SQLite) retient ChromaDB comme index vectoriel** (intégré, Apache-2.0, même moteur que le dépôt d'exemple ITU) ; Qdrant reste l'adaptateur de remplacement. Voir [07](../07-knowledge-and-rag.md) §7.3.

> **Annexe — Comparaison des moteurs vectoriels et lexicaux, modèles d'embeddings.**
> Matériau de recherche brut produit le 2026-11-21 par un sous-agent (modèle Haiku 5.5), relu en partie par l'architecte. Les marqueurs « non vérifié » / `[NV]` / `[V]` / `[P]` / `[S]` / `[LU]` / `[SUPPOSÉ]` sont ceux du sous-agent. Pièce justificative, pas une spécification.

---

# 12 - Comparatif des bases vectorielles et des modèles d'embeddings (ALERTE)

Date de rédaction : 2026-11-21. Recherche documentaire web uniquement, aucun benchmark exécuté.

## 0. Légende

- **[V]** : vérifié dans la page officielle ou le fichier LICENSE lu directement.
- **[P]** : partiellement vérifié (extrait de moteur de recherche, page tierce, ou page officielle lue mais affirmation non explicite).
- **[NV]** : non vérifié (page non lisible ou information non trouvée). Ne pas utiliser comme base de décision sans contrôle.

**Performance** : aucune page de benchmark officiel n'a été lue. Toutes les affirmations de performance sont donc [NV]. Un benchmark interne sur le corpus ALERTE est indispensable.

---

## 1. Tableau comparatif des solutions

| Solution | Licence (SPDX) | Persistance | Filtrage métadonnées | Concurrence | Hybride BM25 / sparse / RRF | Distribué | Portabilité | Export / reconstruction | Maturité (version lue) |
|---|---|---|---|---|---|---|---|---|---|
| **ChromaDB** | Apache-2.0 [V] ([LICENSE](https://github.com/chroma-core/chroma/blob/main/LICENSE), [docs](https://docs.trychroma.com/)) | Local persistant (SQLite) ou serveur ou Chroma Cloud [V] ([docs](https://docs.trychroma.com/)) | Opérateurs `$eq $gt $gte $lte $in $nin $and $or $contains` [V]. Pré ou post-filtrage **non précisé** [NV] ([doc](https://docs.trychroma.com/docs/querying-collections/metadata-filtering)) | **Non process-safe pour écrivains concurrents sur le même chemin local** [V]. Thread-safe [V] ([cookbook](https://cookbook.chromadb.dev/core/system_constraints/)) | Recherche hybride RRF (k=60), sparse BM25/SPLADE, **API Search indiquée comme disponible uniquement sur Chroma Cloud** [P] ([doc hybride](https://docs.trychroma.com/cloud/search-api/hybrid-search)). En local : **non disponible** selon l'index de doc [P] | Via Chroma Cloud ou serveur ; pas de clustering self-hosted vérifié [NV] | pip, Python [NV pour Windows/macOS] | Pas d'export documenté ; guide de migration : `chroma-migrate` pour les changements de schéma (ex. 0.4.0 : duckdb/clickhouse vers sqlite) [V] ([migration](https://docs.trychroma.com/docs/overview/migration)) | Dernière release lue : **1.5.9 (05 mai)** [P] ([releases](https://github.com/chroma-core/chroma/releases)) |
| **Qdrant** | Apache-2.0 [V] ([LICENSE](https://github.com/qdrant/qdrant/blob/master/LICENSE), [README](https://github.com/qdrant/qdrant)) | Serveur avec stockage disque [P] ; mode local Python `QdrantClient(path=...)` [P] (issu de recherche, non lu dans doc officielle) | Index payload ; l'ordre de création (index payload avant ingestion) influe sur le graphe HNSW filtrable [V] ([indexing](https://qdrant.tech/documentation/concepts/indexing/)). Pré-filtrage strict **non confirmé** [NV] | Serveur multi-clients [P] ; comportement exact en multi-processus du mode local **[NV]** | Sparse vectors (SPLADE++ cité) [V] ; BM25 via index full-text sur champ texte, paramètres k et b par requête [V] ; fusion **RRF** (k configurable v1.16+) et **DBSF** [V] ([hybrid](https://qdrant.tech/documentation/concepts/hybrid-queries/)) | Cluster supporté [NV] (non lu) | Docker `qdrant/qdrant` [V] ([README](https://github.com/qdrant/qdrant)). Binaires Windows/macOS : **[NV]** (page d'installation non lisible) | Export/snapshot : **[NV]** | Fonctionnalités citées jusqu'à v1.17 [V] ; version courante [NV] |
| **Milvus (serveur)** | Apache-2.0 [V] ([LICENSE](https://github.com/milvus-io/milvus/blob/master/LICENSE)) ; pymilvus Apache-2.0 [V] ([LICENSE](https://github.com/milvus-io/pymilvus/blob/master/LICENSE)) | Oui [P] | Filtres supportés en recherche et requête [V] (Lite) ; comportement pré/post [NV] | Multi-clients [P] | Sparse et hybride supportés [V] (Lite) ; BM25 full-text via analyseurs [V] | Standalone et Distributed [V] ([Lite](https://milvus.io/docs/milvus_lite.md)) | Serveur (Docker ou K8s) [NV pour détails] | Export : [NV] | Dernière release lue : **milvus-3.0.6 (11 nov)** [P] ([releases](https://github.com/milvus-io/milvus/releases)) |
| **Milvus Lite** | Licence du paquet Lite : **[NV]** (non trouvée dans la doc) ; pymilvus Apache-2.0 [V] | Fichier `.db` local [V] | Filtres supportés [V] | Un seul processus par répertoire de stockage, verrou fichier [V]. Écritures sur une même collection à sérialiser [V] | Dense, sparse (`SPARSE_FLOAT_VECTOR`, `SPARSE_INVERTED_INDEX`), hybride [V]. BM25 spécifique : [NV] | Non | macOS, Linux, Windows, Python 3.10+ (dépendances faiss-cpu, pyarrow) [V] | Lite 3.x **ne peut pas ouvrir les fichiers `.db` 2.x** : export avec l'outil 2.x puis réimport [V] | Lite v3.2.2 / PyMilvus 3.0.2 [V] ([doc](https://milvus.io/docs/milvus_lite.md)) |
| **PostgreSQL + pgvector** | PostgreSQL License [V] ([LICENSE](https://github.com/pgvector/pgvector/blob/master/LICENSE)) | Oui (PostgreSQL) [V] | **Filtre appliqué après le parcours d'index HNSW** (post-filtrage) par défaut [V] ; itératif via `hnsw.iterative_scan` (`strict_order` ou `relaxed_order`) [V] ; `hnsw.ef_search` défaut 40 [V] ([README](https://github.com/pgvector/pgvector)) | MVCC PostgreSQL multi-processus [P] | **Pas de BM25** [V] ; sparse via `sparsevec` (HNSW limité à 1 000 non-zéros) [V] ; hybride possible via FTS natif + RRF [V] | Via réplication PostgreSQL / Citus [NV] | Serveur Postgres (Docker, Podman) [NV pour détails] | `pg_dump` / export SQL : [P] (standard PostgreSQL) | v0.8.7 [V] ([README](https://github.com/pgvector/pgvector)) |
| **PostgreSQL FTS natif** (`ts_rank`, `ts_rank_cd`) | PostgreSQL License [V] (core) | Oui [V] | Filtres SQL standard [P] | MVCC [P] | `ts_rank` basé sur fréquence des lexèmes ; **pas d'IDF (BM25) explicite** [V, inféré de la doc] ([doc](https://www.postgresql.org/docs/current/textsearch-controls.html)). Configs de langue `arabic`, `french` : **[NV]** (la doc ne les liste pas ; à vérifier avec `\dF`) | Non | Partout où PostgreSQL tourne | SQL standard | Version core [NV] |
| **pg_textsearch** (Timescale) | PostgreSQL License [P] (README : « Postgres OSS licensed ») | Oui (extension) | Expression, partiel, partitionné [V] | Via PostgreSQL [P] | **BM25 natif** (k1, b configurables ; Block-Max WAND) [V] ; tokenizers PostgreSQL : langues **[NV]** | Non | PostgreSQL 17, 18, 19 [V] | Via PostgreSQL | v1.5.1 [V] ([README](https://github.com/timescale/pg_textsearch)). Maturité : jeune, GA v1.0.0 [V] |
| **ParadeDB pg_search** | **AGPL-3.0** [V] ([LICENSE dev](https://github.com/paradedb/paradedb/blob/dev/LICENSE)) | Oui | Via PostgreSQL | Via PostgreSQL | BM25 natif [P] ; tokenizers : `unicode_words` (défaut), `ngram`, `simple` [V] ; **support français/arabe : [NV]** (non trouvé dans la page lue) ([doc](https://www.paradedb.com/docs/documentation/tokenizers/available-tokenizers)) | Non | Docker [NV] | Via PostgreSQL | [NV] |
| **VectorChord-bm25** (TensorChord) | **Double licence AGPLv3 ou ELv2** [V] ([README](https://github.com/tensorchord/VectorChord-bm25), [LICENSE vectorchord](https://github.com/tensorchord/vectorchord/blob/main/LICENSE)) | Oui | Via PostgreSQL | Via PostgreSQL | BM25 natif [V] ; tokenizer dans un paquet séparé [V] ; **testé uniquement en anglais** [V] ; chinois via jieba, japonais via lindera (compilation à part) [V] | Non | Non vérifié | Via PostgreSQL | [NV] |
| **FAISS** | MIT [V] ([LICENSE](https://github.com/facebookresearch/faiss/blob/main/LICENSE)) | **Bibliothèque** : fichiers d'index à gérer soi-même [P] | Pas de métadonnées intégrées [P] : le filtrage est à implémenter dans l'application | Non (bibliothèque en processus) [P] | Dense uniquement [P] ; pas de BM25 [P] | Non | Wheels pip [NV] | Sérialisation d'index, pas d'export logique des métadonnées [P] | [NV] version |
| **LanceDB** | Apache-2.0 [V] ([LICENSE](https://github.com/lancedb/lancedb/blob/main/LICENSE)) | Oui (format Lance, embarqué) [P] | [NV] (page hybride non lisible) | [NV] | Recherche full-text et hybride annoncées [P] ; détails **[NV]** | Cloud [P] | [NV] | [NV] | [NV] |
| **Weaviate** | **BSD-3-Clause ou Weaviate License** selon le fichier LICENSE [V] ([LICENSE](https://github.com/weaviate/weaviate/blob/main/LICENSE)) | Oui [P] | [NV] (page hybride : pré-filtrage non décrit) | Serveur [P] | BM25 + vecteur ; fusion `relativeScoreFusion` (défaut à partir de v1.24) ou `rankedFusion` ; `alpha` défaut 0,75 [V] ([doc hybride](https://docs.weaviate.io/weaviate/concepts/search/hybrid-search)) | Clustering [P] | Docker [P] | [NV] | [NV] |
| **sqlite-vec (+ FTS5)** | **Apache-2.0 OU MIT** [V] ([README](https://github.com/asg017/sqlite-vec)) | Fichier SQLite unique [V] | Colonnes de métadonnées et de clé de partition [V] ; pré-filtrage explicite **[NV]** | Concurrence SQLite [P] | Vecteurs : KNN [V] ; FTS5 BM25 : **[NV]** (page FTS5 non lisible deux fois) | Non | Linux, macOS, Windows, WASM, `pip install sqlite-vec` [V] | Export SQL / dump SQLite [P] | **Pré-v1, ruptures d'API attendues** [V] ; version non lue |

### Notes sur la licence de certains dépôts

- Les dépôts Milvus et Qdrant sont sous Apache-2.0 selon leur fichier LICENSE. Le paquet **Milvus Lite** n'a pas été vérifié séparément.
- ParadeDB pg_search est sous AGPL-3.0. Pour un déploiement d'institution, l'AGPL est une contrainte à faire valider juridiquement.

---

## 2. Embeddings multilingues (FR / EN / AR)

| Modèle | Licence | Dim. | Longueur max | Langues | Arabe confirmé ? | Modes | GPU | Serveurs possibles | URL |
|---|---|---|---|---|---|---|---|---|---|
| **BGE-M3** (BAAI) | **MIT** [V] (métadonnées HF) | 1024 [V] | 8192 tokens [V] | « plus de 100 langues » [V], liste non donnée | **Non confirmé** [NV] | Dense + sparse + multi-vector (ColBERT) [V] | Non imposé ; `use_fp16` conseillé [V] | Ollama : entrée officielle `bge-m3`, ~567 M paramètres [P] ; TEI : sert les embeddings (BGE-M3 non nommé sur la page lue) [V] ; sentence-transformers [NV] | [HF](https://huggingface.co/BAAI/bge-m3), [Ollama](https://registry.ollama.ai/library/bge-m3) |
| **multilingual-e5-large-instruct** | **MIT** [V] | 1024 [V] | 512 tokens [V] | 100 langues XLM-R, qualité réduite pour langues peu dotées [V] | **Non confirmé** [NV] | Dense [V] | Non imposé [NV] | TEI / sentence-transformers [NV] | [HF](https://huggingface.co/intfloat/multilingual-e5-large-instruct) |
| multilingual-e5 base / small | [NV] | [NV] | [NV] | [NV] | [NV] | [NV] | [NV] | [NV] | non lu |
| **jina-embeddings-v3** | **CC-BY-NC-4.0** [P] (métadonnées via recherche ; page HF trop volumineuse pour WebFetch) | [NV] | [NV] | [NV] | [NV] | [NV] | [NV] | [NV] | [HF](https://huggingface.co/jinaai/jina-embeddings-v3) |
| **Qwen3-Embedding-0.6B** | **Apache-2.0** [V] | jusqu'à 1024, MRL 32 à 1024 [V] | 32k [V] | « 100+ langues » [V] | **Non listé** [V] | Dense [V] | [NV] | [NV] | [HF](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) |
| **nomic-embed-text-v2-moe** | **Apache-2.0** [V] | 768 ; MRL vers 256 [V] | 512 tokens [V] | ~100 langues [V] | **Non confirmé** [NV] | Dense [V] | [NV] | [NV] | [HF](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe) |
| **Snowflake arctic-embed-l-v2.0** | **Apache-2.0** [V] | [NV] | [NV] | 74 langues (tag) [V] | **Non confirmé** [NV] | Dense [NV] | [NV] | [NV] | [HF](https://huggingface.co/Snowflake/snowflake-arctic-embed-l-v2.0) |
| **bge-reranker-v2-m3** (reranker) | **Apache-2.0** [V] (métadonnées HF) | n/a | [NV] (exemple à 512) | multilingue [V] ; liste [NV] | **Non confirmé** [NV] | Cross-encoder [V] | [NV] | TEI : rerankers (exemples bge-reranker-large / base) [V] ; BGE-M3 non nommé [V] | [HF](https://huggingface.co/BAAI/bge-reranker-v2-m3) |

**Modèle à exclure** : jina-embeddings-v3 (CC-BY-NC-4.0, usage non commercial). À confirmer sur la page de licence Jina avant tout usage institutionnel.

**Serveurs d'inférence** :
- **Hugging Face Text Embeddings Inference (TEI)** : licence **Apache-2.0** [V] ; CPU x86_64 et aarch64 [V] ; GPU NVIDIA Turing et plus, CUDA capability >= 7.5 [V] ; GPU AMD MI200/MI300 [V] ; Apple Silicon via Homebrew avec Metal [V] ; **Windows non traité** [NV] ([README](https://github.com/huggingface/text-embeddings-inference)).
- **Ollama** : BGE-M3 présent dans le registre officiel [P].
- **vLLM, sentence-transformers** : non lus [NV].

---

## 3. BM25 correct pour FR et AR

| Moteur | Tokenisation / normalisation | Stemming FR | Stemming AR | Constat |
|---|---|---|---|---|
| **Milvus** | Analyseurs `standard`, `english`, `chinese`, `thai`, **`arabic`** (normalisation arabe, normalisation des chiffres, stemming arabe, stop-words) [V] | Pas d'analyseur FR natif listé ; filtre `stemmer` sans liste de langues [V] | Oui via analyseur `arabic` [V] | Seul moteur lu avec un analyseur arabe documenté. FR à configurer [NV] |
| **ParadeDB pg_search** | `unicode_words` (défaut, minuscules), `ngram`, `simple` [V] | [NV] | [NV] | Pas de langue spécifique confirmée |
| **VectorChord-bm25** | Tokenizer dans un paquet séparé [V] | [NV] | [NV] | **Testé uniquement en anglais** [V] ; à exclure pour FR/AR sans test |
| **pg_textsearch** | Configs PostgreSQL [P] | [NV] | [NV] | À vérifier (`SELECT cfgname FROM pg_ts_config;`) |
| **PostgreSQL FTS** | Configs de langue ; `french` et `arabic` **probables** dans l'installation standard [NV] | À vérifier | À vérifier | Pas de BM25 natif |
| **Qdrant** | Tokenizer `multilingual` (« multiples langues, dont alphabets non latins ») ; `word`, `whitespace`, `prefix`, `code` [V] ; stemmer Snowball, liste de langues renvoyée vers rust-stemmers [V] | [NV] | [NV] | À tester sur le corpus |
| **Chroma** | Pas de BM25 en local vérifié [P] | - | - | Implémenter BM25 à part |
| **SQLite FTS5** | tokenizers `unicode61` (`remove_diacritics`), `porter`, `trigram` ; `bm25()` | [NV] | [NV] | Page non lue ; pas d'analyseur arabe connu |
| **Weaviate** | BM25 avec options (word, lowercase, etc.) annoncées [P] ; liste non lue [NV] | [NV] | [NV] | À vérifier |

**Recommandation de prétraitement, indépendante du moteur** (à valider par un test) : normalisation Unicode NFKC ; pour l'arabe : retrait des tachkīl (diacritiques), normalisation des alef (أ إ آ -> ا), ta marbuta/ya finale selon la politique choisie, retrait des tatwīl ; pour le français : retrait des accents optionnel (`remove_diacritics`) ; stemmer Snowball français et arabe au niveau applicatif si le moteur n'en a pas.

---

## 4. Verdicts par cible

### (1) Déploiement partagé de référence (plusieurs workers)

**Candidats** : Qdrant (serveur, Apache-2.0, sparse + BM25 full-text + RRF natifs) ; PostgreSQL + pgvector (+ pg_textsearch).

- **Qdrant** : meilleur ajustement fonctionnel (vecteurs, texte, fusion RRF, index payload pour filtres) et licence Apache-2.0. Points non vérifiés : pré-filtrage strict des permissions et le clustering.
- **PostgreSQL + pgvector** : opérationnel bien connu, MVCC multi-processus, licence permissive. Point bloquant documenté : **filtre post-HNSW par défaut** (risque de fuite de rappel et de non-retour de résultats autorisés sans `iterative_scan`). Contournement : index partiel par KB ou recherche exacte (le planificateur utilise alors le B-tree sur l'identifiant de KB) ; à mesurer.
- Verdict : **Qdrant** en premier choix, **pgvector** si l'institution a déjà PostgreSQL en exploitation.

### (2) Développement / test léger sans serveur (Linux, Windows, macOS)

- **Milvus Lite** : pip, Windows/macOS/Linux, filtres, sparse et hybride [V], **un seul processus** par base [V], pas d'authentification [V], migration 2.x vers 3.x non directe [V].
- **Chroma local persistant** : pip, Apache-2.0, mais écrivain unique et **pas de BM25/sparse hybride en local** (selon la doc) [P] ; BM25 à implémenter à part.
- **sqlite-vec + FTS5** : fichier unique, très léger, mais **pré-v1** [V] et FTS5 non vérifié [NV].
- Verdict : **Milvus Lite** pour le dev et les tests (fonctionnalités proches de la cible, pas de serveur), **Chroma local** comme alternative si BM25 est géré hors base.

### (3) Sandbox ITU / démo

Environnement inconnu. Le critère décisif est la possibilité d'installer des paquets Python sans Docker.

- Sans Docker possible : **Milvus Lite** (même API que le dev).
- Avec Docker ou Podman : **Qdrant** (même cible que la référence).
- Verdict : **Milvus Lite** par défaut ; **Qdrant** si un conteneur est autorisé. Vérifier d'abord la capacité du Sandbox (questions à poser à l'ITU).

---

## 5. Recommandation tranchée

**Choix** : **Qdrant (Apache-2.0)** pour le déploiement partagé ; **Milvus Lite** pour le dev/test et la démo sans serveur ; **modèle BGE-M3 (MIT)** pour les embeddings, **bge-reranker-v2-m3 (Apache-2.0)** en reranker, servi par TEI ou Ollama. Écarter jina-embeddings-v3 (CC-BY-NC).

**Conditions avant de figer ce choix** (non vérifiées, à tester) :
1. **Test de pré-filtrage des permissions** : insérer 100 000 chunks dans deux KB, requête sur un agent qui n'a accès qu'à une KB, vérifier que le rappel top-k est complet. Sans ce test, ne pas retenir Qdrant pour la partie permissions.
2. **Test BM25 FR/AR** sur un échantillon réel (Qdrant `multilingual` vs prétraitement applicatif).
3. **Benchmark interne** : aucune performance n'a été vérifiée depuis des sources officielles.
4. **Abstraction** : une interface unique (`search`, `upsert`, `export`) pour que Milvus Lite et Qdrant restent interchangeables.

**Risques** :
- Mode local de Qdrant : comportement multi-processus **non vérifié**.
- Chroma en mode serveur ou cloud : hybride BM25 peut être réservé au cloud ; ne pas dépendre de Chroma pour la recherche hybride.
- Milvus Lite : non prévu pour la production ; la licence du paquet Lite est **non vérifiée**.
- Recherche arabe : aucun moteur lu ne confirme un traitement arabe de bout en bout hors Milvus (`arabic` analyzer).
- Sandbox ITU : inconnu, risque de devoir basculer.

---

## 6. Migration et export

- **Chroma** : `chroma-migrate` documenté pour les changements de schéma, mais pas d'export logique générique dans le guide de migration [V]. La remarque « migrations non documentées » du dossier est **partiellement infirmée** (des migrations sont documentées), la contrainte de concurrence est **confirmée**.
- **Milvus Lite** : 2.x vers 3.x par export avec les outils 2.x [V].
- **pgvector** : export standard PostgreSQL [P].
- **Qdrant** : snapshots et export **[NV]**.

---

## 7. URLs non lues (ou non entièrement lues)

- https://docs.trychroma.com/docs/search/hybrid-search : 404 (remplacée par https://docs.trychroma.com/cloud/search-api/hybrid-search, lue).
- https://qdrant.tech/documentation/guides/installation/ et https://qdrant.tech/documentation/operations/installation/ : la page n'a renvoyé que l'URL (contenu non lu).
- https://qdrant.tech/documentation/concepts/indexing/ : lue partiellement (100 000 premiers caractères sur 132 491).
- https://www.sqlite.org/fts5.html et https://sqlite.org/fts5.html : échec de lecture (x2).
- https://lancedb.github.io/lancedb/hybrid_search/hybrid_search/ et https://lancedb.com/docs/search/full-text-search/ : échec de lecture.
- https://github.com/huggingface/text-embeddings-inference : lue, sans mention de BGE-M3 ni de Windows.
- https://huggingface.co/jinaai/jina-embeddings-v3 : trop volumineuse (10 Mo), licence confirmée par recherche seulement.
- https://huggingface.co/Snowflake/snowflake-arctic-embed-l-v2.0 : contenu tronqué (dimensions, longueur non lues).
- https://docs.paradedb.com/documentation/tokenizers/available-tokenizers : redirigée, lue partiellement.
- https://docs.weaviate.io/... : redirection depuis weaviate.io, lue.
- https://milvus.io/docs/analyzer-overview.md : lue ; la page BM25 et IDF n'est pas détaillée.
- https://github.com/chroma-core/chroma/releases : version 1.5.9 lue, date ambiguë (05 mai) [P].
- https://cookbook.chromadb.dev/core/system_constraints/ : lue.
- https://docs.trychroma.com/ : lue (page d'accueil, licence Apache-2.0).
- Pages de performance et de benchmark officielles : **non cherchées** (hors périmètre de cette passe).
- Pages de versions FAISS, LanceDB, Weaviate (version courante) : **non lues**.
- Documentation Ollama (bge-m3 tag et quantification) : seul un extrait de recherche a été lu [P].
