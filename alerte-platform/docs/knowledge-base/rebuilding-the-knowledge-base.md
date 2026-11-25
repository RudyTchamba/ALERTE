# Reconstruire la base de connaissances

Prérequis : Python 3.11+, dépendances du backend installées (`backend/.venv`), `tesseract` et `pdftotext` (poppler) installés, les PDF dans un dossier source en lecture seule (ici `alerte/`). **Aucune donnée traitée de l'ancien projet n'est utilisée.**

## 1. Inventaire (lecture seule)
```bash
cd alerte-platform/backend
.venv/bin/python scripts/kb_inventory.py --source ../../alerte --out ../knowledge_bases/inventory
```
Produit `pdf_inventory.jsonl` et `inventory_summary.json` (SHA-256, pages, pages sans couche texte, doublons).

## 2. Modèles OCR (une fois)
Le pipeline OCR utilise Tesseract avec `ALERTE_OCR_LANGS` (défaut `ara+fra+eng`). Si `fra`/`ara` manquent, les pages concernées sont marquées « à relire ». Sans droits administrateur :
```bash
mkdir -p data-kb-build/tessdata && cp /usr/share/tesseract-ocr/5/tessdata/{eng,osd}.traineddata data-kb-build/tessdata/
curl -L -o data-kb-build/tessdata/fra.traineddata https://github.com/tesseract-ocr/tessdata_fast/raw/main/fra.traineddata
curl -L -o data-kb-build/tessdata/ara.traineddata https://github.com/tesseract-ocr/tessdata_fast/raw/main/ara.traineddata
```
**Important sur une machine chargée** : lancer le backend avec `OMP_THREAD_LIMIT=1`. Mesuré ici : une page OCR passe de ~400 s à ~3 s (sur-souscription des threads OpenMP).

## 3. Backend isolé, import, publication (mêmes endpoints que l'interface)
```bash
OMP_THREAD_LIMIT=1 ALERTE_DATA_DIR=./data-kb-build ALERTE_TESSDATA_DIR=./data-kb-build/tessdata ALERTE_OCR_LANGS=fra+eng+ara \
  .venv/bin/python -m uvicorn app.main:app_factory --factory --port 8020
.venv/bin/python -u scripts/kb_build.py --api http://localhost:8020 --create-workspace "ALERTE — Corpus PDF" --stage setup,ingest,publish
```
Le jeton propriétaire n'est affiché qu'une fois : le conserver. Relancer le script est **idempotent** (un code de document déjà présent est ignoré).

## 4. Embeddings (BGE-M3) et index
Redémarrer le backend avec le serveur d'embeddings (Ollama par défaut) :
```bash
ollama pull bge-m3
OMP_THREAD_LIMIT=1 ALERTE_EMBED_BASE_URL=http://localhost:11434/v1 ALERTE_EMBED_MODEL=bge-m3 ALERTE_EMBED_PROVIDER=openai_compat \
ALERTE_DATA_DIR=./data-kb-build ALERTE_TESSDATA_DIR=./data-kb-build/tessdata .venv/bin/python -m uvicorn app.main:app_factory --factory --port 8020
.venv/bin/python -u scripts/kb_build.py --api http://localhost:8020 --token <jeton> --stage embed --collections CM
```
**Machine lente** : ajouter `ALERTE_EMBED_BATCH_SIZE=2` (le client d'embeddings a un délai de 60 s par requête : un lot de 16 passages le dépasse sur CPU saturé et fait échouer le job). La pondération d'autorité de la recherche est neutre par défaut (`ALERTE_AUTHORITY_SPREAD=0`, voir `retrieval-evaluation.md`).

L'étape est **reprenable** : elle ne calcule que les chunks sans vecteur ; interface : page de la base → *Versions et index* → calculer les embeddings. **Coût mesuré sur la machine de développement : ~7 s par passage (CPU saturé)** ; sur GPU ou une machine libre, prévoir des ordres de grandeur inférieurs.

## 5. Évaluation puis export
```bash
.venv/bin/python scripts/kb_eval.py --api http://localhost:8020 --token <jeton> --out ../knowledge_bases/evaluation --label lexical   # ou hybrid
.venv/bin/python scripts/kb_export.py --api http://localhost:8020 --token <jeton> --out ../knowledge_bases
git check-ignore -v knowledge_bases/CM/documents.jsonl knowledge_bases/_local/CM/chunks/chunks.jsonl   # le 1er ne doit PAS être ignoré, le 2e oui
```
L'export applique la politique de droits (`publication-policy.md`).
