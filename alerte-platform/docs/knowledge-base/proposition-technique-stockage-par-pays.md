# Étape 2 — Proposition technique (à valider avant l'étape 4)

> **Décisions validées et implémentées (2026-11-25) :** **A** — le stockage canonique est `data/blobs/knowledge_sources/` (`CM/`, `AE/`, `GL/`, `organizations/ITU/`) : un seul exemplaire, ni lien ni `storage/`, anciens blobs conservés ; **B** — CLI en direct sur les services ; **C** — états détaillés, `status` conservé et dérivé. Les passages ci-dessous sur `ALERTE_STORAGE_DIR`, `os.link` et `storage/` sont **abandonnés** ; la référence est [cli-et-pipeline.md](cli-et-pipeline.md).


Respecte l'architecture V1 : on **adapte** `app/knowledge`, on ne remplace aucune brique (SQLite + FTS5 + ChromaDB + BGE-M3, jobs en processus, API FastAPI, interface React).

## 1. Stockage physique simplifié par pays

```text
alerte-platform/storage/knowledge_sources/        (ignoré par Git : droits de redistribution)
├── CM/   fichier_a.pdf  fichier_b.pdf …
├── AE/   …
├── GL/   …
└── ITU/  …
```
* Une **portée** = un code déjà défini dans le projet (`CM`, `AE`, `GL`, `ITU`), validé par `^[A-Z][A-Z0-9]{1,7}$` ; le dossier est créé à la demande.
* **Un fichier PDF = un fichier** dans le dossier de sa portée. Pas de sous-dossier par document.
* **Nom physique** = nom fourni à l'import, nettoyé (séparateurs, caractères de contrôle, longueur). Si le nom existe déjà avec un **autre contenu**, le nouveau fichier reçoit un suffixe technique `__<8 premiers caractères du SHA-256>` ; si le contenu est **identique** (même SHA-256), aucun fichier n'est ajouté (doublon). Le nom physique n'a **aucun rôle d'identité**.
* Configuration : `ALERTE_STORAGE_DIR` (défaut : `alerte-platform/storage`, indépendant du dossier de lancement). Le dossier de données d'exécution (`ALERTE_DATA_DIR`) reste séparé (base, index, ancres, clés).

**Décision à valider A — canonique ou lien ?** Le contrat V1 (doc 06) place les originaux dans un **stockage adressé par contenu** (`data/blobs`). Je propose de **le conserver** (intégrité, export/import d'archives inchangés) et de faire du dossier par pays un **lien physique (`os.link`)** vers le même fichier, avec **repli en copie** si le lien est impossible (autre disque). Pas de doublon de 136 Mo sur un même disque. La base enregistre **les deux** (`blob_sha256` et `storage_path`) ; la commande `sources verify` détecte un fichier modifié ou supprimé à la main. *Alternative* : rendre le dossier par pays canonique et supprimer l'original du blob store (plus simple à lire, mais modifie le contrat V1 et l'export).

## 2. Modèle documentaire (migration Alembic additive `0003`)
Sur `document_version` (une ligne par PDF et par version de traitement) :
| Champ | Rôle |
|---|---|
| `storage_scope` | code de portée du dossier (`CM`) |
| `storage_path` | chemin **relatif** à `ALERTE_STORAGE_DIR` (ex. `CM/fichier_a.pdf`) |
| `migration_filename` | nom du fichier **au moment de la migration** (null si import direct) |
| `upload_filename` | nom fourni à l'import (déjà `original_name`, conservé) |
| `download_name` | nom de téléchargement d'origine, **seulement s'il est réellement connu** |
| `provenance` | JSON : origine (`legacy_project`, `platform_existing`, `upload`), chemin source, date, opérateur |
| `processing_state` | `uploaded, validating, queued, extracting, ocr_processing, structuring, chunking, embedding, indexing, ready, needs_review, failed` (remplace le `status` à 5 valeurs ; `retired` reste) |
| `processing_error` | dernière erreur lisible + étape |
Nouvelle table `document_event` (**historique** : version, état, étape, message, date, job) → traçabilité et reprise.
`Document.jurisdiction` devient celui de la **portée** (`country`), jamais déduit d'un nom. Titre officiel = `Document.title` (distinct du nom de fichier) ; type, éditeur, année, domaine, fiabilité : **uniquement** saisis ou lus dans le contenu, sinon `unknown`.
Embeddings : `chunk_embedding` gagne `created_at` et `processing_version` (hash du texte déjà dans `chunk.text_sha256`).

## 3. Services communs (un seul moteur métier)
Nouveau package `app/knowledge/services/` — **aucune logique dans les routes ni la CLI** :
| Service | Rôle | Isolation |
|---|---|---|
| `sources.import_pdf(scope, kb_id, stream, filename, meta)` | validation, stockage, doublon (SHA-256), enregistrement, état `uploaded` | portée **obligatoire** |
| `sources.import_many(...)` | N appels **indépendants** (un échec n'arrête pas les autres) | idem |
| `sources.migrate(mapping, dry_run)` | copie **non destructive** depuis un dossier source, provenance | idem |
| `pipeline.process_document(version_id)` | extraction → OCR → structure → chunks → (embeddings) → index, avec états et événements ; **relançable** sans duplication | par base |
| `pipeline.requeue_stuck()` | remet en `failed/queued` les versions restées `processing` après une interruption | par base |
| `build.build_kb(kb_id|country, steps, publish)` | traite **uniquement** les documents en attente de **cette** base, embeddings manquants, index, contrôle de cohérence, publication éventuelle | **refuse sans périmètre** |
| `build.check_coherence(kb_id)` | documents ↔ chunks ↔ FTS ↔ vecteurs ↔ empreinte | par base |
Contrats d'entrée : un objet `Scope` (portée + base) validé par le service ; les routes API et la CLI **construisent** ce `Scope`, ne le contournent pas.

## 4. CLI applicative : `python -m app.cli`
Module `app/cli.py` qui appelle **directement les services** (même processus, mêmes sessions), les jobs s'exécutent de façon synchrone avec la progression affichée.
```bash
python -m app.cli knowledge sources migrate --map CM=/chemin/alerte/data/docs/CM --dry-run
python -m app.cli knowledge import --country CM --kb CM  fichier1.pdf fichier2.pdf
python -m app.cli knowledge build --country CM            # ou --kb-id <ID> ; sans périmètre : REFUS explicite
python -m app.cli knowledge process --document <ID>       # relance individuelle
python -m app.cli knowledge embed|index|check|publish --kb-id <ID>
python -m app.cli knowledge sources verify --country CM
```
**Décision à valider B — la CLI appelle-t-elle les services en direct ou l'API HTTP ?** En direct = pas de serveur à lancer, même logique métier, mais elle ouvre la base : à utiliser **backend arrêté** ou en SQLite WAL (supporté). Via HTTP = serveur requis, mais comportement strictement identique à l'interface. Je recommande **en direct** pour la construction (long, sans serveur) avec la même couche de services que l'API.
Les scripts `kb_build.py`, `kb_export.py`, `kb_eval.py` perdent leur périmètre par défaut (`--country`/`--kb-id` **obligatoire**) ; `kb_build.py` cesse de dériver des codes depuis les noms de fichiers.

## 5. API et interface
* `POST /knowledge-bases/{id}/documents` accepte déjà un fichier ; ajout : **métadonnées par fichier** (champ JSON), `POST /documents/{id}/versions/{n}/reprocess`, `GET /knowledge-bases/{id}/status` (compteurs par état, chunks, vecteurs, index, version active, dernière construction), `POST /knowledge-bases/{id}/build` (périmètre = la base, jamais global).
* Interface (onglets existants) : **Documents** : sélection de fichiers avec **liste d'aperçu** (nom, taille, SHA-256 calculé dans le navigateur, **métadonnées par ligne**, portée/base affichées en haut), progression et état **par document**, bouton **Relancer**, filtres par état ; **Construction** : carte « Cameroun — base CM » avec compteurs et boutons *Traiter les documents en attente*, *Calculer les embeddings manquants*, *Reconstruire cette base*, chaque action indiquant « portée : CM » avant confirmation ; **Qualité** : cohérence documents/chunks/index. Aucune action « tout construire ».

## 6. Embeddings, index, reconstruction
* Un embedding = (chunk, empreinte du modèle, dimension, **date**, version du texte) ; jamais mélangés entre empreintes (déjà vrai : 409 si l'empreinte change sans `reembed`).
* **Index incrémentaux** : `reindex` ne supprime plus toute la base ; mise à jour **par document**. La reconstruction complète d'une base écrit dans une **nouvelle version de travail** ; elle n'est activée (publication) qu'après `check_coherence` ; en cas d'échec la **dernière version publiée reste active** (déjà garanti par l'immuabilité des `kb_version`).
* Isolation : en plus des tests existants, tests « construire/reconstruire `CM` ne modifie ni documents, ni chunks, ni vecteurs, ni FTS, ni versions de `AE` » (comparaison d'empreintes avant/après).

## 7. Migration non destructive (étape 3)
Copie des PDF de `<dossier du projet historique alerte>/data/docs/{CM,AE,GL,ITU}` **et** du PDF existant `backend/scripts/corpus_fixes/…decret 98-031…pdf` vers `storage/knowledge_sources/<portée>/` ; le **dossier source** (choix humain du projet historique) sert seulement de **portée de départ à vérifier**, enregistré comme provenance — **jamais** le nom du fichier. Aucun fichier source déplacé ni modifié ; doublons par SHA-256 ; manifeste `knowledge_bases/inventory/migration_manifest.jsonl`. Les anciennes données de `backend/data/` (archive du prototype) ne sont **ni supprimées ni migrées automatiquement** : elles sont étiquetées « prototype, non vérifié » dans l'état des lieux.

## 8. Répartition du travail (aucun fichier partagé)
| Membre | Périmètre (fichiers) |
|---|---|
| 1 — stockage, documents, pipeline | `app/knowledge/services/sources.py`, `pipeline.py`, migration `0003`, `models.py` (champs document), `ingest.py` (états), `app/cli.py` |
| 2 — bases, index, recherche | `services/build.py`, `kbops.py` (embed/reindex/publish), `indexes.py`, `search.py`, tests d'isolation |
| 3 — interface, documentation | `frontend/src/features/kb/*`, i18n, `docs/knowledge-base/*`, `guide-test-complet-interface.md` |
Contrats communs (schémas de réponse `status`, états, `Scope`) figés **avant** les travaux (ce document) ; intégration après chaque étape. Dans cette session, **un seul agent** (moi) réalise les trois parties **séquentiellement** : l'étiquette « membre » désigne la propriété des fichiers, pas des acteurs distincts. Aucun sous-agent Haiku/Opus n'a été utilisé à ce jour.

## 9. Décisions demandées avant l'étape 4
* **A** : lien vers le blob store (recommandé) ou dossier par pays canonique ?
* **B** : CLI en direct sur les services (recommandé) ou via HTTP ?
* **C** : le remplacement de `status` par `processing_state` (migration additive, `status` conservé et dérivé pendant la transition) vous convient-il ?
L'étape 3 (copie des PDF) ne dépend d'aucune de ces décisions et peut être faite maintenant.
