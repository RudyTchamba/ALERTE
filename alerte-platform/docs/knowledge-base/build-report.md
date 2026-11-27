# Rapport de construction de la base de connaissances (2026-11-24)

> **⚠ Document partiellement OBSOLÈTE (27/11/2026).** Il décrit l'ancienne chaîne `scripts/kb_build.py` / port 8020, retirée : la construction se fait désormais par la CLI `python -m app.cli knowledge …` (voir [cli-et-pipeline.md](cli-et-pipeline.md) et le [catalogue des commandes](../runbooks/catalogue-commandes-et-fichiers.md)). Les chiffres de ce document sont ceux d'une construction passée, pas de l'état actuel.


Construction **à partir des 44 PDF originaux** de `alerte/` (lecture seule), avec le pipeline d'`alerte-platform`. Aucune donnée traitée de l'ancien projet (chunks, embeddings, index, archives, extractions, manifeste du prototype) n'a été utilisée. Les valeurs « 45 documents / 4 235 passages » de l'ancien prototype sont **remplacées** par les mesures ci-dessous.

**Verdict** : base **structurée, traçable et publiable avec la politique de droits** ; recherche **lexicale** opérationnelle ; **index vectoriel INCOMPLET** (calcul BGE-M3 en cours sur cette machine) — la base **n'est donc pas déclarée vectorisée** et la recherche hybride n'est pas démontrée.

## 1. Corpus
| Mesure | Valeur |
|---|---|
| PDF trouvés (récursif dans `alerte/`) | **44** (AE 9, CM 17, GL 16, ITU 2 ; aucun PDF ailleurs dans `alerte/`) |
| PDF importés par le pipeline | **44** (0 échec) |
| Documents uniques / doublons | 44 / **0** doublon exact (SHA-256), **0** quasi-doublon |
| Pages | **2133** (141.8 Mo) ; pages sans couche texte (pdftotext) : 64 |
| Pages passées à l'OCR par le pipeline | **91** (Tesseract fra+eng+ara, 250 DPI) |
| Pages à relire (OCR faible, page graphique) | **35** |
| Documents prêts / à relire | **28** `ready` / **16** `needs_review` |
| Knowledge Records (articles reconnus) | **1565** |
| Chunks | **3886** |

| Collection | Documents | Pages | Knowledge Records | Chunks | Vecteurs calculés | Chunks avec texte publié dans Git |
|---|---|---|---|---|---|---|
| AE | 9 | 179 | 218 | 341 | 0 / 341 | 0 |
| CM | 17 | 649 | 889 | 1342 | 152 / 1342 | 0 |
| GL | 16 | 1216 | 458 | 2110 | 0 / 2110 | 78 |
| ITU | 2 | 89 | 0 | 93 | 0 / 93 | 0 |

Domaines (un document peut en avoir plusieurs) :

| Domaine | Documents |
|---|---|
| civil_protection | 22 |
| telecommunications | 13 |
| ai_governance | 9 |
| health | 7 |
| international_commitments | 6 |
| data_protection | 4 |
| cybersecurity | 3 |
| public_services | 1 |

Documents à relire (détail dans l'interface, onglet *Qualité et couverture*) :

| Document | Pages à relire | Avertissement |
|---|---|---|
| AE-02 | 24, 25 | — |
| AE-04 | 1 | — |
| CM-01 | — | suite des articles interrompue : 8 numéro(s) absent(s) ou non reconnu(s) (7, 13, 19, 40, 52, 53, 58, 66) : rel |
| CM-08 | — | suite des articles interrompue : 1 numéro(s) absent(s) ou non reconnu(s) (29) : relire les pages concernées |
| CM-10 | 38 | — |
| CM-11 | 123 | suite des articles interrompue : 1 numéro(s) absent(s) ou non reconnu(s) (210) : relire les pages concernées |
| CM-14 | 4 | — |
| CM-18 | 30, 202 | — |
| GL-01 | — | suite des articles interrompue : 1 numéro(s) absent(s) ou non reconnu(s) (41) : relire les pages concernées |
| GL-07 | 13, 21, 35, 36, 37, 41, 60, 61, 98, 99, 104, 113, 149, 155, 161 | — |
| GL-11 | 2, 8, 104 | — |
| GL-12 | 8, 39 | — |
| GL-13 | 5, 7 | — |
| GL-15 | 2 | — |
| GL-18 | 16 | — |
| ITU-Y.3172 | 6, 32, 33 | — |

Les **titres, types, dates, langues** viennent de la lecture de la première page de chaque PDF (`knowledge_bases/curation/documents.curation.json`). **9 fichiers du dossier source avaient un nom trompeur** (liste dans `corpus-inventory.md`) ; notamment **CM-07 n'est pas le décret 98/031**.

## 2. Embeddings et index
| Élément | État |
|---|---|
| Moteur vectoriel | ChromaDB + index NumPy exact (garde-fou), via `app/knowledge/indexes.py` |
| Modèle | `bge-m3` (Ollama, dimension 1024, vecteurs normalisés), empreinte enregistrée par base |
| Vecteurs calculés | **CM : 152 / 1342** ; AE 0 / 341 ; GL 0 / 2110 ; ITU 0 / 93 (au moment de la rédaction) |
| Débit mesuré | **≈ 5 à 20 s par passage** sur cette machine (CPU, charge 8-14, processus tiers à 100 % de CPU) : le corpus complet demanderait **plusieurs heures à plus d'une journée** ici |
| Statut de l'index hybride | **INCOMPLET** ⇒ la recherche est **lexicale et étiquetée « dégradée »** (un index vectoriel incomplet n'est volontairement pas utilisé : il biaiserait le classement) |
| Reprise | le calcul est **reprenable** : `python -u scripts/kb_build.py --api … --token … --stage embed --collections CM` (ou, dans l'interface, la page de la base → *Versions et index*) ; une tâche était encore en cours pour **CM** à la fin de la session |

## 3. Évaluation (`retrieval-evaluation.md`)
50 questions, **48 évaluables** (2 non évaluables : OCR de l'article 32 de la loi 2024/017). Recherche **lexicale** : Recall@5 **0.667**, MRR 0.524 ; **même langue 1.0** (n = 24) ; **langue croisée 0.333** (n = 24). Objectif T1 (≥ 0,80) **non atteint globalement**. **Hybride : non mesuré.** *Citation validity*, *metadata completeness* (au-delà de la complétude des champs), mesure par arabe : **non exécutées**.

## 4. Droits et publication (`publication-policy.md`)
| Statut | Documents |
|---|---|
| `allowed` | **2** — GL-05 (47 CFR Part 10), GL-06 (rapport FCC) : œuvres du gouvernement fédéral des États-Unis. **Seuls documents dont le texte est publié dans Git** (78 chunks) |
| `restricted` | **1** — GL-07 (Banque mondiale, usage non commercial) |
| `unknown` | **41** — exclus de la publication du texte ; métadonnées, empreintes et identifiants publiés ; en attente de vérification (dont les textes de l'UE, réutilisation probable mais non vérifiée) |

Fiabilité : official 14, summary 5, unofficial 4, unknown 21 (la fiabilité n'est `official` que si le PDF montre une publication officielle). **Aucun PDF n'est copié dans le dépôt.** Le texte complet reste dans `knowledge_bases/_local/` (ignoré par Git). Plus gros fichier suivi : 1,4 Mo (aucun besoin de Git LFS, non installé). `git check-ignore -v` : seul `knowledge_bases/_local/` est ignoré.

## 5. Couverture documentaire (`expected_documents.jsonl`)
Registre de **51** documents attendus (tables de la spécification + textes cités par le corpus) : **34 `found`**, **11 `not_found_in_current_corpus`**, 4 `identified_but_not_downloaded`, 1 `awaiting_verification`, 1 `not_applicable`. Une absence est un **problème de couverture, pas une lacune juridique confirmée**.

* `CM-06` — Decree No. 96/054 of 12 March 1996 on the National Council for Civil Protection — **not_found_in_current_corpus** : Décret 96/054 : aucun PDF dans le dossier source ; cité par CM-12, CM-13, CM-10, CM-15.
* `CM-07` — Decree No. 98/031 of 9 March 1998 on the organisation of emergency and rescue plans — **not_found_in_current_corpus** : Le fichier CM-07 du dossier source est le rapport IDNDR, pas le décret 98/031. Un PDF du vrai décret existe dans alerte-platform/backend/scripts/corpus_fixes/ (hors corpus initial, ajouté par un coéquipier) : à valider avant import.
* `CM-13` — IFRC, Disaster Risk Management law template, Cameroon (2022) — **awaiting_verification** : Le PDF CM-13 est une cartographie IFRC des cadres juridiques de gestion des risques, pas le modèle de loi attendu ; équivalence à vérifier.
* `CM-14` — National Artificial Intelligence Strategy (SNIA), July 2025, MINPOSTEL — **not_found_in_current_corpus** : Seul un article de presse (CM-14) est présent ; la stratégie officielle SNIA n'est pas dans le corpus.
* `CM-17` — Gavi, Cholera in Cameroon: when climate disaster unleashes an epidemic — **not_found_in_current_corpus** : L'article Gavi n'est pas présent ; le PDF CM-17 est un plan d'engagement environnemental et social de la Banque mondiale.
* `AE-04` — How the UAE public alert chain works (UAE-Alert, cell broadcast, NCEMA, TDRA) — **not_found_in_current_corpus** : L'explicatif sur la chaîne d'alerte UAE-Alert n'est pas présent (le fichier AE-04 contient la Charte de l'IA).
* `AE-06` — Record rainfall of 16 April 2024 (National Centre of Meteorology figures) — **not_found_in_current_corpus** : Les chiffres du NCM ne sont pas présents ; le PDF AE-06 est un article scientifique (Natural Hazards 2025) sur la pluie du 16 avril 2024.
* `AE-07` — NCEMA national framework and standards for emergency management — **not_found_in_current_corpus** : Cadre NCEMA : à obtenir.
* `GL-07` — Japan J-Alert, National Instantaneous Warning System — **not_found_in_current_corpus** : Le PDF GL-07 est un rapport Banque mondiale/GFDRR sur les TIC pour la gestion des risques au Japon, pas la page J-Alert d'Inagi.
* `GL-08` — Mauritius modernises alerts with the Common Alerting Protocol (PreventionWeb, Sept 2025) — **not_found_in_current_corpus** : Article PreventionWeb sur l'Île Maurice : absent.
* `GL-10` — ITU, Early Warnings for All flyer (2026) — **not_found_in_current_corpus** : Flyer ITU Early Warnings for All : absent.
* `ITU-03` — ITU reference code and its 57 seed documents — **identified_but_not_downloaded** : Dépôt de code MIT (CrashingGuru/ITUAIReadiness) : consulté pour la méthode, pas ingéré comme document.
* `CM-X-037PM` — Arrêté n°037/PM du 9 mars 2003 portant création de l'Observatoire national des risques (ONR) — **identified_but_not_downloaded** : Cité par CM-10 et CM-15.
* `CM-X-2002-209` — Décret n°2002/209 portant organisation du Ministère de la Santé publique — **identified_but_not_downloaded** : Cité par CM-12 (art. 107).
* `CM-X-2005-103` — Décret n°2005/103 du 13 avril 2005 portant organisation du MINATD — **identified_but_not_downloaded** : Cité par CM-10 et CM-12.
* `CM-X-METEO` — Texte d'organisation de la direction de la météorologie nationale — **not_found_in_current_corpus** : Aucun texte établissant les missions météo dans le corpus.

## 6. Graphe de mandats (`knowledge_bases/CM/graph/`)
14 mandats, 11 institutions, relations *holds_* / *grounded_in* / *context_from* ; chaque source est résolue vers un chunk du corpus reconstruit. Statuts : documented 3, inferred 7, assumed 4 ; **aucun mandat n'est validé** et **aucun registre n'est déclaré complet**. Les actions et types de mandats proviennent du registre du prototype (donnée traitée ancienne, déjà dans le dépôt : `demo/rising-waters/`), les **sources et statuts** viennent de la lecture des PDF (`docs/audits/sources-des-mandats-cameroun.md`).

## 7. Défauts du pipeline trouvés et corrigés pendant la construction (tous testés)
1. **Perte de texte au découpage** (texte entre un titre de section et l'article suivant supprimé) + garde « texte non couvert ».
2. **Suite d'articles interrompue** (OCR « 53 » → « §3 ») détectée ⇒ document `needs_review`.
3. **Pages scan avec cachet** (petite couche texte) traitées comme texte ⇒ OCR.
4. **Articles « (n) »** des décrets émiratis non reconnus ⇒ Knowledge Records AE 2 → 218.
5. **Pondération d'autorité** qui enterrait les documents « unofficial » ⇒ neutre par défaut.
6. **Index vectoriel incomplet** biaisant le classement ⇒ ignoré et signalé.
7. **Vocabulaire de fiabilité** : `unknown` ajouté (la spécification de la mission le demande ; le modèle V1 n'avait que `not_found`).
8. **OCR 100× plus lent** sur machine chargée (threads OpenMP) ⇒ `OMP_THREAD_LIMIT=1` documenté.

## 8. Ce qui n'est pas fait
* **Embeddings complets et mesure hybride/multilingue** (voir §2–3).
* **Interface graphique** : le parcours cliqué d'import/relecture/publication n'a **pas été rejoué** ; les 24 fonctions listées dans la mission ne sont pas toutes vérifiées dans l'interface (la page *Bases de connaissances* existante couvre l'import de PDF, la qualité, les versions, l'export/import, la recherche, les embeddings ; la **liste des documents attendus** et le **graphe de mandats** ne sont **pas** affichés dans l'interface).
* **Knowledge Records** : uniquement des articles reconnus ; pas d'extraction automatique d'obligations ni de pouvoirs. **Identifiants stables** : dérivés à l'export (non stockés en base).
* **Arabe** : aucun document arabe ; OCR arabe non exercé.
* **Tableaux / notes de bas de page** : non vérifiés document par document.
* **Agents** : `search_kb`, permissions et audit existants (tests : 549 réussis) ; **aucun exercice agent n'a été rejoué sur la nouvelle base** dans cette session.
* **Droits** : 41 documents `unknown` à qualifier ; EUR-Lex n'a pas pu être consulté depuis cet environnement.
* Le script de démonstration rapide (`seed_rising_waters.py`) importe encore l'**ancienne archive** (voie dépréciée).

## 9. Reproduire
```bash
cd alerte-platform/backend
.venv/bin/python scripts/kb_inventory.py --source ../../alerte --out ../knowledge_bases/inventory
OMP_THREAD_LIMIT=1 ALERTE_DATA_DIR=./data-kb-build ALERTE_TESSDATA_DIR=./data-kb-build/tessdata ALERTE_OCR_LANGS=fra+eng+ara .venv/bin/python -m uvicorn app.main:app_factory --factory --port 8020
.venv/bin/python -u scripts/kb_build.py --api http://localhost:8020 --create-workspace "ALERTE — Corpus PDF" --stage setup,ingest,publish   # ≈ 25 min
# redémarrer avec ALERTE_EMBED_BASE_URL/ALERTE_EMBED_MODEL puis :
.venv/bin/python -u scripts/kb_build.py --api http://localhost:8020 --token <jeton> --stage embed --collections CM,AE,GL,ITU
.venv/bin/python scripts/kb_eval.py --api http://localhost:8020 --token <jeton> --out ../knowledge_bases/evaluation --label hybrid
.venv/bin/python scripts/kb_export.py --api http://localhost:8020 --token <jeton> --out ../knowledge_bases
```
Détail : `rebuilding-the-knowledge-base.md`. Tests : backend **549 réussis, 2 ignorés** ; frontend **88 réussis** ; ruff/oxlint propres.
