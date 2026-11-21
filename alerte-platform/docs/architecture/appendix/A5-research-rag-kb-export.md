> **Annexe — Recherche : RAG, permissions de retrieval, export de bases de connaissances.**
> Matériau de recherche brut produit le 2026-11-20 par un sous-agent (modèle Haiku 5.5), relu en diagonale par l'architecte. Les marqueurs « non vérifié » / `[NV]` / `[V]` / `[S]` sont ceux du sous-agent ; toute information utilisée dans le dossier principal est citée avec son niveau de vérification. Ce fichier est une pièce justificative, pas une spécification.

---

# ALERTE : recherche RAG, bases de connaissances, permissions, export

Date de la recherche : 2026-11-20. Rédigé par le sous-agent `search`. Aucun fichier du dépôt n'a été modifié.

Légende : **[V]** vérifié sur la source citée ; **[NV]** non vérifié (source inaccessible, source secondaire ou connaissance générale à confirmer).

---

## 1. Pratiques retenues

### P1. Recherche de documents en pipeline RAG : retrieve, augment, generate, avec citations
- **(a) Pratique** : séparer la recherche (retrieval) de la génération. Renvoyer au modèle des passages identifiés par un identifiant stable et exiger des citations rattachées à ces passages.
- **(b) Source** : https://learn.microsoft.com/en-us/azure/foundry/concepts/retrieval-augmented-generation (ms.date 2026-08-21, updated_at 2026-11-17) [V]
- **(c) Problème** : sans identifiants de passage, le modèle invente des sources ou cite de manière non vérifiable.
- **(d) Intérêt ALERTE** : chaque réponse d'agent doit pointer vers document, page, article et extrait.
- **(e) Composant** : service de retrieval et contrat de réponse de l'agent.
- **(f) Limites** : la page ne donne pas de format de citation normatif.
- **(g) Vérification** : chaque affirmation de la réponse doit référencer un `chunk_id` présent dans les résultats renvoyés. Un test échoue si un identifiant cité n'a pas été renvoyé par le retrieval.

### P2. Sécurité au moment du retrieval, pas dans le prompt
- **(a) Pratique** : appliquer les contrôles d'accès au moment de la recherche, sur chaque requête. La page Microsoft indique « Apply access control at retrieval time », et que les contenus récupérés sont une entrée non fiable (risque d'injection de prompt). [V]
- **(b) Sources** :
  - https://learn.microsoft.com/en-us/azure/foundry/concepts/retrieval-augmented-generation (section Security) [V]
  - https://learn.microsoft.com/en-us/azure/search/search-security-trimming-for-azure-search (ms.date 2026-11-09) [V]
  - https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html [V]
- **(c) Problème** : un filtre dans le prompt ou un post-filtrage peut fuiter des contenus ou être contourné.
- **(d) Intérêt** : chaque agent n'accède qu'à certaines bases. Le filtrage doit être imposé par le serveur.
- **(e) Composant** : couche d'accès au moteur de recherche (fonction `search(agent_id, query)`).
- **(f) Limites** : la doc Azure décrit un « security filter pattern » applicatif : le principal est une simple chaîne, et l'application doit authentifier, appliquer le filtre à chaque requête et empêcher les contournements. Le texte précise que `retrievable=false` n'est pas une protection de contenu. [V]
- **(g) Vérification** : tests de fuite automatisés (voir section 4).

#### Règles concrètes retenues (OWASP + doc Azure)
1. **Deny by default** : aucune base accessible sans entrée explicite `agent_kb_grant(agent_id, kb_id)`. [V, OWASP]
2. **Identité jamais fournie par le LLM** : `agent_id` vient de la session serveur, jamais d'un argument d'outil. Le LLM ne peut pas choisir sa base. [V pour le principe « ne pas faire confiance aux entrées modifiables » ; l'extension aux LLM est une extrapolation de ma part, marquée [NV] comme règle de conception]
3. **Pré-filtrage, pas post-filtrage** : l'ensemble `allowed_kb_ids` est calculé avant la recherche et passé comme condition SQL ou `where`. Le post-filtrage peut fuiter via les scores, les facettes et les compteurs. La doc Azure recommande de tester l'ordre des filtres avec semantic ranker. [V]
4. **Filtre sur chaque requête**, y compris la recherche lexicale et la recherche vectorielle. Azure utilise `search.in` pour des listes de groupes ; le pattern est `group_ids/any(g:search.in(g, '...'))`. [V]
5. **Ne pas renvoyer les champs de permission** dans les résultats et les logs d'agent. [V sur `retrievable=false` comme partie du pattern]

### P3. Recherche hybride BM25 + vecteurs avec Reciprocal Rank Fusion
- **(a) Pratique** : exécuter une recherche lexicale (BM25 ou FTS5) et une recherche vectorielle en parallèle, puis fusionner par RRF : `score(d) = Σ 1/(k + rang_i(d))`, avec `k = 60`.
- **(b) Sources** :
  - https://learn.microsoft.com/en-us/azure/search/hybrid-search-overview (ms.date 2026-11-09) [V]
  - https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking (ms.date 2026-11-09) [V] : « 1/(rank + k) », k « small value, such as 60 ».
  - Cormack, Clarke, Büttcher, « Reciprocal rank fusion outperforms Condorcet and individual rank learning methods », SIGIR 2009, p. 758-759, DOI 10.1145/1571941.1572114. [V via résumé de recherche ; PDF non lu, redirections répétées]
- **(c) Problème** : BM25 manque les paraphrases ; le vectoriel manque les codes, numéros d'articles et noms propres exacts. Les deux scores ne sont pas comparables.
- **(d) Intérêt** : les textes juridiques contiennent des numéros d'article, des dates et des termes exacts. Le mode hybride protège ces cas.
- **(e) Composant** : moteur de retrieval.
- **(f) Limites** : la doc Azure indique que `k` de RRF est distinct du `k` des plus proches voisins. Les scores BM25 n'ont pas de borne supérieure. Une fusion ne remplace pas un reranker. Le papier original compare sur TREC, pas sur du droit multilingue. [V]
- **(g) Vérification** : comparer recall@10 et MRR sur un jeu de requêtes labellisées : BM25 seul, vecteur seul, hybride RRF. Retenir la configuration qui maximise recall@10 sans dégrader MRR.

### P4. Chunking structure-aware (articles de loi, en-têtes)
- **(a) Pratique** : découper selon la structure (article, section, en-tête) avant le découpage par taille. Préfixer chaque chunk de son titre de document, de son article et de sa page. Pour un découpage par taille, partir de 512 tokens avec 25 % de recouvrement (128 tokens).
- **(b) Source** : https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-chunk-documents (ms.date 2026-11-09) [V]. Les règles de découpage par article sont une recommandation de conception [NV].
- **(c) Problème** : un découpage aveugle coupe les articles et perd le numéro d'article, donc la citation.
- **(d) Intérêt** : la citation exige « article X du texte Y, page Z ».
- **(e) Composant** : pipeline d'ingestion, étape de chunking.
- **(f) Limites** : la doc Azure indique qu'un découpage par taille fixe peut être fait en caractères ou en tokens, et que le compte de tokens varie selon le modèle. L'exemple NASA montre que 2000 caractères avec 500 de recouvrement donnent 113 chunks, contre 85 sans recouvrement. [V]
- **(g) Vérification** : sur un échantillon de 20 articles, vérifier que chaque chunk contient un en-tête d'article complet, et que la citation `article` correspond au texte. Compter les articles coupés.

### P5. Contextual Retrieval
- **(a) Pratique** : ajouter à chaque chunk un court texte généré par un LLM qui le situe dans le document, avant embedding et avant indexation BM25.
- **(b) Source** : https://www.anthropic.com/news/contextual-retrieval (publié le 19 septembre 2024) [V]
- **(c) Problème** : un chunk isolé perd son contexte (entité, date, texte de référence).
- **(d) Intérêt** : utile pour les chunks qui ne citent pas le nom de la loi ou de l'institution.
- **(e) Composant** : pipeline d'ingestion, avant indexation.
- **(f) Limites** : gains mesurés par Anthropic sur un corpus de test (taux d'échec top-20 : 5,7 % → 2,9 % avec embeddings et BM25 contextuels ; 1,9 % avec reranking). Ces chiffres ne sont pas transposables. Coût estimé : environ 1,02 $ par million de tokens de document, avec prompt caching. Le coût dépend du prompt caching. Les chunks contextualisés sont des données dérivées : ils doivent être exportés avec le document. [V]
- **(g) Vérification** : A/B sur le jeu de requêtes labellisées. Vérifier que le texte de contexte ne contient que des informations présentes dans le document source.

### P6. Reranking après fusion
- **(a) Pratique** : récupérer environ 150 chunks, puis reranker les 20 meilleurs.
- **(b) Sources** :
  - Anthropic Contextual Retrieval (ci-dessus) [V]
  - https://learn.microsoft.com/en-us/azure/search/hybrid-search-overview : semantic ranker placé après la fusion, score dans `@search.rerankerScore`, plage 0 à 4. [V]
- **(c) Problème** : la fusion ordonne mal les tout premiers résultats.
- **(d) Intérêt** : amélioration du top-k, à coût de latence.
- **(e) Composant** : après retrieval, avant le prompt.
- **(f) Limites** : pas de reranker multilingue (FR/EN/AR) identifié et vérifié dans ce travail. Le reranker Cohere cité par Anthropic n'est pas vérifié pour l'arabe. Option repoussée tant que la métrique de base n'est pas établie.
- **(g) Vérification** : mesurer le gain de MRR et de recall@5 avec et sans reranker sur le jeu d'évaluation.

### P7. Filtres de métadonnées pour le retrieval (`where`)
- **(a) Pratique** : stocker `kb_id`, `lang`, `doc_id`, `article`, `page` comme métadonnées, et filtrer sur `kb_id` dans chaque requête.
- **(b) Source** : https://docs.trychroma.com/docs/querying-collections/metadata-filtering (lecture du 2026-11-20) [V]. Opérateurs : égalité, `$gt`, `$gte`, `$lte`, `$in`, `$nin`, `$and`, `$or`, `$contains`, `$not_contains`. `$ne` et `$lt` non documentés dans la page lue. Limites : tableaux non vides, types homogènes.
- **(c) Problème** : filtrage par base et par langue.
- **(d) Intérêt** : appliquer la liste `allowed_kb_ids`.
- **(e) Composant** : index de recherche.
- **(f) Limites** : la page ne donne aucun exemple de filtre sur liste de permissions côté serveur.
- **(g) Vérification** : test de non-régression : une requête avec `kb_id` interdit ne renvoie aucun résultat.

### P8. Export logique de la KB (JSONL + manifest) et réindexation
- **(a) Pratique** : la KB est une source de vérité indépendante du moteur (documents, chunks, métadonnées, sources). Les index (FTS, vecteurs) sont reconstruits à l'import.
- **(b) Sources** :
  - https://jsonlines.org/ : UTF-8, une valeur JSON par ligne, séparateur `\n`, extension `.jsonl`, pas de BOM. [V]
  - https://www.rfc-editor.org/rfc/rfc8493 (BagIt, octobre 2018) : `bagit.txt`, `data/`, `manifest-<algo>.txt`, validation « complete » et « valid ». Recommande SHA-512 et accepte SHA-256. Les implémentations doivent empêcher l'accès hors du bag. [V]
  - https://www.rfc-editor.org/rfc/rfc8785 (JCS, juin 2020, informatif) : sérialisation canonique pour hacher ou signer un JSON. [V]
- **(c) Problème** : lier la KB à un moteur particulier (Chroma, Azure) la rend non portable et non auditable.
- **(d) Intérêt** : exigence « exportable / réimportable ».
- **(e) Composant** : module `kb_export` et `kb_import`.
- **(f) Limites** : RO-Crate, Frictionless et OCI n'ont pas été lus (échecs de récupération). Le choix ci-dessous est un format maison inspiré de BagIt.
- **(g) Vérification** : export puis réimport sur une base vide. Comparer les hashes des chunks et le nombre de documents. Recalculer les SHA-256 du manifest.

### P9. Sécurité de l'archive à l'import (zip-slip, bombes, secrets)
- **(a) Pratique** : valider chaque entrée d'archive avant extraction. Refuser les chemins absolus et `..`, les liens symboliques, les entrées hors `data/`, les tailles et ratios excessifs. Exclure les secrets à l'export par liste blanche.
- **(b) Sources** :
  - https://www.rfc-editor.org/rfc/rfc8493 : « implementations must prevent access to files outside the bag » [V]
  - Zip Slip (Snyk, https://security.snyk.io/research/zip-slip-vulnerability) : **non vérifié**, page non lue (échec de récupération).
  - Seuils de taille et de ratio ci-dessous : **[NV]**, recommandations de conception.
- **(c) Problème** : écriture de fichiers hors répertoire, déni de service par décompression.
- **(d) Intérêt** : l'import peut venir de tiers.
- **(e) Composant** : `kb_import`.
- **(f) Limites** : pas de vérification de signature dans ce travail.
- **(g) Vérification** : tests unitaires avec archives malveillantes (chemin `../`, lien symbolique, bombe de 1 Go compressée en 1 Mo).

### P10. Vérification d'intégrité et signature optionnelle
- **(a) Pratique** : SHA-256 par fichier dans `manifest.json`, puis hash du manifest canonique (JCS) ; signature optionnelle (Ed25519 ou clé de l'institution) du hash du manifest.
- **(b) Sources** : BagIt (RFC 8493) et JCS (RFC 8785) [V] ; choix de Ed25519 [NV].
- **(c) Problème** : altération ou substitution d'une base.
- **(d) Intérêt** : preuve d'origine d'une KB exportée.
- **(e) Composant** : export et import.
- **(f) Limites** : la signature n'est utile que si la gestion des clés est définie.
- **(g) Vérification** : modifier un octet d'un chunk et vérifier l'échec de l'import.

### P11. Modèle d'embedding multilingue
- **(a) Pratique** : BGE-M3 en dense (1024 dimensions), avec une fenêtre de 8192 tokens.
- **(b) Sources** :
  - https://huggingface.co/BAAI/bge-m3 (lecture 2026-11-20) : dimension dense 1024, contexte 8192 tokens, plus de 100 langues, dense + sparse + multi-vector, licence MIT. Nombre de paramètres non affiché sur la page lue. [V]
  - https://ollama.com/library/bge-m3 : `ollama pull bge-m3`, téléchargement 1,2 Go, 567 millions de paramètres ; la page indique « Updated 2 years ago » et doit être revérifiée. [V]
- **(c) Problème** : retrouver des passages en FR, EN et AR avec un seul modèle.
- **(d) Intérêt** : un seul modèle pour les trois langues, et un mode sparse disponible pour plus tard.
- **(e) Composant** : indexation et requêtes.
- **(f) Limites** :
  - Qualité sur l'arabe **non mesurée** ici. Le modèle annonce plus de 100 langues, mais aucun chiffre par langue n'a été lu. [NV]
  - Vitesse sur CPU 4 cœurs : non vérifiée. Ordre de grandeur estimé à partir de 567 M de paramètres : plusieurs dizaines de ms par chunk de 512 tokens, donc quelques minutes pour quelques milliers de chunks. [NV, à mesurer]
  - Taille mémoire fp32 estimée à environ 2,3 Go pour les poids. [NV]
- **(g) Vérification** : benchmark local sur 500 chunks FR/EN/AR : temps total, RAM, recall@10.

### P12. Alternative légère : multilingual-e5-small
- **(a) Pratique** : modèle de 118 M de paramètres, 384 dimensions, préfixes `query: ` et `passage: `.
- **(b) Source** : https://huggingface.co/intfloat/multilingual-e5-small : **page tronquée, non lue**. Informations issues de miroirs et de pages dérivées (https://huggingface.co/maiyad/multilingual-e5-small, https://keras.io preset) : **[NV]**. Pas de tag `multilingual-e5-small` vérifié sur Ollama (404 sur `ollama.com/library/multilingual-e5`).
- **(c) Problème** : réduire la taille et le temps de calcul sur CPU.
- **(d) Intérêt** : solution de repli si BGE-M3 est trop lent.
- **(e) Composant** : indexation.
- **(f) Limites** : langues et qualité arabe **non vérifiées** ; préfixes obligatoires selon la FAQ du modèle relayée par un miroir. [NV]
- **(g) Vérification** : même benchmark que P11.
- nomic-embed-text : page Ollama lue. Téléchargement 274 Mo, contexte 2K, `ollama pull nomic-embed-text`. Langues **non précisées** sur la page ; à considérer comme **non adapté à l'arabe sans test**. [V pour les données de la page ; NV pour l'adéquation]

### P13. Recherche lexicale sans serveur : SQLite FTS5
- **(a) Pratique** : stocker chunks et métadonnées dans SQLite, avec une table FTS5 (BM25 via `bm25()`).
- **(b) Source** : https://sqlite.org/fts5.html : **échec de lecture** (WebFetch). Contenu décrit ici à partir de la connaissance générale de FTS5 : tokenizers `unicode61` (option `remove_diacritics`) et `porter` ; `trigram` pour sous-chaînes. **[NV]**
- **(c) Problème** : recherche lexicale sur quelques milliers de chunks sans service externe.
- **(d) Intérêt** : une seule base transactionnelle, facile à exporter.
- **(e) Composant** : moteur de retrieval.
- **(f) Limites** : tokenisation arabe (diacritiques, clitiques) **non testée** ; `unicode61` ne fait pas de racinisation arabe. [NV]
- **(g) Vérification** : jeu de requêtes arabes avec et sans diacritiques.

### P14. Recherche vectorielle : numpy brute-force ou sqlite-vec
- **(a) Pratique** : pour quelques milliers à quelques dizaines de milliers de chunks, la recherche exhaustive en numpy est suffisante. Option : extension sqlite-vec.
- **(b) Source** : https://github.com/asg017/sqlite-vec : projet **pré-v1**, « expect breaking changes », licence Apache-2.0 ou MIT, C pur, `vec0` pour KNN. Version courante non lue. [V]
- **(c) Problème** : pas de serveur vectoriel à maintenir.
- **(d) Intérêt** : tout en un fichier SQLite.
- **(e) Composant** : moteur de retrieval.
- **(f) Limites** : sqlite-vec est pré-v1 ; la page ne précise pas l'algorithme (brute force ou approximatif). Pour numpy, le filtrage par `kb_id` doit se faire avant le produit scalaire. [V/NV]
- **(g) Vérification** : mesurer la latence p95 sur 50 000 chunks synthétiques.

### P15. ChromaDB : état vérifié et place dans l'architecture
- **(a) Pratique** : si Chroma est retenu, ne l'utiliser que comme index reconstructible.
- **(b) Sources** :
  - https://docs.trychroma.com/docs/overview/getting-started : la page ne donne pas de numéro de version ; elle utilise `chromadb.Client()` (en mémoire), `create_collection`, `get_or_create_collection`, `add` avec `ids` uniques, `upsert`, `query(query_texts, n_results)` ; `n_results` vaut 10 par défaut. Le client persistant n'est pas détaillé. [V]
  - https://cookbook.chromadb.dev/core/system_constraints/ (source secondaire, via recherche) : thread-safe mais **pas process-safe** pour des écrivains partageant le même chemin local. Recommandation : mode client-serveur (`chroma run --path`). [V via résumé de recherche, à confirmer sur la doc officielle]
  - Version actuelle de chromadb : **non vérifiée** (une source tierce indique 1.5.9, non confirmée).
  - Migration entre versions : **non vérifiée**, pas de guide officiel trouvé.
- **(c) Problème** : Chroma impose des contraintes de concurrence et de version.
- **(d) Intérêt** : API simple pour prototyper.
- **(e) Composant** : index optionnel.
- **(f) Limites** : données en mémoire par défaut ; concurrence limitée ; migration non documentée (dans ce travail).
- **(g) Vérification** : rebuild complet depuis l'export JSONL et comparaison des résultats.

### P16. Ingestion documentaire : choix des outils
Tableau comparatif (vérifié sauf mention) :

| Outil | Licence | Constat vérifié | Limite |
|---|---|---|---|
| PyMuPDF (pymupdf.readthedocs.io, lu) | **AGPL ou commerciale** | Texte de tous types de documents, Markdown, rapide (8 s pour 7 031 pages selon la page), OCR via Tesseract | AGPL : à valider avec l'équipe juridique si le code est distribué ou exposé en service |
| pymupdf4llm | non vérifiée | non lu | même régime que PyMuPDF : **[NV]** |
| pdfplumber (github.com/jsvine/pdfplumber, lu) | **MIT** | coordonnées de chaque caractère, tables, rendu de page de débogage | pas d'OCR ; PDF uniquement |
| Tesseract (github.com/tesseract-ocr/tesseract, lu) | **Apache-2.0** | OCR de plus de 100 langues ; tessdata installables | vitesse CPU et qualité arabe non vérifiées ; `ara`, `fra`, `eng` à confirmer dans `tessdata` |
| Docling (github.com/docling-project/docling, lu) | **MIT** pour le code ; modèles à licence propre | PDF, DOCX, HTML, images ; sortie Markdown et JSON sans perte (DoclingDocument) ; OCR « extensive » | provenance page/bbox **non mentionnée** dans la page ; besoins CPU non précisés ; plus lourd |
| Unstructured (github.com/Unstructured-IO/unstructured, lu) | **Apache-2.0** | `partition` détecte le type ; dépendances système (tesseract, poppler, libreoffice) | `by_title` et types d'éléments non confirmés sur la page ; dépendances lourdes |

- **(a) Pratique retenue** : pipeline en deux voies.
  1. PDF avec couche texte : pdfplumber (MIT), page par page, avec détection des tables.
  2. PDF scanné (page sans texte) : rendu d'image puis Tesseract (Apache-2.0) avec `ara+fra+eng`.
  3. Découpage structuré (P4) sur le texte produit.
- **(b) Sources** : pages GitHub listées ci-dessus, lues le 2026-11-20. [V]
- **(c) Problème** : extraire page et article pour citer.
- **(d) Intérêt** : licences permissives (MIT et Apache), sans AGPL.
- **(e) Composant** : pipeline d'ingestion.
- **(f) Limites** :
  - Durée typique sur CPU 4 cœurs : **non vérifiée**. Estimation : quelques secondes par page scannée avec Tesseract LSTM ; à mesurer. [NV]
  - Qualité de l'OCR arabe **non mesurée**. [NV]
  - Docling pourrait être testé en second temps pour les mises en page complexes.
- **(g) Vérification** : jeu d'essai de 30 pages (FR, EN, AR, dont 10 scannées) : taux de caractères corrects (CER) et temps par page.

### P17. Métriques d'évaluation RAG
- **(a) Pratique** : évaluer le retrieval séparément de la génération.
- **(b) Sources** :
  - https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/rag-evaluators (ms.date 2026-06-02, updated 2026-08-26) [V]
- **Liste exacte des évaluateurs Azure** :

| Évaluateur | Type | Entrées | Définition | Échelle |
|---|---|---|---|---|
| Document Retrieval | processus (retrieval) | `retrieval_ground_truth`, `retrieved_documents` | Fidelity, NDCG, XDCG, Max Relevance, Holes, à partir de labels de pertinence | score 0 à 1 par métrique |
| Retrieval | processus | `query`, `context` | pertinence des chunks au regard de la requête (LLM-juge) | 1 à 5, seuil 3 |
| Groundedness | système | `response`, `context` (+ `query` recommandé) | la réponse reste dans le contexte, sans fabrication (précision) | 1 à 5, seuil 3 |
| Groundedness Pro (preview) | système | `query`, `response`, `context` | cohérence stricte, service Azure AI Content Safety | booléen |
| Relevance | système | `query`, `response` | exactitude, complétude et pertinence directe | 1 à 5, seuil 3 |
| Response Completeness (preview) | système | `ground_truth`, `response` | couverture de l'information attendue (rappel) | 1 à 5, seuil 3 |

- Définitions de précision et de rappel : Groundedness = précision ; Response Completeness = rappel. [V]
- **(c) Problème** : mesurer séparément la qualité de la recherche et celle de la réponse.
- **(d) Intérêt** : jeu de tests FR/EN/AR.
- **(e) Composant** : harnais d'évaluation.
- **(f) Limites** : les évaluateurs Azure sont payants et dépendent d'un modèle juge. Le plan sans service payant est décrit ci-dessous (**[NV]** pour la méthode, qui est une recommandation de conception et non une source lue).
- **(g) Vérification** : voir section 4.

---

## 2. Recommandations tranchées

### 2.1 Moteur de retrieval
**Décision : SQLite comme source de vérité et moteur unique, avec FTS5 (BM25) et vecteurs stockés en BLOB, recherche vectorielle exhaustive en numpy sur l'ensemble pré-filtré par `allowed_kb_ids`, fusion RRF avec k = 60.**
- Pas de Chroma en production : contraintes de concurrence (process-safe non garanti), migrations non documentées. Chroma reste possible comme index reconstructible hors chemin critique.
- Pas de post-filtrage : le filtre `kb_id IN (...)` est appliqué avant FTS5 et avant le produit scalaire.
- Option ultérieure : sqlite-vec (pré-v1) si la latence l'exige. Reranker en option après mesure.

### 2.2 Embeddings
**Décision : BGE-M3, dense uniquement, 1024 dimensions, via Ollama (`ollama pull bge-m3`).** Repli : multilingual-e5-small, après vérification de sa fiche officielle et des performances en arabe. Mesurer le temps et la RAM sur le CPU cible avant tout engagement. Tant que la vitesse n'est pas mesurée, considérer les durées comme **non vérifiées**.

### 2.3 Format d'archive de KB
**Décision : archive ZIP `alerte-kb-<kb_id>-<version>.zip` avec `manifest.json`, `documents.jsonl`, `chunks.jsonl`, `sources/` (fichiers originaux), `embeddings/` (optionnel), et SHA-256 par fichier. Inspiré de BagIt.**

Arborescence :
```
alerte-kb-kb-ma-codes-penal-v3.zip
├── manifest.json
├── manifest.sha256          (SHA-256 du manifest canonisé JCS)
├── bag-info.txt             (lisible par un humain)
├── data/
│   ├── documents.jsonl      (une ligne par document : id, titre, langue, licence, provenance)
│   ├── chunks.jsonl         (une ligne par chunk : id, doc_id, page, article, texte, sha256)
│   ├── sources/<doc_id>.pdf (fichiers originaux, optionnels)
│   └── embeddings/bge-m3.f32.npy   (optionnel, avec ligne chunk_id par ligne)
└── signature.json           (optionnel)
```

Exemple de `manifest.json` (valeurs fictives, à remplacer) :
```json
{
  "format": "alerte-kb-archive",
  "format_version": "1.0.0",
  "kb_id": "kb-ma-codes-penal-2026",
  "kb_title": "Code pénal (extraits)",
  "kb_version": "3",
  "created_at": "2026-11-20T10:00:00Z",
  "exporter": "alerte-kb-export/0.1.0",
  "languages": ["fr", "ar", "en"],
  "default_license": "LicenseRef-ALERTE-Internal",
  "embedding": {
    "model": "bge-m3",
    "provider": "ollama",
    "dimensions": 1024,
    "normalized": true,
    "included": false
  },
  "chunking": {
    "strategy": "article-aware",
    "max_chars": 2000,
    "overlap_chars": 200,
    "title_prefix": true
  },
  "files": [
    {"path": "data/documents.jsonl", "sha256": "<hex>", "bytes": 12034, "records": 42},
    {"path": "data/chunks.jsonl", "sha256": "<hex>", "bytes": 983412, "records": 1876}
  ],
  "provenance": {
    "source_hashes_included": true,
    "ingestion_tool": "pdfplumber 0.11 (MIT) + tesseract 5 (Apache-2.0)"
  }
}
```

Champs obligatoires du manifest : `format_version`, `kb_id`, `kb_version`, `files[].sha256`, `languages`, `default_license` (SPDX ou `LicenseRef-`), `embedding` (modèle et dimension, même si les vecteurs sont exclus), `chunking` (paramètres), `provenance`.

Chaque ligne de `chunks.jsonl` : `chunk_id`, `doc_id`, `kb_id`, `lang`, `page`, `article`, `text`, `text_sha256`, `char_start`, `char_end`, `license`.

Signature optionnelle : Ed25519 sur le SHA-256 du manifest canonisé JCS (RFC 8785). [NV pour le choix de l'algorithme]

Import : valider le manifest, recalculer chaque SHA-256, rejeter tout chemin hors `data/`, tout lien symbolique, et toute entrée dépassant les seuils. Seuils proposés **[NV]** : 500 Mo décompressés, 10 000 entrées, ratio de compression 100:1 au maximum. Exclure à l'export tout fichier hors liste blanche (`.env`, clés, `.git`).

### 2.4 Pipeline d'ingestion
1. Entrée : PDF ou DOCX. Calcul du SHA-256 de l'original.
2. Extraction par page avec pdfplumber (MIT). Si une page n'a pas de couche texte, rendu image puis Tesseract (Apache-2.0) avec `ara+fra+eng`.
3. Normalisation : Unicode NFC, direction RTL préservée pour l'arabe, suppression des en-têtes et pieds de page répétés.
4. Découpage structure-aware par article (`Article N` / `المادة N`) ; repli sur 512 tokens avec 25 % de recouvrement.
5. Préfixe contextuel par chunk : titre de document, article, page (P5 en option, après mesure).
6. Embedding BGE-M3 (dense) et indexation FTS5.
7. Écriture de la KB dans SQLite, puis export JSONL.
Éviter PyMuPDF tant que la question de l'AGPL n'est pas tranchée.

### 2.5 Métriques d'évaluation
Sans service payant :
- **Retrieval** (déterministe) : recall@5, recall@10, MRR, nDCG@10, à partir d'un jeu de requêtes labellisées (`query`, `relevant_chunk_ids` avec grade 0 à 3). Équivalent des métriques Document Retrieval de Azure. [V pour les métriques, NV pour le jeu)
- **Citation precision** (déterministe) : pour chaque citation, le `chunk_id` est dans les résultats renvoyés et le texte cité est une sous-chaîne normalisée du chunk. Cible : 100 %. [NV]
- **Groundedness** (LLM-juge local) : prompt qui demande si chaque phrase de la réponse est soutenue par les chunks cités ; score 1 à 5, seuil 3 comme Azure. [NV]
- **Response completeness** (LLM-juge local) : comparaison à une réponse de référence. [NV]
- **Sécurité** (déterministe) : taux de fuite entre KB = 0 sur des requêtes d'agents sans droit. Test bloquant.
- Le juge local doit être un modèle différent du modèle de génération, ou au minimum une version figée. Vérifier l'accord juge/humain sur 50 réponses. [NV]

---

## 3. Points non vérifiés (à traiter avant de figer)
- Lecture du papier RRF (PDF) : seul le résumé de recherche a été utilisé.
- SQLite FTS5 : page non lue ; tokenisation arabe non testée.
- Chroma : version courante et migration non vérifiées ; la contrainte de concurrence vient d'une source secondaire.
- multilingual-e5-small : fiche officielle non lue ; langues et préfixes issus de miroirs.
- BGE-M3 : vitesse CPU, RAM réelle et qualité arabe non mesurées.
- Ollama `bge-m3` : page marquée « Updated 2 years ago ».
- RO-Crate (researchobject.org) et Zip Slip (Snyk) : non lus.
- Docling : provenance par page et besoins CPU non confirmés.
- pymupdf4llm : licence non vérifiée.
- Tesseract : tessdata `ara`, `fra`, `eng` et vitesse CPU non vérifiés.
- Seuils ZIP (500 Mo, 10 000 entrées, ratio 100:1) : recommandations de conception, non sourcées.

## 4. Plan de vérification
1. Jeu d'essai : 30 pages FR/EN/AR (10 scannées), 100 requêtes labellisées (dont 20 avec numéros d'article exacts).
2. Benchmarks : BGE-M3 vs e5-small sur le CPU 4 cœurs (temps, RAM, recall@10). Tesseract sur les pages scannées (CER et temps).
3. Tests de sécurité : agent sans droit ; requête qui tente de forcer un `kb_id` ; filtres appliqués avant FTS5 et vecteurs.
4. Tests d'export : round-trip, vérification des SHA-256, archive malveillante (`../`, lien symbolique, bombe).
5. Évaluation : retrieval déterministe (recall, MRR, nDCG), citation precision, puis LLM-juge (groundedness, completeness).

## Sources consultées
- https://learn.microsoft.com/en-us/azure/foundry/concepts/retrieval-augmented-generation
- https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/rag-evaluators
- https://learn.microsoft.com/en-us/azure/search/hybrid-search-overview
- https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking
- https://learn.microsoft.com/en-us/azure/search/search-security-trimming-for-azure-search
- https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-chunk-documents
- https://www.anthropic.com/news/contextual-retrieval
- https://docs.trychroma.com/docs/overview/getting-started
- https://docs.trychroma.com/docs/querying-collections/metadata-filtering
- https://cookbook.chromadb.dev/core/system_constraints/ (secondaire)
- https://huggingface.co/BAAI/bge-m3
- https://ollama.com/library/bge-m3
- https://ollama.com/library/nomic-embed-text
- https://github.com/asg017/sqlite-vec
- https://sqlite.org/fts5.html (non lu)
- https://www.rfc-editor.org/rfc/rfc8493
- https://www.rfc-editor.org/rfc/rfc8785
- https://jsonlines.org/
- https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
- https://pymupdf.readthedocs.io/en/latest/about.html
- https://github.com/jsvine/pdfplumber
- https://github.com/tesseract-ocr/tesseract
- https://github.com/docling-project/docling
- https://github.com/Unstructured-IO/unstructured
- Cormack, Clarke, Büttcher, SIGIR 2009, DOI 10.1145/1571941.1572114
