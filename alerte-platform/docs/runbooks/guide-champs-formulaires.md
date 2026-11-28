# Guide champ par champ — quoi saisir dans chaque formulaire (Rising Waters — Cameroun, CM-01)

**Pour qui.** Une personne qui connaît peu le projet et doit remplir les formulaires d'ALERTE pour tester le scénario de démonstration « Rising Waters — Cameroun » (code `CM-01`).
**Comment s'en servir.** Chaque section = un formulaire : où l'ouvrir, un tableau champ par champ avec la valeur EXACTE à saisir, le résultat attendu, la vérification. Copiez les valeurs ; ne les « arrangez » pas.
**Ce document ne remplace pas** la trame d'exécution ([parcours A et B](guide-parcours-A-et-B.md), qui renvoie ici avec « § Nom ») ni le [catalogue des commandes et fichiers](catalogue-commandes-et-fichiers.md) (toutes les commandes en ligne de commande, dans l'ordre) ni la [configuration `.env`](configuration-env.md) (variables d'environnement). Il n'en recopie pas le contenu.

> **Exercice fictif, pas une alerte réelle.** HydroSense et les chiffres des événements sont inventés ; les institutions et les textes de loi cités par les mandats viennent des documents du corpus.

## Légende de preuve et statuts (à lire avant tout)

Ce guide a été rédigé en **lisant le code et les données du dépôt** (arbre de travail de la branche `Rudy` au 27/11/2026, modifications non validées incluses). **Rien n'a été exécuté** : ni l'interface, ni l'API, ni les tests, ni un service. Par conséquent :

| Marque | Sens | Usage dans ce guide |
|---|---|---|
| **[UI]** | vérifié en cliquant dans l'interface | **jamais utilisé ici** : à vous de le constater |
| **[API]** | vérifié par un appel d'API | **jamais utilisé ici** |
| **[TEST]** | couvert par un test automatisé du dépôt (le chemin du test est cité) | utilisé quand j'ai trouvé le test ; je ne l'ai pas lancé |
| **[DOC]** | déduit de la lecture du code ou de la documentation | utilisé pour tout le reste |
| **[ABS]** | fonctionnalité absente | utilisé quand le code ne l'offre pas |

| Statut | Sens |
|---|---|
| **PASS** | résultat attendu constaté ET preuve conservée — **à ne cocher que par la personne qui a exécuté** |
| **FAIL** | résultat différent : noter le message exact |
| **BLOCKED** | impossible faute de prérequis : dire lequel |
| **NOT TESTED** | non exécuté. **Tous les statuts de ce guide sont NOT TESTED.** |

**Raisons autorisées quand un champ reste vide** (une seule, écrite telle quelle) : « facultatif, sans conséquence » · « facultatif, valeur par défaut » · « non applicable à ce rôle » · « non requis dans le mode testé » · « donnée indisponible, test bloqué » · « anomalie à corriger ». Quand une valeur ne peut pas être déterminée à partir du dépôt, le guide écrit **À DÉTERMINER** et dit pourquoi.

**Colonnes des tableaux de champs** : Champ affiché (FR / EN) · Signification · Obligatoire ? · Type / valeurs autorisées · Valeur à saisir (Rising Waters) · Exemple valide / remarque. Les libellés viennent de `frontend/src/i18n/fr/*.json` et `en/*.json` ; quand FR et EN sont identiques, un seul est écrit.

## Règles qui évitent la plupart des erreurs

1. **Les codes sont des clés.** `MET`, `DPC`, `AG-MET`, `CM-L10`, `issue_weather_warning`… se saisissent à l'identique (majuscules/minuscules comprises) : l'import CSV, le scénario et les sièges se retrouvent par ces codes.
2. **Ordre de saisie** (une étape dépend de la précédente) : § Espace → § Pays → § Institutions → § Actions → § Bases de connaissances (construites en ligne de commande) → § Mandats → § Profils (facultatif en SANS IA) → § Agents → § Permissions → § Scénarios → § Exercices. Le catalogue d'actions doit exister **avant** l'import des mandats et du scénario.
3. **Valeurs par défaut du formulaire d'exercice** : mode « Modèle réel » et rythme « Automatique » (`ExercisesPage.tsx:50`). Vérifiez le mode avant « Créer ».
4. **Ne transformez jamais une hypothèse en disposition légale.** Un mandat n'est « documenté » que s'il est **validé** et rattaché à une source qui se résout vers un vrai passage (voir § Mandats).
5. **Ne montrez jamais aux agents** le champ « Panne » ni les étiquettes d'un inject ; ne présentez jamais les lacunes visées par l'auteur comme un résultat connu d'avance (voir § Scénarios).

## État de départ à connaître (relevé dans une copie de l'espace de développement du 27/11/2026 à 13:13, non relue en direct)

| Fait | Source | Preuve |
|---|---|---|
| Base **CM** construite : 17 documents, 1 351 passages, publiée en v1 ; **GL, AE et ITU non construites** | `catalogue-commandes-et-fichiers.md` §C ; `guide-test-complet-interface.md:8` | [DOC] |
| Registre CM : 14 mandats importés ; **CM-L10 et CM-L11 validés, les 12 autres « proposé »** | copie de la base de développement faite par l'audit à 13:13 (non relue en direct) ; `guide-test-complet-interface.md:8` | [DOC] |
| Aucun profil de modèle dans l'espace de développement (0 ligne) | même copie | [DOC] |
| Dans cette copie, **AG-HYDRO a le rôle « Institution » et AG-ANTIC le rôle « Système d'IA testé »**, l'inverse de `setup-cm.json` | même copie ; `demo/rising-waters/setup-cm.json` | anomalie à corriger (voir § Agents) |
| Dans cette copie, le pays s'appelle « Cameroon » et les noms d'institutions sont en français ; `setup-cm.json` écrit « Cameroun » et des noms en anglais. Seuls les **codes** comptent pour le fonctionnement | même copie | remarque |

Ce guide donne les valeurs de `demo/rising-waters/setup-cm.json` (celles que crée le script `backend/scripts/seed_rising_waters.py`). Si votre espace a été saisi à la main avec d'autres libellés, les **codes** doivent seulement être identiques.

---

## § Espace — Espace de travail (workspace)

**Où** : page `/access` (écran d'entrée). **Bouton** : « Créer l'espace de travail » / *Create workspace*, dans la carte « Créer un espace de travail » / *Create a workspace* (`access.createTitle`). Si un espace existe déjà, l'écran propose de coller son jeton (« Se connecter avec un jeton ») ; créer un second espace exige un jeton propriétaire.

**Il n'y a PAS de champ « description »** : un espace n'a que deux champs, le nom et l'identifiant court (`WorkspaceCreate` : `name`, `slug`, `backend/app/workspaces/schemas.py:17-19`).

Preuve : [DOC] `EntryPage.tsx:15-18`, `workspaces/schemas.py`.

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Nom de l'espace de travail / Workspace name | nom affiché de l'espace qui contient tout le projet | oui | texte, 1 à 200 caractères | `ALERTE — Demonstration` | valeur utilisée par `seed_rising_waters.py` (`WS_NAME`) |
| Identifiant court (slug) / Short identifier (slug) | identifiant technique dans les adresses | non | `^[a-z0-9][a-z0-9-]{1,98}$` (2 à 99 minuscules, chiffres, tirets) ; aide : « Lettres minuscules, chiffres et tirets. Facultatif. » | (vide) — facultatif, valeur par défaut | s'il est vide, il est déduit du nom : `alerte-demonstration` (`workspaces/service.py:35-38,48`) |
| Jeton d'accès / Access token (carte « Se connecter avec un jeton ») | jeton pour entrer dans un espace existant | oui, pour cette carte seulement | mot de passe, 8 caractères ou plus | non applicable à ce rôle (on ne s'en sert pas pour créer) | à utiliser si un espace existe déjà |

| | |
|---|---|
| **Résultat attendu** | Un message « Espace de travail « ALERTE — Demonstration » créé », le **jeton propriétaire** (affiché **une seule fois**), une case « J'ai copié et conservé le jeton propriétaire. » et le bouton « Continuer vers l'espace de travail » (actif après avoir coché la case). |
| **Vérification** | Après « Continuer », la page Accueil s'ouvre ; le nom de l'espace apparaît dans l'en-tête. Le jeton perdu n'est pas récupérable : relancer avec un autre dossier de données (voir catalogue, commande n° 30). Si l'espace existe déjà et que vous n'avez pas de jeton propriétaire, la création est refusée (code `workspace.bootstrap_disabled`, `workspaces/router.py:35-41`). |
| **Statut** | NOT TESTED |

### Jetons d'accès (page « Jetons d'accès », réservée au propriétaire)

Route `/settings/tokens` ; menu « Système ». Preuve : [DOC] `TokensPage.tsx:15-18`, `workspaces/schemas.py:39-45`.

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Rôle / Role | droits du jeton | oui | `facilitator` (animateur), `observer`, `auditor` (le rôle `player` est créé par siège, pas ici) | `facilitator` pour piloter un exercice ; `observer` pour une personne qui regarde | un jeton est affiché **une fois** |
| Libellé / Label | nom pour retrouver le jeton | non | texte, 200 caractères maximum | (vide) — facultatif, sans conséquence | |
| Expire dans (heures) / Expires in (hours) | durée de validité | non | entier de 1 à 8760 (« Entre 1 et 8760 heures. ») | (vide) — facultatif, valeur par défaut | vide = pas d'expiration |

---

## § Pays — Pays

**Où** : menu Préparer → « Pays et institutions » (`/studio/countries`) → onglet « Pays » / *Countries*. **Bouton d'ouverture** : « Nouveau pays » / *New country*, puis « Enregistrer » / *Save*.
Preuve : [DOC] `CountriesTab.tsx:14-19,82-108`, `workspaces/schemas.py:63-68`, `setup-cm.json` (bloc `country`).

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Nom / Name | nom du pays | oui | texte, 1 à 200 caractères ; unique dans l'espace (`country.duplicate`) | `Cameroun` | |
| ISO 3166-1 alpha-2 | code pays à 2 lettres (libellé non traduit) | non | exactement 2 caractères (« Exactement 2 lettres. ») ; aide : « Deux lettres, p. ex. CM » | `CM` | le scénario s'attache au pays par ce code |
| Langues / Languages | langues du pays | non | liste séparée par des virgules (« Séparées par des virgules ») | `fr, en` | valeur de `setup-cm.json` : `["fr","en"]` |
| Notes | remarques libres | non | texte libre | (vide) — facultatif, sans conséquence | |

| | |
|---|---|
| **Résultat attendu** | Une ligne « Cameroun · CM · fr, en » dans le tableau (colonnes Nom, ISO, Langues, Statut, Actions), statut *actif*. |
| **Vérification** | La liste « Pays » du formulaire d'institution propose « Cameroun » (lors de la saisie suivante). Un pays déjà utilisé ne se supprime pas : le bouton « Supprimer » propose « Archiver plutôt » (`geo.cannotDelete`). |
| **Statut** | NOT TESTED |

---

## § Institutions — Institutions

**Où** : « Pays et institutions » → onglet « Institutions ». **Bouton** : « Nouvelle institution » / *New institution*, puis « Enregistrer ». Le **code** ne peut plus être modifié après la création (« Ne peut plus être modifié ensuite. »). Preuve : [DOC] `InstitutionsTab.tsx:16-23,96-135`, `workspaces/schemas.py:87-95`, `setup-cm.json`.

**Les codes doivent correspondre EXACTEMENT** à ceux du scénario (destinataires des injects), des mandats (colonne `institution` du CSV) et des agents. **COORD et ONR ne sont pas des sièges** : dans `setup-cm.json` ils portent `"seat": false`. C'est une simple indication du fichier : l'interface n'a **aucun champ « siège »** sur une institution, et le script retire cette clé avant d'envoyer (`seed_rising_waters.py:103`). Ils ne reçoivent aucun inject (voir § Scénarios) et n'ont pas d'agent ; ils existent seulement parce que des mandats les citent (CM-L02 pour COORD, CM-L07 pour ONR). **HYDRO** est une institution de type « Système d'IA » (`ai_system`) : le système d'IA testé.

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Code | identifiant unique de l'institution | oui | 1 à 32 caractères `^[A-Za-z0-9_.-]+$` ; unique (`institution.duplicate`) | voir tableau ci-dessous | |
| Nom / Name | nom complet | oui | texte, 1 à 300 caractères | voir tableau ci-dessous | |
| Nom en langue locale / Local-language name | nom officiel local | non | texte libre | (vide) — facultatif, sans conséquence | `setup-cm.json` n'en définit pas |
| Pays / Country | pays de l'institution | oui s'il existe au moins un pays | liste des pays de l'espace ; aide : « Une institution appartient à un pays… » | `Cameroun` | pré-rempli s'il n'y a qu'un pays |
| Type | nature de l'institution | non (défaut « Autre ») | `ministry` Ministère · `agency` Agence · `regulator` Régulateur · `operator` Opérateur · `local_authority` Collectivité locale · `ai_system` Système d'IA · `advisory` Organe consultatif · `other` Autre | voir tableau ci-dessous | `ai_system` n'a pas d'aide à la saisie : il désigne le système d'IA testé |
| Domaines / Domains | thèmes de l'institution | non | liste séparée par des virgules (l'aide affichée est celle des langues : « Séparées par des virgules ») | (vide) — facultatif, sans conséquence | aucun domaine dans `setup-cm.json` ; non utilisé par les règles (seul `snapshot.py:103` les copie) |
| Description | texte libre | non | texte libre | (vide) — facultatif, sans conséquence | |

**Valeurs des 11 institutions** (à saisir une par une ; colonne « Siège » = ce que l'exercice en fera) :

| Code | Nom (valeur de `setup-cm.json`) | Type | Siège dans l'exercice |
|---|---|---|---|
| `HYDRO` | `HydroSense (fictional AI flood forecasting and alert system)` | Système d'IA (`ai_system`) | oui, **siège jamais activé** (système d'IA testé) |
| `MET` | `National Meteorology Directorate, with the National Observatory on Climate Change (ONACC)` | Agence (`agency`) | oui |
| `DPC` | `Civil Protection Directorate, Ministry of Territorial Administration (MINAT)` | Agence (`agency`) | oui |
| `OPS` | `Mobile network operator (generic)` | Opérateur (`operator`) | oui |
| `ART` | `Telecommunications Regulatory Board (ART), with the Ministry of Posts and Telecommunications (MINPOSTEL)` | Régulateur (`regulator`) | oui |
| `MINSANTE` | `Ministry of Public Health (MINSANTE)` | Ministère (`ministry`) | oui |
| `DPA` | `Personal Data Protection Authority (APDP)` | Régulateur (`regulator`) | oui |
| `CTD` | `Local councils (Douala City Council, Far North communes)` | Collectivité locale (`local_authority`) | oui |
| `ANTIC` | `National Agency for Information and Communication Technologies (ANTIC)` | Agence (`agency`) | oui |
| `COORD` | `Conseil national de protection civile / comité de crise (le « chef d'exercice » du prototype n'est pas un siège)` | Agence (`agency`) | non (`seat: false`) |
| `ONR` | `Observatoire national des risques (ONR)` | Agence (`agency`) | non (`seat: false`) |

| | |
|---|---|
| **Résultat attendu** | Un tableau (Code, Nom, Type, Pays, Domaines, Statut, Actions) à 11 lignes pour le Cameroun. |
| **Vérification** | Le filtre « Pays » = Cameroun montre 11 institutions ; la liste « Institution » des pages Agents et Mandats les propose (`CODE — nom`). Une erreur « Code invalide. » = caractère interdit (espace, accent). Un code déjà pris renvoie `institution.duplicate`. |
| **Statut** | NOT TESTED |

---

## § Actions — Catalogue d'actions

**Où** : « Pays et institutions » → onglet « Registre des mandats » → section « Catalogue d'actions ». **À faire avant** d'importer les mandats ou le scénario : un mandat ou une exigence ne peut citer qu'une action du catalogue. Preuve : [DOC] `MandatesTab.tsx:245-285`, `mandates/schemas.py:20-26`, `mandates/csv_import.py:92-127`, `demo/rising-waters/actions.csv`.

**Différence à comprendre.** Une action du catalogue décrit **ce qu'une situation exige** (ex. « décider d'alerter la population »). Les 25 actions de Rising Waters sont de dérivation **« Auteur du scénario »** (`scenario_author`) : elles sont **proposées par le scénario**, elles ne sont **pas** une obligation juridique établie ; les rapports les signalent comme telles. Une obligation établie viendrait d'un texte cité (dérivation « Référentiel (cité) », `referential`, avec une « Note de référence »). Aucune des 25 n'est de ce type.

### Voie recommandée : import CSV (25 lignes d'un coup)
Bouton « Importer un CSV » / *Import CSV* → choisir `demo/rising-waters/actions.csv` → « Essai à blanc » / *Dry run* → lire le résultat → « Importer pour de bon » / *Import for real* (actif seulement s'il n'y a aucune erreur). Colonnes du CSV : `code,label,domain,derivation,justification,reference_note`. Un code déjà présent est ignoré (import idempotent). Une dérivation `scenario_author` sans justification est refusée.

### Voie manuelle : bouton « Nouvelle action » / *New action*

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Code | identifiant de l'action | oui | `^[A-Za-z0-9_.\-]+$`, 64 caractères maximum | `issue_weather_warning` (exemple : première ligne du CSV) | les 25 codes sont dans le tableau ci-dessous |
| Libellé / Label | ce que l'action exige | oui | texte, 300 caractères maximum | `émettre un avis officiel de météo ou de crue` | |
| Dérivation / Derivation | d'où vient l'attente ; aide : « D'où vient l'attente. » | non (**défaut du formulaire : « Référentiel (cité) »**) | `referential` Référentiel (cité) · `scenario_author` Auteur du scénario · `agent_proposed` Proposée par un agent | **`Auteur du scénario`** (changer le défaut !) | laisser « Référentiel (cité) » présenterait une exigence du scénario comme une obligation officielle : erreur |
| Justification | pourquoi l'action est exigée | **oui si la dérivation est « Auteur du scénario » ou « Proposée par un agent »** (`action.justification_required`) | texte libre | `Action exigée par le scénario Rising Waters (définie par l'auteur du scénario, pas par un texte officiel).` | le bouton « Créer » ne bloque pas : l'erreur vient du serveur |
| Note de référence / Reference note | référence du texte cité | non | texte libre | (vide) — non applicable à ce rôle | à renseigner seulement pour une dérivation « Référentiel (cité) » |
| (Domaine / domain) | regroupe des actions (utilisé par les règles de lacunes) | — | **absent du formulaire manuel** ; présent dans le CSV (colonne `domain`) | [ABS] dans le formulaire ; valeur dans le tableau ci-dessous | pour que le domaine soit renseigné, utiliser le CSV |

**Les 25 actions** (valeurs du CSV ; dérivation `scenario_author` et justification identiques pour toutes) :

| Code | Libellé | Domaine (CSV seulement) |
|---|---|---|
| `issue_weather_warning` | émettre un avis officiel de météo ou de crue | `alerting` |
| `validate_ai_forecast` | vérifier et valider une prévision produite par l'IA avant une décision publique | `ai_oversight` |
| `decide_public_alert` | décider d'alerter la population | `alerting` |
| `compel_operator_alert` | ordonner aux opérateurs mobiles de relayer une alerte publique | `alerting` |
| `send_mass_alert` | envoyer techniquement l'alerte aux téléphones (SMS ou diffusion cellulaire) | `alerting` |
| `correct_false_alert` | corriger ou annuler une fausse alerte | `alerting` |
| `liability_alert_harm` | répondre des dommages causés par une alerte erronée | `liability` |
| `block_spoofed_alert` | stopper les fausses alertes qui imitent le canal officiel | `security` |
| `report_sensor_outage` | signaler que les capteurs de l'IA sont en panne et la prévision peu fiable | `ai_oversight` |
| `act_on_local_warning` | agir sur une alerte locale qui contredit l'IA | `coordination` |
| `multilingual_alerting` | alerter dans les langues comprises par la population | `inclusion` |
| `reach_unconnected` | atteindre les personnes sans téléphone ni couverture réseau | `inclusion` |
| `activate_contingency_plan` | activer le plan d'urgence et de secours | `coordination` |
| `evacuate_zone` | ordonner l'évacuation d'une zone dangereuse | `coordination` |
| `coordinate_response` | coordonner la réponse multisectorielle | `coordination` |
| `cholera_response` | piloter la riposte à l'épidémie (choléra) | `health` |
| `access_location_data` | utiliser les données de localisation téléphonique pour la santé publique | `data` |
| `protect_personal_data` | protéger les données personnelles | `data` |
| `authorise_transfer_abroad` | autoriser le transfert de données personnelles à l'étranger | `cross_border` |
| `cross_border_agreement` | conclure un accord avec un acteur étranger qui traite des données nationales | `cross_border` |
| `public_communication_after_error` | expliquer publiquement l'erreur | `coordination` |
| `accountability_report` | établir clairement qui était responsable de chaque défaillance | `coordination` |
| `set_alert_standard` | fixer la norme technique des messages d'alerte publique sur les téléphones | `alerting` |
| `human_validate_ai_alert` | approuver par une validation humaine une alerte rédigée par l'IA avant sa diffusion | `ai_oversight` |
| `authorise_automatic_ai_alert` | autoriser la diffusion automatique d'alertes rédigées par l'IA sans validation humaine | `ai_oversight` |

| | |
|---|---|
| **Résultat attendu** | Essai à blanc : « 25 créés, 0 ignorés, 0 erreurs » ; le tableau « Catalogue d'actions » (Code, Libellé, Dérivation, Justification) liste 25 lignes avec le badge « Auteur du scénario ». |
| **Vérification** | À l'import des mandats (§ Mandats) : aucune erreur « action absente du catalogue ». Dans le scénario : aucune erreur `inject.unknown_action`. |
| **Statut** | NOT TESTED |

---

## § Bases de connaissances — Bases de connaissances et documents

**Où** : menu Préparer → « Bases de connaissances » (`/studio/knowledge`). **Boutons** : « Nouvelle base de connaissances » / *New knowledge base* (assistant en 3 étapes : « Nom et type » → « Pays et domaine » → « Relecture », puis « Créer ») ; « Importer une archive » / *Import archive*. Page d'une base : onglets « Documents », « Qualité et couverture », « Versions et index », « Test de recherche », « Export / import », « Construction ». Commandes en ligne de commande (construction, publication) : **voir le catalogue, commandes n° 11 à 17**, pas répétées ici.

### Les six mots qu'il ne faut pas confondre

| Terme | Ce que c'est | Où | Se crée par |
|---|---|---|---|
| **PDF source** | le fichier d'origine d'un texte de loi, copié dans le dossier de sa base : `<ALERTE_DATA_DIR>/blobs/knowledge_sources/CM/…pdf`. L'application ne le « connaît » pas tant qu'il n'est pas enregistré | disque | copie (commande n° 12) |
| **Manifeste** (`m.jsonl`) | la liste des PDF copiés, avec leur empreinte SHA-256 ; sert à enregistrer (`adopt`) puis à appliquer les métadonnées (`curate`). **Ce n'est pas** le `manifest.json` d'une archive | disque | `sources-migrate --apply --manifest` (n° 12) |
| **Archive ZIP** | un export/import d'une base entière (manifeste + empreintes + signature Ed25519 si l'instance a une clé) | bouton « Importer une archive » ; onglet « Export / import » | assistant d'export. **Ce n'est pas la voie de chargement des PDF de la démonstration** (l'ancienne archive du prototype n'est plus utilisée) |
| **Base importée / enregistrée** | les documents sont connus de l'application (état « reçu » puis « en attente ») ; rien n'est encore découpé | page de la base | `adopt` ou bouton « Enregistrer ces fichiers dans CM » ou import de fichiers |
| **Base indexée** | texte extrait (OCR si scan), découpé en passages (« extraits »/chunks), index lexical + vecteurs calculés ; la colonne « Indexés (vecteurs) » affiche `n/n` | liste des bases | `knowledge build` (n° 15) ou boutons de l'onglet « Construction » |
| **Base publiée** | une **version figée et immuable** (v1, v2…) ; **les agents ne lisent que des versions publiées** ; la publication est **refusée** si des documents sont encore en cours de traitement (`kb.publish.processing`) ou si les vecteurs sont incomplets (`kb.publish.vectors_incomplete`, `knowledge/kbops.py:398-421`) ; republier sans changement est refusé (`kb.publish.unchanged`) | onglet « Versions et index » | « Publier » / `knowledge publish` (n° 17) |

### Création d'une base (assistant « Nouvelle base de connaissances »)
Preuve : [DOC] `KbListPage.tsx:20-26,100-135`, `knowledge/schemas.py:17-26`, `knowledge/kbops.py:174-198`. **Pour la démonstration, la base `CM` se crée en ligne de commande** (`knowledge kb-create --code CM --name CM`, n° 11) parce que l'assistant **n'a pas de champ « Code »** : le code est déduit du nom (`slugify_code`), ce qui donne `CM` pour le nom `CM`.

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Nom / Name | nom de la base ; sert à déduire son code | oui | texte, 1 à 200 caractères (serveur : 300) | `CM` | donne le code `CM` ; la matrice d'accès affiche ce nom (« AG-MET peut lire CM ») |
| Description | texte libre | non | texte libre | (vide) — facultatif, sans conséquence | |
| Type | nature de la base ; aide : « « Pratiques mondiales » alimente les précédents internationaux ; « Rapports antérieurs » conserve des analyses passées. » | non (défaut `National`) | `national` National · `global_practices` Pratiques mondiales / Global practices · `scenario` Scénario · `prior_reports` Rapports antérieurs / Prior reports · `mixed` Mixte | `National` | pour la base GL (précédents internationaux) : `Pratiques mondiales` — **GL n'est pas construite à ce jour : donnée indisponible, test bloqué** |
| Pays / juridiction / Country / jurisdiction | pays couvert ; aide : « …Recommandé pour une base nationale : sans lui, la base n'est reliée à aucune institution. » | non, mais recommandé pour une base nationale | liste des pays | `Cameroun` | sans pays rattaché, un badge « Sans pays rattaché » apparaît |
| Domaine / Domain | thème de la base ; aide : « p. ex. early_warning » | non | texte, 100 caractères maximum | (vide) — facultatif, sans conséquence | aucune valeur dans le dépôt pour CM |
| Langues / Languages | langues des textes | non | liste séparée par des virgules | `fr, en` | les documents CM sont en `fr` (13) et en `en` (4) d'après `documents.curation.json` ; la valeur de ce champ de la base n'est fixée par aucun fichier du dépôt : **À DÉTERMINER** par le propriétaire de la base (`fr, en` est cohérent avec les documents) |

### Import de documents (onglet « Documents »)
Preuve : [DOC] `DocumentsTab.tsx:21-33,104-132`. Bouton « Choisir des fichiers » / *Choose files* (ou glisser-déposer ; PDF, DOCX, TXT, MD, HTML). Une **liste d'aperçu** « N fichier(s) à importer dans la base CM » s'affiche **avant l'envoi** ; rien n'est déduit du nom du fichier. Bouton « Importer N fichier(s) dans CM ». Chaque fichier devient un document indépendant ; un doublon (même SHA-256) est refusé seul (`kb.document.duplicate`).

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Fichier / File | le document à importer | oui | PDF, DOCX, TXT, MD, HTML, HTM | un PDF de `alerte/data/docs/CM/` (dossier **en lecture seule**, ne rien y modifier) | l'empreinte SHA-256 s'affiche (12 premiers caractères) |
| Titre / Title | titre du document | non (défaut : nom du fichier sans extension) | texte | titre du tableau « 17 documents CM » ci-dessous | |
| Type de document / Document type | catégorie | non | texte libre (`law`, `decree`, `plan`, `report`…) | valeur du tableau ci-dessous | |
| Langue / Language | langue du texte | non | texte libre | `fr` ou `en` (tableau) | |
| Juridiction / Jurisdiction | pays ou juridiction | non | texte libre | `CM` | |
| Redistribution | droit de redistribuer le texte | non (défaut `unknown`) | `unknown`, `allowed`, `restricted` | `unknown` | les 17 documents CM sont `unknown` dans `documents.curation.json` |
| Licence (SPDX) | licence du document (non proposée à l'import, seulement sur la fiche) | non | texte | (vide) — facultatif, sans conséquence | |

**Limite à connaître.** Un document importé par l'interface reçoit un code technique `DOC-0001`, `DOC-0002`… Les codes `CM-01`…`CM-18` (ceux des mandats) sont posés par la commande `knowledge curate`, qui relie chaque PDF à sa fiche par l'empreinte SHA-256 (`knowledge/services/curation.py:41-45`). Pour que les sources des mandats (`CM-10`, `CM-05`, `CM-01`…) correspondent, **la base CM se construit par la ligne de commande** (n° 12 à 15).

### Fiche d'un document (clic sur le titre) : métadonnées, droits
Preuve : [DOC] `DocumentPage.tsx:58-88`, `knowledge/schemas.py:50-64`. Bouton « Enregistrer ». **Attention** : si le document n'a pas de fiabilité, le formulaire propose `unofficial` par défaut (`DocumentPage.tsx:45`) : à corriger avant d'enregistrer si le tableau ci-dessous dit autre chose.

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Titre / Title | titre | non | texte, 500 caractères maximum | titre du tableau ci-dessous | |
| Type de document / Document type | catégorie | non | texte libre | `law`, `decree`, `plan`, `report`, `press`, `statement` (valeurs de la curation) | |
| Numéro / Number | numéro officiel | non | texte | ex. `2024/017` pour CM-01 | |
| Date | date du texte | non | date `AAAA-MM-JJ` | ex. `2024-12-23` pour CM-01 | |
| Juridiction / Jurisdiction | juridiction | non | texte | `CM` | |
| Langue / Language | langue | non | texte | `fr` / `en` | |
| URL de la source / Source URL | adresse d'origine | non | URL | (vide) — facultatif, sans conséquence | `null` dans la curation |
| Fiabilité / Reliability | confiance dans la source | non | `official`, `summary`, `unofficial`, `unknown`, `not_found` | valeur du tableau | CM : 1 `official`, 3 `summary`, 2 `unofficial`, 11 `unknown` |
| Validité / Validity | le texte est-il en vigueur ? | non | `in_force`, `replaced`, `unknown` | `unknown` | les 44 documents sont `unknown` dans la curation ; un texte `replaced` est exclu des recherches courantes |
| Licence (SPDX) | licence | non | texte | (vide) — facultatif, sans conséquence | |
| Redistribution | peut-on le publier ? ; aide : « Les documents inconnus ou restreints sont exclus d'un export ouvert. » | non | `allowed`, `restricted`, `unknown` | `unknown` | |
| Niveau de preuve par défaut / Default evidence level | niveau de preuve attribué par défaut aux mandats issus de ce texte | non | `documented`, `inferred`, `assumed` | `documented` (valeur du formulaire) | ne transforme pas à lui seul un mandat en disposition légale (voir § Mandats) |

**Les 17 documents de la base CM** (valeurs de `knowledge_bases/curation/documents.curation.json`, collection `CM` ; il n'y a pas de `CM-06` : la numérotation du corpus est reprise telle quelle) :

| Code | Titre | Type | Numéro | Date | Langue | Fiabilité | Validité | Redistribution |
|---|---|---|---|---|---|---|---|---|
| `CM-01` | Loi n°2024/017 du 23 décembre 2024 relative à la protection des données à caractère personnel | `law` | `2024/017` | `2024-12-23` | `fr` | `official` | `unknown` | `unknown` |
| `CM-02` | Loi n°2010/013 du 21 décembre 2010 régissant les communications électroniques au Cameroun | `law` | `2010/013` | `2010-12-21` | `fr` | `unknown` | `unknown` | `unknown` |
| `CM-03` | Loi n°2015/006 du 20 avril 2015 modifiant et complétant certaines dispositions de la loi n°2010/013 | `law` | `2015/006` | `2015-04-20` | `fr` | `unknown` | `unknown` | `unknown` |
| `CM-04` | Loi n°2010/012 du 21 décembre 2010 relative à la cybersécurité et la cybercriminalité au Cameroun | `law` | `2010/012` | `2010-12-21` | `fr` | `unknown` | `unknown` | `unknown` |
| `CM-05` | Loi n°86/016 du 6 décembre 1986 portant réorganisation générale de la protection civile | `law` | `86/016` | `1986-12-06` | `fr` | `unofficial` | `unknown` | `unknown` |
| `CM-07` | Rapport du Cameroun sur la Décennie internationale de la prévention des catastrophes naturelles (IDNDR) | `report` | `—` | `—` | `fr` | `unknown` | `unknown` | `unknown` |
| `CM-08` | Décret n°2005/124 du 15 avril 2005 portant organisation du Ministère des Postes et Télécommunications | `decree` | `2005/124` | `2005-04-15` | `fr` | `unknown` | `unknown` | `unknown` |
| `CM-09` | Loi n°90/047 du 19 décembre 1990 relative à l'état d'urgence | `law` | `90/047` | `1990-12-19` | `fr` | `unknown` | `unknown` | `unknown` |
| `CM-10` | Plan national de contingence du Cameroun, livre premier (avril 2011) | `plan` | `—` | `2011-04` | `fr` | `unknown` | `unknown` | `unknown` |
| `CM-11` | Loi n°2019/024 du 24 décembre 2019 portant Code général des collectivités territoriales décentralisées | `law` | `2019/024` | `2019-12-24` | `fr` | `unknown` | `unknown` | `unknown` |
| `CM-12` | IFRC — Republic of Cameroon: Mapping of International Disaster Response Laws, Rules and Principles (mai 2021, brouillon) | `report` | `—` | `2021-05` | `en` | `summary` | `unknown` | `unknown` |
| `CM-13` | IFRC — Republic of Cameroon: Mapping of Legal and Policy Arrangements for Disaster Risk Management, including Public Health Emergencies and international disaster assistance | `report` | `—` | `—` | `en` | `summary` | `unknown` | `unknown` |
| `CM-14` | Article de presse (Investir au Cameroun) sur la Stratégie nationale d'intelligence artificielle | `press` | `—` | `—` | `fr` | `unofficial` | `unknown` | `unknown` |
| `CM-15` | Déclaration du Cameroun, 79e session de l'Assemblée générale des Nations unies, Sixième Commission : protection des personnes en cas de catastrophe | `statement` | `—` | `—` | `fr` | `unknown` | `unknown` | `unknown` |
| `CM-16` | UNICEF Cameroon — Floods Flash Update No. 5, Far North (24 octobre 2024) | `report` | `—` | `2024-10-24` | `en` | `summary` | `unknown` | `unknown` |
| `CM-17` | Banque mondiale / MoPH Cameroun — Environmental and Social Commitment Plan, Health Security Program in Western and Central Africa, Phase III (P508837) | `report` | `—` | `—` | `en` | `unknown` | `unknown` | `unknown` |
| `CM-18` | Plan de préparation et de riposte au choléra, Ministère de la Santé publique | `plan` | `—` | `—` | `fr` | `unknown` | `unknown` | `unknown` |

### Publication (onglet « Versions et index »)

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Note | commentaire de la version publiée | non | texte, 1000 caractères maximum | `v1 — construction à partir des PDF originaux` | texte du guide historique (étape 6) ; libre. Le bouton « Publier » fige les documents prêts |

Boutons voisins : « Reconstruire l'index lexical », « Calculer les embeddings » (nécessite le serveur d'embeddings, sinon la recherche reste « lexical seul »). L'onglet « Construction » regroupe les actions de la base (« Traiter les documents en attente », « Calculer les embeddings manquants », « Construire cette base », « Vérifier la cohérence », « Publier CM ») ; chaque bouton nomme la base et demande confirmation ; **il n'existe pas de construction globale**.

| | |
|---|---|
| **Résultat attendu** | Liste des bases : colonne « Version publiée » = `v1` (sinon badge « non publiée ») ; « Documents » = 17 ; « Indexés (vecteurs) » = `1351/1351` ; états des documents « prêt » ou « à relire ». |
| **Vérification** | Onglet « Versions et index » : une ligne `v1` avec « Empreinte du manifeste ». Onglet « Qualité et couverture » : « Qualité d'extraction moyenne ». Refus attendus à connaître : « des documents sont encore en cours de traitement » ; « vectorisation incomplète » (relancer « Calculer les embeddings manquants ») ; « aucun changement depuis la dernière version publiée ». |
| **Statut** | NOT TESTED (la base CM existe dans l'espace de développement ; GL : BLOCKED, non construite) |


---

## § Mandats — Registre des mandats

**Où** : « Pays et institutions » (`/studio/countries`) → onglet « Registre des mandats » / *Mandate registry*. Sections de la page : le panneau « Comment utiliser le registre des mandats (et que faire ensuite) », « Revue du registre par institution », « Mandats » (boutons « Importer un CSV » et « Nouveau mandat »), « Catalogue d'actions » (voir § Actions). Preuve : [DOC] `MandatesTab.tsx`, `mandates/schemas.py`, `mandates/csv_import.py`, `mandates/service.py`.

### Ce qu'est un mandat, et les trois niveaux de preuve

Un mandat = « cette institution **peut** ou **doit** faire telle action, selon tel texte ». Il arrive toujours **« proposé »** (jamais validé d'office) et ne devient **actif** que s'il est **validé** ET lié à au moins une source qui se résout vers un passage réel du corpus (`mandates/service.py:238-263`). **Une ligne « proposé » n'est pas documentée.**

Le champ **niveau de preuve** (`evidence_tag`, colonne CSV `evidence`) dit **comment le texte soutient la ligne** :

| Valeur | Sens | Exemple réel (`knowledge_bases/curation/mandates.CM.json`) |
|---|---|---|
| `documented` — « écrit dans un texte » | le texte dit lui-même ce que la ligne affirme | **CM-L13** : DPA, devoir `protect_personal_data`, `CM-01`, ARTICLE 53, extrait « veiller à l'application de la présente loi ». **CM-L15** : DPA, pouvoir `authorise_transfer_abroad`, `CM-01`, ARTICLE 32, extrait « autorisation préalable » |
| `inferred` — « déduit d'un texte » | un texte s'en approche, mais la ligne va **un cran plus loin** que ce qui est écrit | **CM-L10** : ANTIC, pouvoir `block_spoofed_alert`, `CM-04` Article 7 (régulation de la sécurité électronique) ; note d'audit : « Le pouvoir de bloquer n'est pas écrit. » **CM-L01** : DPC, rôle de chef de file (`lead`), `CM-10` ; note : « « chef de file » non écrit » |
| `assumed` — « supposé » | **aucun texte** retrouvé : c'est une hypothèse à examiner | **CM-L04** : DPC, `activate_contingency_plan` ; note : « Décret 98/031 art. 3(1) : préfet / gouverneur / SG Présidence, pas la DPC ». **CM-L06** : MET, `issue_weather_warning` ; note : « Aucun texte d'organisation du service météo dans le corpus : absence de document, pas preuve d'absence de mandat. » **CM-L05**, **CM-L09** sont aussi `assumed` |

**Règles à respecter.**
* Une hypothèse (`assumed`) **ne se présente jamais** comme une obligation légale. Le fichier `mandates.CM.json` le dit : « Hypothèses ('assumed') : jamais présentées comme obligations légales ».
* Le niveau de preuve est une **déclaration de la personne qui prépare le registre** : l'application **ne vérifie pas** qu'il est cohérent avec la source (`validate_mandate` contrôle seulement qu'un passage existe : `mandates/service.py:250-263`). C'est à vous de lire le passage avant de valider. Exemple de prudence : CM-L11 est étiqueté `documented`, mais sa note d'audit précise que « recevoir des alertes » n'est pas écrit.
* Le formulaire manuel « Nouveau mandat » **n'a pas de champ de niveau de preuve** : un mandat saisi à la main reçoit `inferred` (valeur par défaut de l'API, `mandates/schemas.py:77`). Pour un autre niveau : colonne `evidence` du CSV (ou l'API).
* Les lignes **importées par CSV** gardent le nom du document, l'article et la citation d'origine **dans la note** du mandat, mais **n'ont aucune source** : il faut les relier à un passage (ci-dessous).

### Colonnes du fichier `demo/rising-waters/mandats-cm.csv` (14 lignes)

Colonnes : `line_id,country,institution,kind,action,description,source_doc,article,procedure,depends_on,dependency_ready,evidence,assumed_by,quote,audit_note`. L'import ne lit que celles du tableau ; il crée **toujours** des mandats « proposé » sans source (`csv_import.py:1-3`).

| Colonne CSV | Champ du mandat | Valeurs / remarque | Effet à l'import |
|---|---|---|---|
| `line_id` | **code** du mandat (colonne « Réf. ») | `CM-L01`… ; unique ; une ligne déjà importée est ignorée (import idempotent) | clé de référence (`import_ref`) |
| `country` | — | `CM` | **non lue** par l'import |
| `institution` | **institution** | code d'institution **existant** (`DPC`, `COORD`, `ONR`…) | sinon erreur « institution inconnue » |
| `kind` | **type de mandat** | `power`, `duty`, `lead`, `coordination`, `information_sharing`, `procedure`, `human_oversight`, `liability`, `inclusion`, `channel_protection`, `international_agreement`, `prohibition` (mis en minuscules) | valeur hors liste : erreur |
| `action` | **action** | code du catalogue d'actions | sinon erreur « action absente du catalogue » |
| `description` | **formulation** | texte libre | recopié tel quel |
| `source_doc` | source (document) | code de document de la nouvelle base (`CM-10`, `CM-04`…) | **conservé dans la note** « source_doc d'origine (à re-lier) » ; aucune source créée |
| `article` | article | `Article 7`, `ARTICLE 218`… | idem (note) |
| `procedure` | procédure | texte | **vide → `none`** ; renseigné → `general` (les valeurs `specific`/`unknown` ne s'importent pas) |
| `depends_on` | dépendance (texte) | vide pour les 14 lignes | texte de dépendance |
| `dependency_ready` | dépendance prête ? | `yes`, `no`, `unknown` | sinon ignoré |
| `evidence` | **niveau de preuve** | `documented` / `inferred` / `assumed` ; vide ou inconnu → `inferred` | repris |
| `assumed_by` | qui a supposé | vide pour les 14 lignes | note |
| `quote` | **extrait** (citation) | fragment du texte ; plusieurs fragments séparés par « \| » | **conservé dans la note** (« citation : … ») |
| `audit_note` | **justification** de l'auteur du registre | texte | **conservé dans la note** (« note d'audit : … ») |

Il n'existe **pas de colonne « statut »** : le statut est « proposé » à l'import ; il change par les boutons « Valider » / « Rejeter ».

### Les 14 mandats du Cameroun (valeurs à importer ou à saisir)

Tous : pays `CM`, procédure vide dans le CSV. Il n'y a pas de `CM-L08` : la numérotation du registre est reprise telle quelle. « État observé » = copie de la base de développement du 27/11/2026 à 13:13 (non relue en direct).

| Réf. (`line_id`) | Institution | Type (`kind`) | Action | Niveau de preuve (`evidence`) | Formulation (`description`) | État relevé (copie du 27/11, non relue en direct) |
|---|---|---|---|---|---|---|
| `CM-L01` | `DPC` | `lead` | `coordinate_response` | `inferred` | La Direction de la protection civile coordonne les moyens (secours, sauvetage, logistique, forces auxiliaires) | proposé |
| `CM-L02` | `COORD` | `power` | `coordinate_response` | `inferred` | Le Conseil national de la protection civile assiste le Président ; attributions fixées par décret 96/054 | proposé |
| `CM-L03` | `DPC` | `duty` | `decide_public_alert` | `inferred` | L'alerte est diffusée après activation du plan d'urgence ; diffusion par les autorités administratives et la DPC | proposé |
| `CM-L04` | `DPC` | `power` | `activate_contingency_plan` | `assumed` | Activation du plan d'urgence | proposé |
| `CM-L05` | `DPC` | `power` | `evacuate_zone` | `assumed` | Évacuation d'une zone par les autorités administratives | proposé |
| `CM-L06` | `MET` | `duty` | `issue_weather_warning` | `assumed` | Le service météo émet les prévisions et alertes | proposé |
| `CM-L07` | `ONR` | `power` | `issue_weather_warning` | `inferred` | L'ONR gère l'information sur les aléas et menaces (arrêté 037/PM) | proposé |
| `CM-L09` | `OPS` | `power` | `send_mass_alert` | `assumed` | Les opérateurs peuvent techniquement envoyer des SMS de masse | proposé |
| `CM-L10` | `ANTIC` | `power` | `block_spoofed_alert` | `inferred` | L'ANTIC régule et contrôle la sécurité électronique ; l'usurpation d'identité dans les messages est interdite | **validé** |
| `CM-L11` | `CTD` | `power` | `act_on_local_warning` | `documented` | Les communes élaborent des plans de prévention et d'intervention et interviennent en cas de fléaux calamiteux | **validé** |
| `CM-L12` | `MINSANTE` | `duty` | `cholera_response` | `inferred` | L'État détecte, évalue et notifie les événements de santé publique (RSI) ; plan du MINSANTE aligné sur le RSI | proposé |
| `CM-L13` | `DPA` | `duty` | `protect_personal_data` | `documented` | L'Autorité de protection des données veille à l'application de la loi 2024/017 | proposé |
| `CM-L14` | `OPS` | `duty` | `protect_personal_data` | `inferred` | Les responsables de traitement protègent les données et informent en cas de violation | proposé |
| `CM-L15` | `DPA` | `power` | `authorise_transfer_abroad` | `documented` | Le transfert de données à l'étranger exige l'autorisation préalable de l'Autorité | proposé |

### Formulaire « Nouveau mandat » (saisie manuelle d'un mandat)

Bouton « Nouveau mandat » / *New mandate*, puis « Créer ». Exemple : saisir à la main la ligne **CM-L13**.

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Institution | qui porte le mandat | oui | liste `CODE — nom` | `DPA — Personal Data Protection Authority (APDP)` | |
| Type | nature du mandat | non (défaut `power`) | les 12 types (affichés avec des espaces : « information sharing »…) | `duty` | pour CM-L15 : `power` |
| Action | action exigée ; aide : « Issue du catalogue d'actions ci-dessous. » | oui | liste `code — libellé` du catalogue | `protect_personal_data` | |
| Procédure / Procedure | existe-t-il une procédure écrite ? | non (défaut `unknown`) | `specific`, `general`, `none`, `unknown` | `unknown` | le CSV, lui, met `none` quand la colonne est vide |
| Description | formulation du mandat | non | texte libre | `L'Autorité de protection des données veille à l'application de la loi 2024/017` | |
| Sources (bloc) | passages qui fondent le mandat | non à la création ; **obligatoire pour valider** | voir « Relier un mandat à un passage » | (vide) — facultatif, sans conséquence à la création ; à ajouter avant de valider | |
| (niveau de preuve) | — | — | **absent du formulaire** : le mandat est créé `inferred` | [ABS] | |

### Relier un mandat à un passage (chunk) AVANT de le valider

Valable pour un mandat importé (le plus fréquent) ou saisi à la main. Bouton **« Sources »** de la ligne (fenêtre « Sources — CM-L13 ») :

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Base de connaissances / Knowledge base | base où chercher | oui | liste des bases (nom) | `CM` | |
| Texte à rechercher / Search text | mots **du texte** (pas ceux de la description) ; aide : « …cherchez avec des mots français du texte… Plusieurs mots du passage donnent de meilleurs résultats qu'un seul. » | oui | texte | un fragment de la colonne « extrait » du tableau ci-dessous, ex. `veiller à l'application de la présente loi` | « Rechercher » ; « Aucun passage trouvé » → essayer d'autres mots du texte, dans sa langue |
| (résultat) « Utiliser comme source » | choisit le passage affiché | oui (au moins un) | un passage `CODE · Art. n · p. n` | le passage dont le **code de document** et l'**article** correspondent au tableau « Sources » ci-dessous | **lisez le passage** : le logiciel vérifie qu'il existe, pas qu'il soutient le mandat |
| « Enregistrer les sources » | enregistre | — | bouton | — | message « Source enregistrée » ; la ligne affiche « Art. … » au lieu de « aucune source » |

Puis fermer et cliquer **« Valider »** : message « Mandat validé », statut « validé ». Sans source qui se résout : refus « validation impossible : aucune source ne résout vers un chunk réel » (`mandate.validate.no_source`). **« Rejeter »** exige un « Motif du rejet » (c'est la seule « justification » saisissable dans l'interface) ; la ligne devient « rejetée ». Le bouton « Valider » n'envoie ni note ni correction. **Corriger** le texte d'une ligne, voir son historique : [ABS] dans l'interface (API seulement).
Si un badge rouge « citation absente du texte » apparaît à côté d'une source, **ne validez pas**. Par le chemin de l'interface, la citation est copiée du passage (240 premiers caractères) : le badge n'apparaît donc normalement pas, d'où l'obligation de lire le passage vous-même.

**Sources attendues pour les 14 lignes** (document de la **nouvelle** base, article, extrait — jamais un ancien code `CM-S01`…) :

| Réf. | Document (`source_doc`) | Article | Texte à rechercher (`quote`) | Rôle de la source | Justification de l'auteur (`audit_note`) |
|---|---|---|---|---|---|
| `CM-L01` | `CM-10` | `—` | coordination des moyens mis en | `grounds` | Plan national de contingence ; « chef de file » non écrit ; chevauche le CNPC (L02). |
| `CM-L02` | `CM-05` | `Article 3` | Conseil National de la Protection Civile dont | `grounds` | Existence établie par la loi 86/016 ; attributions par source secondaire seulement (décret 96/054 absent). |
| `CM-L03` | `CM-10` | `—` | Diffusion de l'alerte (Autorités administratives, DPC) | `grounds` | Le décret 98/031 art. 3 attribue le déclenchement et la diffusion à l'autorité compétente (préfet, gouverneur, SG de la Présidence) ; texte absent du corpus initial. |
| `CM-L04` | — | — | (aucun texte retrouvé) | — | Décret 98/031 art. 3(1) : préfet / gouverneur / SG Présidence, pas la DPC ; texte absent du corpus initial. **Laisser « proposé » : hypothèse.** |
| `CM-L05` | — | — | (aucun texte retrouvé) | — | CM-13 : « no evacuation procedures » ; CM-09 art. 5(4) seulement sous état d'urgence déclaré. **Laisser « proposé » : hypothèse.** |
| `CM-L06` | — | — | (aucun texte retrouvé) | — | Aucun texte d'organisation du service météo dans le corpus : absence de document, pas preuve d'absence de mandat. **Laisser « proposé » : hypothèse.** |
| `CM-L07` | `CM-10` | `—` | organe central en charge de la gestion de l'information | `grounds` | Soutient la gestion de l'information, pas l'émission d'alertes météo ; PNC 2011 : « non encore totalement opérationnel ». |
| `CM-L09` | `CM-02` | `—` | acheminement gratuit des communications électroniques d'urgence | `context` | Aucun texte ne donne aux opérateurs un pouvoir ou devoir de diffuser des alertes publiques ; le rôle des opérateurs est « à définir » (CM-08 art. 58). |
| `CM-L10` | `CM-04` | `Article 7` | chargée de la régulation des activités de sécurité électronique | `grounds` | Le pouvoir de bloquer n'est pas écrit. |
| `CM-L10` | `CM-04` | `Article 48` | usurpant l'identité d'autrui est interdite | `context` | Le pouvoir de bloquer n'est pas écrit. |
| `CM-L11` | `CM-11` | `ARTICLE 218` | fléaux calamiteux | `grounds` | « recevoir des alertes » n'est pas écrit. |
| `CM-L11` | `CM-11` | `ARTICLE 157` | plans communaux spécifiques de prévention des risques | `grounds` | « recevoir des alertes » n'est pas écrit. |
| `CM-L12` | `GL-17` (**BLOCKED** : base GL non construite ; seul `CM-18` est résoluble dans la base CM) | `Article 6` | dans les 24 heures suivant l'évaluation | `grounds` | Obligation de l'État ; exercice par le MINSANTE déduit de son plan (décret 2002/209 absent). |
| `CM-L12` | `CM-18` | `—` | exigences du Règlement Sanitaire International | `context` | Obligation de l'État ; exercice par le MINSANTE déduit de son plan (décret 2002/209 absent). |
| `CM-L13` | `CM-01` | `ARTICLE 53` | veiller à l'application de la présente loi | `grounds` | — |
| `CM-L14` | `CM-01` | `ARTICLE 22` | informer sans délai | `grounds` | Portée générale ; l'opérateur n'est pas nommé. |
| `CM-L15` | `CM-01` | `ARTICLE 32` | autorisation préalable | `grounds` | — |

**Combien de mandats valider ?** Dans la copie de l'espace de développement du 27/11/2026 (13:13, non relue en direct), **seuls CM-L10 et CM-L11 sont validés** (copie de base du 27/11 13:13, non relue en direct). Les guides existants ne sont pas d'accord avec la base : `guide-test-complet-interface.md:296` demande de valider « CM-L10 et CM-L13 », alors que la base de développement a validé CM-L10 et CM-L11. La liste à valider pour votre test est donc **À DÉTERMINER** par la personne qui pilote le test ; règles de conduite : ne validez que ce dont vous avez **lu** le passage ; **laissez CM-L15 « proposé »** (il sert au test contrefactuel : `geo.guide.counter`) ; les autres restent « proposé » — « ce n'est pas une erreur, et cela garde l'analyse honnête » (`geo.guide.s4`).

### Revue du registre par institution

Section « Revue du registre par institution » : une liste déroulante « Statut de la revue » par institution (libellé d'accessibilité « Statut de la revue DPC »). **Pas de champ « note »** dans l'interface (l'API en accepte une).

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Statut de la revue / Review status | un humain a-t-il examiné **tous** les mandats de l'institution ? | non (défaut `unreviewed`) | `unreviewed` (non revu) · `partial` (partiel) · `reviewed complete` (revu complet) — affichés en anglais, sans traduction | **`unreviewed` pour les 11 institutions** | `mandates.CM.json` : « unreviewed (aucun registre n'est déclaré complet) ». Ne passez à `reviewed complete` que si une personne a réellement examiné toute la liste : jamais pour faire disparaître l'avertissement `registry.not_reviewed` de la préparation (attendu et normal) |

| | |
|---|---|
| **Résultat attendu** | Import CSV : « Essai à blanc : 14 créés, 0 ignorés, 0 erreurs » puis « 14 mandats importés » ; 14 lignes « proposée » avec le badge « aucune source » et le badge « inactif » (« mandat proposed »). Après liaison et validation : statut « validé », plus de badge « aucune source », colonne « Sources » = « Art. … ». |
| **Vérification** | Colonne « Réf. » (`CM-L01`…) ; filtre « Institution » ; page Accueil (compteur de mandats validés). Préparation d'un exercice : avertissement `institution.no_mandates` pour toute institution sans mandat validé (attendu). Erreurs fréquentes : « action absente du catalogue » (importer d'abord le catalogue, § Actions) ; « institution inconnue : 'ONR' » (créer COORD et ONR, § Institutions). |
| **Statut** | NOT TESTED |

---

## § Profils — Profils de modèles

**Où** : menu Préparer → « Agents » (`/studio/agents`) → section « Profils de modèle » (en bas de page). **Bouton** : « Nouveau profil de modèle » / *New model profile*, puis « Créer ». Preuve : [DOC] `AgentsPage.tsx:163-220`, `agents/schemas.py:20-52`, `agents/providers.py:96-113,374-433`, `agents/service.py:41-91`.

**Trois règles.**
1. Le profil est **ignoré en mode « Scénarisé (SANS IA) »** : le fournisseur est forcé à `scripted` quel que soit le profil (`simulation/snapshot.py:75-77` ; [TEST] `backend/tests/simulation/test_effective_profile.py:18-20`). Un profil ne sert que pour « Modèle réel ». Pas besoin d'en créer pour le parcours A.
2. **Sans profil**, un agent utilise le serveur par défaut du `.env` (`ALERTE_LLM_BASE_URL` et `ALERTE_LLM_MODEL`, voir [configuration](configuration-env.md)) — à condition que `ALERTE_LLM_MODE` soit `openai_compat` ; sinon la préparation bloque (`agent.no_model_profile`) (`readiness.py:66-68`).
3. **Tester AVANT d'affecter** : cliquez « Tester la connexion » sur la ligne du profil ; attendez « joignable · N ms » (badge vert). « injoignable » + un message = ne pas affecter ce profil à un agent. Le test envoie un seul appel « ping » (32 jetons) et n'affiche jamais d'URL ni de clé (`agents/service.py:72-91`). La préparation de l'exercice refait la même sonde pour chaque profil effectif et **bloque** le lancement si elle échoue (`provider.test_failed`, `simulation/readiness.py:74-90`).

**Modifier et supprimer un profil (interface).** Sur la page « Agents », chaque ligne de la section « Profils de modèle » a un bouton **Modifier** (mêmes champs que la création, formulaire pré-rempli ; un modèle laissé vide est enregistré comme vide) et un bouton **Supprimer** (avec confirmation). Un profil **utilisé par un agent** ne peut pas être supprimé : le message cite les agents concernés ; changez d'abord leur profil. Les exercices déjà lancés ne sont pas affectés (copie figée). Le champ `extra` n'est pas modifiable par l'interface.

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Nom / Name | nom du profil, unique dans l'espace | oui | texte, 1 à 200 caractères (`model_profile.duplicate` si déjà pris) | au choix, ex. `profil-reel-cm01` | nom libre : aucune valeur imposée par le dépôt |
| Fournisseur / Provider | type de serveur | oui (défaut `openai_compat`) | `openai_compat` (serveur de modèle compatible OpenAI) · `scripted` (SANS IA, règles fixes) · `cassette` (rejeu) | `openai_compat` | `scripted` et `cassette` sont refusés par la préparation en mode « Modèle réel » (`provider.not_ai`). Un profil `cassette` **ne peut pas être créé depuis l'interface** (il exige `extra.cassette`, `service.py:41-43`) |
| Modèle / Model | nom EXACT du modèle servi | non pour l'interface ; **indispensable en pratique** | texte, 200 caractères maximum | **À DÉTERMINER** | dépend du serveur du testeur : copier le nom exact listé par `curl <serveur>/v1/models` (catalogue n° 7) ou la valeur de `ALERTE_LLM_MODEL`. Un profil sans modèle est refusé par la préparation (`agent.no_model_profile`) |
| Référence du point d'accès / Endpoint reference | **NOM d'une variable de configuration** qui contient l'adresse du serveur ; aide : « Nom de la configuration du serveur, pas une URL. » | non (défaut côté serveur : `ALERTE_LLM_BASE_URL`) | `^[A-Za-z_][A-Za-z0-9_]{0,99}$` (pas de `://`) | `ALERTE_LLM_BASE_URL` | **jamais une URL, jamais une clé** (l'interface ne le contrôle pas, le serveur refuse une URL). Le nom est cherché dans l'environnement, puis dans les réglages `ALERTE_…` et le `.env` |
| Température / Temperature | « créativité » du modèle | non (défaut 0) | nombre de 0 à 2 | `0` | 0 = réponses les plus reproductibles |
| Jetons max / Max tokens | longueur maximale de la réponse | non, **ne peut pas être vide** (défaut 1024) | entier ; **serveur : 16 à 32 768** (l'interface accepte dès 1 : une valeur < 16 est refusée par le serveur) | `1024` (défaut) | à augmenter si les réponses sont tronquées (**À DÉTERMINER** selon le modèle) |
| Délai (s) / Timeout (s) | attente maximale d'une réponse | non (défaut 120) | nombre ≥ 1 (l'interface exige ≥ 1) ; **serveur : au plus 1800** (l'interface n'impose pas de plafond) | `120` (défaut) | augmenter pour un gros modèle sur machine lente |
| `extra` — `request_body` | paramètres de requête supplémentaires (surtout pour **désactiver la « réflexion »** des modèles qui la pratiquent) | non | **[ABS] dans l'interface** (seulement par l'API). Liste blanche : `chat_template_kwargs` (objet) et `reasoning_effort` (texte) ; tout autre champ est refusé (`model_profile.request_body_invalid`) | (vide) — facultatif, sans conséquence | exemple API : `{"extra": {"request_body": {"chat_template_kwargs": {"enable_thinking": false}}}}` (exemple du code, valable pour vLLM ; le support dépend du serveur ET du modèle). `PATCH /api/v1/model-profiles/<id>` |
| `extra` — `api_key_ref` | NOM de la variable qui contient la clé du serveur | non | **[ABS] dans l'interface** ; nom de variable, jamais la clé | (vide) — facultatif, valeur par défaut | par défaut, la clé lue est celle de `ALERTE_LLM_API_KEY` (`providers.py:431`) |

**Affecter le profil à un agent** : dans le formulaire de l'agent, liste « Profil de modèle » (`nom (fournisseur)`), voir § Agents.

| | |
|---|---|
| **Résultat attendu** | Une ligne dans « Profils de modèle » (Nom, Fournisseur, Modèle, Référence du point d'accès, Connexion). Après « Tester la connexion » : « joignable · 345 ms » (exemple de forme) ou « injoignable » avec la raison (`endpoint non configuré : définir la variable ALERTE_LLM_BASE_URL`, `modèle non configuré`, délai dépassé…). |
| **Vérification** | « Aperçu du prompt » d'un agent : le texte ne contient **aucun** secret ni nom de variable ([TEST] `backend/tests/agents/test_citations_prompt.py:62-74`). Dans la liste des agents, la colonne « Profil de modèle » affiche le nom du profil ou « aucun profil de modèle ». |
| **Statut** | NOT TESTED (Modèle réel : BLOCKED tant que le nom exact du modèle et le serveur ne sont pas connus) |

---

## § Agents — Agents

**Où** : menu Préparer → « Agents » (`/studio/agents`). **Bouton** : « Nouvel agent » / *New agent*, puis « Enregistrer ». Sur chaque ligne : « Modifier », « Aperçu du prompt », « Cloner », « Archiver ». Preuve : [DOC] `AgentsPage.tsx:18-35,84-130`, `agents/schemas.py:7-12,54-117`, `simulation/engine.py`, `agents/runtime.py`.

**Un agent = une institution jouée par une IA** (une mission, des consignes, des outils, des limites). Il ne sait que ce que son institution saurait : ses mandats validés, les documents des bases qui lui sont accordées (§ Permissions) et l'annuaire des autres sièges. **Il n'existe pas de champ « Objectif »** : l'objectif est la ligne **`Objective:`** du champ « Instructions » (de même `Contacts`, `Limits`, `On each event`, `Output`, voir plus bas). Ces textes sont en **anglais** dans `setup-cm.json` ; le prompt demande à l'agent d'écrire dans la langue de l'exercice (français pour CM-01).

**Les 9 agents se créent un par un, ou par le script** `seed_rising_waters.py --from 5 --until 5` (commande n° 19 du catalogue ; `--fix-agents` aligne rôle, institution, mission et consignes d'un agent déjà présent qui diffère du pack — c'est la correction de l'anomalie AG-HYDRO / AG-ANTIC signalée plus haut). Le script ne transmet **ni outils, ni limites, ni profil** : l'API applique ses défauts (4 outils, 4 étapes, 3 recherches, 2 appels au conseiller).

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Code | identifiant de l'agent | oui | texte ; interface 1 à 40 caractères, serveur 1 à 64 ; unique (`agent.duplicate`) | `AG-` + code d'institution : voir tableau des 9 agents | `AG-MET` |
| Nom / Name | nom affiché | oui | interface 1 à 200, serveur 1 à 300 | `Agent ` + code : `Agent MET`… | |
| Rôle / Role | nature de l'agent ; aide : « Système d'IA : ses sorties sont scénarisées par le scénario, jamais produites par un modèle. » | non (défaut `Institution`) | `institution` Institution · `ai_system` Système d'IA testé / AI system under test · `legal_adviser` Conseiller juridique / Legal adviser | `Institution` pour 8 agents ; **`Système d'IA testé` pour AG-HYDRO** | `Conseiller juridique` : inutile ici (voir plus bas) |
| Institution | institution représentée | **oui** côté serveur, sauf pour `legal_adviser` (`agent.institution_required`) ; l'interface laisse la liste vide : l'erreur arrive après coup | liste `CODE — nom` | l'institution de même code que l'agent | |
| Mission | ce que fait l'institution, en une phrase | non (jamais vide ici) | texte, **4000 caractères au plus** (aucune limite affichée) ; **le prompt n'en lit que 600** | texte du tableau ci-dessous | |
| Instructions | comportement : personnage, priorités, ton, objectif, contacts, limites, conduite, résultat ; aide : « Texte libre : ton, contraintes, langue. Ne mentionnez jamais les lacunes attendues. » | non (jamais vide ici) | texte, **8000 caractères au plus** ; **le prompt n'en lit que 1500** | texte du bloc de chaque agent ci-dessous | ne jamais y écrire de panne, d'étiquette ni de lacune visée |
| Profil de modèle / Model profile | modèle affecté à cet agent | non | liste `nom (fournisseur)` ; vide = « aucun profil de modèle » | **Parcours A (SANS IA)** : (vide) — non requis dans le mode testé. **Parcours B** : (vide) pour utiliser le serveur par défaut du `.env`, ou un profil testé (§ Profils) | ignoré en mode « Scénarisé (SANS IA) » |
| Outils / Tools | actions autorisées à l'agent | non | cases : `search_kb` (chercher dans ses bases) · `ask_legal` (poser une question au conseiller juridique intégré) · `post` (écrire au tableau de coordination) · `decide` (enregistrer une décision citée). **Défaut du formulaire : `search_kb`, `post`, `decide`** ; défaut de l'API : les 4 | **les 4 cochés** pour les 8 agents-institutions (état créé par le script) ; AG-HYDRO : non applicable à ce rôle (laisser le défaut) | `decide` termine l'activation ; à la dernière étape seuls `post` et `decide` restent permis |
| Étapes max par activation / Max steps per activation | nombre maximal d'étapes (appels au modèle) dans une activation | non (défaut **4**) | entier **1 à 8** (bornes du serveur ; l'interface applique les mêmes) | `4` | AG-HYDRO : non applicable à ce rôle |
| Recherches max / Max searches | recherches dans les bases par activation | non (défaut **3**) | entier **0 à 10** | `3` | 0 interdit toute recherche |
| Appels max au conseiller par inject / Max adviser calls per inject | questions à `ask_legal` | non (défaut **2**) | entier **0 à 5** | `2` | voir « Écarts » : la limite n'est pas lue correctement pour un siège humain, et le formulaire d'édition réaffiche toujours 2 |

### Les 9 agents de Rising Waters

Source : `demo/rising-waters/setup-cm.json` (bloc `agents`), longueurs mesurées. « Institution » = code de l'institution ; le nom de l'agent est `Agent <code>`. Les limites sont celles du formulaire par défaut : **étapes 4 · recherches 3 · conseiller 2** ; pour AG-HYDRO : non applicable à ce rôle.

| Institution | Code agent | Rôle | Mission (texte exact) | Instructions (objectif, contacts, limites, conduite, résultat) | Outils | Limites numériques |
|---|---|---|---|---|---|---|
| `HYDRO` | `AG-HYDRO` | Système d'IA testé (`ai_system`) | Forecast floods and draft warning messages for the authorities. You do not decide; you inform. | bloc ci-dessous (326 car.) | non applicable à ce rôle | non applicable à ce rôle |
| `MET` | `AG-MET` | Institution (`institution`) | Observe, forecast and warn about weather and climate hazards; judge the quality of forecasts. | bloc ci-dessous (998 car.) | `search_kb`, `ask_legal`, `post`, `decide` | étapes 4 · recherches 3 · conseiller 2 |
| `DPC` | `AG-DPC` | Institution (`institution`) | Protect the population; decide public alerts and evacuations; activate emergency plans; coordinate relief. | bloc ci-dessous (1049 car.) | `search_kb`, `ask_legal`, `post`, `decide` | étapes 4 · recherches 3 · conseiller 2 |
| `OPS` | `AG-OPS` | Institution (`institution`) | Run the mobile network; transmit messages only when the law or a lawful order allows it; protect subscriber data. | bloc ci-dessous (1090 car.) | `search_kb`, `ask_legal`, `post`, `decide` | étapes 4 · recherches 3 · conseiller 2 |
| `ART` | `AG-ART` | Institution (`institution`) | Regulate operators; say what operators may or must do; protect consumers. | bloc ci-dessous (959 car.) | `search_kb`, `ask_legal`, `post`, `decide` | étapes 4 · recherches 3 · conseiller 2 |
| `MINSANTE` | `AG-MINSANTE` | Institution (`institution`) | Lead the health response, including epidemic detection and control. | bloc ci-dessous (866 car.) | `search_kb`, `ask_legal`, `post`, `decide` | étapes 4 · recherches 3 · conseiller 2 |
| `DPA` | `AG-DPA` | Institution (`institution`) | Enforce the personal data protection law; authorise transfers of personal data abroad. | bloc ci-dessous (892 car.) | `search_kb`, `ask_legal`, `post`, `decide` | étapes 4 · recherches 3 · conseiller 2 |
| `CTD` | `AG-CTD` | Institution (`institution`) | Relay local warnings, open shelters, manage schools and local services. | bloc ci-dessous (797 car.) | `search_kb`, `ask_legal`, `post`, `decide` | étapes 4 · recherches 3 · conseiller 2 |
| `ANTIC` | `AG-ANTIC` | Institution (`institution`) | Electronic security; respond to cyber incidents such as fake alerts and fraudulent links. | bloc ci-dessous (890 car.) | `search_kb`, `ask_legal`, `post`, `decide` | étapes 4 · recherches 3 · conseiller 2 |

**Les textes ci-dessous sont à copier tels quels** (un bloc par agent : mission, puis instructions). Les mots-clés d'une instruction se lisent ainsi — il n'y a **pas** de champ séparé pour chacun :

| Ligne dans « Instructions » | Ce que c'est |
|---|---|
| (premier paragraphe) | le personnage et ses contraintes |
| `Priorities:` / `Tone:` | priorités et ton |
| **`Objective:`** | **l'objectif** (il n'y a pas de champ « Objectif » distinct) |
| `Contacts (seats you can ask or inform):` | les sièges avec lesquels échanger — le prompt contient aussi l'annuaire des autres sièges |
| `Limits:` | ce que l'agent ne peut pas faire |
| `On each event:` | la conduite à tenir à chaque événement |
| `Output:` | le résultat attendu (une décision) |

#### AG-HYDRO — Agent HYDRO (institution HYDRO) — bases : CM

Mission (copier dans « Mission ») :

```text
Forecast floods and draft warning messages for the authorities. You do not decide; you inform.
```

Instructions (copier dans « Instructions », 326 caractères) :

```text
Objective: Not an LLM seat: HydroSense is the fictional AI system under test.
Limits: It is never activated as a decision-maker, never posts and never searches documents.
On each event: Its outputs are fixed in the scenario events (system_output) and received by the institutions.
Output: None: it informs, it does not decide.
```

#### AG-MET — Agent MET (institution MET) — bases : CM, INT (= GL, non construite)

Mission (copier dans « Mission ») :

```text
Observe, forecast and warn about weather and climate hazards; judge the quality of forecasts.
```

Instructions (copier dans « Instructions », 998 caractères) :

```text
You own the science. You are judged on forecast accuracy and you fear both false alarms and missed events. You can warn about weather, but you cannot order the public to act or compel anyone. You distrust model output that no forecaster has reviewed.
Priorities: never release an unvalidated forecast as official; protect the credibility of weather warnings; get decisions to the people who hold the power to act
Tone: precise and cautious, numbers first
Objective: Give DPC a validated, quantified assessment of every weather or flood forecast, with its confidence.
Contacts (seats you can ask or inform): DPC (decides public alerts); CTD (local needs)
Limits: You may warn about weather and judge forecast quality; you cannot order the public to act or compel anyone.
On each event: Check the event and any model output against your documents, state how reliable it is, then tell the seats concerned what you found.
Output: One decision: your forecast verdict, its confidence and its legal basis.
```

#### AG-DPC — Agent DPC (institution DPC) — bases : CM, INT (= GL, non construite)

Mission (copier dans « Mission ») :

```text
Protect the population; decide public alerts and evacuations; activate emergency plans; coordinate relief.
```

Instructions (copier dans « Instructions », 1049 caractères) :

```text
You are the decision-maker under time pressure. You must weigh the cost of a false alarm (panic, injuries, lost trust) against a missed flood. You want a named person to validate any alert before it goes out, and you do not control the phone networks.
Priorities: protect lives without causing a panic; have a legal basis and a named validator for every alert; keep one clear line of command during the response
Tone: decisive and practical
Objective: Decide whether and how to alert and protect the population, on a documented legal basis.
Contacts (seats you can ask or inform): MET (forecast validity); OPS (message dispatch); ART (network capacity); CTD (local relay)
Limits: You do not control the phone networks and cannot compel operators unless a retrieved document gives you that power.
On each event: Ask the seats whose input you need (forecast, dispatch, networks, local relay), then decide; if answers are pending, decide provisionally and revise when they arrive.
Output: One decision: the action taken or refused, and the legal basis.
```

#### AG-OPS — Agent OPS (institution OPS) — bases : CM, INT (= GL, non construite)

Mission (copier dans « Mission ») :

```text
Run the mobile network; transmit messages only when the law or a lawful order allows it; protect subscriber data.
```

Instructions (copier dans « Instructions », 1090 caractères) :

```text
You are a licensed commercial operator. Technically you can broadcast to millions of phones within minutes, but you need a clear written instruction from an authority with a legal basis. You worry about liability, network load and sending anything unvalidated to your customers.
Priorities: act only on an instruction you can show a legal basis for; avoid liability and network overload; reach customers quickly once the order is valid
Tone: pragmatic, asks for written instructions
Objective: Deliver lawful alerts and data requests through the networks, only on a clear instruction and legal basis.
Contacts (seats you can ask or inform): ART (regulator); DPC (alert owner); DPA (personal data)
Limits: You execute lawful instructions; you do not decide whether an alert is justified, and you do not release personal data unless your documents allow it.
On each event: Check who is asking, under which authority and for what purpose; ask the seats concerned for what you need to act lawfully, then decide.
Output: One decision: executed, refused or referred, with the authority relied on.
```

#### AG-ART — Agent ART (institution ART) — bases : CM, INT (= GL, non construite)

Mission (copier dans « Mission ») :

```text
Regulate operators; say what operators may or must do; protect consumers.
```

Instructions (copier dans « Instructions », 959 caractères) :

```text
You are the telecom regulator. You set technical standards and supervise operators, but you do not decide the content of a public alert and you are careful about acting without a written legal basis. You care about reach, languages and handset support.
Priorities: act within written powers; reach for every language and handset; keep operators and authorities aligned on standards
Tone: formal, cites the texts
Objective: Keep operators and authorities aligned with telecom and alert-channel rules.
Contacts (seats you can ask or inform): OPS (operators); DPC (alert owner); ANTIC (cybersecurity)
Limits: You regulate operators and standards; you do not decide public alerts and you do not run the networks.
On each event: Assess what the event means for operator obligations and channel integrity; tell OPS and DPC what the rules require, and ask ANTIC when authenticity is in doubt.
Output: One decision: your regulatory position and the texts it rests on.
```

#### AG-MINSANTE — Agent MINSANTE (institution MINSANTE) — bases : CM, INT (= GL, non construite)

Mission (copier dans « Mission ») :

```text
Lead the health response, including epidemic detection and control.
```

Instructions (copier dans « Instructions », 866 caractères) :

```text
You are the national health ministry. You lead detection and response for epidemics and you need data quickly, but you know health and location data need a lawful basis.
Priorities: contain the outbreak quickly; use data only with a lawful basis; keep DPC, operators and the data protection authority informed
Tone: urgent but careful, cites the texts
Objective: Lead the health response and obtain the information it needs lawfully.
Contacts (seats you can ask or inform): DPC (civil protection); DPA (data protection); OPS (operators)
Limits: You cannot oblige operators or others to hand over personal data outside what the law allows.
On each event: Assess the health need; when you need something from others, ask the seat concerned with the purpose and the scope; then decide.
Output: One decision: the health action and any data request, with the legal basis.
```

#### AG-DPA — Agent DPA (institution DPA) — bases : CM, INT (= GL, non construite)

Mission (copier dans « Mission ») :

```text
Enforce the personal data protection law; authorise transfers of personal data abroad.
```

Instructions (copier dans « Instructions », 892 caractères) :

```text
You are the personal data protection authority. You apply the data protection law: lawful basis, purpose, and prior authorisation of transfers abroad. You neither block public-health work nor approve blindly.
Priorities: protect personal data; require a lawful basis and a stated purpose; authorise transfers abroad only on the conditions of the law
Tone: formal, cites the texts
Objective: Rule on requests that involve personal data or transfers abroad, within the law.
Contacts (seats you can ask or inform): MINSANTE (health data requester); OPS (data holder)
Limits: You authorise or refuse on the basis of the law; you do not run the health response or the networks.
On each event: Identify what is requested and by whom; ask the requester for what is missing; then authorise, refuse or set conditions.
Output: One decision: authorise, refuse or conditions, with the articles relied on.
```

#### AG-CTD — Agent CTD (institution CTD) — bases : CM

Mission (copier dans « Mission ») :

```text
Relay local warnings, open shelters, manage schools and local services.
```

Instructions (copier dans « Instructions », 797 caractères) :

```text
You are the local authorities (city council and communes). You are closest to the population and the field, and you work with what the national level gives you.
Priorities: relay warnings in the languages people speak; open shelters and keep local services running; tell the national level what is happening on the ground
Tone: practical and local
Objective: Get warnings and help to local people and report field needs upward.
Contacts (seats you can ask or inform): DPC (national alerts); MET (forecasts)
Limits: You act within your communes; you do not issue national alerts or command national bodies.
On each event: Relay what is validated, report field facts to DPC, ask MET or DPC for what you lack, then decide your local action.
Output: One decision: the local action and its legal basis.
```

#### AG-ANTIC — Agent ANTIC (institution ANTIC) — bases : CM, INT (= GL, non construite)

Mission (copier dans « Mission ») :

```text
Electronic security; respond to cyber incidents such as fake alerts and fraudulent links.
```

Instructions (copier dans « Instructions », 890 caractères) :

```text
You are the national cybersecurity agency. You think like an attacker: spoofed alerts, fake links, a compromised AI feed. You favour authentication and human validation, and you speak up when data leaves the country.
Priorities: stop spoofed or tampered alerts; require authentication and human validation; protect citizens' data
Tone: blunt and security-minded
Objective: Protect the authenticity of public alerts and respond to cyber incidents.
Contacts (seats you can ask or inform): ART (regulator); OPS (operators)
Limits: You do not decide public alerts or regulate telecom operators; you assess and act on electronic security within your mandate.
On each event: Assess what the event means for electronic security, ask the seats concerned what they observed, tell them what to do or check, then decide.
Output: One decision: your security assessment and action, with the legal basis.
```


### HYDRO, LEGAL et COORD : trois choses qui ne sont pas des « agents qui décident »

| Élément | Ce que c'est | Preuve |
|---|---|---|
| **HYDRO** (HydroSense) | le **système d'IA fictif testé** (institution de type `ai_system`, agent `AG-HYDRO` de rôle « Système d'IA testé »). Il **n'est jamais activé comme décideur** : l'activation renvoie un résultat vide sans appeler de modèle. **Sa « sortie » est écrite à l'avance** dans le champ « Sortie du système d'IA (JSON) » (`system_output`) des **injects 2, 8 et 14** (voir § Scénarios) et reçue par les autres destinataires (« AI system output received » dans leur prompt). HYDRO a quand même besoin d'un **siège** dans l'exercice (il est destinataire des injects 2, 8, 14 : sans siège, la préparation bloque `inject.recipient_without_seat`), mais ce siège ne se déclenche jamais et ne reçoit/écrit aucun message | [DOC] `agents/runtime.py:465` ; `simulation/common.py:11,65-66` ; `simulation/engine.py:656-669,673-677` ; `agents/prompt.py:131-132` ; [TEST] `backend/tests/agents/test_runtime.py:269-275`, `backend/tests/mandates/test_rising_waters_pack.py:106-112` |
| **LEGAL** (conseiller juridique) | **pas un siège ni un agent à créer**. C'est l'**outil `ask_legal`** : une question posée au service de conseil intégré, qui répond en quatre parties avec citations vérifiées, terminée par la mention anglaise « For exercise purposes only; confirm with a qualified lawyer. ». Pour un agent, il utilise le modèle **de l'agent** et **ses** bases ; pour un joueur humain, bouton « Interroger le conseiller juridique ». Le rôle « Conseiller juridique » existe dans le formulaire mais n'est pas activable et aucun setup de démonstration ne l'utilise. La configuration propre d'un conseiller (profil, consignes) n'atteint pas le moteur (aucune clé `legal_adviser` dans l'instantané de l'agent, `agents/service.py:247-256`) | [DOC] `agents/runtime.py:348-409` ; [TEST] `backend/tests/agents/test_runtime.py` (`test_ask_legal_four_parts_checked_and_closing_added`) |
| **COORD** | deux choses de même nom, à ne pas confondre : **(1)** le **module de règles interne** `simulation/coord.py`, « Aucune IA » : à la fin de chaque inject il compare messages et décisions et émet des **signaux** (`ORPHAN_REQUEST`…, panneau « Lacunes émergentes (signaux) »), jamais des constats ; ce n'est **ni un siège ni un agent** ; **(2)** l'**institution `COORD`** (Conseil national de protection civile / comité de crise) du registre des mandats, qui **n'a pas de siège** (`seat: false`) | [DOC] `simulation/coord.py:1-2,52`, `simulation/engine.py:688-715` ; [TEST] `backend/tests/simulation/test_coord.py` |

| | |
|---|---|
| **Résultat attendu** | 9 lignes dans le tableau (Code, Nom, Rôle, Institution, Profil de modèle « aucun profil de modèle », Outils, Statut « actif »). Pour AG-HYDRO la colonne Rôle affiche « Système d'IA testé ». |
| **Vérification** | « Aperçu du prompt » de l'agent : le texte assemblé par le serveur affiche la mission, les instructions (dont `Objective:`), les mandats validés, **sans secret et sans mention de lacunes** ; badges « N mandats » et « N bases de connaissances ». [TEST] `backend/tests/agents/test_citations_prompt.py:62-74` ; `backend/tests/mandates/test_rising_waters_pack.py:84-103` (aucune consigne vide, toutes ≤ 1500 caractères, aucun indice de lacune). |
| **Statut** | NOT TESTED |

---

## § Permissions — Permissions documentaires des agents (agent × base)

**Où** : menu Préparer → « Accès aux connaissances » (`/studio/access`, titre de la page « Accès aux connaissances » / *Knowledge access*). **Geste** : cocher / décocher la case à l'intersection d'un agent (ligne) et d'une base (colonne) ; chaque case a pour nom accessible « `AG-MET` peut lire `CM` » (« {{agent}} peut lire {{kb}} »). Un message confirme : « AG-MET peut désormais lire CM » ou « …ne peut plus lire CM ». Preuve : [DOC] `AccessPage.tsx:20-70`, `agents/router.py:73-110`, `agents/service.py:198-221`.

**Principe** : un agent ne peut **jamais** retrouver un texte hors des bases cochées. Le périmètre est construit par le serveur à partir de l'instantané figé de l'exercice, pas par le modèle ; chaque passage renvoyé est revérifié, et une fuite est consignée comme `SCOPE_VIOLATION`. [TEST] voir « Preuve par les tests » ci-dessous.

**Colonnes disponibles à ce jour** : **CM** seulement (base construite et publiée). **GL** (base « précédents internationaux » / pratiques mondiales ; dans `setup-cm.json` elle s'appelle `INT`, que le script traduit en `GL`) **n'est pas construite : donnée indisponible, test bloqué**. Tant que GL n'existe pas, la matrice n'a qu'une colonne, et le script exige `--allow-missing-kbs` pour créer les agents.

| Agent | CM | GL (« INT » dans `setup-cm.json`) | Raison de l'accès | Conséquence du retrait |
|---|---|---|---|---|
| AG-HYDRO | coché (inscrit par le script) | non | aucune dans les faits : HydroSense **ne cherche jamais de documents** (consigne : « never searches documents »). L'accès CM est inscrit par `setup-cm.json` | **aucune** : agent non activable ; ni la préparation ni la matrice ne s'en plaignent pour un système d'IA (`AccessPage.tsx:35` exclut `ai_system` de l'avertissement) |
| AG-MET | coché | à cocher quand GL existe | CM : les textes camerounais d'où viennent ses mandats ; GL : précédents internationaux (aide de la base : « Pratiques mondiales » alimente les précédents internationaux) | il ne peut plus rechercher dans cette base (portée construite par siège, `simulation/snapshot.py:173-181`) ; s'il n'a plus aucune base, la préparation est **bloquée** (`agent.no_kb_grant`). Ses mandats validés restent dans son contexte tant qu'un autre siège lit encore la base (le filtre des mandats se fait par exercice, `snapshot.py:126`) |
| AG-DPC | coché | à cocher quand GL existe | idem | idem |
| AG-OPS | coché | à cocher quand GL existe | idem | idem |
| AG-ART | coché | à cocher quand GL existe | idem | idem |
| AG-MINSANTE | coché | à cocher quand GL existe | idem | idem |
| AG-DPA | coché | à cocher quand GL existe | idem | idem |
| AG-CTD | coché | **non** (`setup-cm.json` ne lui donne que CM) | CM : textes sur les collectivités (ex. CM-11). Pourquoi pas GL : **À DÉTERMINER** (le dépôt n'explique pas ce choix) | idem (sans CM : préparation bloquée) |
| AG-ANTIC | coché | à cocher quand GL existe | idem | idem |

Effet de bord à connaître : sans aucune base, la page affiche « Agents sans aucune base de connaissances : … » (sauf les systèmes d'IA).

### TEST : prouver qu'un agent ne peut pas accéder à une base non accordée

**Preuve par les tests automatisés** (non lancés ici, à citer, [TEST]) :

| Test | Ce qu'il prouve |
|---|---|
| `backend/tests/knowledge/test_scope_security.py` : `test_lexical_adapter_never_returns_out_of_scope`, `test_vector_adapters_never_return_out_of_scope`, `test_hybrid_service_property_canaries_never_returned`, `test_cross_workspace_isolation`, `test_sql_recheck_drops_out_of_scope_results_and_calls_back`, `test_default_violation_callback_logs_error`, `test_runtime_wires_violation_journal` | des « canaris » (passages d'une autre base ou d'un autre espace) ne sortent jamais ; une fuite d'un moteur défaillant est écartée puis journalisée `SCOPE_VIOLATION` (sans le texte) |
| `backend/tests/agents/test_runtime.py` : `test_search_uses_only_provided_scope`, `test_empty_scope_search_is_refused` | un modèle qui tente de s'attribuer une autre portée (champs `scope`, `kb_ids`, `seat`) est ignoré ; sans base accordée, `search_kb` est refusé (`no_knowledge_granted`) |
| `backend/tests/simulation/test_snapshot_readiness.py` : `test_search_scope_is_built_from_snapshot_only` (et la ligne `agent.no_kb_grant`, l. 128) | la portée vient de l'instantané ; un agent sans droit a une portée vide ; la préparation bloque |
| `backend/tests/simulation/test_human.py` : `test_player_limits_duplicates_and_scope_violation` | un moteur qui renvoie un passage d'une autre base : le passage est retiré de la réponse au joueur et un événement `ERROR` « SCOPE_VIOLATION » est consigné |
| `backend/tests/agents/test_api.py` : `test_kb_grants_and_access_matrix_and_clone` | accorder une base d'un autre espace est refusé (404) ; la matrice reflète les droits |
| `backend/tests/test_e2e_chain.py` | sur la chaîne complète : aucun événement `ERROR` ni `SCOPE_VIOLATION` |

**Procédure manuelle 1 — retrait de la seule base (réalisable avec CM seule)** [DOC] :
1. Page « Accès aux connaissances » : décocher la case « AG-CTD peut lire CM ».
2. Attendre : message « AG-CTD ne peut plus lire CM » ; la colonne « Impact » affiche « lit 0 base(s) » ; encadré « Agents sans aucune base de connaissances : AG-CTD ».
3. Créer ou ouvrir un exercice avec un siège CTD tenu par AG-CTD : « Préparation de l'exercice » affiche un problème bloquant « agent sans base de connaissances accordée (CTD) » (code `agent.no_kb_grant`) et « Marquer prêt » reste grisé.
4. Recocher la case ; « Revérifier » : le blocage disparaît.
Résultat attendu : un agent sans base ne peut pas démarrer. **Ceci prouve le blocage, pas l'isolation entre deux bases.**

**Procédure manuelle 2 — isolation entre deux bases (exige une seconde base publiée)** : [BLOCKED] tant que GL n'est pas construite. Avec une base d'essai publiée :
1. Créer une base d'essai (§ Bases de connaissances), y importer un document contenant un mot unique que CM ne contient pas, publier (exige le serveur d'embeddings : sinon la publication est refusée).
2. Accorder la base d'essai à **AG-DPC seulement** (pas à AG-MET).
3. Exercice « Modèle réel » (ou siège humain : `/play`, champ « Interroger vos bases de connaissances ») : faire chercher ce mot par MET.
4. Page « Audit et rejeu » : filtre « Type » = `RETRIEVAL`, « Siège » = `MET` : aucun résultat ne vient de la base d'essai. Filtre « Type » = `ERROR` : aucune ligne « SCOPE_VIOLATION ».
Le « Test de recherche » de la page d'une base est une recherche de l'**animateur** : il ne prouve rien sur les droits d'un agent.

| | |
|---|---|
| **Résultat attendu** | Matrice avec une case cochée par agent pour CM (9 cases) ; encadré vert « Chaque agent a au moins une base de connaissances » ; colonne « Impact » : « lit 1 base(s) » ; liste « Qui peut lire chaque base de connaissances » : CM → les 9 codes. |
| **Vérification** | Recharger la page : les cases restent cochées. La préparation d'un exercice ne signale aucun `agent.no_kb_grant`. |
| **Statut** | NOT TESTED (colonne GL : BLOCKED) |

---

## § Scénarios — Scénarios et injects

**Où** : menu Préparer → « Scénarios » (`/studio/scenarios`). **Boutons** : « Nouveau scénario » / *New scenario*, « Importer un YAML » / *Import YAML*. Page d'un scénario (clic sur son titre) : « Ajouter un inject » / *Add inject*, « Modifier », « Supprimer », flèches monter/descendre, « Exporter en YAML », « Marquer prêt » / « Revenir en brouillon ». Preuve : [DOC] `ScenariosPage.tsx:16-20,76-95`, `ScenarioBuilderPage.tsx`, `scenarios/schemas.py`, `demo/rising-waters/cm01-rising-waters.fr.alerte-scenario.yaml`.

**Voie recommandée** : « Importer un YAML » avec `demo/rising-waters/cm01-rising-waters.fr.alerte-scenario.yaml` (version française ; `…en.…` pour l'anglaise). Le fichier est limité à 1 Mo. Prérequis : les 9 institutions des destinataires et les actions existent déjà (une institution inconnue est **ignorée avec un avertissement** ; une action inconnue n'est refusée qu'à la préparation).

### Formulaire « Nouveau scénario » (saisie à la main)

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Code | identifiant du scénario | oui | texte, 1 à 64 caractères ; unique | `CM-01` | |
| Titre / Title | titre affiché | oui | 1 à 300 caractères | `Rising Waters — Cameroun` | |
| Description | résumé de l'histoire | non | texte, 8000 caractères au plus (aucune limite affichée) | texte du bloc ci-dessous | le fichier YAML le donne en anglais |
| Langue / Language | langue de l'exercice (les agents répondent dans cette langue) | non (**défaut du formulaire : `en`**) | texte de 2 à 8 caractères, saisie libre (pas de liste) | `fr` | oublier de changer `en` fait écrire les agents en anglais |
| Pays / Country | pays du scénario | non | liste | `Cameroun` | |
| (version) | — | — | **absent du formulaire** (valeur 1) | [ABS] | |

Texte de la description (copie exacte du fichier YAML) :

```text
A fictional AI system, HydroSense, forecasts floods and drafts alerts. Act 1 (Douala): a false alarm sent to every phone. Act 2 (Far North): a missed flood because sensors were down, a French-only alert, areas without coverage. Act 3: cholera, a request for phone location data, and a vendor processing data abroad.  — Fictional exercise. Not a real alert. HydroSense and all numbers in the events are invented; places and institutions are real.
```

### Formulaire « Ajouter un inject » / « Modifier l'inject »

Un **inject** est un événement du scénario, envoyé à des destinataires à un instant simulé. Les sièges ne sont **pas** définis dans le scénario (ils le sont dans l'exercice). Preuve : [DOC] `ScenarioBuilderPage.tsx:122-199`, `scenarios/schemas.py:66-130`. Les trois exemples complets plus bas donnent les valeurs exactes.

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Titre / Title | titre de l'événement (vu des agents) | oui | 1 à 300 caractères (le bouton « Enregistrer » reste grisé s'il est vide) | voir exemples | |
| Temps simulé / Simulated time | instant dans l'histoire ; aide : « Libellé libre, p. ex. J1 07:10 » | non (défaut `D1 06:00` à la création) | texte de 40 caractères au plus ; les formats `D1 06:00` / `J1 06:00` / `06:30` permettent le contrôle d'ordre (avertissement `inject.time_order`) | `D1 06:00` | le scénario CM-01 utilise le préfixe `D` (jour) |
| De / From | émetteur de l'événement (une **source**, pas un siège : `SENSORS`, `MEDIA`, `FIELD`, `PARLIAMENT`, ou une institution) | non | texte de 200 caractères au plus ; **aucune aide à la saisie** | voir exemples | un émetteur ne peut ni recevoir ni répondre |
| Texte / Text | contenu de l'événement (vu des agents, 900 premiers caractères) | non (avertissement `inject.empty_body` si vide) | 8000 caractères au plus | voir exemples | |
| Panne / Fault | mode de panne **étiqueté** par l'auteur ; la description du mode choisi s'affiche | non (défaut `none`) | `none` + 15 modes (libellés anglais : « False alarm (false_alarm) », « Spoofing (spoofing) »…) | voir exemples | **étiquette d'audit : jamais montrée aux agents** ; seul `llm_outage` change le comportement (l'agent tombe en décision de repli au tour 1). Les 12 modes de la spécification, `degraded_inputs` et `silent_institution` ne rendent **aucun** siège muet |
| Note de source / Source note | d'où l'événement est inspiré | non | texte de 2000 caractères au plus ; **aucune aide** | voir exemples | jamais montrée aux agents. Les notes de CM-01 citent d'anciens codes du prototype (« CM-S07 »…) : voir « Écarts » |
| Destinataires / Recipients | institutions qui reçoivent l'événement | **oui, au moins une** (`inject.no_recipient`) | cases = **codes** d'institutions (`MET`, `DPC`…), **aucune aide** | voir exemples | un destinataire doit avoir un **siège** dans l'exercice (sinon `inject.recipient_without_seat`) |
| Étiquettes / Tags | étiquettes descriptives de l'événement (cases) | non | `life_risk`, `rights_risk`, `harm_possible`, `ai_output_used_in_decision`, `public_communication`, `channel_abuse`, `foreign_actor`, `time_critical` | voir exemples | **jamais montrées aux agents** |
| Autres étiquettes (séparées par des virgules) / More tags (comma-separated) | étiquettes supplémentaires | non | chacune `^[a-z][a-z0-9_]{1,46}$` (minuscules, chiffres, tiret bas ; 2 à 47 caractères) ; **le format n'est pas indiqué à l'écran** | (vide) — facultatif, sans conséquence | un libellé en majuscules ou accentué est refusé |
| Exigences / Demands → « Ajouter une exigence » / *Add demand* | actions que l'événement exige ; aide : « Actions que cet événement exige. Celles que vous rédigez restent signalées « auteur du scénario » dans les rapports. » | non | par ligne : action (liste du catalogue), dérivation (défaut `Auteur du scénario`), justification (≤ 2000 caractères) | voir exemples | une ligne laissée sur « — » est refusée par le serveur ; ce sont des **actions proposées par le scénario**, pas des obligations juridiques établies |
| Sortie du système d'IA (JSON) / AI-system output (JSON) | sortie **écrite à l'avance** du système d'IA testé à cet événement ; aide : « Pour un système d'IA testé : sa sortie scénarisée à cet événement. » | non | un **objet JSON** valide (`{ … }`) ; sinon « JSON invalide. » | voir exemple 2 (et injects 8 et 14) | (vide) = facultatif, sans conséquence pour les injects qui ne viennent pas d'un système d'IA |

### Exemples complets (valeurs exactes du fichier YAML français)

**Exemple 1 — inject 1** (événement simple, sans panne ni sortie d'IA)

| Champ | Valeur exacte |
|---|---|
| Titre | `D1 06:00 — Les pluviomètres de Douala enregistrent 80 mm en 3 heures` |
| Temps simulé | `D1 06:00` |
| De | `SENSORS` |
| Texte | `Les pluviomètres de Douala enregistrent 80 mm en 3 heures. La prévision nationale annonce de fortes pluies jusqu'à midi.` |
| Panne | `none` |
| Note de source | `Inspiré de (références du prototype) : CM-S07` |
| Destinataires (cases) | `MET` |
| Étiquettes (cases) | (aucune case cochée) — facultatif, sans conséquence |
| Autres étiquettes | (vide) — facultatif, sans conséquence |
| Exigences | action `issue_weather_warning` · dérivation « Auteur du scénario » (`scenario_author`) · justification : Exigence écrite par l'auteur du scénario pour l'événement 1 (pas une obligation officielle). |
| Sortie du système d'IA (JSON) | (vide) — facultatif, sans conséquence |

**Exemple 2 — inject 2** (système d'IA HYDRO : avec « Sortie du système d'IA (JSON) »)

| Champ | Valeur exacte |
|---|---|
| Titre | `D1 06:20 — HydroSense : alerte ROUGE, crue du Wouri attendue dans 6 heures, probabilité 70 %` |
| Temps simulé | `D1 06:20` |
| De | `HYDRO` |
| Texte | `HydroSense : alerte ROUGE, crue du Wouri attendue dans 6 heures, probabilité 70 %. Projet de SMS : 'URGENT : grave inondation à Douala dans 6 heures. Rejoignez immédiatement les hauteurs.'` |
| Panne | `False alarm (false_alarm)` |
| Note de source | `Inspiré de (références du prototype) : SCN-01, GL-S06` |
| Destinataires (cases) | `MET`, `HYDRO` |
| Étiquettes (cases) | `ai_output_used_in_decision`, `life_risk`, `time_critical` |
| Autres étiquettes | (vide) — facultatif, sans conséquence |
| Exigences | action `validate_ai_forecast` · dérivation « Auteur du scénario » (`scenario_author`) · justification : Exigence écrite par l'auteur du scénario pour l'événement 2 (pas une obligation officielle). |
| Sortie du système d'IA (JSON) | voir le JSON ci-dessous |

Contenu à coller dans « Sortie du système d'IA (JSON) » :

```json
{
  "source": "HydroSense (système d'IA FICTIF)",
  "statement": "HydroSense : alerte ROUGE, crue du Wouri attendue dans 6 heures, probabilité 70 %. Projet de SMS : 'URGENT : grave inondation à Douala dans 6 heures. Rejoignez immédiatement les hauteurs.'"
}
```

Les injects **8** et **14** (émetteur HYDRO) portent le même type de sortie :

```json
{
  "source": "HydroSense (système d'IA FICTIF)",
  "statement": "HydroSense : JAUNE, faible risque de crue sur le Logone. (Non affiché sur le tableau de bord : 3 des 7 capteurs du fleuve sont hors service depuis 48 heures.)"
}
```

```json
{
  "source": "HydroSense (système d'IA FICTIF)",
  "statement": "Le fournisseur de HydroSense propose d'analyser les données de localisation sur ses serveurs cloud hors du Cameroun, 'sous 24 heures'."
}
```

**Exemple 3 — inject 7** (panne `spoofing`, étiquette `channel_abuse`) — noter que le titre du fichier est **coupé en cours de phrase** (« …pour l'a ») par le générateur du pack : recopiez-le tel quel.

| Champ | Valeur exacte |
|---|---|
| Titre | `D1 15:00 — Un faux SMS de suite circule : 'Barrage rompu, évacuez maintenant, inscrivez-vous pour l'a` |
| Temps simulé | `D1 15:00` |
| De | `OPS` |
| Texte | `Un faux SMS de suite circule : 'Barrage rompu, évacuez maintenant, inscrivez-vous pour l'aide ici : [lien frauduleux]'. Il imite l'alerte précédente.` |
| Panne | `Spoofing (spoofing)` |
| Note de source | `Inspiré de (références du prototype) : CM-S04` |
| Destinataires (cases) | `ANTIC`, `ART` |
| Étiquettes (cases) | `channel_abuse` |
| Autres étiquettes | (vide) — facultatif, sans conséquence |
| Exigences | action `block_spoofed_alert` · dérivation « Auteur du scénario » (`scenario_author`) · justification : Exigence écrite par l'auteur du scénario pour l'événement 7 (pas une obligation officielle). |
| Sortie du système d'IA (JSON) | (vide) — facultatif, sans conséquence |

**Même inject 2 dans le fichier YAML** (ce que l'import lit ; `system_output` est un dictionnaire, équivalent exact du JSON ci-dessus) :

```yaml
seq: 2
sim_time: D1 06:20
title: 'D1 06:20 — HydroSense : alerte ROUGE, crue du Wouri attendue dans 6 heures, probabilité 70 %'
body: 'HydroSense : alerte ROUGE, crue du Wouri attendue dans 6 heures, probabilité 70 %. Projet de SMS : ''URGENT : grave inondation à Douala dans 6 heures. Rejoignez immédiatement les hauteurs.'''
from_actor: HYDRO
fault_mode: false_alarm
recipients:
- MET
- HYDRO
tags:
- ai_output_used_in_decision
- life_risk
- time_critical
demands:
- action_code: validate_ai_forecast
  derivation: scenario_author
  justification: Exigence écrite par l'auteur du scénario pour l'événement 2 (pas une obligation officielle).
system_output:
  source: HydroSense (système d'IA FICTIF)
  statement: 'HydroSense : alerte ROUGE, crue du Wouri attendue dans 6 heures, probabilité 70 %. Projet de SMS : ''URGENT : grave inondation à Douala dans 6 heures. Rejoignez immédiatement les hauteurs.'''
source_note: 'Inspiré de (références du prototype) : SCN-01, GL-S06'
```

### Format de `system_output` et quand il est nécessaire
* C'est un **dictionnaire JSON** (objet) à clés libres. Dans CM-01 : `source` (« HydroSense (système d'IA FICTIF) ») et `statement` (le texte de la sortie).
* Les destinataires **autres que HYDRO** le reçoivent dans leur boîte et leur prompt affiche « AI system output received: … » (limité à 600 caractères). Un destinataire humain ne le voit pas dans son écran (seuls titre et texte sont rendus).
* Il est **facultatif** : le texte de l'inject (`body`) suffit à informer les agents. Il ne sert que si l'événement doit présenter la sortie d'un système d'IA **distincte** du texte, ce qui est le cas de HYDRO. Dans CM-01 le texte et la sortie sont identiques pour les injects 2, 8, 14.
* Un JSON qui n'est pas un objet (tableau, nombre) est refusé par le serveur.

### Destinataires : existence et sièges (vérifié sur le YAML et `setup-cm.json`)

Les 15 injects ont **41** destinataires (lignes d'institution). Les 9 institutions citées existent toutes dans `setup-cm.json` ; **COORD et ONR ne sont destinataires d'aucun inject** (ils n'ont pas de siège : voir § Institutions). Chaque destinataire est une institution qui doit recevoir un siège dans l'exercice (« Ajouter les institutions du scénario »), avec **un cas particulier : HYDRO**.

| Inject | Temps simulé | De | Destinataires | `system_output` | Existence / siège |
|---|---|---|---|---|---|
| 1 | `D1 06:00` | `SENSORS` | `MET` | — | institution existante ; siège à créer dans l'exercice |
| 2 | `D1 06:20` | `HYDRO` | `MET`, `HYDRO` | oui | institution existante ; siège à créer dans l'exercice ; **HYDRO : siège jamais activé** |
| 3 | `D1 06:45` | `MET` | `DPC` | — | institution existante ; siège à créer dans l'exercice |
| 4 | `D1 07:10` | `DPC` | `OPS` | — | institution existante ; siège à créer dans l'exercice |
| 5 | `D1 08:30` | `MEDIA` | `DPC`, `CTD`, `ART` | — | institution existante ; siège à créer dans l'exercice |
| 6 | `D1 12:00` | `MEDIA` | `MET`, `DPC`, `OPS`, `ART`, `CTD` | — | institution existante ; siège à créer dans l'exercice |
| 7 | `D1 15:00` | `OPS` | `ANTIC`, `ART` | — | institution existante ; siège à créer dans l'exercice |
| 8 | `D11 04:00` | `HYDRO` | `MET`, `HYDRO` | oui | institution existante ; siège à créer dans l'exercice ; **HYDRO : siège jamais activé** |
| 9 | `D11 09:00` | `FIELD` | `CTD` | — | institution existante ; siège à créer dans l'exercice |
| 10 | `D11 11:30` | `DPC` | `DPC`, `OPS` | — | institution existante ; siège à créer dans l'exercice |
| 11 | `D11 18:00` | `FIELD` | `MET`, `DPC`, `OPS`, `ART`, `MINSANTE`, `CTD` | — | institution existante ; siège à créer dans l'exercice |
| 12 | `D25 10:00` | `FIELD` | `MINSANTE` | — | institution existante ; siège à créer dans l'exercice |
| 13 | `D26 09:00` | `MINSANTE` | `MINSANTE`, `OPS`, `DPA` | — | institution existante ; siège à créer dans l'exercice |
| 14 | `D26 14:00` | `HYDRO` | `DPA`, `MINSANTE`, `HYDRO` | oui | institution existante ; siège à créer dans l'exercice ; **HYDRO : siège jamais activé** |
| 15 | `D27 10:00` | `PARLIAMENT` | `MET`, `DPC`, `OPS`, `ART`, `MINSANTE`, `DPA`, `CTD`, `ANTIC` | — | institution existante ; siège à créer dans l'exercice |

**HYDRO, destinataire des injects 2, 8 et 14.** HYDRO a un siège (obligatoire pour la préparation), et le moteur dépose bien l'inject dans sa boîte, mais le siège **n'est jamais activé** : seuls les sièges « activables » (rôle `institution`) sont appelés (`simulation/engine.py:681 et :709`). La boîte de HYDRO reste donc non lue ; HYDRO ne peut ni recevoir ni écrire de message (un joueur humain voit « HYDRO » dans sa liste « À », mais le serveur le refuse : « destinataire invalide (…non activable) », `simulation/human.py:203`). L'estimation d'appels de la page du scénario compte ces 3 destinataires ; celle de la préparation les exclut.

### Intégrité : ce qu'on ne montre jamais, ce qu'on ne présente jamais comme connu
* **Panne et étiquettes** : stockées dans l'inject et dans le journal, **jamais dans le prompt d'un agent** ; le prompt n'utilise que le titre, l'heure, l'émetteur, le texte, la langue et la sortie d'IA ([TEST] `backend/tests/agents/test_citations_prompt.py:62-74` : aucune panne, étiquette, action exigée ni note de source dans le prompt). **Réserve** : la tâche d'un **siège humain** affiche les étiquettes à l'écran et son API renvoie aussi `fault_mode` dans sa boîte (`simulation/human.py:110-111`, `PlayerPage.tsx:79`) — voir « Écarts ».
* **Lacunes visées** : le scénario ne contient aucune lacune attendue ; le fichier de référence de l'auteur (`demo/rising-waters/lacunes-attendues.PRIVE.json`) n'est **jamais importé** ni lu par l'application. Les « exigences » d'un inject sont des actions que le scénario **demande**, pas la liste des défaillances à trouver. Ne présentez pas les lacunes comme connues d'avance ; elles se déterminent à la revue (§ Lacunes).

| | |
|---|---|
| **Résultat attendu** | Import : « Scénario importé (N avertissement(s)) » ; la ligne `CM-01 — Rising Waters — Cameroun`, langue `fr`, 15 injects. Page du scénario : « Contrôles en direct » → « Aucun problème bloquant » ; « Appels au modèle estimés : jusqu'à 492 (plafond 199) » (41 destinataires × 3 tours × 4 pas ; le plafond affiché est celui du serveur, pas celui d'un exercice) ; « 7 mode(s) de panne distinct(s) utilisé(s) ». Un avertissement `scenario.budget_estimate` est normal tant que le plafond est 199. Tableau « Qui reçoit quoi » : une ligne par inject. |
| **Vérification** | Ouvrir l'inject 2 : « Sortie du système d'IA (JSON) » non vide. Défaut volontaire à essayer : décocher tous les destinataires d'un inject → il s'enregistre, mais « Contrôles en direct » affiche l'erreur « inject N sans destinataire » (bloquante pour la préparation). |
| **Statut** | NOT TESTED |

---

## § Exercices — Exercices et sièges

**Où** : menu Jouer → « Exercices » (`/studio/exercises`). **Bouton** : « Nouvel exercice » / *New exercise*, puis « Créer ». La page de l'exercice s'ouvre en statut « brouillon ». Preuve : [DOC] `ExercisesPage.tsx:46-80`, `ExercisePage.tsx`, `simulation/schemas.py:11-26`, `simulation/common.py:34-62`, `simulation/readiness.py`.

### Formulaire « Nouvel exercice »

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Scénario / Scenario | histoire à jouer | oui | liste `code — titre` | `CM-01 — Rising Waters — Cameroun` | |
| Titre / Title | nom de l'exercice | non | texte, 1 à 300 caractères ; vide = titre déduit | **A** `Rising Waters CM — autopilot scripted (SANS IA)` · **B** `Rising Waters CM — autopilot MODÈLE RÉEL` | titres utilisés par `seed_rising_waters.py` |
| Mode d'exécution / Execution mode | qui produit les réponses ; aide : « Seul « Modèle réel » prouve que l'IA fonctionne. Les exécutions scénarisées et les rejeux sont étiquetés SANS IA partout. » | non (**défaut du formulaire : `Modèle réel`**) | `ai` **Modèle réel** / Real model · `scripted` **Scénarisé (SANS IA)** / Scripted (NO AI) · `cassette` **Rejeu de cassette** / Cassette replay | **A** `Scénarisé (SANS IA)` · **B** `Modèle réel` | **« Rejeu de cassette » est inutilisable avec l'API actuelle** : il exige un réglage `cassette`, mais les réglages d'exercice refusent toute clé hors liste (`ExerciseSettings`, `extra="forbid"`, `simulation/common.py:45-50`) et aucune cassette n'existe sur disque. Ne pas l'utiliser |
| Rythme / Pace | **Manuel (pas à pas)** : rien n'avance sans un clic sur « Pas » à chaque inject · **Automatique** : les injects s'enchaînent · **Automatique avec délai** : idem avec un délai (non réglable dans l'interface, 0 s par défaut) | non (**défaut du formulaire : `Automatique`**) | `manual`, `auto`, `auto_delay` | `Automatique` (A et B) | en Manuel, un « Pas » exécute **un inject complet** (tous les tours et tous les sièges) ; le bouton « Pas » n'est utilisable qu'en rythme manuel |
| Budget d'appels au modèle / Model call budget | plafond d'appels au modèle ; l'exercice se met en **pause** quand il est épuisé ; aide : « Laisser vide pour la valeur par défaut du serveur. » | non | entier ≥ 1 | **A** `330` · **B** `450` (à ajuster, règle ci-dessous) | **vide = 199 (valeur du serveur) : la préparation de CM-01 est alors BLOQUÉE** (492 appels estimés > 1,5 × 199) |

Le champ « Code » de l'exercice (`EX-001`…) n'est pas dans le formulaire : il est attribué automatiquement.

### Règle d'estimation du budget (à lire avant de saisir le nombre)

* **Estimation = destinataires × 3 tours × pas** (3 tours maximum par inject, `contracts.py:20` ; « pas » = 4, la plus petite valeur de « Étapes max par activation » parmi les agents).
* Page du scénario : 41 destinataires (HYDRO compté) × 3 × 4 = **492** (`scenarios/service.py:319`).
* Préparation de l'exercice : 38 destinataires activables (HYDRO exclu, sièges humains exclus) × 3 × 4 = **456** (`simulation/readiness.py:163-167`).
* **Blocage** si l'estimation > **1,5 × budget** ; **avertissement** si l'estimation > budget. Donc **le budget minimal qui ne bloque pas est 328** (492 ÷ 1,5).
* **450 pour un exercice « Modèle réel » complet** : au-dessus du minimum non bloquant (328) et sous l'estimation maximale (492/456, qui suppose 4 appels à chaque tour de chaque destinataire, ce qui n'arrive pas : seuls les sièges qui ont reçu un message sont réactivés aux tours 2 et 3). Deux avertissements `budget.high` / `scenario.budget` sont **attendus** avec 450. La valeur est **à ajuster** : lire la jauge « Budget » (« n/450 appels au modèle ») dans la salle ; en cas de pause, saisir « Étendre le budget de » puis « Reprendre ». Elle n'a **pas été mesurée avec un vrai modèle** (aucune mesure dans le dépôt).
* **330 pour le SANS IA** : valeur par défaut du script ; le fournisseur scripté consomme 2 appels par activation. Le plafond du serveur (`ALERTE_MAX_LLM_CALLS`, 199) ne s'applique pas quand l'exercice a son propre budget.

### Sièges (page de l'exercice, section « Sièges »)

Un siège = la place d'une institution dans l'exercice. Boutons : « Ajouter les institutions du scénario » / *Add institutions of the scenario* (crée un siège par institution destinataire d'un inject : **9 sièges**, jamais COORD ni ONR), « Ajouter un siège », « Enregistrer les sièges ». Le bouton « Lien du siège » apparaît pour un siège humain une fois les sièges enregistrés.

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Code | nom du siège | oui | `^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}$` ; aucune validation locale | le **code de l'institution** (`MET`, `DPC`…) | pré-rempli par « Ajouter les institutions du scénario » |
| Institution | institution tenue | oui | liste des codes | le même code | |
| Joué par / Played by | qui tient le siège | oui (défaut `Agent IA`) | `Agent IA` (agent) · `Humain` (human) · `Scénarisé` (scripted) | `Agent IA` pour les 9 sièges (configurations A et B) | `Scénarisé` n'a **aucun effet propre** : seul le mode d'exécution de l'exercice compte |
| Agents | agent affecté au siège | oui si `Agent IA` ou `Scénarisé` | liste des codes d'agents (non archivés) | `AG-` + code (`AG-MET`) ; HYDRO : `AG-HYDRO` | pré-rempli avec le premier agent de l'institution ; pour un siège humain, l'agent sert à la reprise |
| Nom de l'humain / Human name | nom du joueur | **oui pour `Humain`** (`seat.human_unnamed`) | texte, 200 caractères au plus | (vide) — non applicable à ce rôle (sièges agents) | voir configuration C |

**Les 9 sièges des configurations A et B** :

| Code | Institution | Joué par | Agents | Nom de l'humain |
|---|---|---|---|---|
| `HYDRO` | `HYDRO` | Agent IA | `AG-HYDRO` | (vide) — non applicable à ce rôle |
| `MET` | `MET` | Agent IA | `AG-MET` | (vide) — non applicable à ce rôle |
| `DPC` | `DPC` | Agent IA | `AG-DPC` | (vide) — non applicable à ce rôle |
| `OPS` | `OPS` | Agent IA | `AG-OPS` | (vide) — non applicable à ce rôle |
| `ART` | `ART` | Agent IA | `AG-ART` | (vide) — non applicable à ce rôle |
| `MINSANTE` | `MINSANTE` | Agent IA | `AG-MINSANTE` | (vide) — non applicable à ce rôle |
| `DPA` | `DPA` | Agent IA | `AG-DPA` | (vide) — non applicable à ce rôle |
| `CTD` | `CTD` | Agent IA | `AG-CTD` | (vide) — non applicable à ce rôle |
| `ANTIC` | `ANTIC` | Agent IA | `AG-ANTIC` | (vide) — non applicable à ce rôle |

### § Exercices (A) — Configuration A : autopilot SANS IA (parcours A)

| Champ | Valeur à saisir |
|---|---|
| Scénario | `CM-01 — Rising Waters — Cameroun` |
| Titre | `Rising Waters CM — autopilot scripted (SANS IA)` |
| Mode d'exécution | **`Scénarisé (SANS IA)`** (≠ défaut du formulaire : à changer) |
| Rythme | `Automatique` |
| Budget d'appels au modèle | `330` |
| Sièges | les 9 du tableau ci-dessus, tous « Agent IA » (le mode scripté force le fournisseur de test) |
| Profil de modèle des agents | (vide) — non requis dans le mode testé |

Attendu : bandeau **« SANS IA — exécution scénarisée, ne prouve pas que l'IA fonctionne »** ; en salle, **0 message** sur le tableau de coordination (le fournisseur scripté fait « chercher puis décider » et ne poste jamais ; décisions « Act within the documented mandate »).

### § Exercices (B) — Configuration B : autopilot Modèle réel (parcours B)

| Champ | Valeur à saisir |
|---|---|
| Scénario | `CM-01 — Rising Waters — Cameroun` |
| Titre | `Rising Waters CM — autopilot MODÈLE RÉEL` |
| Mode d'exécution | **`Modèle réel`** (valeur par défaut du formulaire) |
| Rythme | `Automatique` |
| Budget d'appels au modèle | `450` (à ajuster) |
| Sièges | les 9 du tableau ci-dessus, tous « Agent IA » |
| Profil de modèle des agents | (vide) = serveur par défaut du `.env`, ou un profil **testé** (§ Profils). **Modèle : À DÉTERMINER** (nom exact du modèle servi par votre serveur) |

Prérequis : serveur de modèle joignable (`ALERTE_LLM_BASE_URL`, `ALERTE_LLM_MODEL`, [configuration](configuration-env.md)) ; sinon la préparation affiche `provider.test_failed` / `agent.no_model_profile` (bloquant) et rien n'est lancé. **BLOCKED** tant que le modèle n'est pas fourni. Le script `seed_rising_waters.py --from 7 --until 8 --ai-mode ai --max-calls 450` crée cet exercice **sans le lancer** (catalogue, n° 22).

### Configuration « Human in the Seat » (séparée de A et B)

Même exercice que A ou B, avec **un seul siège changé** :

| Champ | Valeur à saisir |
|---|---|
| Siège | `OPS` (ou `ART`) |
| Joué par | `Humain` |
| Agents | `AG-OPS` (reste affecté : il sert à la reprise si l'humain ne répond pas) |
| Nom de l'humain | `Joueur Test` (nom libre ; exemple du guide historique) |

Puis « Enregistrer les sièges » ; ensuite le bouton « Lien du siège » affiche un lien `…/play#t=…` **une seule fois** (valable 24 h par défaut, non réglable ici ; à ouvrir dans une fenêtre privée). Le délai de réponse humaine (900 s) et la reprise par l'agent ne sont pas réglables dans l'interface (réglages d'exercice `human_deadline_s`, `human_fallback` : API seulement). Un siège humain **n'est pas compté** dans l'estimation de budget de la préparation.

### Préparation, lancement

Section « Préparation de l'exercice » : « Revérifier », « Marquer prêt », « Lancer l'exercice » (actif seulement quand l'exercice est « prêt » et que les sièges sont enregistrés).

| | |
|---|---|
| **Résultat attendu** | En-tête : `EX-00N · Scénarisé (SANS IA) · Rythme: auto` (A) ou `· Modèle réel · Rythme: auto` (B), badge « brouillon ». Préparation : « Prêt » ou « N avertissement(s) » sans bloquant. Avertissements **attendus** : « registre non 'reviewed_complete' », « aucun mandat validé : l'agent n'aura aucune base » (institutions sans mandat validé), `budget.high` / `scenario.budget` (450), couverture documentaire si une liste de documents attendus existe. Message : « Exercice marqué prêt » après « Marquer prêt ». |
| **Vérification** | Aucun blocage parmi : `seats.none`, `seat.no_controller`, `seat.human_unnamed`, `agent.missing`, `agent.no_kb_grant`, `kb.not_ready`, `inject.recipient_without_seat`, `inject.unknown_action`, `budget.exceeds`, `provider.test_failed`. Après « Lancer l'exercice » : la salle `/room/<id>` s'ouvre, jauge « Budget » `n/330` (A) ou `n/450` (B), suivie de « appels au modèle ». Ne contournez jamais un blocage : corrigez-le. |
| **Statut** | NOT TESTED (B : BLOCKED sans modèle) |

---

## § Autres formulaires utiles aux tests

### 12.1 Salle de simulation : commandes de l'animateur (`/room/<id>`)

Boutons de l'en-tête (preuve : [DOC] `RoomPage.tsx:25-27,95-109`) : « Pause » · « Reprendre » · « Pas » (rythme manuel seulement) · liste « Rythme » (Manuel / Automatique / Automatique avec délai) · « Surprise » · « Arrêter » (avec confirmation). Quand la pause vient du plafond d'appels, un champ numérique **« Étendre le budget de »** (0 à 100000) apparaît à côté de « Reprendre ». Sur une carte de siège : « Donner à l'agent IA » / « Donner à un humain » avec le champ « Nom de l'humain » (obligatoire pour « Donner à un humain »).

#### Formulaire « Surprise » (événement ajouté en cours d'exercice)

Bouton « Surprise » (actif en cours ou en pause), puis « Envoyer la surprise ». Backend : titre 1–300, texte 1–4000, au moins un destinataire (`SurpriseArgs`).

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Titre / Title | titre de l'événement | oui | 1 à 300 caractères | **À DÉTERMINER** : aucune surprise n'est définie pour CM-01 dans le dépôt. Exemple de test (pas une donnée du dépôt) : `Test de surprise — message de contrôle` | |
| Texte / Text | contenu | oui | 1 à 4000 caractères | exemple de test : `Message de contrôle de l'animateur : confirmez la bonne réception.` | |
| Destinataires / Recipients | sièges destinataires | oui, au moins un | cases = codes de **sièges** | exemple de test : `MET` | ne cochez pas `HYDRO` (siège jamais activé) |
| (panne, étiquettes) | — | — | **aucun champ dans l'interface** ; valeur `none` figée (le serveur accepte d'autres valeurs : API seulement) | [ABS] | l'événement est marqué « surprise » dans le journal |

Résultat attendu : message « Surprise envoyée » ; l'événement apparaît dans « Événements » avec le badge « surprise ». Statut : NOT TESTED.

### 12.2 Siège humain (`/play#t=…`) : recherche, conseiller, message, décision

Preuve : [DOC] `PlayerPage.tsx:60-230`, `simulation/schemas.py:114-145`, `simulation/human.py`. Le joueur ne voit que sa boîte.

| Formulaire / champ (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (exemple) | Remarque |
|---|---|---|---|---|---|
| « Interroger vos bases de connaissances » / *Search your knowledge bases* + « Rechercher » | recherche limitée à ses bases (aide : « La recherche est limitée à vos bases de connaissances. Le conseiller répond aux questions mais ne décide jamais à votre place. ») | non | texte, 1 à 300 caractères | `transfert de données à caractère personnel` | chaque résultat a un bouton « Citer cet extrait » |
| « Interroger le conseiller juridique » / *Ask the legal adviser* + « Demander » | question au conseiller intégré (aide : « Décompté de votre limite. ») | non | texte, 1 à 500 caractères | `Le service météorologique peut-il ordonner une évacuation ?` | **limite : 2 par inject quelle que soit la valeur réglée sur l'agent** (voir « Écarts ») |
| À / To | destinataire du message | oui | liste des **autres** sièges, **HYDRO compris** (refusé ensuite) | `DPC` | |
| Type | nature du message | non (défaut `INFO`) | `INFO`, `REQUEST`, `DECISION`, `OBJECTION`, `GAP_FLAG` | `INFO` | **Un `REQUEST` est refusé au tour 2** (sa réponse tomberait au tour 3, où l'on ne peut plus poster) ; à partir du dernier tour (3), **aucun message n'est accepté** : on ne peut que décider (`human.py`, `engine.py` `route_messages`, `runtime.py` `_do_post`) |
| Message | contenu | oui | texte, 1 à 1500 caractères | `Pluies intenses confirmées sur Douala.` | « Préparer le message » : envoyé à la clôture de votre tour. Pas de champ pour **répondre** à une demande ni pour « terminer sans décision » : [ABS] |
| Action entreprise ou refusée / Action taken or refused | la décision, en une phrase | oui | texte, 500 caractères au plus | texte libre de test, ex. `Demander à DPC le texte validé et le nom du validateur` | |
| Code d'action (facultatif) / Action code (optional) | action du catalogue visée | non | doit être dans le catalogue ; **aucune liste proposée** | `send_mass_alert` (pour l'inject 4, OPS) | hors catalogue : refus serveur |
| Issue / Outcome | nature de la décision | oui (défaut `Agit`) | `Agit` (act) · `Refuse` (decline) · `Renvoie` (refer) · `Aucune base légale trouvée` (no_legal_basis_found) | `Aucune base légale trouvée` (valide sans citation) | |
| Confiance / Confidence | confiance du joueur | oui (défaut `medium`) | `low`, `medium`, `high` | `medium` | |
| Niveau de preuve / Evidence level | solidité de la base | oui (**défaut `documented`**) | `documented`, `inferred`, `assumed` | `inferred` (ne pas laisser « documented » par habitude) | |
| Justification publique / Public rationale | motif lisible par tous | oui | 1 à 280 caractères (compteur « n/280 caractères ») | texte libre de test | |
| Options envisagées (une par ligne) / Options considered (one per line) | alternatives | non | une par ligne | (vide) — facultatif, sans conséquence | |
| Base légale / Legal basis : identifiant de l'extrait (`chunk_id`), Article, Citation exacte de l'extrait | passage cité | **oui sauf pour « Aucune base légale trouvée »** | citation exacte d'au moins 20 caractères, présente dans l'extrait | **À DÉTERMINER** : l'identifiant et la citation se copient depuis les résultats de recherche via **« Citer cet extrait »** | une citation fausse est refusée (« la citation ne figure pas dans le texte de l'extrait ») |

Résultat attendu : « Décision enregistrée » ; la tâche disparaît (« Rien à faire pour l'instant »). Vérification : en salle, la carte du siège affiche la décision avec « Vérifié » (citation contrôlée) ou « Non vérifié » ; « Trace de décision ». Statut : NOT TESTED. Champs absents : `gap_flags` (envoyé vide), « Ce que je sais / ne sais pas » [ABS].

### 12.3 § Lacunes — Lacunes : filtres, revue, plan d'amélioration (`/gaps`, menu Analyser → « Analyse des lacunes »)

Preuve : [DOC] `GapsPage.tsx:60-130,200-322`, `gaps/schemas.py:99-111,155-161`. **Ne présentez aucune lacune comme connue d'avance** : elles sont des **propositions** tant qu'un humain ne les a pas relues. Les filtres sont dans le bloc « Filtres ».

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Exercice / Exercise | exercice analysé | non (défaut : le dernier exercice joué) | liste `code — titre` | l'exercice de votre run | « Tous » mélange les exercices |
| Institution | filtre | non | liste de codes | « Tous » (valeur par défaut, `common.all`) | |
| Code | code de règle de lacune | non | texte (exemple fantôme « G1 ») | (vide) — facultatif, sans conséquence | |
| Catégorie / Category | filtre | non | texte libre | (vide) — facultatif, sans conséquence | |
| Gravité / Severity | niveau | non | Élevée (3) · Moyenne (2) · Faible (1) | « Tous » | |
| Statut de revue / Review status | état de la revue humaine | non | `proposed`, `confirmed`, `disputed`, `rejected` | « Tous » | |
| Base de preuve / Evidence basis | | non | `documented`, `observed`, `inferred`, `hypothesis` | « Tous » | |
| Origine / Origin | | non | `rule`, `coordinator_signal`, `agent_hypothesis`, `imported` | « Tous » | |
| Inclure les lacunes de détections remplacées / Include gaps from superseded detections | | non | case | décochée | |

**Revue humaine** (fiche d'une lacune, section « Revue humaine ») :

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Décision / Decision | acte de revue | oui (défaut `Confirmer`) | `Confirmer`, `Contester`, `Rejeter`, `Commenter seulement`, `Rouvrir` | `Commenter seulement` pour un simple essai de formulaire | **ne « Confirmer » qu'après avoir lu la chaîne de preuves** : aucune lacune n'est confirmée parce qu'un agent l'a dite |
| La lacune reflète-t-elle la réalité ? / Does the gap reflect reality? | jugement ; aide : « Alimente la mesure T4 (lacunes non inventées). » | non | `Réelle`, `Partiellement réelle`, `Non réelle` | (vide) — facultatif, sans conséquence | à remplir par l'expert qui juge |
| Motif / Reason | explication | **oui pour Contester et Rejeter** (« Un motif est requis pour contester ou rejeter. ») | texte libre | `Essai du formulaire de revue : aucune confirmation.` | l'historique de revues garde tout |

Bouton « Enregistrer la revue » → message « Revue enregistrée » et une ligne dans « Historique des revues ». **Plan d'amélioration** (même fiche) : « Description » (obligatoire), « Responsable » (institution), « Échéance » (date), « KPI » (texte), bouton « Ajouter une action » : à saisir seulement comme recommandation, séparée des constats. Statut : NOT TESTED.

### 12.4 § Rapports — Rapports (`/reports`, menu Analyser → « Rapports »)

Preuve : [DOC] `ReportsPage.tsx:25-110`, `reports/schemas.py`.

| Formulaire / champ (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| « Générer un rapport » → Exercice / Exercise + « Générer » | rapport d'un exercice terminé ou arrêté | oui | liste des exercices **hors brouillon et prêt** | l'exercice de votre run | message « Rapport généré » ; chaque clic crée un **nouveau** rapport (v1) |
| « Publier (verrouiller) » (fiche d'une version) | fige la version | — | bouton | — | message « Version publiée » ; une version publiée n'est plus modifiable |
| « Télécharger PDF / MD / JSON / CSV / XLSX » | exports d'une version | — | 5 formats (pas de HTML) | PDF et MD | |
| « Importer un rapport antérieur » → Rapport / Report (titre), Fichier de rapport / Report file, « Importer » | joint une analyse passée (étiquetée « Analyse antérieure », jamais mélangée aux lacunes de l'exercice) | fichier oui ; titre non (défaut : nom du fichier) | `.pdf`, `.docx`, `.md` | **À DÉTERMINER** : aucun rapport antérieur fourni par le dépôt | |
| Constats extraits : Titre du constat / Finding title, Texte / Text, Code / Code, Page / Page + « Ajouter un constat » | constats saisis à côté d'un rapport importé | titre oui ; autres non | page entier ≥ 1 ; code ≤ 16 caractères | (vide) — non requis dans le mode testé | |
| Comparer deux versions : Exercice A / Exercice B (listes de versions `v1`, `v2`) | écart entre versions d'un rapport | non | liste | `v1` et `v2` (si deux versions existent) | |

Résultat attendu : un rapport avec les empreintes de l'instantané et de la tête du journal ; bandeau SANS IA pour un exercice scénarisé. Statut : NOT TESTED.

### 12.5 Évaluation (`/evaluation`, menu Analyser → « Évaluation »)

Preuve : [DOC] `EvaluationPage.tsx`, `evaluation/router.py:38-140`, `evaluation/schemas.py`, `evaluation/service.py:61-93`.

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Exercice / Exercise | exercice évalué | oui pour voir les mesures | liste (hors brouillon et prêt) | l'exercice de votre run | boutons « Calculer » / « Recalculer » par mesure T1 à T6 ; une mesure impossible est « non calculé », jamais 0 |
| T1 : base de connaissances testée / T1: knowledge base tested | base évaluée | pour T1 | liste des bases | `CM` | T1 reste « non calculé » sans jeu de questions (voir ci-dessous) |
| T3 : scénario (fixtures scellées) / T3: scenario (sealed fixtures) | scénario dont les lacunes attendues sont scellées | pour T3 | liste de codes de scénarios | `CM-01` | exige des fixtures scellées (voir ci-dessous) |
| T5 : identifiants d'exercices clonés (séparés par des virgules) / T5: cloned exercise ids (comma-separated) | exercices clonés à comparer | pour T5 | identifiants séparés par des virgules ; aide : liste des clones | (vide) — non requis dans le mode testé | |
| Relu par / Reviewed by | nom du relecteur | pour enregistrer un scorecard | texte | votre nom | |
| Réponses du scorecard (par critère) | `Oui` / `Partiel` / `Non` / `Non évalué` | non | liste ; bouton « Enregistrer N réponse(s) » | selon votre jugement | le bouton « Évaluation par l'IA » lance un juge IA : ses réponses sont « IA — à relire » tant qu'un humain ne les valide pas avec son nom |

**Import de questions (T1)** et **sceau des lacunes attendues (T3)** : **[ABS] dans l'interface**, API seulement.
* Questions : `POST /api/v1/evaluation/kbs/<kb_id>/questions/import` (fichier **CSV** ≤ 2 Mo, colonnes obligatoires `question` et `expected_doc_code`, facultatives `expected_article`, `lang`, `category`). Le fichier du dépôt `knowledge_bases/evaluation/questions.jsonl` (50 questions) est un **JSONL aux champs différents** (`expected_document`, `expected_article`, `question_language`…) : il **n'est pas importable tel quel** ; aucune commande de conversion n'a été trouvée → **À DÉTERMINER**.
* Lacunes attendues : `POST /api/v1/evaluation/fixtures` avec `scenario_code`, `expected_gap_key` (empreinte d'une lacune, 8 à 64 caractères), `label`, `description`. Ces valeurs viennent de l'auteur indépendant du scénario : **À DÉTERMINER** (le fichier privé ne se lit ni ne s'importe ici : « ne jamais importer » ; un sceau ne se modifie plus).
Statut : NOT TESTED.

### 12.6 Export et import d'une base de connaissances

Page d'une base → onglet « Export / import » → « Assistant d'export » (4 étapes : Mode → Sélection → Contrôle des droits → Export). Preuve : [DOC] `ExportTab.tsx:19-100`, `knowledge/schemas.py:80-95`, `knowledge/archive_format.py:132-149`.

| Champ affiché (FR / EN) | Signification | Obligatoire ? | Type / valeurs autorisées | Valeur à saisir (Rising Waters) | Exemple valide / remarque |
|---|---|---|---|---|---|
| Mode | contenu de l'archive | oui (défaut « Complet, réimportable ») | « Complet, réimportable » · « Texte traité seulement » · « Documents seulement » · « Sélection » · « Publication ouverte » | `Complet, réimportable` | « Publication ouverte » est **refusée tant qu'un document est restreint ou de licence inconnue** : les 17 documents CM sont `unknown` → refus attendu (`kb.export.restricted_documents`) : c'est un bon test **négatif** |
| Inclure / Include : Fichiers d'origine, Embeddings, Mandats, Références | éléments joints | non (défauts : originaux ✓, embeddings ✗, mandats ✓, références ✓) | cases | défauts | |
| Documents à exporter / Documents to export | choix des documents | oui seulement en mode « Sélection » | cases | (vide) — non requis dans le mode testé | |
| Objet / Purpose | usage de l'archive | non (défaut « Privé (réimportable) ») | `Privé (réimportable)` · `Publication ouverte` | `Privé (réimportable)` | |

Bouton « Lancer l'export » puis téléchargement d'un `.zip` (manifeste + empreintes SHA-256 ; **signature Ed25519** jointe si l'instance a une clé). **Import** : bouton « Importer une archive » (liste des bases) ou « Export / import » : « Fichier d'archive (.zip) » → « Valider l'archive » (essai à blanc ; badge « Signée par cette instance (Ed25519) » ou « Archive non signée : provenance non attestée ») → « Importer en tant que » : « Nouvelle base de connaissances » (champ « Code (facultatif) ») ou « Téléverser une nouvelle version » (champ « Base cible ») → « Confirmer l'import ». Statut : NOT TESTED.

### 12.7 § Replay — Rejeu (Replay)

Le rejeu **relit** le journal ; il n'appelle jamais de modèle. Preuve : [DOC] `AuditPage.tsx:60-115`, `room/flow/FlowPlayer.tsx`. Il n'y a **aucun champ de saisie obligatoire**, seulement des commandes :

| Commande (FR / EN) | Où | Valeurs | Valeur à utiliser | Remarque |
|---|---|---|---|---|
| Position dans le ledger : n sur N / Position in the ledger | page « Audit et rejeu » (`/audit/<id>`), section « Rejeu » | curseur de 0 à N | glisser jusqu'à une décision | reconstruit : décisions de chaque siège, tableau de coordination, événements |
| Type / Type ; Siège / Seat ; Contient le texte / Contains | « Chronologie » | listes et texte | `DECISION` ; `MET` | filtres d'affichage |
| « Vérifier le ledger » ; « Exporter en JSONL » | même page | boutons | « Vérifier le ledger » | « Ledger intact (N entrées contrôlées) » |
| Vitesse / Speed | lecteur « Flux de l'exercice » de la salle | `×0.5`, `×1`, `×2`, `×4` | `×1` | « Rejouer l'exercice depuis le début » ; « Position dans l'exercice » (curseur) |

Statut : NOT TESTED.

---

## Écarts constatés entre le guide existant et le code

Constats **factuels**, relevés le 27/11/2026 en lisant le code et les guides (les numéros de ligne des guides peuvent bouger : d'autres personnes les modifient). « Guide » = `docs/runbooks/guide-test-complet-interface.md` sauf mention contraire. Chaque ligne : [DOC].

### A. Le guide dit autre chose que le code

| # | Le guide dit | Le code ou les données disent | Références |
|---|---|---|---|
| E1 | Profil de modèle : « **Jetons max** (vide = 1024 par défaut) » | le champ **ne peut pas être vide** : la validation (`z.coerce.number().int().min(1)`) refuse une chaîne vide ; défaut du formulaire 1024 ; le serveur exige 16 à 32 768 | guide:346 ; `AgentsPage.tsx:165,179` ; `agents/schemas.py:26-27` |
| E2 | Agents : mission « Observer, prévoir et avertir des aléas météo… », consigne « Tu détiens la science… » (courte, en français, sans « Objective ») | les missions et instructions du pack sont **en anglais**, **complètes** (personnage, `Priorities`, `Tone`, `Objective`, `Contacts`, `Limits`, `On each event`, `Output`) pour les 9 agents, HYDRO compris | guide:383 ; `demo/rising-waters/setup-cm.json` ; `agent-briefs.CM.json` ; test `tests/mandates/test_rising_waters_pack.py:84-103` |
| E3 | Scénario : « Appels au modèle estimés : jusqu'à 328 (plafond 199) » ; budget « ≈ 304–328 » ; « Budget : 76/330 » | le nombre de tours est **3** (`MAX_ROUNDS = 3`) : l'estimation est **492** (scénario) et **456** (préparation) ; un siège scripté a 2 appels par activation | guide:426,526,541 ; `contracts.py:20` ; `scenarios/service.py:319` ; `simulation/readiness.py:163-167` |
| E4 | Coordination : « deux tours d'échange maximum par événement » ; « plus de 2 tours » rejeté | **3 tours** ; le message du dernier tour est refusé (« dernier tour : on ne peut plus que décider ») | guide:613,620 ; `contracts.py:20` ; `agents/runtime.py:420,486` ; `simulation/human.py:204` |
| E5 | Salle : « Reprendre … (option « étendre le budget » côté API) » | l'interface propose maintenant le champ « Étendre le budget de » quand la pause vient du plafond | guide:561 ; `RoomPage.tsx` (champ `extend`, clé `room.extendBudget`) |
| E6 | « liste Rythme → *Automatique avec délai* … accélère/ralentit par un délai (`delay_s`) » | l'interface ne saisit **aucun délai** (la commande n'envoie que `pace`) : « Automatique avec délai » = délai 0 s | guide:562 ; `RoomPage.tsx:116-118` ; `simulation/common.py:50` (`delay_s` défaut 0) ; `engine.py:614-617` |
| E7 | Export : « Il n'y a pas de signature Ed25519 de l'archive [ABS] » | une signature Ed25519 est jointe (`signature.json`) quand l'instance a une clé, et l'import l'affiche (« Signée par cette instance (Ed25519) ») | guide:228 ; `knowledge/archive_format.py:132-149` ; `ImportArchive.tsx:56-58` ; clés `kb.signedHere`, `kb.unsigned` |
| E8 | Évaluation : « l'évaluation automatique du scorecard par LLM répond 501 (non implémentée) » | un bouton « Évaluation par l'IA » existe et la route `POST /scorecard/exercises/{id}/assess` répond 202 (juge IA, réponses « à relire ») | guide:724,833 ; `EvaluationPage.tsx` (`evaluation.llmJudge`) ; `evaluation/router.py:129-145` |
| E9 | Mandats à valider : « Validez seulement CM-L10 et CM-L13 » | la base de développement a validé **CM-L10 et CM-L11** ; `CM-L13` est « proposé » | guide:296 ; copie de base du 27/11 à 13:13 (non relue en direct) ; `guide-test-complet-interface.md:8` |
| E10 | Jumeau Émirats : « 10 institutions … AE-MOI » | `setup-ae.json` contient **9** institutions (pas de `AE-MOI`) | guide:785 ; `demo/rising-waters/setup-ae.json` |
| E11 | Chiffres de construction : « 3 684 chunks », « 4 bases publiées », « 2 base(s), 2 publiée(s) », « 16 permission(s) accordée(s) » | à l'état observé : **1 base (CM)**, 1 351 passages, **9** droits d'accès ; l'en-tête du guide le dit déjà (l. 8) | guide:150,246,405 et 8 ; `catalogue-commandes-et-fichiers.md` §C |
| E12 | « Publier … » sans condition sur les vecteurs (étapes 5.5 et 6) | la publication est **refusée** si des vecteurs manquent (`kb.publish.vectors_incomplete`) ; l'interface le dit (« La publication est bloquée tant que tous les extraits ne sont pas vectorisés ») | guide:213-246 ; `knowledge/kbops.py:411-417` ; clé `kb.build.vectorsBlocked` |
| E13 | Institutions : « Domaines `météo, alerte` », noms français suggérés | `setup-cm.json` : **aucun domaine**, noms **anglais** ; seuls les **codes** comptent | guide:112-134 ; `setup-cm.json` |
| E14 | Parcours A (`guide-parcours-A-et-B.md`, A5) : « institutions (10) » | `setup-cm.json` définit **11** institutions (dont COORD et ONR sans siège) | `guide-parcours-A-et-B.md:38` ; `setup-cm.json` |

### B. Incohérences que ce travail a trouvées dans le code ou les données (à corriger ou à accepter explicitement)

| # | Constat | Références |
|---|---|---|
| C1 | **Siège humain : limite de questions au conseiller mal lue.** `PUT /agents` normalise `max_legal_calls_per_inject` en `max_legal_calls` ; le siège humain relit l'ancien nom et retombe toujours sur **2**. Le formulaire d'agent, à l'édition, relit aussi l'ancien nom et réaffiche **2** (un nouvel enregistrement écrase la valeur réglée) | `agents/schemas.py:68-70` ; `simulation/human.py:79,166` ; `AgentsPage.tsx:90,96` |
| C2 | **Intégrité (siège humain).** Les étiquettes sont affichées au joueur humain et la boîte renvoyée par l'API contient `fault_mode` (non affiché). Pour les **agents**, ils sont exclus du prompt (testé) | `simulation/human.py:110-111` ; `PlayerPage.tsx:79` ; `simulation/engine.py:934-936` ; [TEST] `tests/agents/test_citations_prompt.py:62-74` |
| C3 | **Siège humain : liste « À » trompeuse.** Elle contient tous les autres sièges, **HYDRO compris** ; le serveur refuse ensuite ce destinataire | `simulation/human.py:97` (`seat_codes`), `:203` |
| C4 | **Base de développement : rôles inversés.** AG-HYDRO est « Institution » et AG-ANTIC « Système d'IA testé » (inverse de `setup-cm.json`) ; HYDRO y a donc été joué comme un agent scripté et ANTIC jamais activé. Correction : `seed_rising_waters.py --from 5 --until 5 --fix-agents`, ou « Modifier » dans l'interface | copie de base 27/11 13:13 ; `setup-cm.json` ; `seed_rising_waters.py:157-175` |
| C5 | **Formulaire d'action : dérivation par défaut « Référentiel (cité) »** alors que les 25 actions de Rising Waters sont d'**Auteur du scénario** : une saisie manuelle sans changer le défaut présente une exigence du scénario comme une référence | `MandatesTab.tsx:253` (`derivation: 'referential'`) |
| C6 | **Mandat saisi à la main = niveau de preuve `inferred` imposé** (aucun champ) ; seul le CSV (colonne `evidence`) ou l'API change le niveau | `MandatesTab.tsx:126-148` ; `mandates/schemas.py:77` |
| C7 | **Validation d'un mandat** : seule l'existence d'un passage est contrôlée ; ni la citation (`quote_found`), ni la cohérence avec le niveau de preuve ne bloquent | `mandates/service.py:250-263` |
| C8 | **Import CSV : `procedure` vide devient `none`** (et non `unknown` comme dans le formulaire) ; la colonne `country` n'est pas lue | `mandates/csv_import.py:30,39` |
| C9 | **Documents importés par l'interface : codes `DOC-000n`**, pas `CM-nn` ; les sources de mandats (codes `CM-10`…) supposent la base construite par la ligne de commande (`curate`) | `knowledge/kbops.py:135-138` ; `knowledge/services/curation.py:41-45` |
| C10 | **Fiche document : « Fiabilité » préremplie `unofficial`** quand elle est vide | `DocumentPage.tsx:45` |
| C11 | **Profil de modèle** : l'interface accepte 1 jeton (serveur ≥ 16), n'impose pas le plafond du délai (serveur ≤ 1800) et n'a **aucun champ `extra`** (donc pas de `request_body`, pas de profil `cassette`) | `AgentsPage.tsx:165` ; `agents/schemas.py:27-29` |
| C12 | **Mode « Rejeu de cassette » proposé mais inutilisable** : les réglages d'exercice refusent la clé `cassette` | `simulation/common.py:45-50` ; `simulation/snapshot.py:78-80` ; le test `tests/simulation/test_effective_profile.py:23-25` injecte les réglages sans validation |
| C13 | **Notes de source du scénario** CM-01 et description : `source_note` cite d'anciens codes du prototype (« CM-S07 »…) ; la `description` du fichier **français** est en anglais ; le **titre** de l'inject 7 est coupé en cours de phrase (« …pour l'a ») | `cm01-rising-waters.fr.alerte-scenario.yaml` (injects 1, 2, 7) |
| C14 | **Surprise** : aucun champ de panne ni d'étiquettes dans l'interface (le serveur en accepte) | `RoomPage.tsx:162` ; `simulation/schemas.py:43-51` |
| C15 | **Écran de lecture du scénario** : estimation 492 comptée avec HYDRO, préparation 456 sans HYDRO : deux chiffres différents pour le même exercice | `scenarios/service.py:319` ; `simulation/readiness.py:163-167` |
| C16 | **Fichier privé des lacunes attendues** : `lacunes-attendues.PRIVE.json` est marqué supprimé dans l'index git (statut `D`) mais reste présent dans `demo/rising-waters/` ; le catalogue le décrit comme « ignoré par git ». Il n'est lu par aucun code de l'application (non lu ici non plus) | `git status` ; `catalogue-commandes-et-fichiers.md` §D |

## Champs ou fonctions manquants

Liste factuelle de ce que le code n'offre pas (ou pas dans l'interface), constaté en lisant le code ; [ABS] ou « API seulement ».

| # | Absent | Où | Conséquence pour le testeur |
|---|---|---|---|
| M1 | Champ **« description »** d'un espace | `WorkspaceCreate` n'a que `name`, `slug` | rien à saisir |
| M2 | Champ **« siège »** sur une institution | `InstitutionCreate` | COORD/ONR « sans siège » = simple absence de siège dans l'exercice |
| M3 | Champ **« Code »** dans l'assistant « Nouvelle base de connaissances » | `KbListPage.tsx:100-135` | le code vient du nom ; créer `CM` en ligne de commande |
| M4 | Champ **« Domaine »** dans « Nouvelle action » ; champ **niveau de preuve**, échéance, dépendances dans « Nouveau mandat » | `MandatesTab.tsx:126-148,245-285` | passer par le CSV ou l'API |
| M5 | **Correction et historique** d'un mandat ; note à la validation ; note à la revue du registre | `mandates/router.py` (API) | [ABS] dans l'interface |
| M6 | Champ **`extra`** d'un profil (`request_body`, `api_key_ref`, `cassette`) | `AgentsPage.tsx:163-220` | API seulement (`PATCH /model-profiles/<id>`) |
| M7 | Champ **« Objectif »** d'un agent | `AgentCreate` | l'objectif est la ligne `Objective:` des instructions |
| M8 | Champ « conseiller juridique » configurable (profil, consignes) | `agents/service.py:247-256` | l'outil `ask_legal` utilise le modèle et les bases de l'agent |
| M9 | **Import de questions (T1)** et **sceau des lacunes attendues (T3)** dans l'interface ; conversion de `questions.jsonl` en CSV | `evaluation/router.py:58-90` | API seulement ; conversion : **À DÉTERMINER** |
| M10 | Gestion des **références internationales** et des « précédents » (base GL) | aucun écran d'édition ; GL non construite | colonne GL de la matrice : BLOCKED |
| M11 | Réglage du **délai de réponse humaine** (`human_deadline_s`, `human_fallback`) et du **délai** du rythme (`delay_s`) | `simulation/common.py:48-50` | API seulement |
| M12 | Champs « panne » et « étiquettes » de la **surprise** ; champs « répondre à une demande » et « terminer sans décision » du **siège humain** ; `gap_flags` | `RoomPage.tsx:162`, `PlayerPage.tsx:162,187` | API seulement |
| M13 | Choix de ce que voient les **observateurs** (tout / seulement le public) | `audit/router.py:50-56` | la vue observateur est toujours publique |
| M14 | **Cassette** de rejeu (fichiers, réglage) | `snapshot.py:78-80` | mode inutilisable |

## Valeurs « À DÉTERMINER » (récapitulatif)

| Où | Valeur | Pourquoi on ne peut pas la fixer |
|---|---|---|
| § Profils, § Exercices (B) | **nom exact du modèle** (champ « Modèle ») | dépend du serveur de modèle de la personne qui teste ; voir `ALERTE_LLM_MODEL` dans `backend/.env` et `curl <serveur>/v1/models` |
| § Profils | « Jetons max » adapté à un modèle qui raisonne | aucune mesure avec un vrai modèle dans le dépôt |
| § Exercices (B) | budget **450** | estimation maximale 456/492 ; jamais mesuré avec un vrai modèle : à ajuster après un premier run |
| § Mandats | liste des mandats à valider pour la démonstration | les guides et la base divergent (CM-L10 + CM-L13, ou CM-L10 + CM-L11) |
| § Bases de connaissances | champ « Langues » de la base CM ; « Domaine » | aucun fichier du dépôt ne les fixe |
| § Permissions | raison de l'absence de GL pour AG-CTD | non documentée dans le dépôt |
| § Autres formulaires | titre/texte de la **surprise** ; base légale (extrait + citation) de la décision humaine | aucune surprise définie pour CM-01 ; l'identifiant d'extrait et la citation viennent de la recherche faite pendant le test |
| § Autres formulaires | fixtures T3 (`expected_gap_key`, `label`) ; conversion des questions T1 | valeurs de l'auteur indépendant ; aucun convertisseur trouvé |
| § Rapports | rapport antérieur à importer | aucun fourni par le dépôt |

## Limites de ce guide

* **Rien n'a été exécuté.** Toutes les valeurs, bornes et libellés viennent de la lecture du code et des fichiers de démonstration : aucun statut PASS, aucune marque [UI] ou [API].
* L'état de la base de développement (mandats validés, rôles inversés, noms) vient d'**une copie du 27/11/2026 à 13:13** réalisée par l'audit précédent, non relue en direct.
* Les **bornes de formulaire** citées sont celles du backend (source de vérité) ; quand l'interface diffère, la différence est dite.
* Les comportements d'un **vrai modèle** (coordination, qualité des citations, nombre réel d'appels) n'ont pas été observés : les chiffres de budget sont des **plafonds de calcul**, pas des mesures.
