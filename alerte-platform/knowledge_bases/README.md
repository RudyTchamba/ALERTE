# knowledge_bases — bases de connaissances d'ALERTE, construites à partir des PDF originaux

Contenu **reconstruit** par le pipeline d'`alerte-platform` (extraction, OCR, découpage, embeddings) à partir des PDF du dossier source `alerte/` (lecture seule). Aucune donnée traitée de l'ancien prototype n'est reprise.

| Dossier / fichier | Rôle |
|---|---|
| `inventory/` | inventaire exhaustif des PDF (SHA-256, pages, pages sans texte, doublons) |
| `curation/` | métadonnées lues dans les PDF (`documents.curation.json`), documents attendus (`expected_documents.jsonl`), mandats du Cameroun avec leurs sources (`mandates.CM.json`) |
| `schema/` | schémas JSON des Document Records, Knowledge Records et chunks |
| `<COL>/` (`CM`, `AE`, `GL`, `ITU`) | `manifest.json`, `documents.jsonl`, `expected_documents.jsonl`, `records/`, `chunks/`, `graph/` (CM) |
| `retrieval/config.yaml` | configuration de recherche effective |
| `evaluation/` | questions (`questions.jsonl`) et résultats mesurés (`results_*.json`) |
| `publication_manifest.json` | documents inclus / exclus / en attente de vérification des droits |
| `_local/` | **ignoré par Git** : export complet avec texte (droits non confirmés) |

**Droits** : le texte d'un document n'est publié ici que si sa redistribution est `allowed` avec preuve ; sinon seuls les métadonnées, empreintes et identifiants sont publiés (`content: null`). Voir `docs/knowledge-base/publication-policy.md`. Reconstruction : `docs/knowledge-base/rebuilding-the-knowledge-base.md`. Résultats chiffrés : `docs/knowledge-base/build-report.md`.
