# État de conformité de l'interface et du backend — spécifications et architecture V1 vs réalité

> Exercice fictif, pas une alerte réelle. **Règle de lecture** : la documentation décrit la **cible** ; le code et le comportement **observé** disent ce qui fonctionne. Référence fonctionnelle prioritaire : *ALERTE — The Project Explained Simply* (elle l'emporte sur *Project Specification* en cas de divergence de comportement). Architecture : **V1** (pas de V2). Mise à jour : 2026-11-23, sur le dépôt actuel (branche `main`).
> Statuts : **Opérationnel** · **Partiel** · **Absent** · **Hors périmètre de cette version** (« Later »). Preuve : **UI** (cliqué), **API**, **TEST**, **DOC** (voir le guide).

## 1. Synthèse en dix lignes
1. La **chaîne complète** (espace → pays/institutions → KB → mandats → agents → permissions → scénario → exercice → préparation → simulation → ledger → lacunes → revue → rapport → audit → rejeu) fonctionne **de bout en bout, en mode SANS IA**, y compris pour **Rising Waters Cameroun** (15 événements, 9 sièges, 16 s) et son **jumeau Émirats** (33 s).
2. **Aucun exercice avec un modèle de production n'a été validé.** Un run réel avec un modèle de 1,5 milliard de paramètres a prouvé le **chemin** (outils, recherche hybride réelle, garde-fous), pas la qualité.
3. Les **lacunes** sortent de règles explicites appliquées au registre : la **démonstration contrefactuelle** (texte retiré → G1 ; ajouté et mandat validé → G1 résolue, G3 + G4 ; retiré → G1) a été **exécutée** sur le code actuel.
4. **Intégrité** : ledger chaîné vérifié (284 entrées) ; **altération détectée** sur une copie isolée ; lecture du ledger **sans appel de modèle**.
5. **Isolation et rôles** : tout accès inter-espaces → 404 ; joueur/observateur → 403 sur boîtes privées et commandes.
6. **Limites majeures** : bibliothèque de références internationales **vide** (R-19), recherche **lexicale** (pas d'embeddings sur la base du prototype), `silent_institution` et 13 autres modes de panne **sans effet** (étiquettes), correction/historique de mandat et nouvelle version de rapport **sans écran**, comparaison de **deux pays** non alignée.
7. **Documents** : droits de redistribution **inconnus** pour les 45 documents ; la base construite n'est **pas** dans Git (voir diagnostic KB).
8. **UX** : l'application est désormais guidée (phases A/B/C, barre de parcours, prérequis, glossaire, explication du Workspace, français complet).
9. **Défauts corrigés pendant cette mission** : voir §6.
10. **CI GitHub** (3 OS) écrite, **jamais exécutée** ; Windows/macOS non testés.

## 2. Les 16 espaces de la navigation cible

| Espace cible | Existe ? | Nom exact dans l'interface | Route | Statut / écart |
|---|---|---|---|---|
| Workspace Home | oui | **Accueil** (+ écran d'entrée) | `/`, `/access` | **Partiel** : pas de liste/sélecteur d'espaces ; un jeton = un espace ; pas de description d'espace (nom + slug seulement) |
| Country & Institutional Manager | oui | **Pays et institutions** (onglets *Pays*, *Institutions*) | `/studio/countries` | Opérationnel (pas de champ « contacts ») |
| Knowledge Base Manager | oui | **Bases de connaissances** (+ page de base : *Documents, Qualité et couverture, Versions et index, Test de recherche, Export / import*) | `/studio/knowledge[/:id[/documents/:id]]` | Opérationnel |
| Mandate Registry | **onglet**, pas une page | onglet **Registre des mandats** (*Revue du registre*, *Mandats*, *Catalogue d'actions*) | `/studio/countries` | **Partiel** : correction du texte et historique en API seulement ; **ajout/retrait de source sur un mandat existant : opérationnel dans l'interface depuis le 2026-11-24** (bouton **Sources**, UI) |
| Agent Manager | oui | **Agents** (+ section *Profils de modèle*) | `/studio/agents` | Opérationnel |
| Knowledge Access Mapping | oui | **Accès aux connaissances** | `/studio/access` | Opérationnel |
| Scenario Builder | oui | **Scénarios** (+ constructeur) | `/studio/scenarios[/:id]` | Opérationnel (branches **absentes**) |
| Participants & Readiness | oui (dans la page d'exercice) | **Exercices** (*Sièges*, *Préparation de l'exercice*) | `/studio/exercises[/:id]` | Opérationnel (délai humain non exposé) |
| Simulation Room | oui | **Salle de simulation** | `/room[/:id]` | Opérationnel (correction : pas de bouton) |
| Player Seat | oui | page **sans menu**, lien personnel | `/play#t=…` | Opérationnel |
| Observer View | oui | page **sans menu**, lien personnel | `/watch#t=…` | Opérationnel (vue publique seule) |
| Gap Analysis & Institutional Assessment | oui | **Analyse des lacunes** | `/gaps[/:id]` | Opérationnel (filtres pays/domaine/confiance absents) |
| Report Center | oui | **Rapports** | `/reports[/:id]` | Opérationnel (nouvelle version : API) |
| Audit & Replay | oui | **Audit et rejeu** | `/audit[/:id]` | Opérationnel |
| Evaluation & Scorecard | oui | **Évaluation** | `/evaluation` | **Partiel** (T1/T3/T4/T5 exigent des données ; scorecard manuel ; LLM 501) |
| Mapping Y.3172 | oui | **Architecture** | `/about/architecture` | Opérationnel (correspondance conceptuelle, pas une conformité) |
| *(ajoutés)* | oui | **Jetons d'accès**, **Glossaire** | `/settings/tokens`, `/help/glossary` | — |

## 3. Exigences R-01 à R-29 (spécifications)
| R | Exigence | Statut | Remarque |
|---|---|---|---|
| 01 | bibliothèque CM + AE + exemples mondiaux | **Partiel** | 45 documents importables (CM 17, AE 9, GL 16, ITU 1, SCN 2) ; **non versionnés dans Git**, droits inconnus |
| 02 | provenance par passage (document, article, langue, date, lien) | **Partiel** | nouvelle ingestion : page + article + section ; import du prototype : **pas de page** |
| 03 | fiabilité (officiel / résumé / non trouvé) | Opérationnel | champ `reliability` |
| 04 | recherche FR/EN | **Partiel** | lexicale opérationnelle ; vectorielle **réelle** testée (BGE-M3, 1 test) ; **pas de jeu de questions valide** pour mesurer |
| 05 | carte des pouvoirs liée à l'article ou « supposé » | Opérationnel | statuts proposé/validé/rejeté ; preuves `documented/inferred/assumed` |
| 06 | expert accepte/corrige/rejette | **Partiel** | accepter/rejeter en UI ; corriger en API |
| 07 | événements un par un à des temps de l'histoire | Opérationnel | temps simulé = libellé ; cadence par rythme |
| 08 | chaque événement seulement à ses destinataires | Opérationnel | constaté |
| 09 | démarrer, pause, reprise, accélérer, arrêter, surprise | Opérationnel | « accélérer » = délai entre événements |
| 10 | nouvelle histoire sans changer le système | Opérationnel | import YAML + éditeur |
| 11 | boîte, mémoire, pouvoirs, documents propres ; jamais la boîte d'un autre | Opérationnel | 403 constaté |
| 12 | décision : sait / ne sait pas / options / choix / base légale / confiance | **Partiel** | pas de champs « sait / ne sait pas » |
| 13 | « aucune base légale trouvée » plutôt qu'inventer | Opérationnel | issue dédiée ; citation fausse refusée |
| 14 | demandes, réponses, objections, alertes de lacune | Opérationnel | **TEST** ; les agents SANS IA ne postent pas |
| 15 | siège humain ; l'IA reprend si silence | Opérationnel | reprise constatée (API) |
| 16 | conseiller juridique en 4 parties | Opérationnel | via le siège (pas d'écran autonome) |
| 17 | lacunes par règles explicites | Opérationnel | G1–G10 + X0/X2/X4 |
| 18 | preuve, gravité, confiance | Opérationnel | |
| 19 | ≥ 2 exemples de pays différents par lacune | **Absent** | bibliothèque de références **vide**, non gérable en UI |
| 20 | vérification de chaque citation | Opérationnel | |
| 21 | journal ordonné de tout | Opérationnel | |
| 22 | toute modification détectable | Opérationnel | constaté sur copie |
| 23 | rejouer sans rappeler l'IA | Opérationnel | constaté |
| 24 | rapport de lacunes + chronologie + scorecard 13 dimensions | **Partiel** | scorecard par saisie humaine ; chronologie via Audit/Trace |
| 25 | export document et PDF | Opérationnel | MD, JSON, CSV, XLSX, PDF |
| 26 | même histoire, deux pays côte à côte | **Partiel** | jumeau jouable ; comparaison automatique non alignée |
| 27 | avant/après un changement de loi | Opérationnel (prévu « Later ») | contrefactuel exécuté |
| 28 | histoire depuis une chronologie réelle | **Hors périmètre** | |
| 29 | profil de défaillance d'un système d'IA précis | **Hors périmètre** | ébauche : modes de panne + sortie scriptée |

## 4. Fonctionnalités F-01 à F-15, qualités Q-01 à Q-12, règles d'or
| Élément | Statut | Détail |
|---|---|---|
| F-01 Bibliothèque … F-14 Journal et rejeu | voir R-xx | F-11 **Exemples du monde : absent** |
| F-15 Langues | **Partiel** | interface **FR/EN complète** (test de parité) ; **rapports en français seulement** ; messages de certains contrôles backend en français ; arabe absent |
| Q-01 Honnête | Opérationnel | bandeau SANS IA, « non calculé », lacunes « déduites » |
| Q-02 Traçable (2 clics) | **Partiel** | chaîne de preuves à l'écran ; passages OCR parfois dégradés |
| Q-03 Compréhensible | **Amélioré** (cette mission) | parcours A/B/C, prérequis, glossaire |
| Q-04 Bilingue | Partiel | cf. F-15 |
| Q-05 Fonctionne hors ligne sur un portable | **Partiel** | exécution locale oui (SQLite) ; modèles : serveur à fournir |
| Q-06 < 20 min en autopilot | **Opérationnel en SANS IA** (16 s) ; **non mesuré avec un vrai modèle** | |
| Q-07 Répétable | **Non mesuré** | T5 exige des exercices clonés |
| Q-08 Sûr | Opérationnel | bandeau « Exercice fictif » ; aucune donnée personnelle |
| Q-09 Ouvert | **Partiel** | export de KB prêt ; publication bloquée par les droits |
| Q-10 Adaptable | Opérationnel | pays/histoire/institution sans refonte (jumeau en 6 minutes) |
| Q-11 Indépendant du fournisseur | Opérationnel | `openai_compat` ; profils |
| Règles d'or 1–10 | **Respectées** | 1 pas de décision sans base (issue dédiée) · 2 citation vérifiée · 3 boîte privée (403) · 4 pouvoirs depuis la carte · 5 hypothèses étiquetées · 6 rien n'est effacé (retrait = statut, corrections = nouvelles entrées) · 7 lacunes = règle + preuve · 8 exemples du monde : **non tenue** (R-19) · 9 documents = données · 10 fiction étiquetée |

## 5. Écarts, défauts connus et backlog (par priorité)
| Prio | Écart / défaut | Effet | Piste |
|---|---|---|---|
| **P0** | Aucun test avec un modèle de génération **de production** | qualité des agents inconnue | machine d'équipe/Sandbox ; `pytest -m model tests/agents` ; exercice réel Rising Waters |
| **P0** | Bibliothèque de références internationales vide (R-19) | « sources insuffisantes » partout | amorcer depuis `precedents.yaml` du prototype ; écran de gestion |
| **P0** | Base du prototype sans embeddings, pages absentes, droits inconnus | retrieval dégradé ; publication impossible | re-extraction ; embeddings sur machine adaptée ; qualification des droits |
| P1 | Deux exercices **simultanés** sur SQLite : « database is locked » dans la détection incrémentale (journalisé, détection finale correcte) | bruit d'erreurs | sérialiser les écritures de lacunes ; `busy_timeout` |
| P1 | `silent_institution` et 13 autres modes de panne = étiquettes | scénarios de panne « sans effet » hors `llm_outage` | implémenter (silence, retard, donnée dégradée) ou le dire dans l'éditeur |
| P1 | Recherche négative lexicale : passages sans rapport affichés | preuves trompeuses | seuil/filtre ; embeddings |
| P1 | Comparaison de **deux pays** par empreinte (institutions) | « 0 persistante » | apparier par action + règle |
| P1 | UI : correction/historique d'un mandat ; nouvelle **version** d'un rapport ; correction d'une décision ; délai humain ; visibilité des observateurs ; filtres pays/domaine/confiance | actions réservées à l'API | écrans |
| P1 | Décision : pas de champs « sait / ne sait pas » | écart à la spec | ajouter au formulaire et au schéma |
| P1 | Liste d'espaces / description d'espace / jeton perdu | prise en main | écran de sélection ; récupération par l'hôte |
| P2 | Rapports en français uniquement ; PDF sans repli si Pango absent ; pas de signature d'archive | | |
| P2 | Branches de scénario, UC-23, UC-24, arabe | « Later » | |

## 6. Corrections apportées pendant cette mission (sans changer l'architecture)
**Expérience utilisateur** : explication du **Workspace** (écran d'entrée et Accueil) ; **parcours en 3 phases** (menu A/B/C numéroté, barre de parcours avec étape suivante, Accueil à compteurs réels et « prochaine étape ») ; **prérequis** visibles sur Agents, Accès, Scénarios, Exercices, Salle, Lacunes, Rapports ; **états vides** avec lien d'action ; **glossaire** (14 notions + « ? » contextuels) ; libellés d'états traduits ; **français complet** ; logo, liens de navigation corrects (une règle CSS soulignait tout), bandeau sobre ; tableaux sans débordement mobile ; accessibilité (axe : 0 violation).
**Défauts fonctionnels** : (1) l'**`ai_mode` d'un exercice était ignoré** : une démonstration « Scénarisé » retombait en repli faute de `ALERTE_LLM_BASE_URL` ; (2) la préparation traitait les contrôles **réussis** du scénario comme des échecs ; (3) le **budget de l'exercice** n'était pas pris en compte par le contrôle de budget du scénario (Rising Waters restait bloqué) ; (4) la génération du **XLSX** échouait quand une lacune n'avait aucune référence ; (5) les messages de préparation affichaient des **identifiants techniques** au lieu des codes d'institution ; (6) `alembic upgrade head` exigeait un dossier de données existant. Chacun a un test de non-régression.
**Outillage ajouté** : `backend/scripts/rising_waters_pack.py` (pack Rising Waters CM/AE au format de la plateforme ; **les lacunes attendues restent dans un fichier privé, jamais dans le scénario**), `seed_rising_waters.py` (préparation par étapes de l'espace « ALERTE — Demonstration »), `ledger_tamper_demo.py` (altération sur copie isolée) ; `.gitignore` : `data-demo/`.

## 7. État des fournisseurs d'IA
| Composant | État |
|---|---|
| Embeddings **BGE-M3** (Ollama) | **réel** : 1 test `-m model` réussi ; indexation réelle de la démonstration ; ≈ 12–14 s par chunk sur le poste de développement (la base entière : machine d'équipe) |
| Génération `qwen2.5:1.5b-instruct` (Ollama) | **réel mais minuscule** : recherche hybride et garde-fous exercés ; ne cite pas correctement → décisions refusées/non vérifiées |
| Génération 7–14 B | **non essayée** |
| `scripted` / `fixture` / `cassette` | outils de test, **jamais une preuve d'IA** |

## 8. Tests exécutés (cette mission)
Voir le compte rendu final : suite backend complète, suite frontend (typecheck, lint, tests, build), ruff, migrations sur environnement vierge, parcours Rising Waters CM et AE, contrefactuel, commandes de simulation, siège humain, observateur, isolation, altération du ledger, rapports ×5 formats, évaluation.


## 7. Mise à jour du 2026-11-24 (stabilisation après fusion)

| Sujet | Avant | Maintenant | Preuve |
|---|---|---|---|
| Source d'un mandat **importé** | impossible dans l'interface (seulement à la création) → blocage de l'ancienne étape 7.3 | bouton **Sources** par ligne (recherche dans la base, **Utiliser comme source**, **Enregistrer les sources**, retrait) ; colonne **Réf.** pour repérer `CM-L10` | **UI** navigateur réel (CM-L10, CM-L13, CM-L14), tests TS |
| Parcours de préparation | 5 compteurs (« fait » dès qu'un objet existe) | 10 étapes à **état réel** (KB non publiée / sans pays = « à compléter » ; mandat « fait » seulement s'il est validé **avec source** ; étapes verrouillées tant que le prérequis manque) + barre « **À faire maintenant** » sur chaque page de préparation | **UI** + **TEST** (`setup.test.ts`, 9 cas) |
| Base de connaissances ↔ pays | champ facultatif, invisible dans la liste, non modifiable après import | colonne **Pays / juridiction**, menu **Rattacher à un pays**, avertissement pour une base nationale sans pays | **UI** |
| Institution ↔ pays | liste « — » par défaut | pays **obligatoire** quand un pays existe, préchoisi s'il est unique | **UI** |
| Revue du registre | texte demandant de tout passer en « revu complet » | panneau d'aide + guide : « revu complet » **uniquement** après une revue humaine réelle | **DOC/UI** |
| `GET /gaps` | 1 requête SQL par lacune | 1 requête pour toutes (74 → 36 ms médian, 42 lacunes) | **TEST** + mesure |
| Pages de l'équipe (`/present`, `/alerte`, `/what-if`, `/responsibilities`, vérification de projet de texte, signatures Ed25519, juge IA) | non auditées | **s'affichent sans erreur** (smoke navigateur 23 routes) ; leur **contenu fonctionnel n'est pas audité** ici | **UI** (affichage seulement) |
| Tests | 517 backend / 56 frontend | **539 réussis + 2 ignorés** / **88** | **TEST** |

Écarts restants (ouverts) : voir [stabilisation-rapport-final.md](../audits/stabilisation-rapport-final.md).


## 8. Mise à jour du 2026-11-24 (base de connaissances reconstruite à partir des PDF)

| Sujet | État | Preuve |
|---|---|---|
| Corpus | **44 PDF** de `alerte/` → 44 documents, 2 133 pages, 3 886 chunks, 1 565 Knowledge Records (export) ; l'ancienne archive de 45 documents / 4 235 passages n'est plus la source | RÉEL (`docs/knowledge-base/build-report.md`) |
| Pipeline | un seul pipeline (interface et `kb_build.py` appellent les mêmes endpoints) ; correctifs : texte perdu au découpage, pages scan avec cachet, articles « (n) », suite d'articles interrompue, index vectoriel incomplet | TEST + RÉEL |
| Recherche hybride | **non opérationnelle sur le corpus** : embeddings BGE-M3 non terminés (≈ 6–20 s/passage sur cette machine) ; recherche **lexicale étiquetée dégradée** | RÉEL |
| Qualité mesurée | Recall@5 lexical 0,667 (même langue 1,000 ; langue croisée 0,333) ; T1 (≥ 0,80) **non atteint** globalement | RÉEL (`retrieval-evaluation.md`) |
| Droits / publication | 2 `allowed`, 1 `restricted`, 41 `unknown` ; texte publié dans Git seulement pour `allowed` | RÉEL |
| Vocabulaire de fiabilité | `unknown` ajouté (`official|summary|unofficial|unknown|not_found`) | TEST |
| Graphe de mandats | `knowledge_bases/CM/graph/` : 14 mandats, institutions, relations, sources résolues vers les chunks | RÉEL |
