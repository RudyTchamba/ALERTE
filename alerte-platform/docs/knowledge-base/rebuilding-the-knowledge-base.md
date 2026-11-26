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

## 3. Migration, import et construction par base (CLI — mêmes services que l'API et l'interface)
Les PDF sont **copiés** (jamais déplacés) dans `<ALERTE_DATA_DIR>/blobs/knowledge_sources/` (`CM/`, `AE/`, `GL/`, `organizations/ITU/`), puis enregistrés et construits **une base à la fois**. `scripts/kb_build.py` est retiré. Séquence complète et exemple réel : [cli-et-pipeline.md](cli-et-pipeline.md) §4.
```bash
export OMP_THREAD_LIMIT=1 ALERTE_DATA_DIR=./data-kb-build ALERTE_TESSDATA_DIR=./data-kb-build/tessdata ALERTE_OCR_LANGS=fra+eng+ara
.venv/bin/python -m app.cli workspace create --name "ALERTE — Corpus PDF"
.venv/bin/python -m app.cli knowledge kb-create --code CM --name Cameroun
.venv/bin/python -m app.cli knowledge sources-migrate --map CM=<dossier source>/CM --apply --manifest m.jsonl
.venv/bin/python -m app.cli knowledge adopt --country CM --manifest m.jsonl
.venv/bin/python -m app.cli knowledge build --country CM --steps process,index
```
Le jeton propriétaire n'est affiché qu'une fois. Relancer est **idempotent** : un fichier déjà enregistré ou un contenu déjà présent (SHA-256) n'est pas dupliqué.

## 4. Embeddings (BGE-M3) et index
La CLI lit la même configuration que le serveur (Ollama par défaut) :
```bash
ollama pull bge-m3
OMP_THREAD_LIMIT=1 ALERTE_EMBED_BASE_URL=http://localhost:11434/v1 ALERTE_EMBED_MODEL=bge-m3 ALERTE_EMBED_PROVIDER=openai_compat \
ALERTE_DATA_DIR=./data-kb-build .venv/bin/python -m app.cli knowledge embed --country CM
```
**Machine lente** : ajouter `ALERTE_EMBED_BATCH_SIZE=2` (le client d'embeddings a un délai de 60 s par requête : un lot de 16 passages le dépasse sur CPU saturé et fait échouer le job). Si des `ReadTimeout` persistent (extraits longs, CPU seul), ajouter `ALERTE_EMBED_TIMEOUT_S=300` : relancer ensuite la même commande de construction ne recalcule que les vecteurs manquants. La pondération d'autorité de la recherche est neutre par défaut (`ALERTE_AUTHORITY_SPREAD=0`, voir `retrieval-evaluation.md`).

L'étape est **reprenable** : elle ne calcule que les chunks sans vecteur ; interface : page de la base → *Versions et index* → calculer les embeddings. **Coût mesuré sur la machine de développement : ~7 s par passage (CPU saturé)** ; sur GPU ou une machine libre, prévoir des ordres de grandeur inférieurs.

## 5. Évaluation puis export
```bash
.venv/bin/python scripts/kb_eval.py --api http://localhost:8020 --token <jeton> --out ../knowledge_bases/evaluation --label lexical   # ou hybrid
.venv/bin/python scripts/kb_export.py --api http://localhost:8020 --token <jeton> --out ../knowledge_bases
git check-ignore -v knowledge_bases/CM/documents.jsonl knowledge_bases/_local/CM/chunks/chunks.jsonl   # le 1er ne doit PAS être ignoré, le 2e oui
```
L'export applique la politique de droits (`publication-policy.md`).
