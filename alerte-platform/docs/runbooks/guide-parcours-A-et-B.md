# Guide de test — Parcours A (sans IA) et Parcours B (modèle réel)

Ce guide est la **trame d'exécution** des tests. Il ne répète ni les commandes ni les valeurs des champs : il dit **dans quel ordre** faire les choses et **quoi vérifier**, et renvoie à :
* le [catalogue des commandes et fichiers](catalogue-commandes-et-fichiers.md) (`#n` = numéro de commande) ;
* le [guide champ par champ](guide-champs-formulaires.md) (`§` = section du formulaire) ;
* le [guide de test complet](guide-test-complet-interface.md) (détail historique de chaque écran, cas extrêmes) ;
* la [configuration `.env`](configuration-env.md) et le [déploiement](../deploiement/README.md).

## Légende
| Marque | Sens |
|---|---|
| **[UI]** action faite dans l'interface · **[CLI]** commande dans un terminal · **[API]** appel direct à l'API · **[TEST]** test automatisé du dépôt · **[DOC]** déduit du code · **[ABS]** non implémenté |
| **PASS** | le résultat attendu a été constaté **et la preuve est conservée** (capture, sortie, identifiant d'exercice) |
| **FAIL** | résultat différent de l'attendu (noter le message exact) |
| **BLOCKED** | test impossible faute de prérequis (modèle, GPU, base absente) : dire lequel |
| **NOT TESTED** | non exécuté. **Toutes les cases de ce guide partent à NOT TESTED** : ne cochez PASS que ce que vous avez vu |

Ne jamais déclarer PASS un test que vous n'avez pas exécuté. Un test **API** n'est pas un test d'**interface** ; un écran qui s'ouvre ne prouve pas que ses fonctions marchent ; un exercice **SANS IA** ne prouve rien sur les modèles.

## Ce qui sépare les deux parcours
| | **Parcours A — SANS IA** | **Parcours B — Modèle réel** |
|---|---|---|
| But | comprendre l'application, vérifier la chaîne **déterministe** (import, préparation, moteur, lacunes, rapport, audit) | **vérifier avec un vrai modèle** : accès au fournisseur, génération, échanges entre agents, décisions citées, lacunes |
| Mode d'exécution de l'exercice | **Scénarisé (SANS IA)** | **Modèle réel** |
| Modèle requis | aucun | serveur joignable, nom exact du modèle ; **un petit modèle (1,5 B) ne valide que le câblage** |
| Ce que le résultat prouve | la plateforme fonctionne | (si le modèle est adapté) le comportement des agents |
| Ce qu'il ne prouve **jamais** | la qualité des décisions, la coordination | — (sauf mesures) |
| Messages entre agents | **aucun** (le fournisseur scripté ne poste pas) | oui, si le modèle suit les consignes de coordination (à observer, non garanti) |

---
## Parcours A — Découverte SANS IA
| N | Type | Action | Détail | Résultat attendu | Statut |
|---|---|---|---|---|---|
| A1 | [CLI] | Préparer l'environnement, `.env`, doctor | #1, #2, #4 | `doctor.py` : 0 bloquant | NOT TESTED |
| A2 | [CLI] | Démarrer backend + interface | #5, #6 | `{"status":"ok"}` ×2 | NOT TESTED |
| A3 | [CLI] | Générer le pack Rising Waters | #9 | « pack écrit dans … » | NOT TESTED |
| A4 | [UI] | Créer l'espace (`/access`) ou [CLI] `workspace create` | #10, § Espace | jeton conservé | NOT TESTED |
| A5 | [UI] | Pays, institutions (11 : 9 sièges dont HYDRO, plus COORD et ONR sans siège), catalogue d'actions (25) | § Pays, § Institutions, § Actions | compteurs de l'Accueil | NOT TESTED |
| A6 | [CLI] | Construire et **publier** la base CM (si absente) | #11 à #17 | `status` : vecteurs = passages ; version 1 active | NOT TESTED |
| A7 | [UI] | Importer les 14 mandats (statut « proposé ») | § Mandats | 14 créés, 0 erreur | NOT TESTED |
| A8 | [UI] | Associer une source à un mandat puis le **valider** (au moins CM-L10, CM-L11) | § Mandats | statut « validé » | NOT TESTED |
| A9 | [UI] | Créer les 9 agents (mission **et** instructions renseignées) | § Agents | 9 agents ; HYDRO de rôle « système d'IA » | NOT TESTED |
| A10 | [UI] | Permissions : base CM pour les 9 agents | § Permissions | matrice cochée | NOT TESTED |
| A11 | [UI] | Importer le scénario YAML (15 injects) | § Scénarios | avertissements lus, 0 erreur de lint | NOT TESTED |
| A12 | [UI] | Créer l'exercice : **Scénarisé (SANS IA)**, rythme **Automatique**, budget 330 | § Exercices (A) | bandeau « SANS IA » | NOT TESTED |
| A13 | [UI] | Préparation (readiness) puis **Lancer** | § Exercices | 0 bloquant ; l'exercice démarre | NOT TESTED |
| A14 | [UI] | Observer la salle de simulation | — | événements, décisions « Act within the documented mandate » ; **0 message** (normal en SANS IA) | NOT TESTED |
| A15 | [UI] | Analyse des lacunes (détection si nécessaire), revue | § Lacunes | signaux listés ; à qualifier, jamais « prouvés » d'avance | NOT TESTED |
| A16 | [UI] | Rapport : générer, lire, exporter | § Rapports | rapport avec bandeau SANS IA | NOT TESTED |
| A17 | [UI] | Audit : vérifier la chaîne du journal ; **Rejeu** | § Replay | chaîne valide ; le rejeu n'appelle aucun modèle | NOT TESTED |

Raccourci des étapes A5–A13 : `seed_rising_waters.py` (#18 à #21). Il crée des objets en mode **SANS IA** : ce n'est **pas** une preuve de fonctionnement de l'IA.

---
## Parcours B — Validation avec un modèle réel
**Prérequis** (sinon, marquer BLOCKED et dire lequel) : (1) le parcours A passé jusqu'à A11 ; (2) un serveur de génération joignable et le **nom exact** du modèle ([déploiement](../deploiement/README.md)) ; (3) le serveur d'embeddings (BGE-M3) ; (4) `doctor.py` sans point bloquant, **y compris « modèle servi »** ; (5) un contexte serveur ≥ 8 192 jetons.

| N | Type | Action | Détail | Résultat attendu | Statut |
|---|---|---|---|---|---|
| B1 | [CLI] | Vérifier le serveur de modèle | #7 puis `doctor.py` | le modèle configuré est listé par `/v1/models` | NOT TESTED |
| B2 | [CLI] | Mesurer la latence (dimensionnement) | #8 | médiane par appel notée ; prompt non tronqué | NOT TESTED |
| B3 | [UI] | Profil de modèle (facultatif) + **Tester la connexion** | § Profils | « joignable » | NOT TESTED |
| B4 | [UI] | Créer l'exercice : **Modèle réel**, rythme Automatique, budget (≈ 450, à ajuster) | § Exercices (B) | pas de bandeau SANS IA | NOT TESTED |
| B5 | [UI] | Préparation : **provoquer volontairement** l'échec (nom de modèle faux) puis corriger | — | « modèle … inaccessible » **bloque** le lancement ; corrigé, « joignable » apparaît | NOT TESTED |
| B6 | [UI] | **Test d'un agent isolé** : exercice court (1 inject, 1 destinataire, ex. inject 1 → MET) | § Exercices | une décision citée, ou un refus motivé | NOT TESTED |
| B7 | [UI] | **Plusieurs agents** : injects 2 à 4 (MET, DPC, OPS) | — | messages de coordination visibles (REQUEST / réponse) | NOT TESTED |
| B8 | [UI] | **Exercice complet** | — | terminé sans pause de budget ; sinon « Étendre le budget » puis reprendre | NOT TESTED |
| B9 | [UI] | Vérifier par décision : citations vérifiées (passage existant), refus quand le texte manque, langue | Trace de décision | citation « vérifiée » ; aucune citation inventée | NOT TESTED |
| B10 | [UI] | Vérifier la coordination : demande → transmission → réponse → prise en compte → décision | Tableau de coordination | au moins une chaîne complète, ou **constat honnête qu'il n'y en a pas** | NOT TESTED |
| B11 | [UI] | Permissions : un agent n'accède qu'à ses bases | § Permissions + tests | aucune citation hors périmètre | NOT TESTED |
| B12 | [UI] | Lacunes fondées sur des preuves vérifiables | § Lacunes | chaque lacune renvoie à des événements | NOT TESTED |
| B13 | [UI] | Rapport, audit (chaîne), **Rejeu** | § Rapports, § Replay | le rejeu restitue l'exercice **sans** nouvel appel au modèle ; présenté comme rejeu | NOT TESTED |
| B14 | [UI] | Scorecard et export | — | valeurs issues des mesures | NOT TESTED |
| B15 | — | Fiche d'enregistrement du run | ci-dessous | remplie | NOT TESTED |

### Fiche d'enregistrement d'un run (à remplir pour chaque exercice du parcours B)
| Champ | Valeur |
|---|---|
| Date, personne | |
| Commit du dépôt (`git rev-parse --short HEAD`) | |
| Modèle (nom exact, quantification, serveur et version) | |
| Machine d'inférence (sonde matérielle) | |
| Embeddings (modèle, empreinte de l'index) | |
| Base CM (version publiée, nombre de passages) | |
| Scénario (code, version, langue) | |
| Identifiant de l'exercice, mode, rythme, budget | |
| Appels consommés / durée | |
| Décisions vérifiées / non vérifiées, messages échangés, lacunes | |
| Anomalies | |

**Budget et critère T6.** Le critère T6 de la spécification (« moins de 200 appels au modèle par exercice ») est **incompatible avec un exercice CM-01 complet en 3 tours** (estimation haute ≈ 456 appels à la préparation, 492 au lint ; la consommation réelle n'a jamais été mesurée avec un vrai modèle). Ne **changez pas** le seuil en silence : publiez la valeur **mesurée** et dites que T6 n'est pas tenu, ou réduisez le coût (scénario réduit) et déclarez-le. 450 n'est qu'un plafond de sécurité à recalibrer après un premier run.

**Coordination : ce qui est garanti et ce qui ne l'est pas.** Les messages sont livrés (tour *n* → *n+1*), une demande postée au tour 2 est refusée (sa réponse tomberait au dernier tour), au dernier tour on ne peut que décider, et seule la **dernière décision d'un siège** sur un inject compte pour les signaux de coordination (une décision provisoire révisée ne crée pas de faux conflit). Un siège non destinataire d'un événement n'en voit que les messages reçus. **Que les agents coordonnent réellement dépend du modèle** : c'est ce que B7 et B10 doivent constater.

**Règle de présentation.** Un résultat du parcours B obtenu avec un petit modèle de test (1,5 B) s'écrit « **test de câblage** » et ne figure ni dans le rapport ni dans la vidéo comme validation de la qualité des agents.
