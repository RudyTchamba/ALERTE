# Étape 1 — État des lieux du pipeline documentaire (2026-11-25)

> **Mise à jour 2026-11-25 :** les défauts listés en §3 ont été traités (stockage par périmètre, CLI, états détaillés, relance, construction par base, interface). Voir [cli-et-pipeline.md](cli-et-pipeline.md). Ce document reste l'état des lieux **avant** implémentation.


Audit en **lecture seule**, fait en lisant le code et en exécutant le pipeline (construction de référence du 2026-11-24, 549 tests backend). Aucun sous-agent n'a été utilisé : l'audit a été fait directement. Les affirmations sont étiquetées **[code]** (lu), **[exécuté]** (constaté en réel), **[test]** (couvert par la suite).

## 0. Constat de contexte
* Le projet historique `alerte/` n'est **plus dans le dépôt** : il est maintenant à `<dossier du projet historique alerte>/` (au même niveau que le dépôt), avec les spécifications, le rapport technique et la présentation ITU. Il contient les **mêmes 44 PDF** (AE 9, CM 17, GL 16, ITU 2 ; 136 Mo). **Conséquence : `kb_build.py` et `kb_inventory.py` sont cassés** (ils lisent `REPO / "alerte/..."`).
* Dans `alerte-platform/`, il n'y a qu'**un seul PDF** : `backend/scripts/corpus_fixes/CM-07_Decree_No_98-031…pdf` (le vrai décret, ajouté par un coéquipier). Pas d'autre PDF source.
* Le dernier commit (`b00e852`, « constructing the knowledge base ») contient mes correctifs et `knowledge_bases/`.

## 1. Réponses aux dix questions

| # | Question | Réponse vérifiée |
|---|---|---|
| 1 | Comment les documents sont-ils découverts ? | **Ils ne le sont pas dans l'application** : un document existe parce qu'un fichier est envoyé (`POST /knowledge-bases/{id}/documents`) [code]. La « découverte » est faite par des **scripts** : `kb_inventory.py` (parcours récursif d'un dossier), `kb_build.py` (parcourt la liste du registre de curation), `legacy_to_archive.py` (parcourt `alerte/data/docs` + l'index du prototype) [code]. |
| 2 | D'où viennent les PDF ? | Du dossier de l'ancien projet, lu **en place** par les scripts (`REPO / original_path`) [code]. Une fois envoyé, le fichier est copié dans le **stockage adressé par contenu** `data/blobs/<sha[:2]>/<sha256>` (`BlobStore`) [code]. Il n'existe **aucune copie des PDF dans `alerte-platform/`** : le nouveau projet dépend de `alerte/` pour reconstruire. |
| 3 | Comment un document est-il associé à un pays ? | **Indirectement** : `KnowledgeBase.country_id` (facultatif) et `Document.jurisdiction` (**texte libre**) [code]. Le script `kb_build.py` fixe la correspondance en dur (`COLLECTIONS = {CM, AE, GL, ITU}`) et dérive le **code du document du préfixe du nom de fichier** (`CM-01`…) via le registre de curation : **dépendance aux noms à supprimer** [code]. |
| 4 | Comment les chunks sont-ils produits ? | `extract.py` (pdfplumber + OCR Tesseract des pages pauvres) → `normalize_text` → `chunk_pages` (stratégie `article-aware`, 2 000 caractères, recouvrement 200) dans le job `kb_ingest` (`ingest_version`) [code, exécuté]. |
| 5 | Comment les embeddings sont-ils générés ? | Job **par base** `kb_embed` (`embed_kb`) : ne traite que les chunks **sans vecteur de l'empreinte courante** → **incrémental par chunk, reprenable** [code, exécuté]. Empreinte du modèle stockée **sur la base** (`embedder_key`, `embedder_fingerprint`) ; changer de modèle exige `reembed=true` (409 sinon) [code, test]. **Manques** : pas de date de génération par vecteur, ni de lien vers la « version de traitement » du document. |
| 6 | Comment les index sont-ils construits ? | FTS5 : **une seule table `chunk_fts`** pour toutes les bases (colonnes `kb_id`, `document_version_id`, `workspace_id`) ; vectoriel : **une collection ChromaDB par empreinte d'embedder** (`alerte_chunks_<clé>`, partagée entre bases, `kb_id` en métadonnée) + index NumPy exact de garde [code]. `reindex_kb` **supprime puis réinsère** les lignes FTS d'une base (non atomique) [code]. |
| 7 | Comment le traitement est-il suivi ? | `document_version.status` ∈ {`processing`, `ready`, `needs_review`, `failed`, `retired`} + `quality_report` (JSON) + table `job` (`queued/running/done/failed/interrupted`, progression, message, résultat, erreur) [code]. **Pas d'historique par document**, pas d'états intermédiaires (`extracting`, `ocr_processing`, `chunking`, `embedding`, `indexing`), pas de suivi de l'embedding **par document**. |
| 8 | Pourquoi certaines commandes construisent-elles « globalement » ? | **Parce que mes scripts ont `--collections CM,AE,GL,ITU` par défaut** (`kb_build.py`, `kb_export.py`, `kb_eval.py`) et que `legacy_to_archive.py` traite toutes les collections [code]. L'**API** est par base (`/knowledge-bases/{id}/embed|reindex|publish`) : elle n'a pas de construction globale. |
| 9 | Quelles opérations ne sont disponibles qu'en CLI ? | Import **en masse depuis un dossier**, application d'un **fichier de métadonnées**, inventaire (SHA-256, doublons), évaluation (Recall@5/MRR), **export vers `knowledge_bases/`** (avec politique de droits), installation des modèles OCR. **Il n'existe aucune CLI** dans l'application : pas de `python -m app.cli` ; les `scripts/*.py` sont des **clients HTTP autonomes** qui dupliquent leur propre logique (correspondances, ordre des étapes). |
| 10 | Réutilisable / à corriger ? | Voir §3. |

## 2. Vérifications du fonctionnement réel (au-delà de l'existence des pages)

| Point | Résultat |
|---|---|
| Import de 44 PDF par l'API | **Fonctionne** (44/44, ~25 min dont OCR) [exécuté]. |
| Doublon exact | Refusé **par base** (`kb.document.duplicate`, même SHA-256, version non retirée) ; **le même PDF peut être dans deux bases** [code, test]. |
| Deux fichiers de même nom, contenu différent | **Aucun écrasement** possible (stockage par hash) ; le nom d'origine n'est qu'un champ (`original_name`, 300 caractères) [code]. |
| Document interrompu | **Défaut** : au redémarrage le job passe `interrupted` mais la **version reste `processing` indéfiniment** ; `publish` refuse alors toute la base (« des documents sont encore en cours de traitement ») et **aucune route ne permet de relancer** le traitement (l'API n'accepte qu'un nouveau fichier) [code]. `ingest_version` sait pourtant « reprendre » une version non publiée (table rase) [code]. |
| Échec d'un fichier dans un lot | Isolé : chaque fichier a son job ; l'interface envoie les fichiers **un par un** ; une erreur n'arrête pas les suivants [code, exécuté]. |
| Version publiée vs reconstruction | La publication est un **instantané immuable** (`kb_version` + `kb_version_item`) ; les agents lisent les versions **publiées** : une ré-ingestion de brouillon ne touche pas la version publiée [code, test]. `reindex_kb` modifie les index de toute la base pendant son exécution [code]. |
| Isolation entre bases | **Effective et testée** : la portée (`SearchScope` : espace, `kb_ids`, versions) n'est construite **que côté serveur**, appliquée dans chaque moteur (FTS, Chroma `where`, NumPy) puis **revérifiée en SQL**, avec journal des violations [code, test `test_scope_security.py` : 9 tests] [exécuté : 0 violation]. Pas de test « construire CM ne modifie pas AE » (aucune notion de construction par pays). |
| Embeddings incrémentaux | Un nouveau document n'embarque que ses chunks (requête `NOT EXISTS` sur `chunk_embedding`) [code]. Non testé explicitement « ajout d'un seul PDF ». |
| Interface actuelle | Onglets : Documents (**envoi multiple** avec un **seul jeu de métadonnées commun**, glisser-déposer, progression par fichier), Qualité, Versions (publier, embeddings, reindex), Recherche, Export/Import. **Absents** : aperçu des fichiers avant envoi, métadonnées par fichier à l'envoi, compteurs par statut, **relance d'un document**, construction « par pays », vue des index par document [code]. |

## 3. Ce qui est réutilisable / à corriger

**Réutilisable tel quel** : extraction/OCR/chunking/qualité (`app/knowledge/extract.py`, `chunking.py`, `ingest.py`), stockage par contenu, jobs avec progression, isolation par portée, publication immuable, embeddings incrémentaux et empreinte, recherche hybride, politique de droits (`redistribution`), export/import d'archives.

**À corriger / ajouter** (alimente l'étape 2) :
1. **Aucun stockage physique par pays** ; aucun chemin de fichier en base.
2. **Aucune CLI applicative** (services partagés avec l'API) ; les scripts doublonnent la logique et ont un **périmètre global par défaut**.
3. **Dépendance aux noms de fichiers** dans `kb_build.py` (code du document = préfixe du nom) et dans la curation (clé = préfixe).
4. **Dépendance au dossier `alerte/`** (chemins relatifs à l'ancien dépôt, désormais invalides).
5. **Statuts trop grossiers**, pas d'historique, **version bloquée en `processing`** après interruption, **aucune relance** de document.
6. **Interface** : métadonnées par fichier, aperçu avant envoi, états détaillés, relance, construction/reconstruction par base avec périmètre affiché.
7. **Embeddings** : date de génération et rattachement à la version de traitement ; état par document.
8. **Reconstruction** : `reindex` non atomique (pas d'espace de travail distinct).
9. **Tests manquants** : isolation « construire CM n'altère pas AE », ajout d'un seul PDF, relance sans duplication, noms arbitraires, collisions de noms, refus sans périmètre.
