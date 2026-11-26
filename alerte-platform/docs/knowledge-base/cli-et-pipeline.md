# Pipeline documentaire, stockage par périmètre et CLI (état implémenté)

Décisions validées : **A** stockage physique unique sous `data/blobs/knowledge_sources/`, **B** CLI qui appelle les services en direct, **C** états de traitement détaillés. Ce document décrit ce qui est **réellement implémenté et testé** ; les étiquettes **[TEST]** (suite automatisée), **[CLI-RÉEL]** (exécuté sur les 44 PDF dans un dossier de données isolé), **[ABS]** (non fait) indiquent le niveau de vérification.

## 1. Organisation physique des PDF
```text
<ALERTE_DATA_DIR>/blobs/knowledge_sources/
├── CM/   (Cameroun — pays)          17 PDF directement dans le dossier
├── AE/   (Émirats arabes unis)       9 PDF
├── GL/   (références globales)      16 PDF
└── organizations/ITU/               (l'ITU est une organisation, pas un pays)   2 PDF
```
* **Un PDF = un fichier** dans le dossier de son périmètre. Pas de sous-dossier par PDF, pas de lien symbolique ni physique, pas de second répertoire racine. Le dossier fait partie de `ALERTE_DATA_DIR` (portable ; aucun chemin absolu en base : `document_version.storage_path` est **relatif**, ex. `CM/CM-02_….pdf`). **[TEST]**
* Le périmètre vient de la **base choisie** (`knowledge_base.scope_kind` : `country`, `global`, `organization`), jamais du nom du fichier : un fichier nommé `AE-01_ITU_2031.pdf` importé dans CM reste dans `CM/`, sans pays, institution, année ni type déduits. **[TEST]**
* Même nom, contenu différent : les deux sont conservés (suffixe technique `__<8 premiers caractères du SHA-256>`) ; même contenu : refus (`kb.document.duplicate`, SHA-256). Écriture atomique via `.incoming/`, jamais d'écrasement, anti-évasion de chemin. **[TEST]**
* Les **anciens originaux** du magasin adressé par contenu (`data/blobs/<sha[:2]>/<sha>`) restent lisibles : si `storage_path` est vide, le résolveur retombe sur l'ancien emplacement (compatibilité V1, archives, exports). Rien n'a été supprimé.
* Migration depuis le projet historique : `sources-migrate` (simulation par défaut, copie seule, source jamais modifiée, doublons par SHA-256, manifeste de provenance `knowledge_bases/inventory/migration_manifest.jsonl`). **[TEST]** **[CLI-RÉEL]**

## 2. Modèle documentaire (migration Alembic additive `0003`)
`document_version` : `storage_path`, `migration_filename`, `download_name` (seulement s'il est connu), `provenance` (JSON : origine `upload`/`adopted`/`legacy_project`, dossier de départ, date), `processing_state`, `processing_error`. `document_event` : historique (version, état, message, job, date). `knowledge_base.scope_kind`, `chunk_embedding.created_at`. L'ancien `status` est conservé et **dérivé** de l'état détaillé (`uploaded…indexing → processing`) : API et exports V1 inchangés.

États : `uploaded → validating → queued → extracting → ocr_processing → structuring → chunking → embedding → indexing → ready | needs_review | failed` (+ `retired`). Au démarrage du serveur, toute version restée « en cours » passe `failed` (« traitement interrompu… ») et peut être relancée individuellement ; la CLI **ne déclenche pas** cette récupération (elle ne doit pas condamner les traitements d'un serveur qui tourne) : commande explicite `recover`. **[TEST]**

## 3. Services partagés (aucune logique dans les routes, la CLI ou l'interface)
`app/knowledge/services/` : `sources.py` (stockage, migration, vérification), `pipeline.py` (états, historique, récupération, relance, dernière version par document), `build.py` (périmètre, état, cohérence, construction), `curation.py` (registre de métadonnées lié aux PDF par SHA-256). Cœur existant : `kbops.py`, `ingest.py`.

**Construction d'une base** (`build_kb`) : 1) traite ses documents en attente (un échec n'arrête pas les autres) ; 2) calcule les embeddings **manquants** (non destructif : en cas de changement de modèle, l'ancien index reste actif jusqu'à la fin) ; 3) remplace atomiquement son index lexical ; 4) contrôle de cohérence ; 5) publie seulement sur demande **et** si tout est cohérent **et** si **tous** les extraits ont un vecteur — sinon la dernière version publiée reste active (`publish_refused` donne la raison). Une panne du serveur d'embeddings (ex. `ReadTimeout`) ne fait pas échouer la tâche mais la marque `partial` avec `vectorization: {status: failed|incomplete, embedded, chunks, error}` ; le code de sortie CLI est 1 et l'onglet Construction affiche un bandeau rouge. Relancer la même commande ne recalcule que les vecteurs manquants. Elle n'écrit que dans les lignes de **sa** base. **[TEST]** (empreinte complète d'une base avant/après la construction d'une autre : documents, versions, chunks, FTS, vecteurs, événements, fichiers).

## 4. CLI : `python -m app.cli`
Appelle directement les services (aucune requête HTTP, aucun serveur). Les opérations sur une base **exigent** `--country <CODE>` ou `--kb-id <ID>` ; sans périmètre : refus (code de sortie 2) :
```text
$ python -m app.cli knowledge build
REFUS : un périmètre explicite est obligatoire : indiquez un pays (--country CM) ou une base (--kb-id <ID>) ; aucune construction globale n'est lancée
$ python -m app.cli knowledge build --country XX
REFUS : aucune base pour le périmètre 'XX' (codes disponibles : AE, CM)
```
| Commande | Effet |
|---|---|
| `workspace create --name N` | crée l'espace, affiche le jeton propriétaire une seule fois |
| `knowledge kb-create --code CM --name Cameroun [--scope-kind organization]` | crée une base ; son dossier = `blobs/knowledge_sources/<code>` (`organizations/<code>`) |
| `knowledge kb-list` | bases, documents par état, chunks, vecteurs |
| `knowledge sources-migrate --map CM=<dossier> --map organizations/ITU=<dossier> [--apply --manifest f.jsonl]` | copie non destructive (simulation sans `--apply`) |
| `knowledge sources-list / sources-verify --country CM` | fichiers non enregistrés / présence + SHA-256 |
| `knowledge adopt --country CM --manifest f.jsonl` | enregistre les fichiers déjà présents (sans copie), provenance reportée |
| `knowledge curate --country CM --curation …/documents.curation.json --manifest f.jsonl` | applique les métadonnées validées, lien PDF↔ligne par SHA-256 |
| `knowledge import --country CM a.pdf b.pdf [--meta language=fr] [--no-process]` | un ou plusieurs fichiers = autant de documents indépendants |
| `knowledge status --country CM [--documents]` | état détaillé |
| `knowledge process --country CM` / `--document <ID>` | traite les documents en attente / un seul document |
| `knowledge retry --country CM` / `recover` | relance les échecs / marque failed les « en cours » orphelins |
| `knowledge embed / index / check / build / publish --country CM` | embeddings manquants (`--reembed`), index lexical, cohérence, construction (`--steps process,embed,index`, `--publish`), publication |

Exemple réel **[CLI-RÉEL]** (dossier de données isolé, 44 PDF du projet historique) :
```text
$ python -m app.cli knowledge sources-migrate --map CM=…/alerte/data/docs/CM --map AE=…/AE --apply --manifest m.jsonl   # copie, source intacte
$ python -m app.cli knowledge adopt --country CM --manifest m.jsonl     → 17 enregistré(s), 0 refusé(s)
$ python -m app.cli knowledge curate --country CM --curation knowledge_bases/curation/documents.curation.json --manifest m.jsonl
curation appliquée à la base : {'applied': 17}
$ python -m app.cli knowledge process --document 01M8AB0FY9NDAAYE9N2F1QZ7RT   → état=ready chunks=15   (AE inchangée : 0 chunk, 9 en attente)
$ python -m app.cli knowledge build --country CM --steps process,index      → 16 documents traités, result: ok
$ python -m app.cli knowledge kb-list
AE  … documents=  9 prêts=  0 en attente=  9 chunks=    0  pending
CM  … documents= 17 prêts= 17 en attente=  0 chunks= 1351 vecteurs=0/1351  lexical_only
$ python -m app.cli knowledge check --country CM
OK documents_have_chunks · OK no_stuck_processing · OK lexical_index_complete (FTS 1351/1351)
KO embeddings_complete  aucun embedding calculé : recherche lexicale seule (dégradée)
OK source_files_intact
```
Le **vrai décret 98/031** (CM-07) donne 14 chunks. Les embeddings n'ont **pas** été calculés dans cette exécution : le contrôle le dit (`KO`), l'index est « lexical seul » — ce n'est pas présenté comme hybride.

## 5. API et interface
Routes ajoutées : `GET /knowledge-bases/{id}/status|check|unregistered`, `POST /knowledge-bases/{id}/build|adopt`, `GET /documents/{id}/versions/{n}/events`, `POST /documents/{id}/versions/{n}/reprocess`, filtre `?state=` sur les documents. Le champ `version` d'un document est sa **dernière** version (un document importé non encore traité apparaît donc avec son état). **[TEST]**

Interface (page d'une base) : **Documents** — périmètre et dossier affichés, sélection de plusieurs fichiers avec **aperçu avant envoi** (nom, taille, SHA-256 calculé dans le navigateur, alerte « même contenu » dans le lot, **métadonnées par fichier**), import indépendant par fichier avec progression, tableau avec **état détaillé**, erreur lisible, bouton **Relancer/Traiter** par document, filtre par état, panneau « fichiers présents mais non enregistrés » ; **Construction** — compteurs par état, chunks, embeddings (x/y), index lexical/vectoriel, version publiée, actions *Traiter les documents en attente / Calculer les embeddings manquants / Reconstruire l'index / Construire cette base / Tout recalculer*, chacune nommant la base et demandant confirmation, vérification de cohérence, publication ; **page document** — état, chemin relatif, SHA-256, provenance, historique de traitement, relance. Aucun bouton « tout construire ». **[TEST]** (vitest/jsdom, 3 tests dédiés + 91 tests front). **[ABS]** Le parcours n'a **pas** été cliqué dans un navigateur réel dans cette session (aucun outil de pilotage de navigateur disponible) : voir le guide §5 pour le contrôle manuel.

## 6. Droits et publication
`redistribution` vaut `unknown` par défaut ; l'import ne publie jamais. L'export « Publication ouverte » reste **refusé** tant que des documents sont `restricted` ou `unknown` (`kb.export.restricted_documents`) ; publier une version de base (usage interne par les agents) ne rend aucun texte public. **Publication bloquée tant que la vectorisation est incomplète** : `publish_kb` (API, CLI `publish`, `build --publish`) refuse avec `kb.publish.vectors_incomplete` (409) si un extrait d'une version à publier n'a pas de vecteur du modèle actif ; la vérification `embeddings_complete` rend aussi la base « incohérente ». **[TEST]** (backend : `test_publication_is_refused_until_every_chunk_has_a_vector`, `test_failed_vectorization_is_reported_and_blocks_publication` ; frontend : bandeau + bouton désactivé). **[TEST]** (tests d'export existants).

## 7. Limites connues
* Les originaux importés par **archive** restent dans l'ancien magasin par contenu (lecture compatible) ; seuls les nouveaux imports et la migration utilisent `knowledge_sources/`.
* Les données du dossier `backend/data` de l'utilisateur (prototype) n'ont **pas** été migrées ni supprimées.
* Embeddings réels (BGE-M3) non recalculés pour AE/GL/ITU/CM dans cette session ; les tests utilisent `FixtureEmbedder` (SANS IA).
* Interface non testée dans un navigateur réel.
