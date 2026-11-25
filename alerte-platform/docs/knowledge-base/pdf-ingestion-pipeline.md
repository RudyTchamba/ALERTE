# Pipeline d'ingestion des PDF

Un **seul** pipeline, dans `backend/app/knowledge/` : l'interface graphique (page *Bases de connaissances → Documents*) et le script `scripts/kb_build.py` appellent les mêmes endpoints (`POST /knowledge-bases/{id}/documents`, job `kb_ingest`). Il n'existe pas de pipeline parallèle pour les scripts.

| Étape | Code | Comportement réel |
|---|---|---|
| Réception | `kbops.store_upload` | signature `%PDF-` vérifiée, SHA-256, blob adressé par empreinte ; refus d'un doublon exact dans la base (`kb.document.duplicate`) |
| Métadonnées | `kbops.create_document` | titre, type, numéro, date, langue, juridiction, fiabilité, validité, droits : fournis par l'import (registre de curation) ou la fiche ; `redistribution` vaut `unknown` par défaut |
| Extraction par page | `extract.py` | `pdfplumber` (couche texte) ; **une page de moins de 80 caractères est envoyée à l'OCR** (Tesseract, 250 DPI, langues `ALERTE_OCR_LANGS`) ; confiance OCR < 60 % ou langue manquante ⇒ page **« à relire »** avec la raison ; aucun échec silencieux ; PyMuPDF (AGPL) jamais utilisé |
| Structuration | `chunking.py` | reconnaissance des **articles** (`Article N`, `ARTICLE N`, `Art. N`, arabe) et des sections ; un article est rattaché à ses chunks ; rien n'est inventé si la reconnaissance échoue (`article = null`) |
| Découpage | `chunking.py` | stratégie `article-aware` ; max 2 000 caractères, recouvrement 200 caractères seulement à l'intérieur d'un article trop long ; page de début/fin conservées |
| Qualité | `ingest.py` | `extraction_quality`, `pages_to_review`, `review_reasons`, détection d'injections de prompt dans le texte ; une version n'est « prête » que si le traitement a abouti |
| Index lexical | `indexes.Fts5Index` | FTS5 mis à jour à chaque chunk |
| Embeddings | `embedders.OpenAICompatEmbedder` + `kbops.embed_kb` | **étape distincte** et reprenable (« Calculer les embeddings ») : modèle, version et empreinte enregistrés par base ; un changement de modèle impose un 409 explicite avant mélange de vecteurs |
| Publication | `kbops.publish_kb` | `kb_version` figée (manifeste SHA-256) ; seules les versions publiées sont lues par les agents |

## Particularités de cette construction (mesurées)
* **OCR** : modèles `fra`, `ara` (Tesseract *fast*) téléchargés en dehors des paquets système ; **`OMP_THREAD_LIMIT=1` indispensable** sur une machine chargée (≈ 3 s par page au lieu de ≈ 400 s).
* **Pages sans couche texte** repérées par l'inventaire : 64 (voir `corpus-inventory.md`) ; le nombre de pages réellement passées à l'OCR et celles à relire figurent dans `build-report.md`.
* Les PDF qui ne sont que des images de page (couverture graphique) produisent peu de texte : leur qualité est visible par document dans l'interface (*Qualité et couverture*) et dans `documents.jsonl` (`extraction`).
* L'import ne rend jamais un document « prêt » sur la seule acceptation du fichier : `extraction_status` vaut `needs_review` tant que des pages sont à relire.

## Tests
Le pipeline est couvert par `backend/tests/knowledge/` (extraction, OCR simulé, chunking, import/export, recherche, isolation) ; cas ajoutés pour cette mission : voir `build-report.md`.
