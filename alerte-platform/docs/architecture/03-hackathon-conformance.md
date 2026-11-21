# 03 — Matrice de conformité avec le hackathon

> Sources officielles lues le 2026-11-20 (sous-agent, annexe [A7](appendix/A7-research-hackathon-and-methods.md)) : [page événement](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/) et [page des propositions](https://aiforgood.itu.int/ai-for-good-sandbox-project-proposals-united-arab-emirates/). Les citations en anglais sont verbatim ; la vérification a été faite par un sous-agent Haiku — **l'équipe doit relire les deux pages avant la finale** (les dates de finale diffèrent : 8 déc. sur la page événement, 9 déc. sur la fiche).

## 3.1 Faits officiels qui orientent l'architecture

| Fait | Conséquence |
|---|---|
| « Accuracy of the AI Prototype does not fall under any evaluation criteria » (FAQ) | On ne vend pas la performance du modèle ; on vend **la méthode, la traçabilité et la qualité des lacunes** |
| « the relevance of the gaps and accuracy of the global policy examples would be a critical part of the evaluation » | Précédents sourcés et vérifiables (I4) ; pas de nombre minimal artificiel |
| « Rather than analysing specific geographies or country specific recommendations, participants should focus on domain specific policy gaps » | Chaque lacune porte un **domaine** et des références internationales ; le rapport sépare « constat national » et « bonne pratique mondiale » |
| « audit logging and chain-of-thought tracing » / « chain-of-thought traces » | Trace de décision (actions, sources, scores, sortie brute validée) + `rationale` public court ; explication : plus fiable qu'un CoT |
| « sequenced, chunked events released progressively (not all at once) » | Libération progressive des événements (inject engine) |
| Base « vectorized, distributed knowledge base hosted in the ITU AI for Good Lab » | KB exportable ; embeddings inclus dans l'archive ; possibilité de ré-héberger sur le Sandbox |
| Livrables : rapport technique 5 pages, dépôt GitHub, base de connaissances, **vidéo ≤ 7 min obligatoire si retenu** | Kit de démo reproductible (doc 13) ; vidéo hors code |
| Sandbox : « cloud credits … to fine-tune AI models » ; GPU, montant, durée **non précisés** | Aucun choix d'architecture ne suppose un GPU Sandbox |

## 3.2 Matrice critères → fonctionnalités (C = critère d'évaluation ; E = exigence/livrable)

| # | Critère / exigence officielle | Fonctionnalité ALERTE | Module (doc) | Preuve (test / artefact) | Prio |
|---|---|---|---|---|---|
| **C1** | **Knowledge base quality** : « completeness, accuracy, and structure of ingested national material » | Ingestion avec contrôle qualité (qualité d'extraction, pages à relire, doublons) ; métadonnées complètes ; versions ; export vérifié ; couverture documentaire visible | knowledge (07) | Rapport de qualité de KB ; T1 (P1) ; aller-retour d'archive | P0 |
| **C2** | **Agent capability** : « relevance and accuracy of agent responses during simulated error scenarios » | Agents mandat-bornés avec outils ; pannes injectées (IA sur-confiante, institution muette, désinformation, LLM indisponible) ; citations vérifiées | agents, scenarios (08) | Tests de discipline de rôle ; T2 ; cassette de démonstration | P0 |
| **C3** | **Gap identification** : « unclear responsibilities, standards, technology and legislative gaps, coordination problems, conflicts between objectives » | Module Gap Analysis (G1–G10 + catégories) avec preuves, domaines, précédents mondiaux, revue humaine | gaps (09) | T3, T4 ; test contrefactuel | P0 (G1, G2, G3, G8 + signaux) · P1 (G4–G7, G9, G10 ; T3/T4) |
| **C4** | **Auditability** : « transparency of agent reasoning through logs, chain-of-thought traces, and source attribution » | Ledger SHA-256 ; trace de décision ; rationale public ; rejeu ; vérification | audit (10) | Tests modification/troncature ; page Audit | P0 |
| **C5** | **Alignment with ITU standards** : Y.3172 + AI Readiness « in the solution architecture » | Table de correspondance Y.3172 → modules ; scorecard 13 dimensions ; vocabulaire ITU dans l'UI | 05, 10 | §3.3 ; scorecard | P0 (mapping) · P1 (scorecard) |
| E1 | « mapped to and adhere to the published and open documents provided by the country » | Registre de licences/provenance par document ; rapport de couverture ; citations obligatoires | knowledge | Inventaire | P0 |
| E2 | Base vectorisée et distribuée | **Embeddings réels** (BGE-M3 par défaut, port `Embedder`) + index vectoriel ; embeddings inclus dans l'archive avec leur empreinte | knowledge | Archive avec `embeddings/` ; test de propriété de portée | **P0** |
| E3 | Agents « assum[ing] the role of a specific government actor » | Agent = institution + mandat + sources | agents | Fiche de rôle | P0 |
| E4 | « Inter-agent coordination protocols should orchestrate the interaction » | Tableau 5 types, 2 tours, coordinateur déterministe | simulation | Tests de tours | P0 |
| E5 | Événements séquencés/progressifs | Inject engine, pas à pas, surprise | scenarios/simulation | Test d'ordonnancement | P0 |
| E6 | Lacunes par domaine ; exemples mondiaux | Champ `domain` ; références internationales rattachées | gaps | Rapport | P0 |
| E7 | Rapport technique 5 pages | Hors plateforme (document de l'équipe) ; **le rapport v2 existant contredit le code sur 12 points (A3 §1.2) : à mettre à jour avec la nouvelle plateforme** | — | — | équipe |
| E8 | Dépôt GitHub | `alerte-platform/` ; README ; licence à décider | — | — | P0 |
| E9 | Base de connaissances publiée | Export « ouvert » (sans documents restreints) | knowledge | Archive | P0 |
| E10 | Vidéo démo 7 min | Kit de démo : rejeu scripté/cassette + mini-run live | 13 | Script de démo | équipe |
| E11 | « Contribution to regional perspective » ; « open local dataset » | KB + registre de mandats exportables, réutilisables par d'autres pays | knowledge/mandates | Archive + CSV | P1 |

## 3.3 Correspondance ITU-T Y.3172 (**vérifiée dans le texte de la Recommandation** — [A10](appendix/A10-itu-pdfs-findings.md))

Y.3172 (06/2019, « In force ») : les nœuds **SRC, C, PP, M, P, D, SINK, MLFO et ML sandbox sont définis** (clauses 3.2.2, 3.2.6, 8.1) ; « ML intent » est décrit en NOTE 12 (8.1) mais **n'est pas défini en clause 3** ; Y.3172 n'exige **aucun audit, aucune traçabilité, aucune provenance ni intervention humaine** (clause 9 : empêcher l'accès non autorisé et les fuites). Les concepts « knowledge record », vectorisation, agents et AI Lab n'y figurent pas (ils viennent du rapport AI Readiness).

| Élément Y.3172 | Clause | Rôle dans ALERTE | Composant |
|---|---|---|---|
| ML intent | NOTE 12 sous 8.1 | Configuration déclarative de l'exercice | Exercise Studio, `exercise_snapshot` |
| SRC (source) | 8.1 | Documents et événements du scénario | `knowledge`, `scenarios` |
| C (collector) | 8.1 | Ingestion pilotée ; libération des injects | `knowledge.ingest`, runner |
| PP (preprocessor) | 8.1 | Extraction, OCR, chunking, analyseur, embeddings | `knowledge.ingest` |
| M (model) | 8.1 | Agents et système IA testé | `agents` |
| P (policy) | 8.1 (NOTE 5) | Permissions, contrôle de citation, règles de lacune, garde-fous | `SearchScope`, `agents.citations`, `gaps.rules` |
| D (distributor) | 8.1 (absent de la chaîne de 8.3) | Tableau et routeur de boîtes | `simulation.board` |
| SINK | 8.1 | Interface, rapports, ledger | frontend, `reports`, `audit` |
| MLFO | 3.2.2, 8.1 | Orchestrateur d'exercice | runner de job `sim` |
| ML sandbox | 3.2.6, 8.1 | Exécution isolée et reproductible | snapshot + mode d'exécution étiqueté |

## 3.4 AI Readiness (13 dimensions) — état de vérification (levé le 2026-11-21)

Le rapport ITU v2.0 a été lu **intégralement** ([A10](appendix/A10-itu-pdfs-findings.md)) : les **13 libellés de dimensions** utilisés par le projet correspondent à ceux du rapport (écarts de casse/orthographe). Points d'attention : le rapport emploie aussi 5 « piliers » et 6 « facteurs » dont les libellés varient selon les sections ; il **ne définit ni échelle de maturité ni formule de score** (REQ-004, REQ-021 seulement) : la grille du scorecard est **conçue par l'équipe** ; il contient des **exigences contradictoires** sur local/distribué et **ne définit pas le format de knowledge record** — voir §3.6.

## 3.5 Ce qui sera démontré en direct (ordre du jury)

| Critère | Séquence de démonstration |
|---|---|
| C1 | Ouvrir la KB → document → chunks → métadonnées/licence → exporter → réimporter → vérifier les hashs |
| C2 | Lancer l'exercice → panne injectée → agent qui cite, agent qui répond « aucune base juridique trouvée », agent « pas notre rôle » |
| C3 | Ouvrir une lacune → chaîne de preuves → précédents → *contrefactuel* (ajout/retrait d'un texte) |
| C4 | Ouvrir une décision → trace (sources + scores + sortie brute + validations) → « Vérifier le journal » → modifier une ligne en base → « entrée n°… altérée » |
| C5 | Page « Architecture » : Y.3172 → modules ; scorecard 13 dimensions |

## 3.6 Étude du dépôt de référence ITU (`CrashingGuru/ITUAIReadiness`) — lue le 2026-11-21

Étude détaillée : [A9](appendix/A9-itu-reference-code-study.md) (dépôt cloné et lu, **aucun code exécuté**) ; PDF ITU lus intégralement : [A10](appendix/A10-itu-pdfs-findings.md).

**1. Ce que le code réalise réellement.** La page du hackathon le cite comme « Reference code for KB creation », mais c'est un **dépôt non officiel de l'ITU** (un contributeur, licence **MIT**). Deux pipelines : `simulation/` (FastAPI + **ChromaDB** + **Ollama** `qwen2.5:14b` / `nomic-embed-text`, jeu d'**évaluation de maturité IA** des pays ; 7 « agents » = appels LLM isolés) et un notebook Colab de RAG générique (FAISS). Ingestion : PyMuPDF (AGPL) en pratique, chunks de 256 mots, IDs `uuid4`, métadonnées plates (pays déduit du nom de fichier). **Défauts confirmés** : filtre `dimension_id` sur une collection qui n'a pas cette métadonnée (retrieval silencieusement vide), double indexation, `kb_decisions` jamais relue, audit non appliqué aux mutations de KB, aucun test. **Absent** : permissions, simulation de crise, multi-agents réels, isolation par pays, versionnement.

**2. Réutilisable / à adapter / à développer séparément.**

| Catégorie | Éléments |
|---|---|
| **Réutilisable** (après contrôle) | `data/framework/dimensions.json` (13 dimensions, 6 facteurs : libellés alignés avec le rapport ITU) ; **ChromaDB comme moteur vectoriel** (même technologie : interopérabilité directe) ; modèle de texte des nœuds Y.3172 (vocabulaire) |
| **À adapter** | Ingestion (remplacer PyMuPDF, chunking par article, métadonnées complètes, **IDs déterministes** pour l'idempotence) ; accès KB (permissions systématiques) ; squelette RAG + prompt JSON (validation Pydantic) |
| **À développer séparément** | Permissions et rôles, simulation multi-agents de crise, audit immuable, versionnement des documents, export/import, évaluation, interface React |

**3. Intégration au pipeline documentaire.** Adaptateur JSONL de **records** (un par chunk : `id` déterministe, `text`, métadonnées `source_file`, `source_type`, `country`, `chunk_index`, `total_chunks`, `ingested_at`, `document_category` + nos champs titre/page/article/licence/version) ; **import** qui recalcule les embeddings si le modèle diffère ; **export** vers une collection Chroma compatible. Test automatisé d'aller-retour (export → format Chroma du dépôt → leur retrieval non modifié → réimport).

**4. Attribution et licence.** Conserver la licence MIT et le copyright (« Vishnu Ram OV ») pour tout code ou donnée réutilisé ; citer le dépôt et le rapport « AI Ready — Report 2.0 » (source de `dimensions.json`) ; **ne pas redistribuer** leurs ~65 PDF (aucune licence) ; ne pas utiliser leurs `sample_national_strategy_*.txt` (synthétiques) ; PyMuPDF **non utilisé** (AGPL).

**5. Matrice des exigences des organisateurs → composants réellement utilisés** (R = code réutilisé · I = interopérable, testé · S = inspiré · — = non couvert par le dépôt) :

| Exigence | Composant ALERTE | Statut |
|---|---|---|
| KB alignée sur les documents ouverts du pays | `knowledge` (provenance, validité, licence, couverture) | — (conçu en propre) |
| Extraction/ingestion avec le code de référence | Pipeline `ingest` d'ALERTE | **S** (idée) — **pas R** : leur ingestion a des défauts et dépend d'AGPL |
| KB vectorisée | Index vectoriel **ChromaDB** + embeddings BGE-M3 | **I** (même moteur) |
| KB distribuée / hébergée au Lab | Export/import de records, déploiement Sandbox | **I** (profil de records) ; modalités du Lab **à confirmer** |
| Format de record uniforme (REQ-024) | Archive `alerte-kb-archive` + profil de records ITU | **S/I** (leur format n'est pas défini) |
| 13 dimensions | `dimensions.json` → scorecard | **R** (données, attribution) |
| Y.3172 | Table de correspondance §3.3 | **S** (nœuds vérifiés dans le texte) |
| Agents, coordination, audit, lacunes, crise | `agents`, `simulation`, `audit`, `gaps` | — (absent du dépôt) |

**6. Tensions du rapport AI Readiness** (REQ-015 KB hébergée au Sandbox, REQ-025 KB distribuée, REQ-026 « données non sorties du pays », REQ-007 transfert de records, FAQ 16 vs REQ-028 : [A10](appendix/A10-itu-pdfs-findings.md)). Position d'ALERTE : **aucun transfert automatique** de données nationales ; l'export et tout partage de records sont des **actes explicites de l'utilisateur**, avec contrôle des droits ; l'endpoint de chaque appel de modèle est consigné. Questions aux organisateurs : format de record attendu, statut des embeddings, capacités du Sandbox.

**7. Comment le démontrer aux évaluateurs.** Présenter cette matrice avec ses « — » ; écrire « dépôt d'exemple cité par la page du hackathon (non officiel) » ; montrer l'aller-retour de records et l'usage de ChromaDB ; montrer la typologie standards / mise en œuvre / politiques du rapport ITU dans le rapport de lacunes.
