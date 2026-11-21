# 02 — Registre des exigences et arbitrages

> Sources : `ALERTE — Project Specification.md` (« Spec », 1318 lignes), `ALERTE — The Project Explained Simply.md` (« Simple », 1060 lignes), brief de mission de l'utilisateur (« U »). Registres exhaustifs : [A1 (321 exigences SP-)](appendix/A1-spec-requirements-register.md) et [A2 (≈200 exigences SI-, 47 divergences)](appendix/A2-simple-requirements-and-divergences.md). Ce document est la **synthèse d'architecture** : exigences regroupées, affectées à un module, priorisées. Les numéros `Lxxx` renvoient aux lignes des deux fichiers sources.

## 2.1 Hiérarchie des documents (arbitrage D-01, bloquant → proposé)

Le Simple se déclare prioritaire sur le *comportement* (l.20) ; la Spec se déclare « single reference » (l.9). **Arbitrage proposé** : *le Simple fait foi pour ce que le système doit faire* (comportement, rôles, écrans, statuts, reprise, observateur) ; *la Spec fait foi pour les outils d'agent, les schémas, les règles G1–G10, les métriques T1–T6, la pile technique* ; *le brief U prime sur les deux* pour tout ce qui concerne la généricité, l'export de KB, les rapports et les lacunes. En cas de conflit non résolu ci-dessous : le plus restrictif en matière d'intégrité l'emporte.

## 2.2 Registre consolidé des exigences d'architecture

Priorités : **P0** = nécessaire au parcours de bout en bout du mercredi 25 ; **P1** = cible stabilisation avant le 28 ; **P2** = documenté, reporté. Vérification = test ou preuve qui démontre l'exigence.

### Plateforme et configuration (U §3, §8)

| ID | Exigence | Source | Module | Prio | Vérification |
|---|---|---|---|---|---|
| FR-01 | Espaces de travail isolés (documents, agents, configs non mélangés) | U§3 | workspaces | P0 | Test canari inter-espaces (aucun chunk/agent/gap d'un espace visible dans un autre) |
| FR-02 | CRUD pays, institutions, domaines ; archivage ; suppression refusée si utilisé par un exercice lancé | U§8 | workspaces | P0 | Tests API ; UI |
| FR-03 | Registre de mandats : pouvoir/devoir, action, texte source (doc+article+page+citation), tag `documented/inferred/assumed`, validation `proposed/validated/rejected` | Spec L475-493 ; Simple l.354 (accepter/corriger/rejeter chaque ligne) | mandates | P0 | Chaque mandat actif résout vers un chunk existant (test CI) |
| FR-04 | Entièrement configurable dans l'UI, sans éditer fichiers | U§3 | frontend + API | P0 | Parcours e2e § 1.4 sans fichier |
| FR-05 | Contrôle de préparation avant lancement (bibliothèque, mandats, scénario, sièges) | Simple l.297 (D-20) | scenarios/simulation | P0 | Liste de contrôles bloquants/avertissements (doc 08 §8.9) |

### Bases de connaissances (U §6, Spec L475-510, Simple l.425-426, l.631)

| ID | Exigence | Source | Module | Prio | Vérification |
|---|---|---|---|---|---|
| FR-10 | Créer/modifier/archiver une KB ; pays, domaine, langues, description | U§6.1 | knowledge | P0 | API + UI |
| FR-11 | Importer PDF, DOCX, MD, TXT, CSV ; extraction (texte, pages, articles) ; OCR pour scans | U§6.1, Spec L502 | knowledge | P0 (PDF/MD/TXT) · P1 (DOCX/CSV) | Jeu d'essai 30 pages FR/EN/AR |
| FR-12 | Métadonnées par document : titre, n°, date, pays, type, langue, lien, fiabilité (officiel/résumé/non officiel/non trouvé), validité (en vigueur/remplacé/inconnu, « remplacé par »), licence, redistribuable | Spec L475-485 ; Simple l.425, l.631 (D-07, D-29) | knowledge | P0 | Schéma + UI |
| FR-13 | Versions de documents en ajout seul ; une **version de KB** = ensemble figé de versions de documents | U§10 (snapshot) | knowledge | P0 | Un exercice lancé référence ses versions ; modifier la KB ne change pas l'exercice |
| FR-14 | Chunking sensible aux articles (FR/EN/AR), métadonnées de provenance conservées | Spec L502 | knowledge | P0 | ≥ 60 % des textes de loi avec article ; 100 % avec doc+page |
| FR-15 | Recherche **hybride réelle** : index lexical (FTS5/BM25) + **index vectoriel** (embeddings réels via le port `Embedder`) + fusion RRF ; filtres documentaires et **permissions appliqués dans la requête et revérifiés** ; BM25 seul uniquement en **mode dégradé signalé** (moteur d'embeddings injoignable) | Spec L761 ; BP-21 | knowledge | **P0** | T1 recall@5 ; test de propriété de portée |
| FR-16 | État d'indexation visible ; reconstruction d'index ; suppression de document | U§6.1 | knowledge | P0 | UI + job |
| FR-17 | **Export ZIP** réimportable : originaux, texte extrait, chunks, config, hashes, version du format, licences ; sélection de documents ; export « complet » vs « traité » | U§6.2-6.3 | knowledge | P0 | Aller-retour export→import : mêmes hashs |
| FR-18 | Import d'archive durci (zip-slip, bombes, symlinks, liste blanche) | U§6.4 ; BP-27 | knowledge | P0 | Archives piégées rejetées |
| FR-19 | Contrôle des droits avant export public : documents « restreint/inconnu » signalés et exclus par défaut | U§6.4 ; D-29 | knowledge | P0 | Export « ouvert » sans document restreint |
| FR-20 | Aucun chemin absolu ni secret dans l'archive | U§6.2 | knowledge | P0 | Test de scan de l'archive |

### Agents, outils, permissions (U §9, Spec L326-333, L360-380)

| ID | Exigence | Source | Module | Prio | Vérification |
|---|---|---|---|---|---|
| FR-20a | Définition d'agent : rôle, mission, instructions, institution, profil de modèle, outils autorisés, bases accessibles | U§9 | agents | P0 | CRUD + UI |
| FR-21 | Outils `search_kb`, `ask_legal`, `post`, `decide` : paramètres validés, autorisations contrôlées **par le backend** | Spec L326-329 ; U§9 | agents | P0 | Tests d'outil + test adversarial n°6 |
| FR-22 | Boucle d'agent contrôlée par le backend (pas max, 1 relance, repli consigné) | U§9 ; BP-33 | agents | P0 | Test « modèle qui boucle » |
| FR-23 | Permission documentaire appliquée **dans la recherche** (pré-filtrage), pas dans le prompt ; l'agent ne fournit jamais son identité | U§9 ; BP-23 | knowledge/agents | P0 | Test canari bloquant |
| FR-24 | Décision structurée : action, base juridique (doc, article, chunk, citation), confiance, options, drapeaux, justification courte | Spec L336-351 | agents | P0 | Validation Pydantic |
| FR-25 | **Contrôle de citation** déterministe ; échec → une relance ; échec répété → décision enregistrée « non vérifiée » (jamais supprimée silencieusement) | Spec L355 ; Simple l.575 (D-19) | agents | P0 | T2 ; tests unitaires |
| FR-26 | Conseiller juridique : réponse en 4 parties + phrase de précaution ; ne cite que des articles présents dans la KB ; ne donne pas d'avis final | Spec L380 ; Simple UC-11 | agents | P0 | Format validé ; citations vérifiées |
| FR-27 | Défense contre l'injection indirecte (documents importés = données) | U§9 ; BP-29 | knowledge/agents | P0 | Tests adversariaux 1–2 |
| FR-28 | Champ `rationale` public, court, contraint ; trace de décision par activation | Critère officiel « chain-of-thought traces » | agents/audit | P0 | UI trace ; test de schéma |

### Moteur et simulation (U §10, Spec L359-370, Simple l.358, l.431, l.439, l.680)

| ID | Exigence | Source | Module | Prio | Vérification |
|---|---|---|---|---|---|
| FR-30 | Événements libérés progressivement ; destinataires ; inégalité d'information | Hackathon ; Spec L215 | scenarios/simulation | P0 | Test d'ordonnancement |
| FR-31 | Boîtes de réception privées ; tableau de coordination avec 5 types (INFO, REQUEST, DECISION, OBJECTION, GAP_FLAG) + réponse accepter/refuser/« pas notre rôle » ; **2 tours maximum** par inject | Spec L359-369 ; Simple l.312 (D-31) | simulation | P0 | Test de tours |
| FR-32 | Coordinateur **déterministe en code** (clôt les tours, route les demandes, lève des signaux) | Spec L370-378 ; U§10 | simulation | P0 | Tests de règles |
| FR-33 | Machine à états : brouillon, prêt, en cours, en pause, interrompu, terminé, arrêté, archivé | Simple l.680 (D-12/D-13) | simulation | P0 | Test paramétré de transitions |
| FR-34 | Pause, reprise, pas à pas, vitesse, arrêt, **événement surprise**, correction | Simple l.358 (D-12) | simulation | P0 (pause/reprise/arrêt/pas) · P1 (vitesse, surprise) | Tests API |
| FR-35 | Snapshot figé au lancement (config, agents, droits, scénario, versions de documents) + empreinte | U§10 | simulation | P0 | Hash du snapshot dans le premier événement du ledger |
| FR-36 | Reprise après coupure depuis la dernière étape validée (étapes idempotentes) | Simple l.439 (D-13) | simulation | P1 (squelette P0) | Test « kill puis reprise » |
| FR-37 | Sièges IA ou humain ; bascule en cours d'exercice ; délai puis reprise par l'IA | Simple l.645 ; Spec L181 (D-11) | simulation | P0 (humain web) | Test de prise de contrôle |
| FR-38 | Vue observateur en lecture seule, visibilité réglable ; **rôles et droits** | Simple l.96, l.717, l.879-887 (D-14/D-15) | simulation/core | P1 (jeton lecture P0) | Test de visibilité |
| FR-39 | Suivi en temps réel (SSE), reprise par `Last-Event-ID` | U§10 | simulation | P0 | Test de reconnexion |

### Audit (U §11, Spec L641-655, L672-680, Simple l.659, l.749)

| ID | Exigence | Source | Module | Prio | Vérification |
|---|---|---|---|---|---|
| FR-40 | Ledger : INJECT, RETRIEVAL, LLM_CALL, TOOL_CALL, BOARD, DECISION, CITATION_CHECK, GAP, HUMAN, ERROR + **SNAPSHOT, STATE, SEAT, FACILITATOR, CORRECTION** (ajoutés, D-17) | Spec L641-649 ; Simple l.431, l.528 | audit | P0 | Catalogue d'événements versionné |
| FR-41 | Chaîne SHA-256 sur JSON canonique, séquence, détection de modification **et** de troncature (ancre de tête) | U§11 ; BP-34 | audit | P0 (chaîne + ancre) · P1 (signature) | Tests modification/troncature |
| FR-42 | Rejeu **sans rappeler les modèles** : (a) lecture de la chronologie ; (b) ré-exécution avec fournisseur « cassette » | U§11 | audit/agents | P0 (a) · P0 (b, simple) | Même `replay_digest` après rejeu (doc 10 §10.3) |
| FR-43 | Trace d'exécution vérifiable (actions, outils, résultats, sources, justification) sans exposer le raisonnement privé | U§11 | audit | P0 | UI trace |
| FR-44 | Bouton « Vérifier le journal » → intact ou première entrée altérée | Spec UI p.7 | audit | P0 | Test |

### Lacunes et rapports (U §7)

Voir doc [09](09-gap-analysis-and-reports.md) pour le détail ; exigences de haut niveau :

| ID | Exigence | Source | Module | Prio |
|---|---|---|---|---|
| FR-50 | Règles G1–G10 exécutées par du code sur registre + demandes + étiquettes ; signaux observés du coordinateur | Spec L553-572 | gaps | P0 (G1, G2, G3, G8 + signaux) · P1 (G4–G7, G9, G10) |
| FR-51 | Chaque lacune : id, titre, description, type, domaine, institutions, mandats, sources (doc/article/page/extrait), événements, messages, décisions, conséquences, gravité, confiance, références, précédents, recommandations, statut de validation | U§7.3 | gaps | P0 |
| FR-52 | Trois axes séparés : `evidence_basis`, `confidence`, `validation_status` ; statuts `proposed / confirmed / disputed / rejected` ; historique de revue append-only | Simple l.696-703 (D-06) | gaps | P0 |
| FR-53 | Hypothèses d'agent ≠ constats | U§7.3 | gaps | P0 |
| FR-54 | Précédents internationaux sourcés, ≥ 2 juridictions distinctes sinon « sources insuffisantes » | Spec L618-626 ; U§7.4 | gaps | P0 (bibliothèque curée) · P1 (retrieval) |
| FR-55 | Page Gap Analysis : filtres, preuves, revue, observations, comparaison d'exercices | U§7.5 | frontend/gaps | P0 (liste, preuves, revue) · P1 (comparaison) |
| FR-56 | Import de rapports antérieurs, consultables, jamais confondus avec les nouvelles lacunes | U§7.6-A | reports | P1 |
| FR-57 | Rapport généré (contexte, méthodologie, lacunes, preuves, responsabilités, précédents, recommandations, validations, limites) ; versions immuables ; comparaison | U§7.6-B | reports | P0 (MD, CSV, JSON) · P1 (PDF, comparaison) · P2 (XLSX) |
| FR-58 | Plan d'amélioration (responsable, échéance, statut) séparé des observations | HSEEP (A7) | gaps/reports | P1 |

### Évaluation (Spec L883-894)

| ID | Exigence | Module | Prio |
|---|---|---|---|
| FR-60 | T1 retrieval ≥ 80 % (40 questions, top-5) ; T2 citations ≥ 95 % ; T3 lacunes prévues ≥ 80 % (fixtures cachées) ; T4 lacunes non inventées ≥ 85 % (revue humaine) ; T5 stabilité ≥ 80 % (3 runs) ; T6 < 20 min et < 200 appels | evaluation | P0 (T2, T6 automatiques) · P1 (T1, T3, T4, T5) |
| FR-61 | Scorecard 13 dimensions ITU, évaluation par critères, « non évalué » ≠ 0 | evaluation | P1 (grille manuelle P0) |

## 2.3 Arbitrage des divergences Simple / Spec (les 47 sont dans l'annexe A2)

| ID | Sujet | Arbitrage retenu | Effet sur l'architecture |
|---|---|---|---|
| D-01 | Hiérarchie des documents | Cf. §2.1 | — |
| D-04 | 11 écrans (Simple) vs 8 pages (Spec) | 11 écrans = design cible ; pages = sous-ensemble MVP ; **les écrans du brief U (Studio, Room…) les englobent** | Routes frontend doc 11 |
| D-06 | Statuts de lacunes | Deux axes : *confiance* (`high/medium/low`, dérivée de la base de preuve) et *statut* (proposé/confirmé/contesté/rejeté), + `evidence_basis` | Modèle `gap` doc 09 |
| D-07 | Statuts de documents | Deux axes : fiabilité (officiel/résumé/non trouvé) et validité (en vigueur/remplacé/inconnu) + « remplacé par » + date | `document` doc 06 |
| D-09 | Nombre de sièges (6/7/8) | **Donnée de scénario, pas une constante** : le moteur accepte N sièges | Aucune constante dans le code |
| D-11 | Siège humain en MVP ? | Oui, version web minimale (exigence du brief U §8 « Participant & Human Assignment ») ; Slack = hors périmètre | `human_task` |
| D-12/13 | Pause, reprise, vitesse, reprise après coupure | Retenir le Simple (états + étapes idempotentes) | State machine doc 08 |
| D-14/15/16 | Observateur, rôles, visibilité | Jetons par rôle (propriétaire, animateur, joueur de siège, observateur, auditeur) ; visibilité par événement | `visibility` du ledger |
| D-17 | Types du journal | Ajout de STATE, SEAT, FACILITATOR, CORRECTION | Catalogue d'événements doc 10 |
| D-18 | « base juridique manquante » | Signal `MISSING_BASIS` du coordinateur, rattaché à G1/G3 dans la règle de regroupement | doc 09 |
| D-19 | Citation échouée : consignée ou non | **Toujours consignée** ; décision « non vérifiée » visible | FR-25 |
| D-21 | Revue d'expert | Statut humain en P0 (le statut doit exister) ; écran dédié simple | `gap_review` |
| D-24 | T1–T6 vs 8 mesures | T1–T6 (Spec) bloquantes ; les 2 mesures du Simple non bloquantes | doc 10 |
| D-28 | Hébergement | Conteneur unique ; LLM par URL OpenAI-compatible ; **mode rejeu pour la démo hors Sandbox** | doc 13 |
| D-29 | Licence du corpus | Les textes ne sont pas sous licence logicielle ; licence **par document** ; export « ouvert » exclut restreint/inconnu | FR-19 |
| D-30/31 | Formulaire de décision, types de message | `options` conservé dans la décision ; réponse = champ `reply_status` d'un `post` lié à un REQUEST (on garde 5 types) | schémas doc 08 |
| D-33/34 | Libellés | Bandeau « Fictional exercise, not a real alert » ; citation échouée = « not verified » | UI |
| D-38 | Noms des dimensions ITU | Libellés officiels du rapport AI Readiness (13) ; **relire `alerte/data/framework/dimensions.json`** | scorecard |
| D-39 | Noms G1–G10 | Codes G1–G10 stables ; libellés de la Spec | `gap_rule` |

## 2.4 Ambiguïtés de la Spec résolues par la généricité

| Ambiguïté (liste A1 §L) | Résolution |
|---|---|
| Injects « All » vs règle « aucun inject à tous » ; budget ≤ 4 destinataires | Autorisé, mais **avertissement** de préparation ; le budget d'appels est calculé (injects × destinataires × tours × pas) et comparé au plafond configurable |
| 6 / 7 / 8 institutions | Donnée de scénario |
| Collision d'IDs `CM-01` / `AE-01` (document vs scénario) | Identifiants internes UUID ; codes lisibles distincts par entité (`SC-…` scénarios, `KB-…`, `DOC-…`) |
| `"article": "to confirm"` | Refusé par la validation : `article` ∈ article du chunk ou `null` si le chunk n'en a pas |
| Seuil de découpe, échelle de confiance, règle de sévérité non définis | Définis doc 07 (chunking), doc 09 (confiance : high/medium/low ; sévérité 1–3 par table de règles + étiquettes) |
| Une lacune par inject (certains injects sans code G) | Un inject peut ne produire **aucune** lacune ; ce n'est pas une anomalie (évite de pré-écrire) |
| « Une juridiction par précédent » vs table | Règle : ≥ 2 juridictions *distinctes* par lacune ; plusieurs précédents d'une même juridiction autorisés mais comptés une fois pour le seuil |
| Dénominateurs T2/T3 | T2 : toutes les citations de l'exercice ; T3 : somme des fixtures du scénario |
| Vidéo optionnelle ou non | Hors code ; à confirmer (voir doc 15) |

## 2.5 Exigences nouvelles du brief U (absentes des deux spécifications)

| ID | Exigence | Doc |
|---|---|---|
| U-01 | Espaces de travail génériques, pays configurables dans l'UI | 06, 08 |
| U-02 | Export/ré-import complet des KB, portable, vérifié, avec droits | 07 |
| U-03 | Registre de mandats éditable, validé humainement | 09 |
| U-04 | Gestion de rapports : import, génération, versions, comparaison, téléchargement | 09 |
| U-05 | Matrice d'accès agent × KB appliquée par le moteur de recherche | 07, 08 |
| U-06 | Snapshot de configuration figé, reproductibilité | 08 |
| U-07 | Trace sans dépendre du raisonnement privé du modèle | 10 |
| U-08 | Scorecard par évaluation indépendante des dimensions ITU | 09, 10 |
| U-09 | Deux expériences UI (Studio / Room) | 11 |

## 2.6 Corrections ciblées (2026-11-21)

| ID | Exigence | Module | Prio | Vérification |
|---|---|---|---|---|
| FR-70 | Moteur vectoriel open source choisi après **comparaison** (Chroma, Qdrant, Milvus, pgvector, FAISS, LanceDB, sqlite-vec) ; embeddings indépendants de l'application | knowledge | P0 | [07](07-knowledge-and-rag.md) §7.3 ; A11 |
| FR-71 | **Permissions documentaires vérifiées strictement** : portée construite côté serveur, pré-filtre dans chaque moteur, **revérification SQL de chaque résultat**, tests de propriété sur chaque adaptateur et au niveau HTTP | knowledge/agents | P0 | T-SEC-03, 13, 14 |
| FR-72 | **Windows, Ubuntu, macOS** : installation, exécution, scripts ; **CI GitHub Actions sur les trois** | transverse | P0 | [13](13-security-testing-deployment.md) §13.4 |
| FR-73 | **Étude effective du dépôt de référence ITU** ; matrice exigences organisateurs → composants réellement utilisés | knowledge | P0 | [03](03-hackathon-conformance.md) §3.6 ; A9 |
| FR-74 | **Indépendance de la détection de lacunes renforcée** (provenance des actions attendues, registre non revu ≠ mandat absent, couverture documentaire, cause, contrôle négatif, scénarios indépendants, benchmark externe, relecture aveugle) | gaps/evaluation | P0 (garde-fous de modèle) · P1 (mesures) | [09](09-gap-analysis-and-reports.md) §9.9 |
| FR-75 | **Indépendance du Sandbox** : tout le parcours fonctionne localement ; déploiement Sandbox après validation locale | transverse | P0 | Recette locale des 15 étapes |
