# knowledge_bases — données de curation et d'évaluation des bases de connaissances d'ALERTE

> **Ce dossier n'est PAS la base construite.** Après un `git clone` il ne contient ni passages, ni vecteurs, ni index : la base se construit sur votre machine à partir des PDF (fournis à part) avec [`demarrage-de-zero.md`](../docs/runbooks/demarrage-de-zero.md). Elle vit ensuite dans `backend/data/` (ignoré par git).

Ce dossier contient les **données d'auteur versionnées** qui accompagnent la construction des bases. Les bases elles-mêmes (documents traités, passages, vecteurs, index) ne sont **pas** ici : elles sont reconstruites à partir des PDF par la CLI (`python -m app.cli knowledge …`) et vivent dans le dossier de données (`ALERTE_DATA_DIR`, ignoré par git). Procédure : [catalogue des commandes](../docs/runbooks/catalogue-commandes-et-fichiers.md) et [docs/knowledge-base/cli-et-pipeline.md](../docs/knowledge-base/cli-et-pipeline.md).

## Contenu réellement présent (vérifié le 27/11/2026)
| Fichier | Rôle | Utilisé par |
|---|---|---|
| `curation/documents.curation.json` | titre, type, fiabilité, droits de chacun des 44 documents sources | `knowledge curate` |
| `curation/expected_documents.jsonl` | documents attendus (mesure de couverture) | contrôle de couverture |
| `curation/mandates.CM.json` | 14 mandats du Cameroun, institutions et sources (documents `CM-xx`) | `rising_waters_pack.py` → `mandats-cm.csv` |
| `curation/agent-briefs.CM.json` | consignes de comportement (objectif, contacts, limites, conduite) des 9 sièges du scénario Rising Waters | `rising_waters_pack.py` → `setup-cm.json` |
| `evaluation/questions.jsonl` | **50** questions de référence (25 FR, 25 EN ; 30 évaluables sur CM) | `scripts/kb_eval.py` |
| `retrieval/config.yaml` | description de la configuration de recherche — **n'est lu par aucun code** (informatif) ; les réglages effectifs sont dans `backend/app/knowledge/search.py` (`ALERTE_AUTHORITY_SPREAD`) | — |
| `schema/*.json` | schémas JSON des enregistrements de documents et de passages | documentation |

## Ce qui n'existe PAS (et qu'une version précédente de ce fichier annonçait à tort)
`inventory/`, `<COL>/` (`CM`, `AE`, `GL`, `ITU`), `results_*.json`, `publication_manifest.json` : **absents**. Ils seraient produits par `scripts/kb_inventory.py`, `kb_export.py` et `kb_eval.py` (anciens outils : leur port par défaut est **8020**, le backend écoute sur **8000** : passer `--api`). `knowledge_bases/_local/` (export complet avec texte, droits non confirmés) est **ignoré par git**.

## État des bases (espace de données de développement, 27/11/2026)
| Base | Documents | Passages | Vecteurs | Publiée |
|---|---|---|---|---|
| **CM** | 17 | 1 351 | 1 351 (BGE-M3, dim. 1024) | oui (version 1) |
| GL, AE, ITU | PDF présents dans `alerte/data/docs`, **non ingérés** | — | — | non |

Points de qualité connus : 6 documents « à relire » (OCR), **CM-07 porte un titre faux** (« Rapport IDNDR » alors que le fichier est le décret 98/031 ; voir `curation/`), recherche **lexicale** mesurée à Recall@5 = 0,60 sur 30 questions CM (français 15/15, anglais 3/15) ; **la recherche hybride (BGE-M3) n'a pas encore été mesurée**.

## Droits
Le texte d'un document n'est publié que si sa redistribution est `allowed` avec preuve ; sinon seuls métadonnées, empreintes et identifiants. Voir `docs/knowledge-base/publication-policy.md`.
