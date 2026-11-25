# Politique de publication (droits documentaires)

**Principe** : le dépôt GitHub montre la base de connaissances **sans publier de texte dont la redistribution n'est pas établie**. Un document accessible sur Internet n'est pas pour autant librement redistribuable.

| `redistribution_status` | Signification | Dans `knowledge_bases/<COL>/` (suivi par Git) | Dans `knowledge_bases/_local/` (ignoré par Git) |
|---|---|---|---|
| `allowed` | licence ou statut légal **établi, avec preuve** (champ `license_evidence`) | métadonnées **+ texte** des Knowledge Records et des chunks | tout |
| `restricted` | restriction constatée (ex. « usage non commercial » lu dans le PDF) | métadonnées, empreintes, identifiants ; `content: null` + `content_withheld_reason` | tout |
| `unknown` | licence non établie (**valeur par défaut**, jamais promue en `allowed`) | idem `restricted` | tout |

* **Jamais publiés** : les PDF dont les droits sont `unknown` ou `restricted` (le dépôt ne contient aucun PDF source : ils restent dans l'ancien dossier `alerte/`, en lecture seule).
* **Toujours publiés** : titre, référence, empreinte SHA-256, nombre de pages, statut d'extraction, droits et leur preuve, identifiants stables, empreintes des chunks (`text_sha256`). Cela permet de vérifier un corpus reconstruit localement sans republier le texte.
* `knowledge_bases/_local/` est dans `.gitignore` : il porte l'export complet, texte compris, pour l'usage interne et l'évaluation.
* `knowledge_bases/publication_manifest.json` liste : ressources incluses (avec texte), exclues (`restricted`) et **en attente de vérification** (`unknown`), avec la raison.

## Statuts établis dans cette construction

Voir `knowledge_bases/curation/documents.curation.json` (champs `redistribution`, `license_evidence`) :

* `allowed` : **GL-05** (47 CFR Part 10) et **GL-06** (rapport FCC) — œuvres du gouvernement fédéral des États-Unis, 17 U.S.C. § 105 (pas de droit d'auteur). Le statut repose sur l'identité de l'émetteur lue dans les PDF ; à confirmer par l'équipe avant publication si un doute existe.
* `restricted` : **GL-07** (Banque mondiale / GFDRR) — la page 2 du PDF n'autorise la reproduction que « for noncommercial purposes » avec attribution.
* `unknown` pour tout le reste, y compris les textes de l'UE (GL-01, GL-02, GL-03) : la réutilisation EUR-Lex (décision 2011/833/UE) est probable mais **n'a pas pu être vérifiée** (le site refuse l'accès automatisé depuis cet environnement). Pour les lois camerounaises et émiraties, aucune licence n'est établie dans les documents.

## Passer un document à `allowed`

1. Trouver la mention de licence / de réutilisation officielle (URL ou page du PDF).
2. La consigner dans `license_evidence` (et `license_spdx` si un identifiant SPDX existe) dans `documents.curation.json`, avec `redistribution: "allowed"`.
3. Reconstruire ou corriger les métadonnées (interface : fiche du document) puis relancer `kb_export.py`.

## Fichiers volumineux

Les PDF sources pèsent 141,7 Mo au total (GL : ~92 Mo) : aucun n'est ajouté au dépôt. Les exports JSONL sont des fichiers texte ; la taille de `chunks.jsonl` est vérifiée dans `build-report.md` (limite GitHub : 100 Mo par fichier). Git LFS n'est ni installé ni utilisé.
