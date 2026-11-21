> **Annexe — Registre des exigences de « The Project Explained Simply » et divergences avec la spec.**
> Matériau de recherche brut produit le 2026-11-20 par un sous-agent (modèle Haiku 5.5), relu en diagonale par l'architecte. Les marqueurs « non vérifié » / `[NV]` / `[V]` / `[S]` sont ceux du sous-agent ; toute information utilisée dans le dossier principal est citée avec son niveau de vérification. Ce fichier est une pièce justificative, pas une spécification.

---

# ALERTE : registre d'exigences (version « Simple ») et divergences avec la spec technique

Sources lues :
- `ALERTE — The Project Explained Simply.md` (1060 lignes, lu intégralement, notes « Simple » ci-dessous, « l.N » = ligne de ce fichier).
- `ALERTE — Project Specification.md` (1318 lignes, lue par sections et vérifiée par `grep -n`, notes « spec » = « l.N » de ce fichier).

Légende des gravités : **Bloquante** = contredit ou omet une exigence « Must » et change le périmètre, le planning ou l'architecture. **Majeure** = exigence absente, ou règle contradictoire qui force un choix de conception. **Mineure** = chiffre, libellé, formulation ou cohérence documentaire.

Légende de la colonne « Dans la spec » : Oui / Partiel / Non / Contraire.

---

## 0. Hiérarchie des documents (ce que dit le Simple)

Citation verbatim, l.20 :
> « How this differs from the first specification. The earlier [ALERTE Project Specification] mixed all four steps and went deep into tools, code and planning. This document stops before any tool is chosen. When the two disagree on what the system should do, this document wins; the earlier one remains the reference for tools, the document list with links, the team plan and Slack. »

Autres passages :
- l.1002 : « The earlier [ALERTE Project Specification] contains proposals for each of these decisions; they should be confirmed against this document before building starts. »
- l.27 : « If you want to change what ALERTE does, change Part 1 first, then follow the change into Parts 2 and 3. »

Verbatim contraire dans la spec, l.9 : « This document is the single reference for building ALERTE ». L.31 : « When something changes (a deadline, a tool, a decision), we update this document first ».

Conclusion : les deux documents revendiquent l'autorité. Le Simple prime sur le comportement, la spec revendique le tout. Les deux fichiers apparaissent comme non suivis par git (`??` dans le statut), donc il n'existe aucun historique permettant de dire lequel est le plus récent (Simple daté du 3 oct. 2026, spec du 2 oct., « version 1.0, first complete draft »). Le Simple renvoie vers un artefact claude.ai (`e430f513…`) dont la version identique au fichier du dépôt n'a pas pu être vérifiée.

---

## 1. Registre d'exigences

### 1.1 Acteurs, rôles, observateurs, usages

| ID | Section / ligne | Catégorie | Énoncé précis (chiffres inclus) | Priorité | Dans la spec | Vérifiabilité |
|---|---|---|---|---|---|---|
| SI-001 | 1.2, l.92-99 | Acteurs & rôles | Six rôles directs : facilitateur, joueur, observateur, rédacteur de scénario, gardien de connaissances, auditeur ; chacun a un besoin et une fréquence d'usage. | Implicite (Must) | Non (la spec ne décrit que les rôles d'équipe, l.966-983) | Revue de la matrice de droits |
| SI-002 | 3.3, l.879-887 | Acteurs & rôles | Matrice rôle × magasin (connaissances, exercice, journal, rapports). Pendant l'exercice, un joueur ne lit que sa boîte et ses décisions ; après, il lit tout ; l'auditeur lit tout après l'exercice. | Must (implicite) | Non | Test d'accès par rôle |
| SI-003 | 3.3, l.899-903 | Sécurité / données | Aucune donnée personnelle réelle (noms, téléphones, localisations, dossiers de santé) n'entre dans les magasins. | Must (Q-08) | Oui (l.680) | Revue des schémas |
| SI-004 | 1.3, l.146-148 | Usage hors périmètre | ALERTE n'est pas utilisé pour décider pendant une vraie crise ; cette mention est affichée sur chaque écran. | Must (implicite) | Partiel (bannière « Exercise, fictional scenario » seulement) | Présence du texte sur chaque écran |
| SI-005 | 1.3, l.149 ; UC-11 l.319 | Conseil juridique | Aucune réponse juridique n'est un avis : chaque réponse finit par « for practice only; confirm with a lawyer ». | Must | Partiel (formule en anglais : « for exercise purposes; confirm with a qualified lawyer », l.380) | Présence de la phrase |
| SI-006 | 1.3, l.150 ; Q-12 l.399 | Respect des personnes | ALERTE ne juge ni ne classe des personnes nommées ; il évalue des règles et des institutions. | Must | Oui (l.959-966) | Relecture du contenu |
| SI-007 | Q-12, l.399 | Respect | Ton neutre ; aucun sujet politique. | Must | Oui (l.217, l.934) | Relecture |
| SI-008 | 1.2, l.111-113 | Population représentée | La population n'utilise pas ALERTE mais doit être prise en compte : qui est atteint, dans quelle langue, qui est laissé de côté. | Must (indirect) | Partiel (gap G7 et dimension 11 seulement) | Présence des 3 questions dans le rapport |
| SI-009 | 1.3, l.128-137 | Situations d'usage | Dix situations (S1 préparation saison des pluies, S2 achat d'IA, S3 alertes cell broadcast, S4 rédaction de loi, S5 formation, S6 retour d'expérience, S7 nouvelle loi, S8 comparaison de pays, S9 recherche, S10 hackathon). ALERTE n'intervient jamais pendant une crise réelle. | Must (S10) ; autres non précisées | Partiel | Revue |
| SI-010 | 1.3, l.141-144 | Lieux d'usage | Quatre contextes : salle avec projecteur ; distance (Yaoundé, Douala, Maroua) ; un portable hors réseau ; scène avec enregistrement de secours. | Must (hors ligne = Q-05) | Partiel (hors ligne l.914 ; pas d'accès distant ni d'hébergement) | Test sur les 4 contextes |
| SI-011 | 1.2, l.96 ; UC-13 l.242 | Observateur | L'observateur (ministre, juge, journaliste) suit l'exercice sans rien modifier, pendant ou après. | Non précisée | Non | Test : aucune action d'écriture possible |
| SI-012 | 1.3, l.144 | Public | Démonstration sur scène devant un public, avec un enregistrement de secours prêt. | Must (S10) | Partiel (l.181 replay ; l.1206) | Répétition |
| SI-013 | 2.5, écran 7, l.717 | Vue publique | Vue publique : horloge, événements déjà publics, décisions et lacunes au fur et à mesure ; aucune boîte privée ; lecture seule. | Non précisée (absente de 2.7) | Non | Affichage sans boîte |
| SI-014 | 2.3, l.885 | Droits observateur | L'observateur n'a pas accès au journal ; il lit le rapport seulement s'il est partagé. | Non précisée | Non | Test de droits |
| SI-015 | UC-04, l.296 | Observateur | L'animateur choisit ce que voient les observateurs : tout, ou seulement les parties publiques. | Non précisée | Non | Réglage testé |

### 1.2 Machine à états de l'exercice

Citation verbatim, l.666 : « A drill moves through six stages, and can be paused or interrupted while it runs. »

| ID | Section / ligne | Catégorie | Énoncé précis | Priorité | Dans la spec | Vérifiabilité |
|---|---|---|---|---|---|---|
| SI-020 | 2.4, l.674-683 | Machine d'états | Huit états : Brouillon, Prêt, En cours, Terminé, Relu, Archivé (six étapes) plus deux états latéraux, Pause et Interrompu. | Must (R-07, R-09) | Non | Test des transitions (table complète) |
| SI-021 | l.676-677 ; UC-04 l.297 | Brouillon → Prêt | Passage à « Prêt » seulement si bibliothèque, carte et histoire existent et si chaque siège est assigné. Sinon ALERTE avertit. | Must | Non | Test : un siège vide bloque |
| SI-022 | l.678 | En cours → Terminé | Fin quand le dernier événement est traité, ou arrêt par l'animateur. | Must | Non | Test |
| SI-023 | l.679 | Pause | Pause volontaire : l'horloge s'arrête ; reprise par l'animateur. | Must (R-09) | Non (aucune commande pause dans les pages 1-2) | Test |
| SI-024 | l.681 | Terminé | Plus d'événements : le détecteur de lacunes, les exemples mondiaux et la scorecard s'exécutent. | Must | Partiel (étapes implicites) | Test |
| SI-025 | l.682 | Relu | Lacunes confirmées, contestées ou rejetées ; rapport prêt, exporté puis partagé. | Must | Non | Test |
| SI-026 | l.683 | Archivé | État final : rejeu, comparaison, recherche. Plus aucune modification. | Must | Non (la spec ne prévoit pas d'archivage) | Tentative d'écriture refusée |

### 1.3 Reprise après coupure

| ID | Section / ligne | Catégorie | Énoncé précis | Priorité | Dans la spec | Vérifiabilité |
|---|---|---|---|---|---|---|
| SI-030 | 2.6, l.439 | Reprise après coupure | Une coupure d'électricité ou de réseau arrête l'exercice ; il reprend là où il s'était arrêté, à partir du journal. Verbatim : « The drill can resume where it stopped, from the logbook ». | Must (implicite) | Non (la spec ne traite que le rejeu et un « offline mode », l.931) | Test : couper, reprendre, comparer le résultat |
| SI-031 | l.680 | Reprise | État « Interrompu » : quelqu'un reprend ; la reprise repart de la dernière entrée du journal. | Must | Non | Test |
| SI-032 | l.437, l.778 | Panne de l'IA | Si le service IA tombe, bascule sur un cerveau de secours sur le portable, ou rejoue un exercice enregistré. | Must | Partiel (l.957) | Test avec Internet coupé |
| SI-033 | l.428, l.770 | Humain silencieux | Après un délai fixé, l'IA prend le siège ; la bascule est consignée. | Must | Partiel (l.952 : « After a set time », délai non chiffré) | Test ; délai à chiffrer |

### 1.4 Écrans

Le Simple décrit 11 écrans (l.705-721). Détail en section 3 du présent document.

| ID | Section / ligne | Catégorie | Énoncé précis | Priorité | Dans la spec | Vérifiabilité |
|---|---|---|---|---|---|---|
| SI-040 | 2.5, écran 1 | Écrans | Accueil : liste des exercices (brouillon, en cours, terminé, archivé) et des histoires ; ouvrir, créer, rejouer. | Non précisée | Non | Écran |
| SI-041 | écran 2 | Écrans | Mise en place : pays, histoire, langue, vitesse, une ligne par siège (IA ou humain nommé) ; vérifier ; démarrer. | Must | Partiel (page 1 : pays, scénario, mode de jeu, modèle ; pas de siège par siège ni de vitesse) | Écran |
| SI-042 | écran 3 | Écrans | Salle de contrôle : horloge, prochains événements, état de chaque siège, salle de coordination, alertes de lacunes ; pause, reprise, vitesse, surprise, correction, arrêt. | Must (R-09) | Partiel (page 2 : horloge, flux, cartes ; aucune commande) | Écran + actions |
| SI-043 | écran 4 | Écrans | Mon siège : fiche de rôle, boîte (la mienne seulement), mes décisions, formulaire, rechercher, demander, décider. | Should (R-15) | Partiel (page 3 « Agent detail », sans vue joueur) | Test du mur de boîte |
| SI-044 | écran 5 | Écrans | Salle de coordination : tous les messages entre institutions, avec type et heure ; demandes, réponses, objections, alertes. | Must (R-14) | Partiel (dans la page 2) | Écran |
| SI-045 | écran 6 | Écrans | Conseiller juridique : boîte de question, réponse en quatre parties, ouverture d'une source. | Must (R-16) | Oui (page 4) | Test |
| SI-046 | écran 7 | Écrans | Vue publique (voir SI-013). | Non précisée | Non | Écran |
| SI-047 | écran 8 | Écrans | Rapport de lacunes : cartes triées par gravité ; filtres par type, institution et secteur ; ouvrir les sources ; marquer confirmé, contesté ou rejeté ; exporter. | Must (R-18) | Partiel (page 5 : filtres type et institution, pas de secteur ni de statuts) | Écran |
| SI-048 | écran 9 | Écrans | Scorecard : 13 dimensions, score, preuves ; jumeaux côte à côte ; ouvrir les preuves ; exporter. | Must (R-24) | Oui (page 6) | Écran |
| SI-049 | écran 10 | Écrans | Rejeu et contrôle : curseur temporel ; bouton « vérifier le journal » qui répond « intact » ou montre la première entrée modifiée. | Must (R-22, R-23) | Oui (page 7) | Test |
| SI-050 | écran 11 | Écrans | Bibliothèque et carte : ajouter des documents avec leur statut, valider ou corriger les lignes de carte, écrire les histoires. | Must (F-01, F-02) | Non (page 8 « Knowledge explorer » est en v2 et en lecture seule) | Écran |
| SI-051 | 2.5, l.735 | Règle écran | Sélecteur FR/EN en haut de chaque écran. | Must (Q-04) | Oui (l.872) | Écran |
| SI-052 | l.736 | Règle écran | Bandeau « Fictional exercise » visible sur tous les écrans. | Must (Q-08) | Oui (l.873) | Écran |
| SI-053 | l.737 | Règle écran | Une couleur va toujours avec un mot : rouge « gap » ou « not verified », ambre « low confidence », vert « verified ». | Must | Oui (l.874) | Revue |
| SI-054 | l.738 | Règle écran | Lisible sur projecteur (salle de contrôle, vue publique). | Must | Oui (l.875) | Démonstration |
| SI-055 | l.739 | Règle écran | L'écran « Mon siège » fonctionne sur téléphone. | Should | Oui pour le mode humain (l.876) | Test téléphone |
| SI-056 | l.740 ; Q-02 l.389 | Traçabilité | Toute mention juridique est cliquable et ouvre le passage et le document original ; de toute décision ou lacune, le texte original est atteint en deux clics. | Must | Partiel (l.670 : clic sur une citation) | Test à deux clics |
| SI-057 | l.725-731 | Écran « Mon siège » | En haut : identité, horloge, bandeau. Boîte : la plus récente en haut, non lus en gras, heure et expéditeur. Formulaire de 5 champs. Bouton « No legal basis found » toujours visible. Aide. Historique avec vert ou rouge. | Must | Partiel | Écran |

### 1.5 Sièges (agents et humains)

| ID | Section / ligne | Catégorie | Énoncé précis | Priorité | Dans la spec | Vérifiabilité |
|---|---|---|---|---|---|---|
| SI-060 | 2.2 F-06, l.540 | Sièges & outils | Chaque siège a une fiche de rôle, une boîte, une mémoire de ses décisions, et quatre capacités : chercher dans la bibliothèque, demander au conseiller, poster dans la salle, enregistrer une décision. | Must | Oui (l.322-329 ; quatre outils) | Schéma |
| SI-061 | F-06, l.541 | Décision | Chaque décision contient : ce qui est connu, ce qui est inconnu, les options, le choix, la base légale (ou « aucune base juridique trouvée »), le degré de certitude et une explication courte. | Must (R-12) | Oui (l.336-351 ; contient aussi gap_flags et reasoning_summary) | Schéma JSON |
| SI-062 | F-06, l.543-556 | Liste des sièges | Dix lignes. Prototype « Oui » : HydroSense, Météo, Protection civile, Opérateur, Régulateur, Santé, Protection des données, Chef d'exercice (8 au total). « Plus tard » : collectivités, cybersécurité. | Must (prototype) | Partiel (MVP = 6 institutions + HYDRO + LEGAL + COORD, l.304-314 ; collectivités et ANTIC en v2, l.311-312) | Liste |
| SI-063 | R-11, l.361 | Mur des boîtes | Chaque institution a sa propre boîte, sa mémoire, ses pouvoirs et ses documents autorisés ; elle ne voit jamais la boîte d'une autre. | Must | Oui (l.323, l.821) | Test de fuite |
| SI-064 | R-13, l.363 | Pas d'invention | Un siège dit « aucune base juridique trouvée » plutôt que d'inventer une base. | Must | Oui (l.330, l.948) | Test « texte manquant » (l.913) |
| SI-065 | R-15, l.365 | Humain dans le siège | Un humain peut tenir n'importe quel siège, depuis un ordinateur ou un téléphone ; l'IA reprend le siège si l'humain ne répond pas. | Should | Contraire (le mode « humain » est en MVP, l.861 et l.877 ; le plan et Slack le placent plus tard, l.1088, l.1110-1154) | Test |
| SI-066 | F-06, l.541-542 ; l.2.7 | Humain dans le siège | Tout siège peut être tenu par une personne ; en cas de silence trop long, l'IA prend le siège et la bascule est consignée. | Prototype : « if time allows » (l.794) | Partiel | Test |
| SI-067 | 1.7, l.430 | Décision sans base | Une décision sans base est autorisée (comme dans la vraie vie) ; elle est consignée « no legal basis » et comptée comme lacune possible. | Must | Oui (l.375) | Test |
| SI-068 | Golden rule 4, l.752 | Pouvoirs | Un siège ne revendique que les pouvoirs inscrits pour lui dans la carte ; sinon : « acting outside its role », consigné. | Must | Partiel (l.322, l.373 : contrôle par mandat ; pas de mention « hors rôle » consignée) | Test des 5 questions hors rôle (l.911) |
| SI-069 | 1.7, l.434 | Hors rôle | Un opérateur qui déclare un état d'urgence est refusé par les règles de son rôle et la tentative est consignée. | Must | Partiel (l.911 : refus ou redirection, sans consignation) | Test |
| SI-070 | UC-08, l.301 | Fiche de rôle | Le joueur reçoit une fiche courte : qui il est, quels pouvoirs la loi lui donne, qui il peut contacter. | Must | Oui (l.322, l.187) | Revue |
| SI-071 | F-04, l.528 ; 1.7 l.428 | Affectation des sièges | Chaque siège est tenu par l'IA ou par un humain nommé ; les changements au cours de l'exercice sont consignés. | Must | Non (un seul « mode de jeu » global, l.180-181) | Test |

### 1.6 Boîte de réception (inbox) et événements

| ID | Section / ligne | Catégorie | Énoncé précis | Priorité | Dans la spec | Vérifiabilité |
|---|---|---|---|---|---|---|
| SI-080 | F-05, l.534-535 ; R-08 l.357 | Inbox | Un événement est livré à l'heure de l'histoire, et seulement aux destinataires prévus. | Must | Oui (l.188, l.821) | Test de fuite |
| SI-081 | F-05, l.535 | Inbox | Les événements peuvent être retardés, partiels ou faux si l'histoire le dit. | Must | Oui (l.215) | Revue de l'histoire |
| SI-082 | Golden rule 3 ; l.894 | Mur temporel | Un siège ne voit jamais un événement avant son heure de l'histoire, même si le fichier de scénario est complet. | Must | Non | Test |
| SI-083 | l.891 | Inbox | Seul le distributeur d'événements écrit dans les boîtes. | Must (principe) | Oui (l.891) | Revue du code |
| SI-084 | 1.4, l.207-218 | Types d'événements | Huit types : mesures, sorties IA, messages officiels, rapports de terrain, réaction publique, incidents techniques, pression politique ou juridique, informations contradictoires. | Must (mélange) | Partiel (l.188, l.215) | Revue de l'histoire |
| SI-085 | l.218 | Inbox | Un événement ne va qu'aux institutions qui le recevraient dans la vie réelle, parfois en retard et parfois incomplet. | Must | Oui (l.188) | Revue |
| SI-086 | UC-09, l.302 | Inbox | Le joueur ne voit que sa propre boîte. | Must | Oui | Test |

### 1.7 Salle de coordination (board)

Citation verbatim, F-07 l.562 : « for each event, seats first assess, then exchange for at most two rounds, then decide; the drill leader closes the round. »

| ID | Section / ligne | Catégorie | Énoncé précis | Priorité | Dans la spec | Vérifiabilité |
|---|---|---|---|---|---|---|
| SI-090 | F-07, l.561 | Board | Cinq types de messages : Information, Demande, Décision, Objection, Alerte de lacune. | Must | Oui (l.359-367, nommés INFO, REQUEST, DECISION, OBJECTION, GAP_FLAG) | Schéma |
| SI-091 | F-07 l.562 ; l.689 | Rounds | Par événement : évaluation, puis au plus deux tours d'échanges, puis décisions ; le chef d'exercice clôt le tour. | Must | Oui (l.369, l.949, l.787) | Test : aucun tour de plus de 2 |
| SI-092 | UC-10, l.312 | Board | Réponse à une demande : acceptée, refusée (avec motif), ou « pas notre rôle ». | Must (R-14 « answers ») | Partiel (aucun type « réponse » dans le protocole) | Test |
| SI-093 | F-07 l.562 ; UC-10 l.313 | Lacunes automatiques | Demande sans preneur, double revendication, deux décisions contradictoires : une lacune est notée automatiquement. | Must | Oui (l.373-376) | Test |
| SI-094 | l.436 | Board | Une limite d'échanges par événement ; l'animateur clôt le tour. | Must | Oui (l.949) | Test |
| SI-095 | l.429, l.771 | Visibilité du board | Un siège ne voit que sa boîte et la salle partagée. | Must | Partiel (le board n'a pas de règle de visibilité : l.322-323 ne précisent pas qui le voit) | Test |
| SI-096 | R-14, l.364 | Board | Les institutions s'envoient demandes, réponses, objections et alertes de lacunes. | Must | Oui | Test |

### 1.8 Décisions

| ID | Section / ligne | Catégorie | Énoncé précis | Priorité | Dans la spec | Vérifiabilité |
|---|---|---|---|---|---|---|
| SI-100 | Golden rule 1, l.749 | Décisions | Aucune décision sans base : elle cite un texte ou dit « aucune base juridique trouvée ». Deux issues seulement. | Must | Oui (l.330, l.375) | Schéma |
| SI-101 | R-12, l.362 | Décisions | Pour chaque décision : connu, inconnu, options, choix, base légale, degré de certitude. | Must | Oui (l.336-351) | Schéma |
| SI-102 | F-06 l.541 | Décisions | Une explication courte accompagne la décision. | Must | Oui (reasoning_summary) | Revue |
| SI-103 | l.729 | Formulaire | Formulaire de décision de 5 champs : ce que je sais, ce que je ne sais pas, ma décision, ma base juridique, mon degré de certitude. Les options n'y figurent pas (voir D-30). | Must | Partiel | Écran |
| SI-104 | 3.2, l.859 | Décisions | Une décision est publiée au board avec sa base, et une alerte de lacune si elle n'a pas de base. | Must | Oui (l.191) | Test du parcours (3.2) |

### 1.9 Citations (vérification)

| ID | Section / ligne | Catégorie | Énoncé précis | Priorité | Dans la spec | Vérifiabilité |
|---|---|---|---|---|---|---|
| SI-110 | F-09, l.573-574 ; R-20 l.371 | Citations | Chaque article cité est vérifié dans la bibliothèque : le passage existe et contient ce qui est cité. | Must | Oui (l.355) | Test automatique |
| SI-111 | F-09, l.575 | Citations | Un échec est affiché en rouge « non vérifié » ; le siège est invité une seule fois à corriger ; le résultat est consigné dans tous les cas (« the result is recorded either way »). | Must | Contraire (l.355 : refus d'acceptation ; l.947 : décision « not recorded ») | Test |
| SI-112 | l.433 | Citations | Un article qui n'existe pas : rouge, correction demandée une fois. | Must | Oui (l.355) | Test |
| SI-113 | T2, l.456 | Citations | 95 % ou plus des citations passent le contrôle. | Must | Oui (T2, l.888) | Mesure |
| SI-114 | R-20 | Citations | Toute citation introuvable est signalée. | Must | Oui | Test |

### 1.10 Conseiller juridique

| ID | Section / ligne | Catégorie | Énoncé précis | Priorité | Dans la spec | Vérifiabilité |
|---|---|---|---|---|---|---|
| SI-120 | R-16 l.366 ; F-08 l.566-568 | Conseiller juridique | Accessible à tout siège, à l'animateur et aux observateurs ; réponse en quatre parties : (1) textes nationaux avec articles, (2) ce qui est flou ou absent, (3) au moins deux autres pays, (4) suggestion marquée comme telle. | Must | Oui (l.378-380) | Test |
| SI-121 | F-08, l.569 | Conseiller juridique | Le conseiller est le seul à chercher dans toute la bibliothèque. | Must | Oui (l.380) | Test |
| SI-122 | UC-11, l.319 | Conseiller juridique | Chaque réponse finit par « for practice only; confirm with a lawyer ». | Must | Partiel (formule différente, l.380) | Présence |
| SI-123 | UC-11, l.317 | Conseiller juridique | La question se pose en langage courant. | Must | Oui | Test |

### 1.11 Lacunes et statuts

Citation verbatim, l.670 : « Only confirmed gaps carry full weight in the report; disputed gaps stay visible with the reason, and rejected gaps are kept in the logbook but left out of the summary. »

| ID | Section / ligne | Catégorie | Énoncé précis | Priorité | Dans la spec | Vérifiabilité |
|---|---|---|---|---|---|---|
| SI-130 | R-17, l.368 | Lacunes | Les lacunes sont détectées par règles claires, en comparant les besoins de l'histoire et les décisions à la carte. | Must | Oui (l.549-551) | Test sur graphe fictif |
| SI-131 | F-10, l.580 | Lacunes | Une lacune n'est retenue que si : une règle se déclenche sur la carte, ou un siège a dit « aucune base », ou une demande est restée sans réponse ou un conflit a été vu. | Must | Oui (l.568) | Test |
| SI-132 | F-10, l.581 | Lacunes | Chaque lacune porte : type, gravité 1-3 (1 = gêne, 2 = retard ou coût, 3 = risque pour la vie ou les droits), confiance, moment, textes contrôlés, preuves. | Must | Oui (l.570-572, l.584-597) | Test |
| SI-133 | R-18, l.369 | Lacunes | Chaque lacune a une gravité et un niveau de confiance. | Must | Oui | Test |
| SI-134 | F-10, l.583-594 | Règles | Dix règles G1 à G10 : personne en charge, deux en charge, pas de procédure, pièce manquante, objectifs en conflit, personne ne répond du préjudice, personnes laissées de côté, IA non contrôlée, canal non protégé, transfrontalier. | Must | Oui (l.553-564 ; intitulés proches) | Test sur petit graphe (l.910) |
| SI-135 | l.698 | Statut | Statut « suspectée » : une règle s'est déclenchée, ou un siège n'a pas de base, ou une demande est sans réponse. | Must | Partiel (seulement « suspected, needs expert check » comme confiance, l.572) | Test d'état |
| SI-136 | l.699 | Statut | « Confirmée par texte » : l'absence, le chevauchement ou le conflit est vérifié dans les textes. | Must | Partiel (étiquette de confiance, l.572) | Test d'état |
| SI-137 | l.700 | Statut | « Revue par un expert » : un avocat ou un expert de terrain examine la lacune et ses preuves. | Should (écran « expert review » en v2 selon l.798) | Non | Test d'état |
| SI-138 | l.701 | Statut | « Confirmée » : acceptée comme réelle ; entre dans le rapport avec ses exemples mondiaux. | Must | Non | Test d'état |
| SI-139 | l.702 | Statut | « Contestée » : l'expert n'est pas d'accord ou doute ; reste dans le rapport avec sa raison. | Must | Non | Test d'état |
| SI-140 | l.703 | Statut | « Rejetée » : pas une vraie lacune (par exemple un texte oublié) ; conservée au journal, exclue du résumé. | Must | Non | Test d'état |
| SI-141 | l.670 ; 1.7 l.432 | Statuts | Seules les lacunes confirmées pèsent pleinement dans le rapport ; une lacune contestée reste visible avec sa raison ; rien n'est supprimé. | Must | Non | Revue du rapport |
| SI-142 | 1.7, l.432 ; UC-19 l.249 | Expert | Un expert peut confirmer ou rejeter une lacune. Cette exigence n'a pas de code R-xx : elle n'existe que dans UC-19. | Must (UC-19 ; écran en v2) | Non (la spec ne traite l'expert que par des tests, l.915) | Test d'état |
| SI-143 | 1.7, l.440 ; l.955 | Lacunes | Une même lacune qui revient plusieurs fois est fusionnée, et toutes ses preuves sont gardées. | Must | Oui (l.955) | Test |
| SI-144 | Golden rule 7, l.755 | Lacunes | Une lacune repose sur une règle qui se déclenche ou sur un fait consigné, jamais sur une opinion. | Must | Oui (l.574) | Revue |
| SI-145 | Q-01, l.388 ; T4 l.458 | Lacunes | Une lacune n'est jamais présentée comme un fait sans source ; ce qui est supposé est marqué. | Must | Oui (T4, l.890) | Relecture (85 %) |
| SI-146 | UC-14, l.323-325 | Rapport de lacunes | Lacunes triées de la plus grave à la moins grave. Chaque lacune montre : ce qui s'est passé, le moment, les textes contrôlés, ce qui manque, comment d'autres pays font, le degré de certitude, les preuves. Filtres par type, institution et secteur. Toute source ouverte. | Must | Partiel (pas de filtre secteur ; champs de la carte présents l.586-597) | Écran |
| SI-147 | UC-19, l.249 | Lacunes | Un expert confirme ou rejette une lacune (voir SI-142). | Must | Non | Test |

### 1.12 Précédents (exemples mondiaux)

| ID | Section / ligne | Catégorie | Énoncé précis | Priorité | Dans la spec | Vérifiabilité |
|---|---|---|---|---|---|---|
| SI-150 | R-19, l.370 | Précédents | Au moins deux exemples de pays ou organisations différents, avec sources, pour chaque lacune. | Must | Oui (l.578, l.615-629) | Comptage |
| SI-151 | F-11, l.599-601 | Précédents | Préférer les lois contraignantes aux directives ; contexte proche du Cameroun à pertinence égale ; jamais deux exemples du même pays pour une lacune ; si moins de deux exemples valables existent, le dire. | Must | Oui (l.617-629) | Test |
| SI-152 | F-11, l.600 | Précédents | Chaque exemple donne : pays, texte, article, ce qu'il fait, ce qu'il faudrait changer pour le Cameroun. | Must | Oui (l.595-596, l.621) | Schéma |
| SI-153 | Golden rule 8, l.756 | Précédents | Chaque lacune reçoit au moins deux exemples, ou la raison écrite de leur absence. | Must | Oui (l.628-629) | Comptage |
| SI-154 | F-11 prototype, l.799 | Précédents | Exemples préparés pour les lacunes de l'histoire, avec recherche automatique. | Must (prototype) | Oui (l.600-613) | Revue |
| SI-155 | F-11, l.804 | Précédents | Bibliothèque mondiale élargie. | Later | Partiel | Revue |

### 1.13 Journal (ledger) et rejeu

Citation verbatim, l.615 : « Records: every event delivered, every search, every AI question and answer, every message, every decision, every quote check, every gap, every facilitator and human action, every error. »

| ID | Section / ligne | Catégorie | Énoncé précis | Priorité | Dans la spec | Vérifiabilité |
|---|---|---|---|---|---|---|
| SI-160 | R-21, l.373 | Journal | Chaque événement, recherche, réponse de l'IA, message et décision est consigné, dans l'ordre. | Must | Oui (l.641-649) | Comptage |
| SI-161 | F-14, l.615 | Journal | Consigne aussi chaque vérification de citation, chaque lacune, chaque action de l'animateur ou d'un humain, chaque erreur. | Must | Partiel (pas de type « animateur », « bascule de siège » ni « correction ») | Revue des types |
| SI-162 | F-14, l.616 ; R-22 l.374 | Journal | Chaque entrée porte une empreinte liée à la précédente ; toute modification casse la chaîne. | Must | Oui (SHA-256, l.653) | Test |
| SI-163 | R-22 ; UC-17 l.247 | Journal | Bouton « vérifier » : « intact », ou première entrée modifiée. | Must | Oui (`verify_log.py`, l.653 ; écran 7) | Test |
| SI-164 | R-23, l.375 | Rejeu | Rejouer un exercice passé sans rappeler l'IA. | Must | Oui (l.672-674) | Test (couper l'accès au modèle) |
| SI-165 | UC-16, l.329 | Rejeu | Un curseur temporel montre ce que chaque institution savait et a fait à un instant donné. | Must | Oui (écran 7) | Test |
| SI-166 | l.659 | Corrections | « Nothing is ever deleted during or after a drill; corrections are new entries that point to what they correct. » | Must | Non (la spec est « append-only » mais ne traite pas la correction) | Test |
| SI-167 | l.431 ; l.528 | Corrections | Erreur de l'animateur (mauvais événement, mauvais siège) : pause et correction ; la correction est écrite au journal, jamais cachée. Chaque action de l'animateur est consignée. | Must | Non | Test |
| SI-168 | Golden rule 6, l.754 | Corrections | Rien n'est effacé ; les corrections s'ajoutent, elles ne remplacent pas. | Must | Partiel | Revue |
| SI-169 | l.651 | Journal | Champs d'une entrée : numéro d'ordre, heure réelle, heure de l'histoire, nature, auteur, contenu, empreinte, empreinte précédente. | Must | Oui (l.656 : seq, real_time, sim_time, type, actor, payload, prev_hash, hash) | Schéma |
| SI-170 | l.874 | Journal | Personne ne modifie le journal ; on n'y ajoute que des entrées. | Must | Oui (l.635-637) | Test |

### 1.14 Rapports, exports, scorecard

| ID | Section / ligne | Catégorie | Énoncé précis | Priorité | Dans la spec | Vérifiabilité |
|---|---|---|---|---|---|---|
| SI-180 | R-24, l.376 | Rapports | Produire un rapport de lacunes, une chronologie des décisions et une scorecard sur 13 dimensions. | Must | Oui (l.200-204) | Revue |
| SI-181 | R-25, l.377 | Exports | Exporter en « document » et en PDF. | Should | Contraire (« PDF or Markdown », l.206 ; « Markdown and PDF », l.679 et l.865) | Test d'export |
| SI-182 | F-13, l.610 | Rapports | Contenu : rapport de lacunes, chronologie, scorecard, liste des hypothèses, résumé pour décideurs ; en français et en anglais. | Must (proto : rapport, chronologie, hypothèses) | Partiel (pas de résumé pour décideurs) | Revue |
| SI-183 | F-13, l.801 | Exports | Prototype : rapport à l'écran et « as a document » ; PDF et résumé pour décideurs si le temps le permet. | Must / Should | Partiel | Revue |
| SI-184 | F-13, l.611 ; R-26 l.379 | Comparaison | Comparer deux pays sur la même histoire (jumeaux). | Must (jumeaux) | Oui (page 6 : côte à côte, l.866) | Test |
| SI-185 | R-27, l.380 | Comparaison | Comparer avant et après un changement de loi. | Later | Non | — |
| SI-186 | R-28, l.381 | Comparaison | Construire un exercice à partir d'une chronologie réelle passée. | Later | Non | — |
| SI-187 | R-29, l.382 ; UC-24 | Comparaison | Construire un exercice à partir d'un système IA décrit (test avant achat). | Later | Non | — |
| SI-188 | UC-20, l.250 | Partage | Exporter et partager le rapport. | Must | Partiel | Test |
| SI-189 | 2.3, l.875 | Archive | Archive des rapports : l'animateur ajoute, personne ne supprime. | Must | Non | Test |
| SI-190 | 1.7, l.441 | Sensibilité | Un constat sensible est formulé de façon neutre, sur les règles et les institutions, jamais sur les personnes ; présenté comme une occasion d'améliorer. | Must | Oui (l.934) | Relecture |
| SI-191 | F-12, l.603-606 | Scorecard | Chacune des 13 dimensions reçoit une note de 0 à 5 avec les preuves de l'exercice. | Must | Oui (l.204, l.727) | Test |
| SI-192 | F-12, l.606 | Scorecard | La note décrit ce que l'exercice a révélé, pas une notation officielle du pays. | Must | Oui (l.727) | Revue |
| SI-193 | l.928-942 | Scorecard | Les 13 dimensions portent les libellés du Simple (dimension 8 « Working with AI », etc.). | Must | Oui (libellés légèrement différents, voir D-43) | Revue |
| SI-194 | l.944 | Scorecard | Les 8 perspectives du hackathon sont chacune couvertes par au moins une dimension et au moins un type de lacune. | Must | Oui (l.745 ; la couverture par type de lacune n'est pas vérifiable dans la spec) | Revue |
| SI-195 | l.719 | Scorecard | La scorecard est vue de tous après l'exercice. | Non précisée | Non | — |

### 1.15 Humain dans le siège, Slack et canaux

| ID | Section / ligne | Catégorie | Énoncé précis | Priorité | Dans la spec | Vérifiabilité |
|---|---|---|---|---|---|---|
| SI-200 | l.969, l.1000 | Slack | Une « porte messagerie » (par exemple Slack) est une nouvelle façon de recevoir les événements et d'envoyer les décisions. Elle respecte le mur des boîtes et est consignée au journal. | Later | Oui en v2 (l.706, l.1088-1098) ; mais l.181 présente Slack comme un mode de jeu sans étiquette v2 (D-40) | Test |
| SI-201 | l.969 | Ajout de canal | Ajouter une porte ne change que les portes, pas les blocs. | Must (principe 7) | Oui (principe 7) | Revue |

### 1.16 Bibliothèque : documents et statuts

| ID | Section / ligne | Catégorie | Énoncé précis | Priorité | Dans la spec | Vérifiabilité |
|---|---|---|---|---|---|---|
| SI-210 | F-01, l.502 | Statuts de documents | Un document porte : titre, numéro, date, pays, type (loi, décret, plan, stratégie, rapport, actualité), langue, lien, fiabilité, statut (en vigueur ou remplacé). | Must | Partiel (pas de date ni de statut en vigueur ou remplacé, l.473-485 et l.392) | Schéma |
| SI-211 | R-02, l.349 | Passages | Pour chaque passage : document, article, langue, date, lien. | Must | Partiel (la date du document est absente des métadonnées, l.473-485) | Schéma |
| SI-212 | R-03, l.350 ; l.262 | Fiabilité | Fiabilité : texte officiel, résumé fiable, ou non trouvé. | Must | Partiel (statuts « Link OK », « Summary only », « To obtain », « Found in search », l.392 ; « Link OK » ne prouve pas que le texte a été lu) | Revue |
| SI-213 | l.267 | Documents | Document illisible : marqué « illisible », non utilisé. Document absent : « non trouvé », lacune possible. | Must | Non (pas d'état « illisible » ; OCR seulement, l.501) | Test |
| SI-214 | l.425 | Documents remplacés | Un texte remplacé reste pour l'historique, marqué « remplacé par… », et n'est jamais la règle en vigueur. | Must | Non | Test |
| SI-215 | l.424 | Conflits entre textes | Deux textes contradictoires : les deux sont montrés ; on dit lequel est plus récent ou de rang supérieur ; une lacune possible est notée. | Must | Partiel (pondération lois > actualités, l.478) | Test |
| SI-216 | l.426 | Langues | Si les versions française et anglaise diffèrent, la version officielle fait référence et la différence est notée. | Must | Non | Revue |
| SI-217 | l.422 | Résumés | Un texte connu seulement par un résumé : toute réponse qui s'appuie dessus est étiquetée « d'après un résumé ». | Must | Partiel (statut « Summary only » ; étiquette sur les réponses non précisée) | Test |
| SI-218 | l.423 | Absence | Texte absent : « aucun texte trouvé » ; on ne comble jamais le trou ; c'est une lacune possible. | Must | Partiel (l.926 : « treat absence as a finding ») | Test (l.913) |
| SI-219 | UC-01, l.263-264 ; F-01 l.504 | Passages | Un passage par article quand c'est possible. Chaque passage porte ses institutions et ses sujets. Un siège ne cherche que dans les documents de son institution. Les documents périmés restent, marqués « remplacé ». | Must | Oui (l.497-505, l.481) | Test |
| SI-220 | UC-01, l.261-265 | Gardien | Le gardien liste les documents (titre, date, lien, langue), leur type et leur fiabilité ; ALERTE découpe, propose les tags ; le gardien vérifie les plus importants. | Must | Partiel (la spec demande une vérification de tous les documents Must, l.503 et l.545) | Revue |
| SI-221 | UC-01, l.265 | Qualité | Un jeu de questions tests confirme que les bons passages reviennent. | Must | Oui (T1, l.887) | Mesure |
| SI-222 | F-01, l.505 | Collections | Collections : Cameroun, Émirats arabes unis, mondial (UE, Philippines, États-Unis, Japon, Maurice, Union africaine, etc.), normes UIT, matériel fictif marqué fictif. | Must | Oui (l.463-469, l.407-461) | Revue |
| SI-223 | R-01, l.348 | Bibliothèque | Au moins le Cameroun et les Émirats arabes unis, plus des exemples d'autres pays. | Must | Oui | Revue |
| SI-224 | R-04, l.351 | Recherche | Trouver les bons passages à partir d'une question en français ou en anglais (arabe plus tard). | Must | Oui (l.504, multilingue) | Test T1 |
| SI-225 | l.273-277 ; R-05 l.353 | Carte | Chaque ligne : institution, peut ou doit, action, article, procédure, degré de certitude. Elle est écrite dans un texte, déduite d'un texte, ou supposée (par qui, quand). | Must | Oui (l.515-540, tags l.487-493) | Schéma |
| SI-226 | R-06, l.354 | Carte | Un expert accepte, corrige ou rejette chaque ligne de la carte. | Must | Partiel (l.545 : l'analyste vérifie chaque ligne ; pas de « rejet » ni de « correction » formalisés) | Test d'état |
| SI-227 | F-02, l.513 | Carte | Aucune ligne n'est supprimée ; elle est remplacée, avec une raison. | Must | Non | Test |
| SI-228 | F-02, l.510-512 | Carte | Pour une action donnée, on obtient la liste des institutions qui peuvent ou doivent la faire, et ce dont elles dépendent. | Must | Oui (graphe, l.517-526) | Test |
| SI-229 | Q-09, l.396 | Ouverture | Le corpus du Cameroun et sa carte peuvent être partagés avec l'UIT comme ressource ouverte. | Must (Q) | Partiel (R10 : « published under the repo's MIT licence », l.117) | Revue juridique |
| SI-230 | l.903 ; l.941 | Licences | Les documents dont la licence est floue sont gardés en référence avec leur lien, sans être copiés dans les exports partagés. | Must | Oui (l.509) | Revue |

### 1.17 Tests et qualité

Citation verbatim, l.451 : « How we will know ALERTE works ».

| ID | Section / ligne | Catégorie | Énoncé précis | Priorité | Dans la spec | Vérifiabilité |
|---|---|---|---|---|---|---|
| SI-240 | l.455 (T1) | Tests | 40 questions à réponse connue ; le bon article figure parmi les 5 premiers résultats ; cible 8 sur 10 ou plus. | Must | Oui (T1 : 80 %, l.887 ; « top 5 ») | Mesure |
| SI-241 | l.457 (T3) | Tests | Au moins 80 % des lacunes que l'histoire est censée révéler apparaissent dans le rapport. | Must | Oui (T3, l.889) | Mesure |
| SI-242 | l.458 (T4) | Tests | Au moins 85 % des lacunes sont jugées réelles ou en partie réelles par un membre de l'équipe et un expert extérieur. | Must | Oui (T4, l.890 : un seul relecteur, pas deux) | Mesure |
| SI-243 | l.459 (T5) | Tests | Même exercice trois fois ; 80 % des lacunes apparaissent dans au moins deux exécutions. | Must | Oui (T5, l.891) | Mesure |
| SI-244 | l.460 (T6) | Tests | Un exercice complet en automatique dure moins de 20 minutes. | Must (Q-06) | Partiel (spec : « under 20 minutes, under 200 calls », l.892) | Chronométrage |
| SI-245 | l.461 | Tests | Deux personnes extérieures à l'équipe lisent un rapport de lacunes et l'expliquent correctement. | Non précisée | Non (absent de T1-T6) | Test d'usage |
| SI-246 | l.462 | Tests | La plupart des lacunes de l'étude IFRC liées à notre histoire sont aussi trouvées. | Must | Partiel (l.894 : « how many », sans seuil) | Comparaison |
| SI-247 | Q-07, l.394 | Répétabilité | Trois exécutions du même exercice donnent surtout les mêmes lacunes. | Must | Oui (T5) | Mesure |
| SI-248 | Q-05, l.392 | Hors ligne | Un exercice complet tourne sur un seul portable sans Internet ; des réponses plus lentes ou plus simples sont acceptées. | Must | Oui (l.914 ; l.782-785) | Test |
| SI-249 | Q-06, l.393 | Rapidité | Un exercice complet de Rising Waters en automatique finit en moins de 20 minutes. | Must | Oui (T6) | Chronométrage |
| SI-250 | Q-01, l.388 | Qualité | Honnête : jamais une supposition présentée comme un fait. | Must | Oui (l.935) | Revue |
| SI-251 | Q-02, l.389 | Qualité | Traçable : deux clics suffisent pour aller d'une décision ou d'une lacune au texte original. | Must | Partiel (l.670) | Test |
| SI-252 | Q-03, l.390 | Qualité | Compréhensible : un non-spécialiste comprend chaque écran et chaque rapport sans formation. | Must | Non (aucun test d'usage hors T) | Test d'usage (deux personnes, l.461) |
| SI-253 | l.913 | Tests | Texte manquant : les agents disent « no legal basis found » au lieu d'inventer. | Must | Oui (l.913) | Test |
| SI-254 | l.912 ; l.956 | Tests | Instructions cachées dans un document : ignorées ; les documents sont des données, jamais des ordres. | Must | Oui (l.912, l.956) | Test |
| SI-255 | l.910 (spec) ; absent du Simple | Tests unitaires | Tests unitaires : règles de lacunes, chaîne d'empreintes, vérification des citations, chargement du scénario. | Must (implicite) | Oui (spec) / Non (Simple) | `pytest` |
| SI-256 | l.1.7 | Tests | Une règle de rôle : cinq questions hors rôle à chaque agent ; il refuse ou redirige. | Must | Oui (l.911) | Test |
| SI-257 | Q-04, l.391 | Langues | Chaque écran et chaque rapport en français et en anglais ; arabe pour le jumeau des Émirats arabes unis plus tard. | Must | Partiel (l.872 ; arabe prévu pour les documents, l.504 et l.761) | Revue |

### 1.18 Architecture, principes, déploiement

| ID | Section / ligne | Catégorie | Énoncé précis | Priorité | Dans la spec | Vérifiabilité |
|---|---|---|---|---|---|---|
| SI-260 | 3.5, l.952-957 | Déploiement | Quatre contextes : un portable hors ligne ; une salle avec un serveur (10 joueurs sur téléphones) ; en ligne (Yaoundé, Douala, Maroua en même temps) ; multi-pays (sommet 2027). | Must (Q-05, R-26) | Partiel (Streamlit local ; pas d'accès distant, pas d'authentification) | Test sur 4 contextes |
| SI-261 | 3.5, l.999 | Déploiement | Le choix d'hébergement reste à faire : il doit couvrir les 4 contextes, y compris hors ligne. | Must | Non (aucune décision d'hébergement) | Décision écrite |
| SI-262 | Q-10, l.397 | Extensibilité | Ajouter un pays, une histoire, une langue ou une institution ne demande pas de refondre le système. | Must | Oui (l.948-970) | Test (ajout d'un pays) |
| SI-263 | Q-11, l.398 ; principe 2, l.819 | Fournisseur d'IA | Une seule porte vers l'IA ; le fournisseur se change sans toucher au reste ; chaque appel est consigné. | Must | Oui (`llm.py`, l.704, l.852) | Test |
| SI-264 | principe 6, l.823 | Hors ligne | Chaque bloc fonctionne sur un portable, avec un cerveau de secours. | Must | Oui (l.782-787) | Test |
| SI-265 | principe 7, l.824 | Remplaçabilité | Un bloc se remplace sans toucher aux autres, à condition d'avoir les mêmes entrées et sorties. | Must | Partiel | Revue |
| SI-266 | principe 8, l.825 ; l.899-903 | Fiction | Aucun bloc n'accepte de donnée personnelle réelle ; chaque sortie (écran, rapport, export) porte la mention « Fictional exercise ». | Must | Oui (l.680, l.873) | Test |
| SI-267 | principe 5, l.822 | Règle avant IA | Quand une règle peut décider (lacunes, citations, livraison), c'est une règle qui décide ; l'IA sert au jugement et à la langue. | Must | Oui (l.719) | Revue |
| SI-268 | principe 3, l.820 | Journal | Aucun bloc n'agit sans laisser d'entrée au journal. | Must | Partiel | Revue |
| SI-269 | 3.1, l.833-841 | Blocs | Sept blocs : portes, gestion de l'exercice, institutions virtuelles, analyse, connaissances, porte IA, journal. | Must (architecture) | Partiel (13 modules, l.692-705, avec correspondance non 1 pour 1 ; aucun module « contrôle de l'horloge ») | Revue |
| SI-270 | principe 1, l.818 | Séparation | Les connaissances sont séparées du moteur de l'exercice : un nouveau pays est une nouvelle connaissance, pas un nouveau logiciel. | Must | Oui | Revue |

### 1.19 Scénarios, histoires, règles de l'histoire

| ID | Section / ligne | Catégorie | Énoncé précis | Priorité | Dans la spec | Vérifiabilité |
|---|---|---|---|---|---|---|
| SI-275 | 1.4, l.155 | Histoires | Un exercice combine un aléa, des secteurs et une façon dont l'IA échoue ; au moins six types de défaillance par histoire. | Must | Oui (l.210, l.275) | Checklist |
| SI-276 | 1.4, l.157-169 | Histoire principale | « Rising Waters » : trois actes (Douala, Logone, déplacés). Jumeau des Émirats arabes unis : mêmes trois actes, même défaillance. | Must (prototype) | Oui (l.220-256) ; durée de l'acte 2 contredite (D-02) | Revue |
| SI-277 | 1.4, l.171-184 | Autres histoires | Familles : crues, IA en santé, glissements de terrain, épidémies, sécheresse, canicule, volcan ou gaz, cyclones, panne de réseau. | Later | Partiel (seulement HC-01, l.269) | — |
| SI-278 | 1.4, l.190-203 | Défaillances | Douze types : fausse alerte, danger manqué, mauvaise donnée, mauvaise zone, mauvaise langue, exclusion, contenu inventé, usurpation, confiance aveugle, atteinte à la vie privée, données envoyées à l'étranger, dégradation dans le temps. | Must | Oui (l.275-290 ; douze types) | Checklist |
| SI-279 | F-03, l.519-521 | Écrire une histoire | Une histoire contient : aléa, lieux, secteurs, description de l'IA fictive, liste d'événements (heure, destinataires, texte, lacunes attendues, type de défaillance). Elle est marquée fictive ; chaque événement a au moins un destinataire ; les branches sont facultatives. | Must | Oui (l.212-218, l.250-253) | Revue |
| SI-280 | F-03, l.520 | Checklist | Une checklist vérifie qu'une histoire couvre au moins six types de défaillance et chaque lacune prévue. | Must | Partiel (T3 seulement) | Test |
| SI-281 | R-10, l.359 | Écrire une histoire | Écrire une nouvelle histoire sans changer le système. | Should | Oui (fichiers de scénario, l.789-810 et l.817) | Test |
| SI-282 | UC-03, l.284-288 | Rédacteur | Le rédacteur choisit aléa, lieu, secteurs et au moins six défaillances ; il ordonne les événements avec leur heure de l'histoire ; il note les lacunes attendues. | Must | Oui (l.212-218) | Revue |
| SI-283 | R-07, l.356 | Déroulement | Les événements arrivent un par un, à des heures fixées de l'histoire. | Must | Oui (l.187-188) | Test |
| SI-284 | 1.7, l.427 | Contradictions | Deux événements qui se contredisent sont normaux : les institutions le remarquent et disent laquelle elles croient. | Must | Oui (l.953) | Test |
| SI-285 | UC-12, l.241 ; R-09 | Surprise | L'animateur ajoute un événement surprise pendant l'exercice (S1, S5). | Should | Non | Test |
| SI-286 | R-09, l.358 ; F-04 l.527 | Commandes | L'animateur démarre, met en pause, reprend, accélère, ralentit, arrête, corrige. | Must (surprise : Should) | Partiel (démarrer seulement) | Test |
| SI-287 | UC-04, l.294 | Vitesse | Exemple : une journée d'histoire en 15 minutes. | Must (exemple) | Oui (10 à 20 minutes, l.218) | Chronométrage |
| SI-288 | UC-05, l.233 | Invitations | Inviter les joueurs et leur attribuer les sièges (S1, S5, S8). | Must | Non | Test |
| SI-289 | UC-07, l.236 | Pilote automatique | Tous les institutions tenues par l'IA (S2, S4, S7, S10). | Must | Oui (l.180) | Test |
| SI-290 | UC-08, l.237 | Joueur humain | Un joueur tient un siège d'institution. | Should (R-15) | Partiel (voir SI-065) | Test |
| SI-291 | Golden rule 9, l.757 ; l.435 | Documents | Les documents informent, ils ne commandent jamais. Un texte caché (« ignore tes règles ») est traité comme de l'information. | Must | Oui (l.912, l.956) | Test |
| SI-292 | l.436 | Échanges sans fin | Une limite d'échanges par événement ; l'animateur clôt le tour. | Must | Oui (l.949) | Test |
| SI-293 | l.437 | Panne de l'IA | Service lent ou en panne : cerveau de secours ou rejeu. | Must | Oui (l.957) | Test |
| SI-294 | l.438 | Stabilité | Des réponses différentes d'une exécution à l'autre sont attendues dans une certaine mesure ; on mesure la stabilité des lacunes. | Must | Oui (T5) | Mesure |
| SI-295 | Golden rule 10, l.758 | Fiction | Les histoires sont fictives, aucune donnée personnelle réelle, aucun individu nommé ni jugé. | Must | Oui (l.214, l.959-966) | Revue |
| SI-296 | Golden rules 1-10, l.747-758 | Règles d'or | Dix règles d'or s'appliquent à toutes les fonctions ; toute modification qui en enfreint une est refusée. | Must | Partiel (ces règles n'existent pas sous cette forme dans la spec) | Revue |

---

## 2. Exigences ajoutées par le Simple et absentes ou faibles dans la spec

Ce sont les points à reprendre dans la spec, avec la citation exacte.

| # | Exigence | Citation verbatim (Simple) | Ligne |
|---|---|---|---|
| E1 | Machine d'états de l'exercice (huit états, latéraux pause et interruption) | « Interrupted | The drill stopped by accident (power or network cut) | Someone resumes it; it restarts from the last logbook entry » | l.680 |
| E2 | Reprise après coupure depuis le journal | « A power or network cut stops a drill | The drill can resume where it stopped, from the logbook » | l.439 |
| E3 | Observateur et vue publique | « Observer (a minister, a hackathon judge, a journalist invited to watch) | Follow what is happening without touching anything » ; « Public view | Observers, audience | … no private inbox | Watch only » | l.96, l.717 |
| E4 | Statuts de lacunes : suspectée, confirmée, contestée, rejetée | « Disputed | The expert disagrees or is unsure; stays in the report with their reason » ; « Rejected | Not a real gap (for example, a text we had missed); kept in the logbook, left out of the summary » | l.702-703 |
| E5 | Correction par nouvelles entrées | « Nothing is ever deleted during or after a drill; corrections are new entries that point to what they correct. » | l.659 |
| E6 | Textes remplacés | « A text is outdated or replaced | Keep it for history, mark it "replaced by…", and never use it as the current rule » | l.425 |
| E7 | Pause, vitesse, surprise, correction | « Let the facilitator start, pause, resume, speed up, stop, and add a surprise event » (R-09, Must ; surprise : Should) | l.358 |
| E8 | Affectation des sièges qui peut changer | « Seat assignment | Which institution, held by AI or by which human, switches over time » | l.645 |
| E9 | Matrice de droits par rôle | « Who can see and do what » (tableau complet des rôles et magasins) | l.879-887 |
| E10 | Contrôle de préparation avant démarrage | « ALERTE checks that every needed piece exists (library, map, story, seats) and warns if something is missing. » | l.297 |
| E11 | Invitation des joueurs et choix de ce que voient les observateurs | « They choose what observers may see (everything, or only the public parts). » | l.296 |
| E12 | Rejet ou correction de chaque ligne de carte | « Let a human expert accept, correct or reject each line of that map » | l.354 |
| E13 | Conflits entre textes et versions linguistiques | « Two texts contradict each other | Show both, say which is more recent or higher in rank, and note a possible gap » ; « The French and English versions differ | Treat the official language version as the reference » | l.424, l.426 |
| E14 | Usage hors crise réelle, affiché à l'écran | « To decide during a real crisis. ALERTE plays fictional stories and its answers are for practice. … ALERTE says this on every screen. » | l.148 |
| E15 | Réponse « acceptée / refusée / pas notre rôle » | « The receiving institution answers: accepted, refused (with reason), or "not our role". » | l.312 |
| E16 | Décision sans base : deux issues seulement, rien de caché | « No decision without a basis. … There is no third option. » | l.749 |
| E17 | Échec de citation : toujours consigné | « The result is recorded either way. » | l.575 |
| E18 | Choix d'hébergement pour les quatre contextes | « Where it is hosted | Must support all four settings, including fully offline » | l.999 |
| E19 | Date du document et statut « en vigueur ou remplacé » | « Document | Title, number, date, country, type (law, decree, plan…), language, link, reliability, status (current or replaced) » | l.631 |

---

## 3. Récits, user journeys et personas

### 3.1 Personas (1.2, l.115-120)

- **Aminatou**, 34 ans, officière de la protection civile à Maroua. A vécu les crues de 2024. Veut savoir, avant la prochaine saison des pluies, qui validera une alerte si la nouvelle IA dit « rouge ». Utilise ALERTE comme joueuse, depuis son téléphone (l.117). Non couvert par le prototype (voir D-11).
- **M. Ndi**, 52 ans, conseiller juridique dans un ministère. Doit rédiger un décret sur les alertes publiques. Utilise le rapport de lacunes et les exemples mondiaux pour une première ébauche (l.118).
- **Sara**, 41 ans, formatrice à l'UIT. Anime un atelier avec des fonctionnaires de trois pays ; la même histoire est jouée pour chaque pays (l.119).
- **Un juge du hackathon à Dubaï**. Dispose de dix minutes. Regarde l'exercice, clique sur une décision, vérifie sa source et contrôle le journal (l.120).

### 3.2 Parcours d'usage (UC et section 3.2)

- **Joueur (UC-08, UC-09, l.299-307)** : reçoit une fiche courte, voit les événements arriver dans sa boîte, écrit ce qu'il sait et ignore, décide, cite son texte ou dit « aucune base juridique trouvée », cherche, demande à une autre institution ou au conseiller. Si personne ne répond à temps, l'IA reprend le siège.
- **Demande entre institutions (UC-10, l.309-313)** : la protection civile demande à un opérateur d'envoyer un message à tous les téléphones de Douala. Réponse : acceptée, refusée ou « pas notre rôle ». Si personne n'accepte, lacune.
- **Question au conseiller (UC-11, l.315-319)** : question en langage courant, réponse en quatre parties, phrase finale de précaution.
- **Lecture du rapport (UC-14, l.321-325)** : lacunes de la plus grave à la moins grave ; chacune avec ses preuves ; sources ouvertes.
- **Audit (UC-16 et UC-17, l.327-330)** : l'auditeur ouvre un exercice passé, déplace un curseur temporel, lance « vérifier le journal » : « intact » ou première entrée modifiée.
- **Acheteur (UC-24, l.332-337)** : décrit un système d'IA, ALERTE construit une histoire à partir de ses défaillances probables, rapport avec des conditions d'achat (non prototype).
- **Parcours d'un événement (3.2, l.845-862)** : le 1er jour à 07:10, la protection civile demande à l'opérateur d'envoyer un SMS à tous les numéros de Douala. Huit étapes : livraison, recherche (mur documentaire), passages, réflexion (une seule porte vers l'IA), proposition en forme fixe, vérification des citations, décision et alerte de lacune, lacune G1 suspectée.

### 3.3 Récits d'histoire (1.4, l.157-169)

- **Acte 1, Douala** : HydroSense annonce une grande crue ; un message part vers tous les téléphones ; panique, embouteillages, blessés ; pas de crue ; un faux message avec un lien frauduleux circule.
- **Acte 2, Extrême-Nord (bassin du Logone)** : trois capteurs sur sept sont en panne ; « low risk » ; un chef de village signale une montée des eaux ; alerte tardive, en français seulement, 30 % de la zone sans réseau ; environ 40 000 personnes déplacées.
- **Acte 3, après la crue** : choléra ; le ministère de la Santé veut des données de localisation ; le fournisseur propose de les analyser sur des serveurs à l'étranger ; le Parlement demande qui était responsable de chaque défaillance.

### 3.4 Usages dans la vie réelle (1.3)

S1 à S10 (voir SI-009) et les quatre lieux (SI-010).

---

## 4. Liste des écrans (Simple, 2.5, l.705-721)

| # | Écran | Qui le voit | Contenu | Actions |
|---|---|---|---|---|
| 1 | Accueil | Tous | Liste des exercices (brouillon, en cours, terminé, archivé) et histoires disponibles | Ouvrir, créer, ouvrir un rejeu |
| 2 | Mise en place | Animateur | Pays, histoire, langue, vitesse, une ligne par siège (IA ou humain nommé) | Choisir, vérifier, démarrer |
| 3 | Salle de contrôle | Animateur | Horloge de l'histoire, prochains événements, état de chaque siège, salle de coordination, alertes de lacunes | Pause, reprise, vitesse, surprise, correction, arrêt |
| 4 | Mon siège | Joueur | Fiche de rôle, boîte (la mienne), mes décisions, formulaire de décision | Lire, chercher, demander, décider |
| 5 | Salle de coordination | Joueurs, animateur, observateurs | Tous les messages entre institutions, avec type et heure | Poster demandes, réponses, objections, alertes |
| 6 | Conseiller juridique | Tous | Boîte de question, réponses en quatre parties | Poser une question, ouvrir une source |
| 7 | Vue publique | Observateurs, public | Horloge, événements déjà publics, décisions et lacunes au fur et à mesure ; pas de boîte privée | Regarder seulement |
| 8 | Rapport de lacunes | Animateur, décideurs, auditeurs | Cartes de lacunes par gravité, avec preuves et exemples mondiaux | Filtrer, ouvrir les sources, marquer confirmée / contestée / rejetée, exporter |
| 9 | Scorecard | Tous, après l'exercice | 13 dimensions, score, preuves ; jumeaux côte à côte | Ouvrir les preuves, exporter |
| 10 | Rejeu et contrôle | Auditeurs, animateur | Curseur temporel sur tout l'exercice ; « vérifier le journal » | Se déplacer dans le temps, voir ce que chaque siège savait, vérifier |
| 11 | Bibliothèque et carte | Gardien des connaissances, rédacteur | Documents avec statut, carte des pouvoirs, éditeur d'histoires | Ajouter documents, valider ou corriger les lignes, écrire les histoires |

Règles communes : sélecteur FR/EN, bandeau « Fictional exercise », couleur accompagnée d'un mot, lisible sur projecteur, « Mon siège » utilisable sur téléphone, chaque mention juridique cliquable (l.733-741).

Incohérence : l.707 dit « a player sees three » ; or le tableau donne à un joueur au moins cinq écrans (Accueil, Mon siège, Salle de coordination, Conseiller juridique, Scorecard après l'exercice).

---

## 5. Vocabulaire

| Terme (FR / EN) | Sens dans le Simple (ligne) | Équivalent dans la spec (ligne) | Remarque |
|---|---|---|---|
| Exercice (drill) | Pratique qui joue une crise sans danger réel (l.1019) | Simulation / exercise (l.156) | Stable |
| Événement (inject) | Information livrée à certaines institutions seulement (l.1021) | inject (l.230) | Stable |
| Siège (seat) | Place d'une institution dans l'exercice, tenue par l'IA ou une personne (l.1040) | « agent » (l.294-296) | Le Simple dit « siège », la spec dit « agent » : même chose, deux mots |
| Salle de coordination / tableau (board) | Espace partagé où les institutions se parlent (l.1018) | « board » (l.699, l.328) | Les deux documents utilisent des mots différents pour le même objet |
| Journal (logbook / ledger) | Trace de chaque étape, qu'on ne peut pas modifier en secret (l.1031) | ledger (l.702, l.678) | Stable |
| Carte des pouvoirs (who-does-what map / mandate graph) | Liste des pouvoirs et devoirs de chaque institution (l.1033) | mandate graph (l.513-540) | Stable |
| Lacune (gap) | Règle manquante, floue ou contradictoire révélée par l'exercice (l.1025) | gap (l.553-572) ; « gap flag » (l.367) | Le Simple réserve « gap » aux lacunes validées ; la spec l'emploie pour toute alerte |
| Exemple mondial (precedent / global example) | Comment d'autres pays traitent la même question (l.598) | precedent (l.600-629) | Synonymes ; la spec dit « precedent card » |
| Passage (chunk) | Morceau d'un document, souvent un article (l.1032) | chunk (l.390, l.471) | Stable |
| Fiche de rôle (role card) | Description donnée à un siège (l.1038) | role card (l.322) | Stable |
| Vérification de citation (quote check / citation check) | Contrôle qu'un article cité existe (l.1035) | citation check (l.353-355) | Stable |
| Conseiller juridique (legal adviser) | Siège qui répond aux questions juridiques (F-08) | LEGAL (l.313, l.378) | Le Simple dit « feature » (l.565) mais aussi « the legal adviser is the only seat » (l.892) |
| Animateur / chef d'exercice (facilitator / drill leader) | Personne qui dirige l'exercice (l.1022) ; chef d'exercice = siège virtuel (l.1020) | COORD (l.314, l.1020) | Trois noms pour deux rôles (humain ou siège virtuel) |
| Jumeau (twin) | Même histoire, autre pays, pour comparer (l.1042) | AE-01 (l.254) | Stable |
| Hypothèse (assumption) | Supposition faute de texte, toujours marquée (l.1015) | assumed (l.493) | Stable |
| Tags de preuve (evidence) | Simple : « écrit dans un texte / déduit / supposé » (l.276) | documented / inferred / assumed (l.487-493) | Équivalents ; la spec ajoute la valeur « gap » (l.538) |
| HydroSense | IA fictive testée (l.1026) | HYDRO (l.304) | Stable |
| Rejeu (replay) | Reconstituer un exercice passé sans rappeler l'IA (l.1036) | Replay (l.672) | Stable |
| Mur (wall) | Barrière intégrée qui empêche un siège de voir l'information d'un autre (l.1045) | Pas de terme équivalent (l.866-895 : « walls ») | Stable |
| Scorecard | Note sur 13 dimensions | Readiness scorecard (l.204) | Stable |

---

## 6. Contradictions internes du Simple

| # | Lignes | Contradiction |
|---|---|---|
| C1 | l.470 / l.472 et l.827 | « 14 features » ; le tableau F-01 à F-15 en compte 15 (l.827 dit « 15 features »). |
| C2 | l.794 et l.59 et l.554-556 | « 8 seats played by AI (7 institutions + HydroSense) and the drill leader » : le tableau des prototypes donne six institutions (Météo, Protection civile, Opérateur, Régulateur, Santé, Protection des données) plus HydroSense plus le chef d'exercice. Le chiffre « 7 institutions » est faux. L.59 liste sept acteurs, sans la cybersécurité. |
| C3 | l.707 et l.711-721 | « A player sees three » ; or Accueil, Conseiller juridique et Scorecard sont vus de « Everyone ». |
| C4 | l.715 et l.717 et l.885 | La salle de coordination est vue des observateurs (écran 5), mais la vue observateur est « public view only », « no private inbox », « Read the public view only ». Pas clair si la salle est publique. |
| C5 | l.881 et l.662, l.751, l.429 | Le joueur « Read (replay) » le journal pendant l'exercice ; or le journal contient tous les événements, et l'information destinée à un siège ne doit jamais être visible d'un autre. |
| C6 | l.729 et l.541 | Le formulaire de décision (5 champs) n'inclut pas les options ; F-06 et R-12 les exigent. |
| C7 | l.581, l.698-700 | Le mot « confirmed by text » est à la fois une confiance (l.581, l.699) et l'étape « Confirmed » du cycle de vie. Deux axes mélangés. |
| C8 | l.725-731 | Le formulaire de 5 champs n'a pas de champ « options » (voir C6). Cette ligne ne contredit rien d'autre. |
| C9 | l.1.6 R-25 et l.801 | R-25 (« Should ») exporte en « document » et PDF ; le prototype F-13 demande un rapport « as a document ». Le format « document » n'est pas défini (Word ? Markdown ?). |
| C10 | l.1.4 l.176 et Q-04 l.391 | Le prototype inclut le jumeau des Émirats arabes unis ; or l'arabe est « later » alors que les textes émiratis sont souvent en arabe. |
| C11 | l.63 à l.69 | Liste de « How an agent ... » numérotée 1 à 13 : les items 8 à 13 répètent les items 2 à 7 ; la ligne 63 contient un résidu de texte (« drillALERTE reads the real laws… »). Défaut d'édition. |
| C12 | l.117 et l.2.7 (l.794) | Une persona (Aminatou) joue depuis son téléphone ; le siège humain est « if time allows ». |
| C13 | l.1.6 R-15 et l.365 | R-15 humain : « Should » ; mais « F-06 Seats … Human or AI: any seat can be held by a person » (l.542) est présenté comme une règle, non comme une option. |

---

## 7. Divergences Simple / spec

Vérifications faites par `grep -n` sur la spec. Les mots-clés cherchés incluent : pause, resume, stop, observ, auditor, login, permission, replaced, remplac, disput, rejet, rejected, confirm, round, deux semaines, two weeks, ten days, novembre, screen, page, PDF, Markdown, Word, export, budget, token, calls, Wi-Fi, offline, Slack, human, timeout, minutes, merge, duplicate, Mbankolo, 262, etc.

| ID | Sujet | Simple (ligne) | Spec (ligne) | Gravité | Proposition d'arbitrage |
|---|---|---|---|---|---|
| D-01 | Hiérarchie des documents | l.20 : le Simple gagne sur « ce que le système doit faire » ; la spec reste la référence pour outils, liste de documents, plan et Slack. l.1002 : la spec doit être confirmée par le Simple. | l.9 : « the single reference for building ALERTE » ; l.31 : « we update this document first » | **Bloquante** | Arbitrer par écrit : le Simple fait foi pour le comportement (parties 1 et 2) ; la spec fait foi pour les outils, le plan, Slack et la liste de documents. Retirer « single reference » de la spec. Règle de changement : on modifie d'abord le Simple pour le comportement, puis la spec pour l'outil. |
| D-02 | Délai de l'acte 2 | l.39 : « Two weeks later, in the Far North » | l.225 : « Ten simulated days later » ; inject 8 à D11 (l.241) | Mineure | Retenir **10 jours** (spec) : cohérent avec la chronologie des injects (D1 à D11). Corriger l.39 en « Ten days later ». |
| D-03 | Date de soumission | l.785 : « The prototype submitted on 10 November » ; l.2.7 : « by 10 November » | l.26, l.64, l.74 : limite le 10 novembre ; l.1104 et l.1154 : soumission planifiée le dimanche 8 novembre | Mineure | Limite dure = 10 novembre ; cible interne = 8 novembre. Écrire les deux dans le Simple. Pas un vrai conflit. |
| D-04 | Nombre d'écrans | l.705 : **11 écrans** (tableau l.709-721) | l.857 : **8 pages** (l.859-868), dont « Knowledge explorer » en v2 | **Majeure** | Retenir les 11 écrans comme **design cible** (rôles) et les 8 pages comme **sous-ensemble MVP**. Ajouter à la spec les écrans absents : Accueil, Mon siège, Vue publique, édition Bibliothèque. Correspondance : 1 Mise en place = page 1 ; 3 Salle de contrôle ≈ page 2 ; 4 Mon siège ≈ page 3 (sans vue joueur) ; 5 Salle de coordination ⊂ page 2 ; 6 = page 4 ; 8 = page 5 ; 9 = page 6 ; 10 = page 7 ; 11 = page 8 (v2, lecture seule). |
| D-05 | Format des exports | l.377 (R-25) : « document and PDF » ; l.801 : « as a document » | l.206 : « PDF or Markdown » ; l.679 : « gap report (Markdown and PDF) » ; l.865 : « export to PDF and Markdown » | Mineure | Retenir **PDF et Markdown** (spec). Réserver « document » (Word) au rapport technique de 5 pages, imposé par le modèle Word de l'UIT (l.86, l.1166). Corriger R-25. |
| D-06 | Statuts de lacunes | l.649 ; l.696-703 : suspectée, confirmée par texte, revue expert, confirmée, contestée, rejetée | l.572 : seulement une étiquette de confiance (« confirmed by text » / « suspected, needs expert check ») ; aucun statut contesté ou rejeté | **Bloquante** (rapport et expert non couverts) | Retenir le Simple, mais séparer deux axes : **confiance** (texte confirmé ou suspecté) et **statut** (suspectée, confirmée, contestée, rejetée). Corriger l.700, qui mélange les deux. |
| D-07 | Statuts de documents et remplacement | l.262, l.267, l.425, l.631 : fiabilité (texte officiel / résumé / non trouvé), illisible, « replaced by… », en vigueur ou remplacé, date | l.392 : « Link OK / Summary only / To obtain » ; aucune règle de remplacement ; pas de date (l.473-485) | **Majeure** | Retenir deux axes : fiabilité (texte officiel / résumé / non trouvé) et validité (en vigueur / remplacé / inconnu) ; ajouter la date au schéma ; spec : « Link OK » ne prouve pas que le texte a été lu, à renommer. |
| D-08 | Nombre de tours d'échange | l.562, l.689, l.777 : **deux** | l.369, l.787, l.949 : **deux** | Aucune divergence | Garder deux. |
| D-09 | Nombre de sièges et d'agents | l.794 : « 8 seats played by AI (7 institutions + HydroSense) and the drill leader » ; l.2.7 | l.294 : « 11 agents : 8 institutions, 1 AI, 1 Legal Adviser, 1 Coordinator » ; MVP (l.304-314) : six institutions + HYDRO + LEGAL + COORD = neuf agents en MVP ; l.316 : CTD et ANTIC redirigés en MVP | **Majeure** | Retenir **six institutions + HydroSense + chef d'exercice = huit sièges IA** (Simple l.554-556 et spec l.304-314 concordent sur les six). Corriger l.794 (« 7 » → « 6 ») et préciser que le conseiller juridique s'ajoute. Corriger la spec R4c (l.110 : « Seven institution agents … local council ») : cela contredit l.294 et l.311. |
| D-10 | Nombre de fonctionnalités | l.470 et l.472 : **14** | l.827 : « 15 features » ; tableau l.476-492 : F-01 à F-15 | Mineure | Retenir **15** (F-15 = langues). Corriger l.470 et l.472. |
| D-11 | Humain dans le siège dans le prototype | l.794 (prototype : « Human seat ... » en « If time allows ») ; R-15 l.365 : **Should** ; l.542 : « any seat can be held by a person » | l.180-181 : mode « Human in the seat » ; l.861 : « play mode » en MVP ; l.877 : bouton « Submit decision » en MVP. Plan (l.1110-1154) : aucune tâche humaine ; Slack en v2 (l.1088) | **Bloquante** (périmètre MVP) | Retenir **Should** (Simple). MVP sans siège humain, sauf une version web minimale si la semaine 4 le permet. Dans la spec : retirer le mode humain de la liste MVP des pages 1 et 2, ou l'ajouter au plan. Slack reste en v2 (les deux documents concordent). |
| D-12 | Pause, reprise, vitesse, surprise | R-09 (l.358) : **Must** (surprise : Should) ; F-04 (l.527) ; écran 3 (l.713) | l.861-862 : seulement « press Start » ; aucune commande pause, reprise ou vitesse ; aucun module de contrôle de l'horloge (l.692-705) | **Bloquante** | Retenir le Simple : démarrer, pause, reprendre, arrêter et vitesse en MVP ; surprise en Should. Ajouter un module « contrôle de l'horloge » à la spec. |
| D-13 | Reprise après coupure | l.439 ; l.680 ; l.779 (état Interrompu, reprise depuis le journal) | Aucune reprise. Mitigation : « Offline mode, push to GitHub at least daily, recorded runs » (l.931) ; rejeu seulement (l.672-674) | **Majeure** | Retenir le Simple. Coût faible : le rejeu reconstruit déjà l'état à partir du journal (l.672-674). Ajouter l'état « interrompu » et la procédure de reprise à la spec. |
| D-14 | Observateur et vue publique | l.96 ; UC-13 l.242 ; écran 7 l.717 ; l.885 | Absent. Seul « a hackathon judge » (l.172) et « live exercise page » (l.862) ; aucune vue en lecture seule | **Majeure** (démonstration sur scène et public) | Retenir le Simple. Prévoir une vue publique en lecture seule (page simple). Priorité à fixer : Should est la proposition. |
| D-15 | Rôles produit et authentification | l.92-99 (six rôles) ; l.879-887 (matrice) ; l.956 (en ligne) | Aucun rôle produit, aucune authentification ; Streamlit (l.857) | **Majeure** | Retenir le Simple. Ajouter une section « Droits et accès » et choisir une authentification, indispensable dès qu'on joue en ligne (l.956). |
| D-16 | Visibilité des messages et du journal | l.715 (observateurs voient la salle) ; l.881 (joueur lit le journal pendant l'exercice) ; l.662, l.751 (aucune information d'un siège visible d'un autre) | l.322-323 : « board messages addressed to it » ; aucune règle de visibilité pour le board ; journal en JSON ouvert (l.678) | **Majeure** | Définir la visibilité de chaque message (privé, partagé, public). Le joueur ne lit pas le journal pendant l'exercice. L'observateur ne voit que la vue publique. |
| D-17 | Actions de l'animateur, bascules, corrections dans le journal | l.431, l.528, l.645, l.659, l.754 | Types du journal (l.641-649) : INJECT, RETRIEVAL, LLM_CALL, BOARD, DECISION, CITATION_CHECK, GAP, HUMAN, ERROR. Aucun type pour l'animateur, la bascule de siège, l'état de l'exercice ou la correction | **Majeure** | Ajouter à la spec les types ANIMATEUR, CORRECTION (qui pointe vers l'entrée corrigée), BASCULE_SIEGE et ETAT_EXERCICE. |
| D-18 | Lacune « base juridique manquante » | l.430 : « counted as a possible gap » | l.375 : « missing legal basis » gap, hors G1-G10 (l.553-564) | Mineure | Ajouter ce type aux règles, ou l'intégrer à G1 ou G3. |
| D-19 | Citation contestée : consignée ou non | l.575 : « recorded either way » ; l.749, l.754 : rien n'est caché ni effacé | l.355 : « Before a record is accepted … » ; l.947 : décision « not recorded » après deux échecs de JSON | **Majeure** (règle d'or 2 et 6) | Retenir le Simple : toujours consigner. Pour un JSON cassé, écrire une entrée ERREUR et une décision marquée « non enregistrée », visible. Pas de disparition silencieuse. |
| D-20 | Contrôle de préparation avant démarrage | l.297 : ALERTE vérifie bibliothèque, carte, histoire et sièges, et avertit | l.186-187 : « Set-up » sans contrôle | Mineure | Ajouter le contrôle à la spec (page 1). |
| D-21 | Revue par un expert : exigence absente | UC-19 (l.249) ; statut « Expert review » (l.700) ; écran expert « if time allows » (l.798) ; 1.7 l.432 | Aucun R-xx ; expert seulement en test (l.915) | **Majeure** | Ajouter une exigence Must : « un expert confirme, conteste ou rejette une lacune ». L'écran peut rester en v2 ; le statut doit exister en MVP. |
| D-22 | Valeurs des tags de preuve | l.276 : écrit dans un texte / déduit / supposé | l.487-493 : documented / inferred / assumed ; l.538 : « gap » comme valeur | Mineure | Garder trois valeurs. Corriger l.538. |
| D-23 | Codes en double | Codes UC, R, F, G, Q (l.29) | CM-01 est un identifiant de document (l.398) et de scénario (l.220-228) ; AE-01 de même (l.421 et l.254) | Mineure | Renommer les scénarios (par exemple SC-CM-01, SC-AE-01). |
| D-24 | Cibles de test : nombre et seuils | l.451-462 : huit mesures ; T1 80 % (8/10, top 5) ; T2 95 % ; T3 80 % ; T4 85 % ; T5 80 % ; T6 moins de 20 min ; deux mesures sans seuil (compréhension, IFRC « most ») | l.883-892 : six cibles T1 à T6 ; T6 = moins de 20 min **et** moins de 200 appels ; IFRC sans seuil (l.894) | Mineure | Retenir T1 à T6 (spec). Ajouter les deux mesures du Simple comme non bloquantes, avec un seuil pour IFRC (par exemple « au moins la moitié »). |
| D-25 | Budget d'appels LLM | Absent (Q-06 l.393 : temps seulement) | l.787 : 10 à 15 injections × 4 destinataires au plus × 2 tours, moins de 200 appels par CM-01 ; T6 l.892 | Mineure | Ajouter à Q-06 : au plus 200 appels de modèle par exercice CM-01. |
| D-26 | Délai avant reprise par l'IA | l.428, l.770 : « After a set time » | l.952 : « After a set time » ; aucun chiffre dans les deux | Mineure | Chiffrer le délai dans les deux documents. |
| D-27 | Durée d'une journée de l'histoire | l.294 : exemple « one story day in 15 minutes » | l.218 : « about 10 to 20 real minutes » ; l.1.7 Q-06 : moins de 20 min | Mineure | Retenir 10 à 20 minutes (spec). Le Simple dit « exemple », c'est cohérent. |
| D-28 | Lieu d'hébergement et accès en ligne | l.142 ; l.956 : joueurs à Yaoundé, Douala et Maroua en même temps | Streamlit local, Ollama ou API hébergée seulement pour le modèle (l.774-787) ; aucune décision d'hébergement | **Majeure** | Décider : hébergement de l'application, authentification, et ce qui fonctionne sans Internet. |
| D-29 | Droits sur la licence du corpus | Q-09 (l.396) : corpus et carte partageables comme « open resource » ; l.903 : licence floue = pas de copie | R10 (l.117) : « published under the repo's MIT licence » ; l.509 : documents à licence floue non redistribués ; l.941 | **Majeure** (juridique) | Ne pas appliquer la licence MIT (logiciel) aux textes officiels. Choisir une licence de données ouvertes pour le corpus et garder la liste des documents non redistribués. |
| D-30 | Formulaire de décision et options | l.729 : 5 champs, sans options | l.541 : options incluses ; l.336-351 : JSON avec options, gap_flags et reasoning_summary | Mineure | Ajouter « options » au formulaire, ou le retirer de l'objet décision. |
| D-31 | Types de messages | l.312 : « réponse » (accepted, refused, not our role) | l.359-367 : cinq types, sans « réponse » | Mineure | Ajouter le type RÉPONSE, ou prévoir la réponse comme DÉCISION de l'institution sollicitée. |
| D-32 | Formule juridique finale | l.319 : « for practice only; confirm with a lawyer » | l.380 : « for exercise purposes; confirm with a qualified lawyer » | Mineure | Retenir une formule unique, dans les deux langues. |
| D-33 | Bandeau d'avertissement | l.736 : « Fictional exercise » ; l.148 : « ALERTE says this on every screen » | l.214 : « Exercise, fictional scenario » ; l.873 : « Fictional exercise, not a real alert » | Mineure | Retenir la formule de l.873 (la plus complète). |
| D-34 | Citation non vérifiée : libellé | l.575, l.731 : « not verified » ; rouge | l.355 : « unsupported » ; rouge | Mineure | Retenir un libellé unique, par exemple « non vérifiée ». |
| D-35 | Langue arabe et jumeau émirati | Q-04 (l.391) : arabe plus tard ; l.804 : jumeau émirati dans le prototype | l.504 et l.761 : embeddings en arabe ; l.421 et l.427 : textes émiratis en EN/AR ; l.330 et l.872 : sorties de l'IA en français ou en anglais | Mineure | Dire quelle langue fait foi pour les textes émiratis (l.426 du Simple). |
| D-36 | Slack dans les modes de jeu | l.969 : « later » | l.181 : Slack présenté comme mode de jeu sans étiquette v2 ; v2 à l.706, l.1088, l.1158 | Mineure | Ajouter « (v2) » à l.181. |
| D-37 | Nombre d'institutions dans le Simple | l.59 : sept acteurs (sans cybersécurité) ; l.794 : « 7 institutions » | Tableau l.543-556 : huit institutions (dont collectivités et cybersécurité) | Mineure | Corriger l.59 et l.794 (voir C2). |
| D-38 | Noms des dimensions ITU | l.928-942 : « Cross-domain links », « Local context », « Working with AI », « Priorities » | l.729-743 : « Cross-domain correlation », « Contextualisation and regional impact », « Collaboration with AI », « Granular priorities » | Mineure | Retenir les libellés officiels du cadre ITU (ITU-02, l.459). |
| D-39 | Nommage des règles de lacunes | l.583-594 : G1 « Nobody in charge » ; G2 « Two in charge » ; G3 « No procedure » | l.553-564 : G1 « Orphan responsibility » ; G2 « Overlapping mandate » ; G3 « Missing procedure » | Mineure | Garder les codes G1 à G10 ; choisir un intitulé. |
| D-40 | Architecture : nombre de blocs | l.833-841 : sept blocs | l.692-705 : treize modules ; le tableau ne correspond pas bloc par bloc | Mineure | Ajouter à la spec une correspondance blocs ↔ modules (le Simple l.1.6 le demande). |
| D-41 | Mention « Sources » (date) | l.1050 : sources ouvertes le 2 et le 3 octobre | l.33 et l.388 : liens vérifiés le 2 octobre | Mineure | Aucun effet ; harmoniser la date. |
| D-42 | Mapping Y.3172 | l.911-924 : dix éléments (Intent, Source, Collector, Pre-processor, Model, Policy, Distributor, Destination, Orchestrator, Sandbox) | l.712-723 : mêmes dix éléments | Aucune divergence | Garder. |
| D-43 | Gap rules G1 à G10 (contenu) | l.583-594 | l.553-564 | Aucune divergence sur le fond (noms, voir D-39) | Garder. |
| D-44 | Vérification d'un jeu de questions | l.265 (UC-01) : le gardien fait tourner un jeu de questions | l.505 (étape 7), l.906 : 40 questions : 20 Cameroun, 10 EAU, 10 mondial | Aucune divergence | Garder ; préciser la répartition 20/10/10 dans le Simple. |
| D-45 | Précédents : jeux prêts | l.598 et F-11 (l.599-601) | l.600-613 : paires prêtes pour CM-01 | Aucune divergence (la spec est plus précise) | Reprendre la liste dans le Simple comme annexe. |
| D-46 | Cadre de rapport technique | Absent du Simple (le Simple ne parle pas du rapport à l'UIT) | l.86 : 5 pages, modèle Word ; l.1168-1179 : répartition des pages | Hors périmètre | Aucun arbitrage : garder dans la spec. |
| D-47 | Test d'un juge en 10 minutes | l.806 : un juge voit un run de 10 minutes, une décision, deux cartes de lacunes, le journal, deux scorecards | l.172 : « see every requirement working in 10 minutes » ; démo l.1205-1206 | Aucune divergence | Garder. |

---

## 8. Chiffres vérifiés sans écart

- Rounds : deux (Simple l.562, l.689 ; spec l.369, l.949). Pas de divergence.
- Dimensions du cadre ITU : 13 (Simple l.928-942 ; spec l.729-743). Pas de divergence sur le nombre.
- Perspectives du hackathon : 8 (Simple l.944 ; spec l.745).
- Règles de lacunes : G1 à G10 (Simple l.583-594 ; spec l.553-564).
- Types de défaillance : 12 (Simple l.190-203 ; spec l.275-290).
- Types de messages : 5 (Simple l.561 ; spec l.359-367).
- Règles d'or : 10 (Simple l.747-758) : la spec n'a pas de liste équivalente.
- Qualités : Q-01 à Q-12 (Simple l.388-399) : la spec ne les numérote pas.
- Gravités : 1, 2, 3 (Simple l.581 ; spec l.570).
- Scorecard : 0 à 5 (Simple l.605 ; spec l.204).
- Mots d'un exercice : 10 à 20 minutes pour un jour d'histoire (spec l.218) ; moins de 20 minutes pour le run complet (les deux).
- Dates de hackathon : limite 10 novembre, finale à Dubaï le 8 décembre (spec l.64-77) ; le Simple ne donne pas de date de finale, il dit « Dubai final ».
- Acte 1 : jour 1 à 06:00 à 15:00 ; acte 2 et acte 3 : mêmes événements dans les deux documents (inject 8, 10, 11, 13, 14, 15 concordent).
- Chiffres du contexte : 410 000 personnes, 262 écoles, 65 centres de santé (Simple l.47 ; spec l.127) ; 38 pays en cell broadcast (Simple : non ; spec l.134) ; Mbankolo 2023 (Simple l.48 ; spec l.129).
- Y.3172 : mêmes dix éléments (D-42).

---

## 9. Points à trancher en premier (synthèse)

1. **D-01** : qui fait foi (bloquante).
2. **D-11** : siège humain en MVP ou non (bloquante, périmètre).
3. **D-12** : pause, reprise, vitesse dans l'architecture (bloquante).
4. **D-06** : statuts de lacunes (bloquante pour le rapport).
5. **D-04** et **D-09** : nombre d'écrans et de sièges (majeure).
6. **D-07**, **D-13**, **D-14**, **D-15**, **D-16**, **D-17**, **D-19**, **D-21**, **D-28**, **D-29** : majeures (droits, reprise, corrections, hébergement, licences).
7. Les autres sont des corrections de chiffres et de formulations (mineures).

Fin du document.
