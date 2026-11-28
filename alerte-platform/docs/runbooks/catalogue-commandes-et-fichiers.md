# Catalogue des commandes et des fichiers — de l'environnement vierge à l'exercice rejoué

Ce document est la **référence unique** : toute commande ou tout fichier nécessaire aux tests y figure, dans l'ordre. Chaque commande a été relevée dans le dépôt (scripts, `--help`, README) ; la colonne *Vérifié* dit ce qui a réellement été exécuté. Le [guide de test](guide-test-complet-interface.md) renvoie ici au lieu de répéter.

Conventions : `$R` = `alerte-platform/` (racine de la plateforme) · `$B` = `$R/backend` · `$SRC` = dossier des PDF sources (`<dépôt>/alerte/data/docs`, **lecture seule**, jamais modifié) · « venv » = `source $B/.venv/bin/activate` (Windows : `$B\.venv\Scripts\Activate.ps1`).
Légende *Vérifié* : **EXÉC** exécuté lors de la préparation de ce document · **--help** option lue mais commande non lancée · **NT** non testé.

## A0. Raccourci « de zéro » (recommandé)
Le guide [demarrage-de-zero.md](demarrage-de-zero.md) enchaîne tout (installation, configuration, construction, validation, publication) pour quelqu'un qui vient de cloner. **Les commandes #10 à #17 ci-dessous sont regroupées dans UNE commande reprenable** : `python scripts/build_kb_from_pdfs.py --country CM --src <PDF>/CM [--publish]` (dossier `backend/`, venv activé). Les PDF sources ne sont **pas** dans le dépôt git : l'équipe les fournit.

## A. Commandes, dans l'ordre

| # | Objectif | Dossier | Commande exacte | Produit / modifie | Résultat attendu | Vérifié | Risque |
|---|---|---|---|---|---|---|---|
| 1 | Préparer Python, Node, `.env` | `$R` | `python3 scripts/setup.py` | `backend/.venv`, `frontend/node_modules`, `backend/.env` (jamais écrasé) | « Créé backend/.env… » | --help | écrase rien |
| 2 | Vérifier l'environnement | `$R` | `python3 scripts/doctor.py` | rien (fichier sonde temporaire dans `ALERTE_DATA_DIR`) | 0 point BLOQUANT | **EXÉC** | — |
| 3 | Connaître la machine (modèles) | `$R` | `python3 scripts/hardware_probe.py --label <nom>` | `alerte-hardware-<nom>.txt/.json` | rapport | **EXÉC** (Linux) | — |
| 4 | Configurer `.env` | `$B` | éditer `backend/.env` (modèle : `$R/.env.example`, [matrice](configuration-env.md)) | `.env` | — | — | **ne jamais commiter** |
| 5 | Démarrer backend + interface | `$R` | `python3 scripts/dev.py` (Terminal 1) | processus | `:8000` et `:5173` | **EXÉC** (services déjà actifs) | port occupé |
| 5b | (variante manuelle) backend | `$B` (venv) | `python -m uvicorn app.main:app_factory --factory --reload --port 8000` | — | « Uvicorn running » | --help | `--reload` : développement seulement |
| 5c | (variante manuelle) interface | `$R/frontend` | `. ~/.nvm/nvm.sh && nvm use && npm run dev` (Terminal 2) | — | `:5173` | NT | nvm doit être chargé |
| 6 | Santé des services | — | `curl http://localhost:8000/api/v1/health` puis `curl http://localhost:5173/api/v1/health` | — | `{"status":"ok"}` ×2 | **EXÉC** | — |
| 7 | Serveur de modèles prêt | — | `curl http://localhost:11434/v1/models` (Ollama) | — | `bge-m3` et le modèle de génération listés | **EXÉC** | nom exact du modèle |
| 8 | Mesurer le modèle (dimensionnement) | `$R` | `python3 scripts/llm_bench.py --url <URL>/v1 --model <nom exact> --calls 5` | rapport facultatif `--out` | médiane par appel | **EXÉC** (1,5 B, machine chargée) | machine au repos requise |
| 9 | (Facultatif : le pack est **déjà dans le dépôt**) Régénérer le **pack de démonstration** | `$B` (venv) | `python scripts/rising_waters_pack.py` | `demo/rising-waters/*` (scénarios, `setup-*.json`, `mandats-cm.csv`, `actions.csv`, `lacunes-attendues.PRIVE.json`, README) | « pack écrit dans … » | **EXÉC** | **remplace les fichiers du pack** ; lit `alerte/data/scenarios` (rôles, scénarios) ; AE : avertissement, `mandats-ae.csv` **périmé, ne pas importer** |
| 10 | Créer l'espace (jeton propriétaire) | `$B` (venv) | `python -m app.cli workspace create --name "ALERTE — Demonstration"` | base SQLite | jeton affiché **une seule fois** | --help | jeton perdu = irrécupérable |
| 11 | Créer les bases | `$B` | `for c in CM GL; do python -m app.cli knowledge kb-create --code $c --name $c; done` *(AE : seulement si construit, voir C)* | base, dossiers `blobs/knowledge_sources/<code>` | bases créées | --help | — |
| 12 | Copier les PDF (simulation puis réel) | `$B` | `python -m app.cli knowledge sources-migrate --map CM=$SRC/CM` puis le même avec `--apply --manifest m.jsonl` | copies dans `blobs/knowledge_sources/CM`, `m.jsonl` | « N copiés » (la source reste intacte) | --help | l'option sans `--apply` ne fait que simuler |
| 13 | Enregistrer les documents | `$B` | `python -m app.cli knowledge adopt --country CM --manifest m.jsonl` | base | 17 enregistrés, 0 refusé | --help | — |
| 14 | Appliquer titres/types/fiabilité | `$B` | `python -m app.cli knowledge curate --country CM --curation ../knowledge_bases/curation/documents.curation.json --manifest m.jsonl` | métadonnées | — | --help | modifie les métadonnées (par SHA-256) |
| 15 | **Construire** la base (OCR, découpage, embeddings, index) | `$B` | `python -m app.cli knowledge build --country CM --steps process,embed,index,check` | chunks, vecteurs, FTS | `vectorization` complète, `result: ok` | --help ; exécuté par l'utilisateur sur CM (1 351/1 351) | long sur CPU ; `ReadTimeout` → `ALERTE_EMBED_TIMEOUT_S`, `ALERTE_EMBED_BATCH_SIZE` |
| 16 | Vérifier la base | `$B` | `python -m app.cli knowledge status --country CM --documents` et `python -m app.cli knowledge check --country CM` | — | 6 contrôles OK ; vecteurs = chunks | **EXÉC** (lecture) | — |
| 17 | Publier une version | `$B` | `python -m app.cli knowledge publish --country CM --note "v1"` (ou interface : page de la base) | version active | refusée si **vecteurs incomplets** (409) | --help | — |
| 18 | Préparer l'espace jusqu'au mandat | `$B` (venv) | `python scripts/seed_rising_waters.py --token <jeton> --from 2 --until 4 --allow-missing-kbs` | pays, institutions, actions, mandats **proposés** | « [4] Mandats importés » | **EXÉC** (aide) ; une exécution réelle : NT | `--allow-missing-kbs` accepte que GL manque (signalé) ; **refuse le fichier de mandats périmé** |
| 19 | Agents + droits | `$B` | `python scripts/seed_rising_waters.py --token <jeton> --from 5 --until 5 --allow-missing-kbs [--fix-agents]` | agents, accès | « 9 agents prêts » | NT | un agent existant **différent du pack** fait échouer ; `--fix-agents` l'aligne |
| 20 | Scénario | `$B` | `python scripts/seed_rising_waters.py --token <jeton> --from 6 --until 6 --lang fr` | scénario importé | « Scénario importé » | NT | — |
| 21 | Exercice **SANS IA** (parcours A) | `$B` | `python scripts/seed_rising_waters.py --token <jeton> --from 7 --until 8` | exercice joué en mode scripted | « terminé… Aucun modèle de langage n'a été appelé » | NT | prouve la chaîne déterministe, **pas** l'IA |
| 22 | Exercice **Modèle réel** (parcours B) | `$B` | `python scripts/seed_rising_waters.py --token <jeton> --from 7 --until 8 --ai-mode ai --max-calls 450` | exercice préparé, **non lancé** | « PRÉPARÉ… Il n'est PAS lancé » | NT | préparation **bloquée** si le modèle est inaccessible ; lancer ensuite dans l'interface |
| 23 | Tests backend | `$B` (venv) | `python -m pytest -m "not model and not gpu" -q` | — | 0 échec | **EXÉC** (voir rapport d'étape) | ≈ 25 min sur une machine chargée |
| 24 | Qualité du code backend | `$B` (venv) | `python -m ruff check app tests` | — | All checks passed | **EXÉC** | — |
| 25 | Tests frontend | `$R/frontend` | `npm run typecheck ; npm run lint ; npx vitest run` | — | 0 erreur | **EXÉC** | nvm chargé |
| 26 | Tests avec un VRAI modèle | `$B` | `python -m pytest -m model tests/knowledge` | — | — | NT | exige serveurs configurés |
| 27 | Évaluer la recherche | `$B` | `python scripts/kb_eval.py --api http://localhost:8000 --token <jeton> --collections CM --label cm-lexical --out ../knowledge_bases/evaluation` | `results_<label>.json` | Recall@k, MRR | --help (le port par défaut du script est **8020**, ancien : toujours passer `--api`) | — |
| 28 | Basculer la machine de génération | `$R` | `python3 scripts/llm_target.py status` (lecture) · `init-aws` / `aws` / `local` (**écrivent `backend/.env`**, avec sauvegarde) | `.env` | — | NT | **décision du propriétaire du `.env`** |
| 29 | Vérifier le journal d'un exercice | `$B` | `python scripts/ledger_tamper_demo.py --data-dir <ALERTE_DATA_DIR> --exercise <id>` (variable `ALERTE_TOKEN` : jeton propriétaire ou auditeur) | copie temporaire | altération détectée | NT | — |
| 30 | Réinitialiser les données de démonstration | — | **nouvel espace** : `ALERTE_DATA_DIR=<dossier vide>` puis redémarrer (rien n'est supprimé de l'ancien) | — | espace neuf | NT | ne jamais supprimer `backend/data` sans accord |

## B. Commandes obsolètes — ne pas utiliser
| Commande | Pourquoi |
|---|---|
| `scripts/kb_build.py` | retiré (sort en erreur) ; équivalent : `knowledge build` |
| `scripts/legacy_to_archive.py`, `seed_demo.py`, `seed_cameroon.py`, `fix_cameroon_*.py` | produisent ou corrigent l'**ancien prototype** (codes `CM-S01…`) : la démonstration part de la **nouvelle** base |
| `--api http://localhost:8020` | ancien port ; le backend écoute sur **8000** |
| `seed_rising_waters.py --country AE` (avant la construction de la base AE) | le script s'arrête avec un message explicite tant que la base AE n'est pas **construite et publiée** (`build_kb_from_pdfs.py --country AE`) ; le registre de mandats AE existe désormais |

## C. Périmètre documentaire (à la date de rédaction)
Base **CM** : 17 documents, 1 351 passages, 1 351 vecteurs (BGE-M3), publiée (état observé le 27/11/2026). **GL, AE, ITU : non construites** dans cet espace de données (les PDF existent dans `alerte/data/docs`, mais ne sont pas ingérés). Ne pas présenter ces bases comme complètes ; les agents n'ont accès qu'à CM tant que GL n'est pas construite et publiée (hors période d'un exercice : mémoire limitée).

## D. Fichiers : importés ou générés

| Fichier | Fonction | Source | Importé / généré | Commande | Étape d'usage | Vérifier |
|---|---|---|---|---|---|---|
| `alerte/data/docs/CM/*.pdf` (17) | corpus Cameroun | prototype (lecture seule) | **source** | — | #12 | `sources-list --country CM` |
| `alerte/data/docs/{AE,GL,ITU}/*.pdf` | corpus AE (9), GL (16), ITU (2) | prototype | source, **non ingérés** | — | — | — |
| `m.jsonl` | manifeste des PDF copiés | généré | généré | #12 | #13, #14 | 17 lignes |
| `knowledge_bases/curation/documents.curation.json` | métadonnées des documents (44) | auteur | **versionné** | — | #14 | `status --documents` |
| `knowledge_bases/curation/mandates.CM.json` | 14 mandats + institutions + revue | auteur | **versionné** | — | #9 | 14 mandats |
| `knowledge_bases/curation/agent-briefs.CM.json` | consignes de comportement des 9 sièges | auteur | **versionné** | — | #9 | test `test_rising_waters_pack` |
| `knowledge_bases/evaluation/questions.jsonl` | 50 questions (25 FR, 25 EN ; 30 sur CM) | auteur | versionné | — | #27 | 50 lignes |
| `demo/rising-waters/setup-cm.json` | pays, institutions, actions, **agents** | généré | généré | #9 | #18, #19 | 9 agents |
| `demo/rising-waters/mandats-cm.csv` | 14 mandats « proposés » | généré | généré, **importé** | #9 | #18 | 14 lignes |
| `demo/rising-waters/actions.csv` | catalogue de 25 actions | généré | généré, importé | #9 | #18 | 25 lignes |
| `demo/rising-waters/cm01-rising-waters.{fr,en}.alerte-scenario.yaml` | scénario CM-01, **15 injects** ; sorties HydroSense dans `system_output` des injects 2, 8 et 14 | généré | généré, **importé** | #9 | #20 | 15 injects |
| `demo/rising-waters/ae01-…twin.en…yaml`, `setup-ae.json` | jumeau Émirats | généré | généré, **non utilisé** (AE non construit) | #9 | — | — |
| `demo/rising-waters/mandats-ae.csv` | **16 mandats AE PROPOSÉS** (`AE-L01`…`AE-L16`), tirés de `knowledge_bases/curation/mandates.AE.json` (documents AE-01, 04, 05, 09, 10, 11, 12 ; 36 citations vérifiées dans le texte des PDF ; 5 `documented`, 11 `inferred`) | généré | généré, **importé** | #9 | seed `--country AE` | à **valider par un humain** ; l'ancien fichier du prototype (`AE-S02`…) a été **remplacé** |
| `demo/rising-waters/lacunes-attendues.PRIVE.json` | lacunes visées par l'auteur | généré | **jamais importé**, ignoré par git | #9 | évaluation T3 | — |
| `backend/data/db/alerte.sqlite` | base (espace, bases, exercices, journal) | généré | généré | #10… | tous | sauvegarde : `sqlite3 … ".backup copie.sqlite"` |
| `backend/data/blobs/knowledge_sources/CM/` | PDF copiés | copie | généré | #12 | #15 | `sources-verify --country CM` |
| `backend/data/vector/` | index vectoriel (Chroma) | généré | généré | #15 | recherche | `knowledge check` |
| `backend/data/keys/…`, `anchors/` | clé de signature, ancres du journal | généré | généré (1er démarrage / exercice) | — | audit | **clé privée : ne jamais partager** |
| `backend/data-kb-build/tessdata/` | langues OCR (`ara fra eng osd`) | externe | copié, **ignoré par git** | installation Tesseract | #15 | `tesseract --list-langs --tessdata-dir …` |
| Rapports (MD/JSON/CSV/XLSX/PDF) | livrables | généré par l'interface | généré | page Rapports | analyse | **aucun rapport n'existe encore** |
| Cassettes de rejeu | rejeu d'un exercice | — | **aucune sur disque** | — | mode « cassette » | inutilisable via l'API actuelle |
| Vidéo de démonstration (≤ 7 min) | soumission | — | **absente** | — | — | — |
| `ALERTE_Technical_Report_v2.pdf` | rapport technique (5 pages) | auteur | présent, non suivi par git | — | soumission | à aligner sur les chiffres mesurés |
