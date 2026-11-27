# Architecture de la base de connaissances

> **⚠ Document partiellement OBSOLÈTE (27/11/2026).** Il décrit l'ancienne chaîne `scripts/kb_build.py` / port 8020, retirée : la construction se fait désormais par la CLI `python -m app.cli knowledge …` (voir [cli-et-pipeline.md](cli-et-pipeline.md) et le [catalogue des commandes](../runbooks/catalogue-commandes-et-fichiers.md)). Les chiffres de ce document sont ceux d'une construction passée, pas de l'état actuel.


Cette page décrit ce qui est **réellement implémenté** (architecture V1, aucune décision V2 réintroduite). Elle complète `docs/architecture/07-knowledge-and-rag.md`.

```
PDF originaux (alerte/, lecture seule)
   │  kb_inventory.py  → inventaire : SHA-256, pages, pages sans texte, doublons
   ▼
Registre de curation (documents.curation.json : lecture de la 1re page, droits avec preuve)
   │  kb_build.py = client HTTP des MÊMES endpoints que l'interface (POST /knowledge-bases/{id}/documents …)
   ▼
Pipeline backend `app/knowledge` (job kb_ingest)
   extract.py   pdfplumber + OCR Tesseract des pages pauvres → pages (méthode, confiance, « à relire »)
   chunking.py  découpage par structure (articles, sections), fenêtres + recouvrement
   ingest.py    tables SQLite : document, document_version, chunk (+ FTS5)
   embedders.py BGE-M3 via serveur compatible OpenAI (Ollama) → vecteurs normalisés
   indexes.py   FTS5 (lexical) · NumPy exact · ChromaDB (vectoriel) ; recherche hybride RRF (search.py)
   ▼
Publication de version (kb_version) → agents (search_kb, permissions agent × base) → audit
   ▼
kb_export.py → knowledge_bases/ (Git) : documents.jsonl · knowledge_records.jsonl · chunks.jsonl · manifest · expected_documents
                               ↘ _local/ (ignoré par Git) : texte complet, usage interne
```

## Couches de données

| Couche | Où elle vit | Remarque |
|---|---|---|
| Document source (PDF) | blob adressé par SHA-256 (`data/blobs`), original intact dans `alerte/` | jamais publié si droits non établis |
| **Document Record** | table `document` (+ `document_version`) ; export `documents.jsonl` | métadonnées, provenance, validité, droits, extraction |
| **Knowledge Record** | **dérivé à l'export** (article reconnu = un record) ; schéma `schema/knowledge_record.schema.json` | **choix V1** : pas de nouvelle table ; le record référence ses chunks (`chunk_ids`) |
| **Chunk** | table `chunk` + FTS5 + index vectoriel | porte document, pages, article, section, langue, qualité |
| Mandats / relations | modules `mandates` (registre, sources) ; `graph/` à venir | voir `docs/audits/sources-des-mandats-cameroun.md` |

## Identifiants stables
Les ULID de la base (`app_chunk_id`) sont propres à une instance. Les identifiants **publiés** sont dérivés du contenu : `doc_` + SHA-256(PDF, code) ; `ck_` + SHA-256(PDF, ordinal, empreinte du texte) ; `kr_` + SHA-256(PDF, article, empreintes des chunks). Un même PDF retraité avec les mêmes paramètres redonne les mêmes identifiants ; une nouvelle version du PDF (autre SHA-256) en donne d'autres.

## Relation avec les dépôts de référence ITU
* `CrashingGuru/ITUAIReadiness` (licence MIT) : jeu de simulation (FastAPI + ChromaDB + Ollama, embeddings `nomic-embed-text`, découpage par fenêtres de 256 mots, parsing docling/PyMuPDF). C'est le « code de référence pour la création de KB » cité par le hackathon. **Aucun de ses fichiers n'a été copié** ; ALERTE reprend l'idée (ChromaDB + Ollama + extraction → chunks → vecteurs) avec un pipeline plus riche (articles, OCR par page, FTS5, RRF, droits).
* `CrashingGuru/Sandbox_Training` (MIT) : catalogue de notebooks/jeux de données de la formation Sandbox. Il ne contient **pas** de code de construction de KB ; son schéma de métadonnées (`schema/metadata.schema.json` : `source_type` hosted/external, licence obligatoire, empreintes) a inspiré la distinction « inclus / exclu / en attente » du manifeste de publication.
Les deux dépôts ne sont donc pas interchangeables : le premier montre une méthode de construction, le second une organisation de catalogue. PyMuPDF (AGPL) n'est pas utilisé.

## Ce qui n'est pas fait
* Le graphe de mandats exporté (`graph/`) n'est pas généré : le registre vit dans l'application (module `mandates`) ; voir `build-report.md`.
* Les Knowledge Records sont limités aux **articles reconnus** ; les documents sans structure d'articles (rapports, plans) n'ont que des chunks.
