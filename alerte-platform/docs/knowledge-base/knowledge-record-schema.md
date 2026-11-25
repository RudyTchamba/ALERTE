# Schémas : Document Record, Knowledge Record, Chunk

Schémas JSON (draft-07) dans `knowledge_bases/schema/` : `document.schema.json`, `knowledge_record.schema.json`, `chunk.schema.json`.

* **Document Record** = une ligne de `documents.jsonl` : identité du PDF (`sha256`, taille, pages), métadonnées (titre lu dans le PDF, type, numéro, date, langue, juridiction, domaines, institutions), qualification (`reliability`, `validity`), droits (`redistribution_status`, `license_spdx`, `license_evidence`), extraction (méthode, qualité, pages à relire, nombre de chunks) et `curation_notes`. Les champs non établis valent `null` ou `unknown` : **rien n'est fabriqué**.
* **Knowledge Record** = une disposition structurée. Implémentation actuelle : `record_type = "article"` pour chaque article reconnu par le pipeline ; `content` = texte de l'article (concaténation de ses chunks), `chunk_ids` pointe vers les chunks, `source_hash` fige le contenu, `review_status` vaut `needs_review` si le document a des pages à relire. Les types d'enregistrement `obligation`, `power`, `procedure`… sont prévus par le vocabulaire de la mission mais **ne sont pas extraits automatiquement** : ils relèvent du registre de mandats (`documented / inferred / assumed`), alimenté par un humain avec une source.
* **Chunk** = fragment destiné à la recherche : même provenance que le document, pages, article, section, langue, `evidence_tag`, `text_sha256`, `char_count`.

## Identifiants stables
`doc_<16>` = SHA-256(`sha256_du_pdf|code`)[:16] · `ck_<20>` = SHA-256(`sha256_du_pdf|ordinal|text_sha256`)[:20] · `kr_<20>` = SHA-256(`sha256_du_pdf|article|text_sha256…`)[:20]. L'ULID interne (`app_chunk_id`) est conservé pour le rapprochement avec une instance, mais n'est **pas** stable.

## Texte et droits
`content` / `text` valent `null` (avec `content_withheld_reason`) dans les fichiers suivis par Git quand `redistribution_status != "allowed"` ; le texte complet est dans `knowledge_bases/_local/` (ignoré). Voir `publication-policy.md`.
