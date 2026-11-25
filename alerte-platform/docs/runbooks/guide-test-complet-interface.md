# Guide de test complet d'ALERTE depuis l'interface — de l'espace vide au rapport rejoué

> **Exercice fictif, pas une alerte réelle.** Toutes les données de ce guide sont fictives (HydroSense et les chiffres des événements sont inventés ; les institutions et les textes de loi sont réels).
> Ce guide a été écrit **après** avoir exécuté le parcours sur le code actuel. Chaque étape indique **ce qui a réellement été vérifié** (légende ci-dessous). Ce qui n'existe pas est dit.

> **Tu découvres ALERTE ?** Commence par le [guide de démonstration pas à pas](guide-demonstration-pas-a-pas.md). Ce document-ci est le guide de **test complet** (cas avancés, tests extrêmes, couverture exhaustive).

## 0. Comment lire ce guide

**Légende de vérification** (inscrite à chaque étape) :

| Marque | Signification |
|---|---|
| **[UI]** | cliqué et constaté dans l'interface (navigateur automatisé, Chrome) |
| **[API]** | exécuté par la même route d'API que l'interface appelle, sans cliquer ; les libellés d'écran ont été relevés dans l'interface |
| **[TEST]** | couvert par un test automatisé du dépôt uniquement |
| **[DOC]** | déduit du code ou de la documentation, non exécuté |
| **[ABS]** | **non implémenté** dans cette version |

**Langue de l'interface** : le sélecteur **FR / EN** est en haut à droite. Ce guide cite les libellés **français** ; l'équivalent anglais figure entre parenthèses quand il diffère. (Au premier lancement la langue suit celle de votre navigateur.)

**Noms de pages** (menu latéral, tels qu'affichés en français) :
`Préparer` → *Pays et institutions* · *Bases de connaissances* · *Agents* · *Accès aux connaissances* · *Scénarios* ;
`Jouer` → *Exercices*, *Salle de simulation* ; `Analyser` → *Carte des responsabilités*, *Analyse des lacunes*, *Et si… ? (réforme)*, *Rapports*, *Audit et rejeu*, *Évaluation* ; `Système` → *Architecture*, *Jetons d'accès*, *Glossaire* ; (*Carte des responsabilités*, *Et si… ? (réforme)*, `/present` et `/citizen` ont été ajoutées par l'équipe : **non auditées par ce guide**.)
En haut de chaque page, la **barre de parcours** indique la phase (A/B/C), l'étape et l'**étape suivante**. Le bouton « ? » à côté d'un titre explique la notion (voir aussi *Glossaire*).

**Notions clés** (détail dans *Glossaire*) : **Workspace** = espace isolé qui contient tout un projet ; **KB** = bibliothèque de documents découpés en **chunks** (passages) ; **Mandat** = « cette institution peut/doit faire telle action, selon tel texte » ; **Agent** = institution virtuelle ; **Inject** = un événement du scénario ; **Siège** = place d'une institution dans un exercice ; **Readiness** = contrôles avant lancement ; **Gap** = lacune ; **Ledger** = journal chaîné ; **Replay** = rejeu sans appeler de modèle.

### Deux façons de suivre ce guide
1. **Pas à pas manuel** : vous faites tout dans l'interface (recommandé pour apprendre).
2. **Raccourci** : le script `backend/scripts/seed_rising_waters.py --until N` prépare l'espace de démonstration jusqu'à l'étape N (1 espace · 2 institutions/actions · 3 bases · 4 mandats · 5 agents+accès · 6 scénario · 7 exercice · 8 exercice joué). Vous reprenez ensuite à l'étape suivante dans l'interface avec le jeton affiché.

### Ce que cette version ne fait PAS (à savoir avant de commencer)
* Un espace n'a **pas de champ « description »** : seulement un nom et un identifiant court facultatif.
* Les **embeddings** (recherche vectorielle) ne sont calculés que si un serveur d'embeddings est configuré (`lancement-local.md` §2) ; une base construite sans cette étape (étape 5.2 bis) **n'en contient pas** : la recherche est alors **lexicale** (« dégradée », signalée). Le raccourci `seed_rising_waters.py` importe encore l'**ancienne archive du prototype** (voie dépréciée, conservée pour la démonstration rapide) ; pour le corpus reconstruit, suivre l'étape 5.
* Le **mode « Modèle réel »** n'a été validé qu'avec un très petit modèle (`qwen2.5:1.5b-instruct`), qui ne sait pas citer correctement : la démonstration se fait en **« Scénarisé (SANS IA) »**, qui prouve la plateforme, **jamais** que les agents raisonnent bien.
* Détail complet : `etat-conformite-interface.md`. Cas de test : `matrice-tests-fonctionnels-et-extremes.md`.

---

## Étape 1 — Préparer l'environnement et lancer l'application

| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Avoir le backend (API) et le frontend (interface) démarrés et reliés |
| **Pré-requis** | Python/Node déjà installés (ne rien réinstaller) ; `backend/.venv` existant |
| **Navigation** | Deux terminaux (voir `lancement-local.md`) |
| **Action** | Terminal 1 : `cd alerte-platform/backend && source .venv/bin/activate && python -m uvicorn app.main:app_factory --factory --reload --port 8000`. Terminal 2 : `cd alerte-platform/frontend && . ~/.nvm/nvm.sh && nvm use && npm run dev`. Avant la première démonstration : `cd backend && .venv/bin/python scripts/rising_waters_pack.py` (génère `demo/rising-waters/`) |
| **Saisie** | Pour une démonstration propre sans toucher à vos données : préfixer le backend par `ALERTE_DATA_DIR=./data-demo` |
| **Résultat attendu** | Terminal 1 : `Application startup complete`. Terminal 2 : `Local: http://localhost:5173/` |
| **Vérification** | `curl http://localhost:8000/api/v1/health` → `{"status":"ok"}` ; `curl http://localhost:5173/api/v1/health` → idem (liaison frontend↔backend) ; ouvrir **http://localhost:5173/access** |
| **Erreur possible** | Port occupé ; `nvm: command not found` ; page blanche |
| **Correction** | Voir `lancement-local.md` §9 |
| **Étape suivante** | Étape 2 |

*Vérification : [UI] pour la liaison, l'ouverture des 20 pages et les flux SSE (flux d'exercice lu à travers le proxy) ; [API] pour les commandes.*

---

## Étape 2 — Ouvrir ou créer l'espace de travail (Workspace)

**À quoi sert un espace de travail ?** C'est le **conteneur isolé d'un projet ALERTE** : pays, institutions, bases de connaissances, mandats, agents, permissions, scénarios, exercices, rapports. Ce n'est ni un pays, ni un scénario, ni un exercice. Deux espaces ne voient jamais les données l'un de l'autre (vérifié : tout accès croisé répond 404). On y entre avec un **jeton**.

| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Disposer d'un espace propre pour la démonstration |
| **Pré-requis** | Étape 1. Aucune donnée |
| **Navigation** | Page **/access** (écran d'entrée, deux cartes : « Créer un espace de travail » / « Se connecter avec un jeton ») |
| **Action** | Si c'est le **premier démarrage** (ou une base vierge) : carte de gauche, bouton **Créer l'espace de travail** (Create workspace). Si **un espace existe déjà** : carte de droite, collez son jeton, bouton **Se connecter** (Sign in) |
| **Saisie** | **Nom de l'espace de travail** : `ALERTE — Demonstration`. **Identifiant court (slug)** : `alerte-demo` (facultatif ; minuscules, chiffres, tirets). *Il n'y a pas de champ description.* |
| **Résultat attendu** | Une carte « Espace de travail « ALERTE — Demonstration » créé » avec le **jeton propriétaire** (affiché **une seule fois**), une case « J'ai copié et conservé le jeton propriétaire. » et le bouton **Continuer vers l'espace de travail** |
| **Vérification** | Cochez la case, cliquez **Continuer** : la page **Accueil** affiche « Espace ALERTE — Demonstration », l'encadré **Qu'est-ce qu'un espace de travail ?**, vos trois phases et l'état du système (`database`, `data_dir`, `knowledge` : actif) |
| **Erreur possible** | Message « Un espace existe déjà. En créer un autre exige le jeton propriétaire » (création refusée) ; jeton perdu |
| **Correction** | Collez le jeton propriétaire de l'espace existant. **Jeton perdu : non récupérable** (seul son hash est conservé) → relancez le backend avec un autre `ALERTE_DATA_DIR` (rien n'est supprimé). Avec un jeton **propriétaire** valide vous pouvez créer un second espace (testé : isolation complète) |
| **Étape suivante** | Étape 3 (*Pays et institutions*) |

**Ne créez pas plusieurs espaces identiques** : un seul « ALERTE — Demonstration » suffit. Où retrouver ensuite ses ressources : tout est dans le menu latéral ; l'**Accueil** compte vos ressources en temps réel.
*Vérification : [UI] pour l'Accueil, le menu et le glossaire ; [API] pour la création d'espace et l'isolation ; la création par le formulaire n'a pas été cliquée.*

**Rôles et jetons** (page *Jetons d'accès*, propriétaire uniquement) : créez un jeton `facilitator` (animateur), `observer` (observateur) et `auditor` (auditeur) avec un libellé et une durée (heures). Un jeton n'est affiché **qu'une fois**. Bouton **Révoquer** pour l'invalider. *[API]*

---

## Étape 3 — Créer ou vérifier le pays

| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Déclarer le pays du scénario |
| **Pré-requis** | Étape 2 |
| **Navigation** | Menu **Pays et institutions** → onglet **Pays** |
| **Action** | Bouton **Nouveau pays** (New country) puis **Enregistrer** |
| **Saisie** | **Nom** : `Cameroun` · **ISO 3166-1 alpha-2** : `CM` · **Langues** : `fr, en` · **Notes** : `Pays du scénario Rising Waters` |
| **Résultat attendu** | Une ligne « Cameroun · CM · fr, en » dans le tableau (Nom, ISO, Langues, Statut, Actions) |
| **Vérification** | La ligne apparaît avec le statut *actif* ; l'étape 4 propose « Cameroun » dans la liste « Pays » |
| **Erreur possible** | Code ISO ≠ 2 lettres (« Exactement 2 lettres ») ; suppression refusée si le pays est utilisé |
| **Correction** | Corriger la saisie ; pour un pays utilisé, **Archiver** plutôt que **Supprimer** |
| **Étape suivante** | Étape 4 |

*Un pays n'est pas un espace de travail : un espace peut contenir plusieurs pays (le jumeau Émirats, étape 26, vit dans le même espace). Vérification : [UI] libellés du formulaire ; [API] création.*

---

## Étape 4 — Créer ou vérifier les institutions

Les **identifiants (codes)** ci-dessous sont ceux du scénario : ils doivent être saisis **exactement**. Les codes sont **uniques dans un espace**.

| Code | Nom suggéré | Type | Siège dans l'exercice | Rôle |
|---|---|---|---|---|
| `HYDRO` | HydroSense (système d'IA fictif testé) | Système d'IA | oui | l'IA testée : ses sorties sont **écrites dans le scénario**, jamais produites par un modèle |
| `MET` | Service météorologique national (avec l'ONACC) | Agence | oui | émet les avis météo ; juge la prévision de l'IA |
| `DPC` | Direction de la protection civile (MINAT) | Agence | oui | décide les alertes publiques et évacuations |
| `OPS` | Opérateur de téléphonie mobile (générique) | Opérateur | oui | peut diffuser des SMS, demande une base légale |
| `ART` | Agence de régulation des télécommunications (ART) | Régulateur | oui | dit ce que les opérateurs peuvent/doivent faire |
| `MINSANTE` | Ministère de la Santé publique | Ministère | oui | conduit la riposte au choléra |
| `DPA` | Autorité de protection des données personnelles (APDP) | Régulateur | oui | tranche données de localisation et transferts à l'étranger |
| `CTD` | Collectivités locales (Douala, communes de l'Extrême-Nord) | Collectivité locale | oui* | alertes et abris locaux |
| `ANTIC` | Agence nationale des TIC (cybersécurité) | Agence | oui* | fausses alertes, liens frauduleux |
| `COORD` | Conseil national de protection civile / comité de crise | Agence | **non** | porte des mandats mais **n'est pas un siège** |
| `ONR` | Observatoire national des risques | Agence | **non** | porte un mandat (CM-L07) mais n'est pas un siège |

\* **Statut réel** : dans les spécifications, `CTD` (conseils municipaux) et `ANTIC` (cybersécurité) sont « *Later* ». Dans cette plateforme, **rien n'empêche d'en faire des sièges** (ce sont des institutions comme les autres) et les événements 7 et 9 du scénario les ont pour destinataires : ils sont donc créés ici. Le **chef d'exercice (« Drill leader ») du prototype n'est pas un siège** : c'est du code déterministe qui clôture les tours et émet des signaux (demande orpheline, chevauchement…). Le **conseiller juridique** n'est pas non plus un siège : c'est l'outil `ask_legal` que chaque siège peut appeler.

| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Créer les institutions qui joueront (et celles qui n'ont que des mandats) |
| **Pré-requis** | Étape 3 |
| **Navigation** | **Pays et institutions** → onglet **Institutions** |
| **Action** | **Nouvelle institution** (New institution) → remplir → **Enregistrer** ; répéter 11 fois |
| **Saisie** | **Code** `MET` · **Nom** `Service météorologique national (ONACC)` · **Nom en langue locale** (vide) · **Pays** `Cameroun` · **Type** `Agence` · **Domaines** `météo, alerte` · **Description** (facultatif) |
| **Résultat attendu** | Tableau (Code, Nom, Type, Pays, Domaines, Statut, Actions) avec 11 lignes pour le Cameroun |
| **Vérification** | Le filtre **Pays** = Cameroun montre 11 institutions ; ouvrez ensuite **Agents** : la liste « Institution » les propose |
| **Erreur possible** | Code déjà utilisé (`institution.duplicate`) ; code avec espace/accents |
| **Correction** | Choisir un autre code (lettres, chiffres, `.-_`, 32 max) |
| **Étape suivante** | Étape 5 |

**Contacts/relations** : il n'y a **pas** de champ « contacts » sur une institution dans cette version [ABS] ; les relations entre institutions résultent des échanges de l'exercice (tableau de coordination).
*Raccourci* : `seed_rising_waters.py --until 2` crée pays, 11 institutions et les 25 actions (étape 7). *Vérification : [UI] libellés du formulaire ; [API] création.*

---

## Étape 5 — Construire les bases de connaissances à partir des PDF originaux

**Décision actuelle** : les bases sont **reconstruites par le pipeline d'ALERTE à partir des PDF originaux** du dossier `alerte/` (lecture seule). L'ancienne archive prétraitée du prototype (45 documents, 4 235 passages) **n'est plus utilisée** : elle contenait des fichiers mal étiquetés (par exemple « décret 98/031 » qui était un rapport IDNDR) et des chunks sans pages. Détail et chiffres : [docs/knowledge-base/build-report.md](../knowledge-base/build-report.md).

**Résultat de la construction de référence** (mesuré, voir le rapport) : **44 PDF** → 44 documents uniques (0 doublon), 2 133 pages, **3 684 chunks** (CM 1 322 · GL 2 083 · AE 186 · ITU 93), 4 bases publiées en `v1`. Ces valeurs viennent de l'exécution réelle ; si vous reconstruisez, les vôtres peuvent différer légèrement (OCR).

**Droits documentaires — à comprendre d'abord.** Sur 44 documents : **2 `allowed`** (GL-05, GL-06 : œuvres du gouvernement fédéral des États-Unis), **1 `restricted`** (GL-07 : usage non commercial), **41 `unknown`**. L'application les utilise tous normalement ; l'**export « Publication ouverte »** refuse ceux qui ne sont pas `allowed` ; le dépôt GitHub ne reçoit le **texte** que des documents `allowed` ([publication-policy.md](../knowledge-base/publication-policy.md)).

### 5.1 Préparer l'environnement et les fichiers (une fois)
```bash
cd alerte-platform/backend
.venv/bin/python scripts/kb_inventory.py --source ../../alerte --out ../knowledge_bases/inventory   # inventaire : SHA-256, pages, pages sans texte
# modèles OCR français/arabe sans droits administrateur : voir docs/knowledge-base/rebuilding-the-knowledge-base.md §2
```
**Sur une machine chargée, lancer le backend avec `OMP_THREAD_LIMIT=1`** (mesuré : une page OCR passe de ≈ 400 s à ≈ 3 s). Backend isolé conseillé (`ALERTE_DATA_DIR=./data-kb-build`) pour ne pas mélanger avec vos données.

### 5.2 Importer les PDF (voie graphique, ou script équivalent)
| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Créer les bases `CM`, `AE`, `GL`, `ITU` et y importer chaque PDF avec ses métadonnées |
| **Pré-requis** | 5.1 ; étapes 2 à 4 (le pays rattache la base) |
| **Navigation** | **Bases de connaissances** → **Nouvelle base de connaissances** (nom, type, **pays**, domaine, langues) → page de la base → onglet **Documents** → téléverser un PDF → fiche du document (titre, type, langue, **fiabilité**, **validité**, **droits**) |
| **Action** | Pour chaque PDF : téléverser, renseigner/vérifier les métadonnées lues **dans le PDF** (`knowledge_bases/curation/documents.curation.json`), suivre le job d'extraction |
| **Équivalent script** | `python -u scripts/kb_build.py --api http://localhost:8020 --create-workspace "ALERTE — Corpus PDF" --stage setup,ingest,publish` (mêmes endpoints que l'interface) |
| **Résultat attendu** | Chaque document passe `ready` ou **`needs_review`** (pages à relire, ou « suite des articles interrompue ») ; 44 documents au total (CM 17 · AE 9 · GL 16 · ITU 2) |
| **Vérification** | onglet **Qualité et couverture** : pages OCR, pages à relire, articles reconnus ; `GET /knowledge-bases` |
| **Erreur possible** | « un document identique existe déjà » (SHA-256) ; OCR : « langues OCR absentes » ; PDF chiffré/illisible |
| **Correction** | ne pas réimporter un doublon ; installer les modèles OCR ; fournir un PDF lisible |
| **Étape suivante** | 5.3 |

*Vérification : **[API/script]** import des 44 PDF jusqu'à la publication (≈ 25 min sur une machine chargée, dont ≈ 4 min pour le scan CM-01) ; **[UI]** le parcours cliqué de téléversement n'a pas été rejoué dans cette session : les libellés sont ceux de l'application, à confirmer.*

**À savoir sur les résultats** : (a) **CM-01** (loi 2024/017) est un scan : l'OCR lit parfois mal un numéro d'article (« 53 » lu « §3 ») → le pipeline signale désormais **« suite des articles interrompue : 8 numéro(s) absent(s) »** et met le document en `needs_review` ; (b) **CM-07** est le rapport IDNDR et **non** le décret 98/031 (le vrai décret est un document attendu, voir `expected_documents.jsonl`) ; (c) les titres de plusieurs autres fichiers du dossier source étaient inexacts (liste dans [corpus-inventory.md](../knowledge-base/corpus-inventory.md)).

### 5.2 bis Calculer les embeddings (recherche hybride)
Page de la base → **Versions et index** → calculer les embeddings (BGE-M3 via Ollama, `ALERTE_EMBED_BASE_URL`/`ALERTE_EMBED_MODEL`), ou `kb_build.py --stage embed`. **Sans cette étape la recherche est lexicale seule** (étiquette « dégradé ») et une requête dans une autre langue que le texte ne trouve pas le passage. Mesuré ici : ≈ 6 s par passage sur la machine de développement (CPU saturé) : l'opération est longue et **reprenable**. Un index partiellement vectorisé est affiché comme **incomplet**, jamais comme « hybride ».

### 5.3 Créer une base vide et y ajouter un document (UC-01)
| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Apprendre la création d'une base et l'ajout d'un document (utile pour le test contrefactuel, étape 20) |
| **Pré-requis** | Étape 2 |
| **Navigation** | **Bases de connaissances** → **Nouvelle base de connaissances** (assistant : *Nom et type* → *Pays et domaine* → *Relecture*) |
| **Action** | Remplir puis **Suivant** jusqu'à la création ; sur la page de la base : onglet **Documents** → **Choisir des fichiers** |
| **Saisie** | **Nom** `CM — Base documentaire Cameroun (essai)` · **Description** `Base d'essai pour Rising Waters` · **Type** `National` · fichier : un PDF/TXT/DOCX/MD/CSV de votre choix. Métadonnées facultatives : Titre, Juridiction `CM`, Langue `fr`, Redistribution `unknown` |
| **Résultat attendu** | Une barre de progression (suivi SSE du job d'ingestion) puis une ligne dans le tableau (Code `DOC-0001`, Titre, Juridiction, Validité, Redistribution, **Qualité d'extraction**, **Pages à relire**, Statut) |
| **Vérification** | Cliquez le titre : page *Document* (Métadonnées, Historique des versions, Aperçu de la page, **Extraits** avec article et page) |
| **Erreur possible** | Doublon (`kb.document.duplicate`, même SHA-256) ; fichier illisible ; statut « à relire » |
| **Correction** | Retirer le doublon ; pour un scan, voir les *Pages à relire* ; voir 5.6 |
| **Étape suivante** | 5.4 |

*Mesuré : le PDF scanné `CM-01` (4,7 Mo, 24 pages) s'ingère en ≈ 3 min, qualité d'extraction 0,88, statut `needs_review`, 71 chunks avec pages et articles. [API] ; l'avertissement « serveur d'embeddings non configuré » s'affiche si BGE-M3 n'est pas réglé (non bloquant).*

### 5.4 Contrôler l'extraction, les métadonnées, pages, articles et chunks
Sur la page d'un document : **Métadonnées** (Titre, Type de document, Numéro, Date, Juridiction, Langue, URL de la source, Fiabilité *official/summary/unofficial/not_found*, Validité *in_force/replaced/unknown*, Licence SPDX, **Redistribution** *allowed/restricted/unknown*, Niveau de preuve par défaut) → **Enregistrer** ; **Aperçu de la page** (Précédent/Suivant) ; **Extraits** (chunks : n°, Article, Pages, Texte).
Repérer les problèmes : onglet **Qualité et couverture** → **Synthèse de la qualité** (qualité moyenne, % de documents avec articles, pages OCR, alertes d'injection) et **Par document** (colonnes *Qualité d'extraction, Pages, OCR, Articles, Pages à relire, Avertissements*). Un **texte OCR dégradé** est visible : p. ex. l'article 32 de la loi 2024/017 apparaît « Le transfert de don étranger, ou à une organisation inté… » (c'est la réalité du scan, pas un bug d'affichage).
**Couverture documentaire** : saisissez un **Document attendu** (+ **Juridiction**) → **Ajouter** ; la couverture devient un ratio (ex. 1 sur 2). Une absence n'est jamais une preuve d'inexistence si le corpus est incomplet.
*[API] mesures ; [UI] présence des onglets/colonnes.*

### 5.5 Publier, reconstruire l'index, rechercher, exporter
| Opération | Où / bouton | Résultat attendu |
|---|---|---|
| **Publier une version** | onglet **Versions et index** → champ **Note** `v1` → **Publier** | une ligne `# 1` avec l'**empreinte du manifeste** ; les agents ne lisent **que** les versions publiées. Republier sans changement : refus « aucun changement » |
| **Reconstruire l'index lexical** | même onglet → **Reconstruire l'index lexical** | job de reconstruction (index FTS5 resynchronisé) |
| **Calculer les embeddings** | **Calculer les embeddings** | nécessite un serveur d'embeddings ; sinon message « serveur d'embeddings non configuré » et recherche lexicale (« mode dégradé ») |
| **Rechercher** | onglet **Test de recherche** → **Requête** + **Rechercher** (champ **Article** facultatif) | liste de résultats (document, article, page, extrait, score, signaux *lexical/vecteur*) ; **Mode dégradé** affiché si pas d'embeddings |
| **Exporter** | onglet **Export / import** → **Assistant d'export** : **Mode** *(Complet réimportable / Texte traité seulement / Documents seulement / Sélection / Publication ouverte)* ; cases *Fichiers d'origine, Embeddings, Mandats, Références* → **Suivant** | archive ZIP (manifeste + empreintes SHA-256) téléchargeable |
| **Importer / dry-run** | même onglet, **Importer une archive** → **Valider l'archive** | rapport avant toute création |

Requêtes d'essai (base CM, recherche lexicale réelle) : « état d'urgence » → `CM-09` Art. 6 ; « transfert de données à caractère personnel vers un pays tiers autorisation préalable » → `CM-01` Article 32 ; « Agence nationale des technologies de l'information et de la communication » → `CM-02` Art. 96, `CM-04` Art. 7.
**Modes d'export réellement disponibles** : l'export **« Publication ouverte »** est **refusé** (erreur `kb.export.restricted_documents`, liste des documents) tant que des documents sont `restricted` ou `unknown` ; **« Sélection »** exporte les documents choisis (testé : 16 documents, 1 592 chunks) ; les modes « Complet réimportable » (avec/sans originaux) ne sont **pas** destinés à la publication. Les **mandats et références ne sont pas exportés** (avertissement du manifeste). *Il n'y a pas de signature Ed25519 de l'archive [ABS].*
*Vérification : [API] publication, export sélection, import, refus d'export ouvert ; [UI] libellés ; recherche [API] (le clic n'a pas été automatisé).*

### 5.6 Cas de test de la base (voir la matrice, famille KB)
Document valide · sans métadonnées suffisantes (liste « missing_meta » dans *Qualité*) · illisible (pages à relire) · remplacé ou obsolète (Validité = `replaced` : exclu des recherches courantes) · droits inconnus (export ouvert refusé) · doublon (409) · texte sans article (chunks « Article — » vide, p. ex. `CM-18`) · recherche sans résultat · export ouvert de documents non redistribuables (422). Voir `KB-01` à `KB-12`.

---

## Étape 6 — Vérifier la qualité et publier les KB

| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | S'assurer que chaque base est exploitable puis la publier |
| **Pré-requis** | Étape 5 |
| **Navigation** | Page de la base → **Qualité et couverture** puis **Versions et index** |
| **Action** | Lire la synthèse, puis **Publier** (champ **Note**) pour `CM` et `GL` |
| **Saisie** | Note : `v1 — construction à partir des PDF originaux` |
| **Résultat attendu** | Colonne « Version publiée » = `v1` dans la liste des bases |
| **Vérification** | *Accueil* → phase A : « 2 base(s), 2 publiée(s) » |
| **Erreur possible** | « des documents sont encore en cours de traitement » ; « aucune version de document prête » |
| **Correction** | Attendre la fin des jobs ; vérifier qu'il y a au moins un document `ready`/`needs_review` |
| **Étape suivante** | Étape 7 |

*Une base non publiée bloque la préparation d'un exercice (étape 14). [API]/[TEST].*

---

## Étape 7 — Configurer le registre des mandats

**Trois statuts de ligne** : *écrit dans un texte* (`documented`), *déduit d'un texte* (`inferred`), *supposé* (`assumed`). Un mandat n'est **documenté et actif** que s'il est **validé** et rattaché à une **source qui se résout** vers un vrai passage. Un registre non « revu complet » ne permet **jamais** d'affirmer une absence.

### 7.0 D'abord : le catalogue d'actions (obligatoire avant d'importer les mandats)

Un mandat dit « telle institution peut/doit faire **telle action** ». L'import de mandats **refuse** toute ligne dont l'action n'existe pas dans le catalogue : vous obtenez « *action absente du catalogue : 'coordinate_response'* » sur les 14 lignes. **Il faut donc créer les 25 actions de Rising Waters avant l'étape 7.1.**

| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Charger les 25 actions que le scénario exige |
| **Pré-requis** | Étape 2 |
| **Navigation** | **Pays et institutions** → onglet **Registre des mandats** → section **Catalogue d'actions** → bouton **Importer un CSV** |
| **Action** | **Choisir un fichier** → `actions.csv` → **Essai à blanc** → vérifier → **Importer pour de bon** |
| **Saisie** | Fichier : `alerte-platform/demo/rising-waters/actions.csv` (colonnes `code,label,domain,derivation,justification,reference_note`) |
| **Résultat attendu** | Essai à blanc : « 25 créés, 0 ignorés, 0 erreurs » ; le tableau **Catalogue d'actions** liste 25 lignes de dérivation **Auteur du scénario** |
| **Vérification** | *Accueil* ; l'import des mandats (7.1) annonce ensuite « 14 créés, 0 erreurs » |
| **Erreur possible** | Ligne sans justification pour une dérivation « Auteur du scénario » ; code invalide (espace) |
| **Correction** | Compléter la colonne `justification` ; relancer (les codes déjà présents sont ignorés : import **idempotent**) |
| **Étape suivante** | 7.1 |

*Autres moyens* : bouton **Nouvelle action** (une par une) ; ou `python scripts/seed_rising_waters.py --token <jeton> --from 2 --until 2`. Les codes d'action sont **communs** aux deux pays (le jumeau Émirats réutilise ce même catalogue). *Vérification : [API] import CSV (essai à blanc puis réel, idempotent) et test automatisé ; [UI] bouton ajouté dans cette version.*

### 7.1 Importer le registre du prototype (avec essai à blanc)
| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Charger les 14 lignes de mandats du Cameroun |
| **Pré-requis** | Étape 4 (codes d'institution) **et 7.0 (catalogue d'actions)** |
| **Navigation** | **Pays et institutions** → onglet **Registre des mandats** → bouton **Importer un CSV** (Import CSV) |
| **Action** | **Fichier CSV** `demo/rising-waters/mandats-cm.csv` → **Essai à blanc** (Dry run) → vérifier → **Importer pour de bon** |
| **Saisie** | Fichier : `alerte-platform/demo/rising-waters/mandats-cm.csv` |
| **Résultat attendu** | Essai à blanc : « 14 créés, 0 ignorés, 0 erreurs » ; après import : 14 lignes **« proposé »**, **sans source**, **inactives** (« mandat proposed ») |
| **Vérification** | *Accueil* → « 14 mandat(s), 0 validé(s) » |
| **Erreur possible** | « **action absente du catalogue** » sur les 14 lignes : le catalogue n'a pas été importé (7.0). « institution inconnue : 'ONR' » si `COORD`/`ONR` n'ont pas été créés (étape 4) — **cas de test d'un import partiel** |
| **Correction** | Créer l'institution manquante puis relancer (les lignes déjà importées sont ignorées : import idempotent) |
| **Étape suivante** | 7.2 |

*[API] 14 créés, 2 erreurs « institution inconnue » constatées quand `COORD` et `ONR` manquent ; rejeu idempotent ; [UI] libellés.*

### 7.2 Associer une source puis valider (3 mandats d'exemple)
**Validez seulement `CM-L10` et `CM-L13` maintenant. `CM-L15` est réservé au test contrefactuel (étape 20) : laissez-le « proposé ». Les 11 autres restent « proposés » : ce n'est pas une erreur, c'est ce qui garde l'analyse honnête (un mandat sans source retrouvée n'est pas documenté).**

Pour chaque mandat à valider (le tableau ci-dessous donne la valeur à saisir) :
1. **Pays et institutions** → onglet **Registre des mandats** → dans la liste **Mandats**, repérez la ligne par la colonne **Réf.** (`CM-L10`).
2. Cliquez **Sources** sur cette ligne. Une fenêtre s'ouvre ; la liste **Sources déjà liées** est vide (« aucune source »).
3. Dans **Base de connaissances**, choisissez **Cameroun** ; dans **Texte à rechercher**, saisissez le texte du tableau en français ; cliquez **Rechercher**.
4. Repérez le passage indiqué dans la colonne « Passage à choisir » (code du document + article) ; cliquez **Utiliser comme source** sous ce passage.
5. Cliquez **Enregistrer les sources** : la source apparaît dans **Sources déjà liées** (ex. « Art. Article 7 »).
6. Cliquez **Fermer**, puis **Valider** sur la ligne : le statut passe à **validée** et l'avertissement « aucune source » disparaît.

*[UI] vérifié dans un navigateur réel (Chrome) sur `CM-L10`, `CM-L13`, `CM-L14` : refus clair sans source, ajout de source, validation. Avant cette version, l'interface ne permettait d'ajouter une source qu'à la **création** d'un mandat, pas à un mandat importé : c'est ce qui bloquait ici.*

| Ligne (import_ref) | Action | Base | Texte à rechercher | Passage à choisir |
|---|---|---|---|---|
| `CM-L15` — le transfert de données à l'étranger exige l'autorisation préalable de l'APDP — **à valider à l'étape 20, pas ici** | `authorise_transfer_abroad` | `CM` | `transfert de données à caractère personnel vers un État étranger autorisation préalable` | `CM-01` **ARTICLE 32** |
| `CM-L10` — l'ANTIC est l'organisme de sécurité électronique | `block_spoofed_alert` | `CM` | `Agence Nationale des Technologies de l'Information régulation activités de sécurité électronique` | `CM-04` **Article 7** |
| `CM-L13` — l'autorité de protection des données contrôle la loi 2024/017 | `protect_personal_data` | `CM` | `veiller à l'application de la présente loi délivrer les autorisations réclamations` | `CM-01` **ARTICLE 53** |

* **Valider** sans source → refus **« validation impossible : aucune source ne résout vers un chunk réel »** (`mandate.validate.no_source`). *[API] constaté.*
* **Rejeter** exige un **motif** (« Motif du rejet ») ; la ligne devient *rejeté*, jamais supprimée de l'historique. *[API]*
* **Corriger** le texte d'une ligne : **pas de bouton dans l'interface** (seulement Sources / Valider / Rejeter / Supprimer par ligne) ; la correction existe côté API (`PATCH /mandates/{id}`) [ABS en UI]. L'**historique** d'une ligne (création, mise à jour, validation) existe côté API mais n'est **pas affiché** dans l'interface [ABS en UI].
* **Supprimer** une ligne : bouton **Supprimer**.

### 7.3 La revue du registre : ne la déclarez que si elle est réelle
Section **Revue du registre par institution** (même onglet) : pour chaque institution, la liste **Statut de la revue <code>** propose `unreviewed` (non revu) · `partial` (partiel) · `reviewed complete` (revu complet).

* `reviewed complete` est une **déclaration humaine** : « j'ai examiné tous les mandats de cette institution pour la période voulue et la liste est complète ». **Ne la cochez pas pour faire disparaître un avertissement.**
* Dans cette démonstration, **laissez `unreviewed`** pour toutes les institutions : seuls 3 mandats sur 14 ont une source. La conséquence attendue et normale : la préparation (étape 14) affiche des avertissements `registry.not_reviewed` (« registre non 'reviewed_complete' ») et les lacunes sont qualifiées « déduites », pas « documentées ».
* Vous pouvez passer une institution en `partial` si vous avez examiné une partie de ses mandats.
*[API] constaté (effet sur les lacunes) ; [UI] libellés et panneau d'aide « Comment utiliser le registre des mandats » ajouté en haut de l'onglet.*

**Maintenant, voici ce que vous devez faire : passez à l'étape 8 (profils de modèles). Les avertissements de registre non revu restent affichés : c'est voulu.**

### 7.4 Deux institutions ou aucune
* **Aucune institution n'a le pouvoir** (cas de base) : tous les mandats « proposés » ⇒ pour chaque action exigée par le scénario la règle **G1 « Responsabilité orpheline »** apparaît. *Constaté : 42 lacunes (22 × G1, 8 × G6, 7 × G7, 2 × G8, 2 × G10, 1 × G9).*
* **Deux institutions semblent avoir le même pouvoir** : p. ex. `issue_weather_warning` est portée par `MET` (devoir, CM-L06) **et** `ONR` (pouvoir, CM-L07). La règle **G2 « Mandats qui se chevauchent »** exige **deux pouvoirs** (`kind=power`) **sans chef de file** : à tester en validant les deux lignes, en passant CM-L06 en `power`, puis en relançant (*non exécuté dans ce guide*).

### 7.5 Catalogue d'actions (détail des champs)
Même onglet, section **Catalogue d'actions** (voir 7.0 pour l'import) : **Libellé**, **Dérivation** *(Référentiel (cité) / Auteur du scénario / Proposée par un agent)*, **Justification**, **Note de référence**. Les 25 actions du pack sont de dérivation **Auteur du scénario** (« exigée par le scénario, **pas une obligation officielle** ») : les rapports les signalent comme telles.

---

## Étape 8 — Créer et configurer les profils de modèles

| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Déclarer le modèle qu'un agent appellera (uniquement pour un exercice « Modèle réel ») |
| **Pré-requis** | Étape 2 ; un serveur compatible OpenAI (Ollama, vLLM…) ; **facultatif pour la démonstration SANS IA** |
| **Navigation** | **Agents** → section **Profils de modèle** (en bas de la page) → **Nouveau profil de modèle** |
| **Action** | Remplir puis **Enregistrer** ; puis **Tester la connexion** sur la ligne |
| **Saisie** | **Nom** `ollama-local` · **Fournisseur** `openai_compat` · **Modèle** `qwen2.5:1.5b-instruct` · **Référence du point d'accès** `ALERTE_LLM_BASE_URL` (un **nom de variable**, jamais une URL ni une clé) · **Température** `0` · **Jetons max** (vide) · **Délai (s)** `120` |
| **Résultat attendu** | « joignable » (reachable) si `ALERTE_LLM_BASE_URL` est défini dans `backend/.env` et que le serveur répond |
| **Vérification** | Le badge « joignable » ; l'aperçu du prompt ne contient **aucun secret** |
| **Erreur possible** | « injoignable » ; `endpoint non configuré : définir la variable ALERTE_LLM_BASE_URL` ; `modèle non configuré` ; saisie d'une URL à la place d'un nom |
| **Correction** | Renseigner `ALERTE_LLM_BASE_URL`/`ALERTE_LLM_MODEL` dans `backend/.env`, **redémarrer** le backend ; saisir le *nom* de variable |
| **Étape suivante** | Étape 9 |

**Modèle par défaut ou par agent** : un agent **sans profil** utilise le serveur par défaut (`ALERTE_LLM_BASE_URL`/`ALERTE_LLM_MODEL`) lorsque l'exercice est en « Modèle réel » ; un agent **avec profil** utilise le sien (fonctionnalité **implémentée** ; non exercée avec deux modèles distincts dans ce guide). *[API]/[TEST] ; [UI] libellés.*

**Les trois modes d'exécution (à ne jamais confondre)** — choisis à la **création de l'exercice** (étape 15), champ **Mode d'exécution** :
| Mode | Ce que c'est | Étiquetage |
|---|---|---|
| **Modèle réel** | les agents appellent le fournisseur de modèle | seul mode qui peut montrer un agent IA ; qualité non validée avec un modèle de production |
| **Scénarisé (SANS IA)** | réponses déterministes (recherche puis décision citant le meilleur passage) | bandeau « **SANS IA — exécution scénarisée, ne prouve pas que l'IA fonctionne** » sur toutes les pages de l'exercice et dans les rapports |
| **Rejeu de cassette** | rejoue les réponses enregistrées d'un exercice | étiqueté « REJEU » ; exige une cassette nommée dans les paramètres [TEST] |

L'**ai_mode de l'exercice prime** sur le profil de l'agent (un exercice « Scénarisé » n'appelle jamais de modèle, même si l'agent a un profil).

---

## Étape 9 — Créer les agents

**Un agent = une institution virtuelle** : mission, instructions, **outils** et **limites**. Il ne sait que ce que son institution saurait.

| Outil | Utilité (du point de vue de l'utilisateur) |
|---|---|
| `search_kb` | chercher dans les **seules bases accordées** à l'agent (étape 10) |
| `ask_legal` | poser une question au **conseiller juridique** : réponse en 4 parties avec citations vérifiées, terminée par « pour exercice seulement ; à confirmer avec un juriste » |
| `post` | écrire dans le **tableau de coordination** (INFO, REQUEST, DECISION, OBJECTION, GAP_FLAG) |
| `decide` | enregistrer une **décision** avec sa base légale (citation exacte vérifiée) ou « aucune base légale trouvée » |

| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Créer un agent par institution qui doit jouer |
| **Pré-requis** | Étape 4 (institutions) |
| **Navigation** | **Agents** → **Nouvel agent** (New agent) |
| **Action** | Remplir le formulaire → **Enregistrer** ; répéter pour `HYDRO, MET, DPC, OPS, ART, MINSANTE, DPA, CTD, ANTIC` |
| **Saisie** | **Code** `AG-MET` · **Nom** `Agent MET` · **Rôle** `Institution` (pour HYDRO : `Système d'IA testé` ; `Conseiller juridique` existe mais **n'est pas nécessaire** : `ask_legal` est intégré) · **Institution** `MET` · **Mission** `Observer, prévoir et avertir des aléas météo ; juger la qualité des prévisions.` · **Instructions** `Tu détiens la science. Tu ne peux pas ordonner au public d'agir. Tu te méfies d'une sortie de modèle non validée par un prévisionniste.` · **Profil de modèle** `—` (aucun) · **Outils** : les 4 cochés · **Étapes max par activation** `4` · **Recherches max** `3` · **Appels max au conseiller par inject** `2` |
| **Résultat attendu** | Une ligne (Code, Nom, Rôle, Institution, Profil de modèle « aucun profil de modèle », Outils, Statut actif) avec **Modifier / Aperçu du prompt / Cloner / Archiver** |
| **Vérification** | **Aperçu du prompt** : le prompt système assemblé par le backend, **sans secret**, sans mention de lacunes attendues ; la mention « N mandats / N bases de connaissances » |
| **Erreur possible** | Code en double (`agent.duplicate`) ; institution déjà liée ; outil inconnu |
| **Correction** | Autre code ; **Cloner** pour dupliquer proprement |
| **Étape suivante** | Étape 10 |

**HydroSense (`HYDRO`, Système d'IA testé)** n'est **jamais joué par un modèle** : sa « sortie » à chaque événement qui lui est adressé est le champ **Sortie du système d'IA (JSON)** de l'inject (événements 2, 8, 14).
*Raccourci* : `seed_rising_waters.py --until 5` crée les 9 agents avec les missions du prototype. *Vérification : [UI] liste et libellés ; [API] création.*

---

## Étape 10 — Configurer les permissions agents × bases (Knowledge Access Mapping)

| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Décider quel agent peut lire quelle base — **appliqué par le serveur à chaque recherche** |
| **Pré-requis** | Étapes 6 (bases publiées) et 9 (agents) |
| **Navigation** | **Accès aux connaissances** (titre « Qui peut lire chaque base de connaissances ») |
| **Action** | Cocher/décocher la case à l'intersection **agent (ligne) × base (colonne)** |
| **Saisie** | Cases nommées « **AG-MET peut lire Cameroun** », etc. Permissions de l'exemple : `HYDRO` → CM seul ; `CTD` → CM seul ; `MET, DPC, OPS, ART, MINSANTE, DPA, ANTIC` → **CM + GL** |
| **Résultat attendu** | Notification « AG-MET peut désormais lire Cameroun » ; colonne **Impact** (« lit 2 base(s) ») ; avertissement « Agents sans aucune base de connaissances : … » si une ligne est vide |
| **Vérification** | Rechargez la page : les cases restent cochées. *Accueil* → « 16 permission(s) accordée(s) » |
| **Erreur possible** | Agent sans base : la préparation (étape 14) **bloque** (`agent.no_kb_grant`) |
| **Correction** | Cocher au moins une base par agent |
| **Étape suivante** | Étape 11 |

**Tester qu'un agent ne peut pas lire une base non accordée** : (1) décochez `AG-MET × GL` ; (2) lancez un exercice ; (3) **Audit et rejeu** → type `RETRIEVAL` du siège `MET` : les résultats ne viennent **jamais** de `GL`. Le périmètre est **construit par le backend** (jamais par le modèle) et chaque passage retourné est **re-vérifié côté base** ; en cas de violation un événement `SCOPE_VIOLATION` est consigné. *[TEST] : `tests/knowledge/test_scope_security.py` (canaris par moteur) ; [API] : `GET /exercises/{id}/snapshot` ; la procédure d'Audit n'a pas été cliquée.*

---

## Étape 11 — Créer ou sélectionner le scénario « Rising Waters — Cameroun »

**Le scénario central est celui des spécifications** (CM-01, 3 actes, 15 événements). Il n'est **pas** livré dans l'application : on l'**importe** depuis le pack généré (étape 1).

| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Charger les 15 événements de Rising Waters |
| **Pré-requis** | Étape 4 (les codes `MET, HYDRO, DPC, OPS, ART, CTD, ANTIC, MINSANTE, DPA` doivent exister) et étape 3 |
| **Navigation** | **Scénarios** → **Importer un YAML** (Import YAML) |
| **Action** | Choisir le fichier ; la page du scénario s'ouvre |
| **Saisie** | `alerte-platform/demo/rising-waters/cm01-rising-waters.fr.alerte-scenario.yaml` (version française ; `…en.…` pour l'anglais) |
| **Résultat attendu** | Notification « Scénario importé (0 avertissement(s)) » ; la ligne **CM-01 — Rising Waters — Cameroun**, langue `fr`, 15 injects |
| **Vérification** | Ouvrez-le : sections **Injects**, **Qui reçoit quoi**, **Contrôles en direct** : « Aucun problème bloquant » et « Appels au modèle estimés : jusqu'à 328 (plafond 199) » |
| **Erreur possible** | Un destinataire du YAML n'existe pas dans l'espace → avertissement/erreur ; YAML invalide (`scenario.import_invalid`) |
| **Correction** | Créer l'institution manquante (étape 4) puis réimporter |
| **Étape suivante** | Étape 12 |

**Les trois actes et ce qu'ils testent** (questions des spécifications) : *Acte 1 — fausse alerte à Douala* : qui vérifie la prédiction de l'IA ? qui peut demander/obliger la diffusion ? qui répond des dommages ? qui protège le canal ? *Acte 2 — crue manquée (Extrême-Nord)* : désaccord IA/terrain, capteurs défaillants, alerte tardive, français seulement, zones sans réseau. *Acte 3 — choléra et données* : base légale des données de localisation, transfert à l'étranger, responsabilité.

**Branches conditionnelles** (« si la protection civile refuse… ») : **non implémentées dans cette version** [ABS] — le prototype les écrivait mais les laissait désactivées ; la plateforme n'a pas de champ de condition. Seule la ligne principale se joue.
*Vérification : [API] import (15 injects, 41 destinataires) et lint ; [UI] libellés et page du constructeur.*

---

## Étape 12 — Configurer les événements (injects) et leurs destinataires

| # | Temps simulé | Destinataires | Panne | Actions exigées |
|---|---|---|---|---|
| 1 | D1 06:00 | MET | — | `issue_weather_warning` |
| 2 | D1 06:20 | MET, HYDRO | `false_alarm` | `validate_ai_forecast` |
| 3 | D1 06:45 | DPC | `over_trust` | `decide_public_alert` |
| 4 | D1 07:10 | OPS | `over_trust` | `compel_operator_alert`, `send_mass_alert` |
| 5 | D1 08:30 | DPC, CTD, ART | `false_alarm` | `liability_alert_harm` |
| 6 | D1 12:00 | MET, DPC, OPS, ART, CTD | `false_alarm` | `correct_false_alert`, `public_communication_after_error` |
| 7 | D1 15:00 | ANTIC, ART | `spoofing` | `block_spoofed_alert` |
| 8 | D11 04:00 | MET, HYDRO | `missed_event` | `report_sensor_outage`, `validate_ai_forecast` |
| 9 | D11 09:00 | CTD | `missed_event` | `act_on_local_warning` |
| 10 | D11 11:30 | DPC, OPS | `language_error` | `multilingual_alerting`, `reach_unconnected` |
| 11 | D11 18:00 | MET, DPC, OPS, ART, MINSANTE, CTD | — | `coordinate_response`, `activate_contingency_plan`, `evacuate_zone` |
| 12 | D25 10:00 | MINSANTE | — | `cholera_response` |
| 13 | D26 09:00 | MINSANTE, OPS, DPA | `privacy_breach` | `access_location_data`, `protect_personal_data` |
| 14 | D26 14:00 | DPA, MINSANTE, HYDRO | `data_leaves_country` | `authorise_transfer_abroad`, `cross_border_agreement` |
| 15 | D27 10:00 | MET, DPC, OPS, ART, MINSANTE, DPA, CTD, ANTIC | — | `accountability_report` |

Les **lacunes visées par l'auteur ne sont PAS dans le scénario** (elles sont dans `demo/rising-waters/lacunes-attendues.PRIVE.json`, à ne **jamais** importer : elles servent à mesurer, de façon indépendante, si l'exercice les retrouve — mesure T3). Les **étiquettes** (`life_risk`, `public_communication`, `harm_possible`, `ai_output_used_in_decision`, `channel_abuse`, `foreign_actor`…) sont dérivées des **faits** de chaque événement ; elles alimentent les règles de lacunes.

| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Vérifier/modifier un événement, ordonner, visualiser la distribution, lancer le lint |
| **Pré-requis** | Étape 11 |
| **Navigation** | Page du scénario (**Scénarios** → cliquer le scénario) |
| **Action** | **Ajouter un inject** / **Modifier** / **Supprimer** / **Monter** · **Descendre** (ordre) / **Exporter en YAML** / **Marquer prêt** |
| **Saisie** | Formulaire de l'inject : **Titre** `D1 06:20 — HydroSense : alerte ROUGE…` · **Temps simulé** `D1 06:20` (libellé libre) · **De** `HYDRO` · **Texte** · **Panne** (liste des 15 modes + `none`) · **Note de source** · **destinataires** (cases par code) · **étiquettes** (cases + « Autres étiquettes ») · **Ajouter une exigence** (action + justification) · **Sortie du système d'IA (JSON)** `{"statement": "…"}` pour un événement adressé à HYDRO |
| **Résultat attendu** | Tableau **Qui reçoit quoi** : une ligne par inject, une colonne par institution, « Oui » là où l'événement est distribué |
| **Vérification** | **Contrôles en direct** : « Aucun problème bloquant » ; « 7 mode(s) de panne distinct(s) utilisé(s) » (≥ 6 recommandé) |
| **Erreur possible** | Lint : `scenario.no_injects`, `inject.no_recipient`, `inject.unknown_recipient`, `inject.unknown_action`, `inject.unknown_fault_mode`, `inject.all_recipients` (distribué à tous : l'inégalité d'information est ce que l'exercice observe), `scenario.budget_estimate` |
| **Correction** | Corriger l'inject indiqué ; créer l'action manquante (étape 7.5) |
| **Étape suivante** | Étape 13 |

**Tests négatifs** (voir `SC-01`…`SC-10`) : destinataire inexistant, inject sans destinataire, action inconnue, inject à tout le monde : détectés par le lint. **Mauvais ordre chronologique** et **événements contradictoires** : **aucune vérification automatique** [ABS] (le temps simulé est un libellé libre ; l'ordre est celui de la liste ; la contradiction est voulue par le scénario).
**Modes de panne** : un mode est une **étiquette descriptive** (elle compte pour la couverture ≥ 6 et figure dans le ledger). **Seul `llm_outage`** change le comportement (le siège destinataire tombe en repli « décision de repli » ; constaté). Les 14 autres (dont `silent_institution`) **ne rendent pas** un siège muet : la panne est portée par le texte de l'événement.
*Vérification : [API] import, lint, ordre, surprise ; [UI] libellés du formulaire et du tableau.*

---

## Étape 13 — Préparer les participants et les sièges

| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Créer l'exercice, donner un siège à chaque institution (agent IA ou humain nommé) |
| **Pré-requis** | Étapes 9–12 |
| **Navigation** | **Exercices** → **Nouvel exercice** |
| **Action** | Remplir la fenêtre → **Créer** ; la page de l'exercice s'ouvre en statut *brouillon* ; bouton **Ajouter les institutions du scénario** puis **Enregistrer les sièges** |
| **Saisie** | **Scénario** `CM-01 — Rising Waters — Cameroun` · **Titre** `Rising Waters CM — autopilot scripted` · **Mode d'exécution** `Scénarisé (SANS IA)` · **Rythme** `Automatique` · **Budget d'appels au modèle** `330` (voir étape 14) |
| **Résultat attendu** | La page affiche « **EX-001 · Scénarisé (SANS IA) · Rythme: auto** », le bandeau **SANS IA**, et 9 lignes de sièges **préremplies** (`MET | MET | Agent IA | AG-MET`…) |
| **Vérification** | Colonnes **Code · Institution · Joué par · Agents · Nom de l'humain** ; « Joué par » ∈ *Agent IA / Humain / Scénarisé* |
| **Erreur possible** | Siège sans institution ou sans contrôleur ; agent non affecté ; siège humain sans nom |
| **Correction** | Compléter la ligne (voir étape 14) |
| **Étape suivante** | Étape 14 |

**Configuration A — Autopilot** : tous les sièges « Agent IA » (état par défaut après *Ajouter les institutions du scénario*).
**Configuration B — Human in the Seat** : sur la ligne `OPS` (ou `ART`), **Joué par** = `Humain` et **Nom de l'humain** = `Joueur Test`, puis **Enregistrer les sièges** ; un **lien de siège** `…/play#t=pla_…` est généré (à copier, **affiché une seule fois**, valable 24 h par défaut). L'agent du siège sert à la **reprise** si l'humain ne répond pas. Le **délai de réponse humaine** par défaut est **900 s** (`human_deadline_s`) avec reprise par l'agent ; ce réglage **n'est pas exposé dans l'interface** [ABS en UI] (API : paramètres de l'exercice).
*Vérification : [UI] création de l'exercice, préremplissage des 9 sièges, enregistrement ; [API] invitation et jeton de siège.*

---

## Étape 14 — Vérifier « Exercise Readiness » (contrôles avant lancement)

Sur la page de l'exercice, section **Préparation de l'exercice** : « N problème(s) bloquant(s) » / « N avertissement(s) » ; **Revérifier** (Re-check) ; **Marquer prêt** ; **Lancer l'exercice**.
**Bloquant** = empêche **Marquer prêt**. **Avertissement** = on peut lancer, mais c'est consigné dans le ledger (événement `SNAPSHOT.readiness`). **Info** = simple information.

| Contrôle (code) | Niveau | Ce qui est vérifié / pourquoi | Pour corriger |
|---|---|---|---|
| `seats.none` | Bloquant | au moins un siège | **Ajouter les institutions du scénario** |
| `seat.no_controller` | Bloquant | chaque siège a un contrôleur ; « agent » exige un agent | choisir Agent IA + un agent |
| `seat.human_unnamed` | Bloquant | un siège humain doit avoir un humain **nommé** | saisir **Nom de l'humain** |
| `seat.human_no_agent` | Avertissement | pas de recherche/reprise sans agent | affecter un agent |
| `agent.missing` | Bloquant | l'agent du siège existe | réaffecter un agent |
| `agent.no_model_profile` / `provider.not_ai` / `provider.test_failed` | Bloquant (mode *Modèle réel* seulement) | modèle valide et joignable | étape 8 ; ou passer en *Scénarisé* |
| `agent.no_kb_grant` | Bloquant | l'agent lit au moins une base | étape 10 |
| `kb.not_ready` | Bloquant | la base accordée est **publiée** | étape 6 |
| `scenario.no_inject` | Bloquant | le scénario a des événements | étape 11 |
| `inject.no_recipient` / `inject.unknown_recipient` | Bloquant | chaque événement a ≥ 1 destinataire existant | étape 12 |
| `inject.recipient_without_seat` | Bloquant | **chaque destinataire a un siège** (message : « destinataire sans siège : `CTD` ») | ajouter le siège |
| `inject.unknown_action` | Bloquant | chaque demande référence une action du catalogue | étape 7.5 |
| `scenario.budget` / `budget.exceeds` | Bloquant | estimation d'appels > **1,5 × plafond** | augmenter **Budget d'appels au modèle** (≥ 330 ici) |
| `budget.high` | Avertissement | estimation > plafond | idem |
| `institution.no_mandates` | Avertissement | « aucun mandat validé : l'agent n'aura aucune base » | validez des mandats (7.2) |
| `registry.not_reviewed` | Avertissement | « registre non revu complet : les lacunes seront rétrogradées » | 7.3 |
| `kb.coverage` | Avertissement | couverture documentaire incomplète | 5.4 |
| `provider.scripted` / `document.redistribution_unknown` | Info | exercice SANS IA / droits inconnus | — |

**Pannes volontaires à provoquer** (matrice `RD-01`…`RD-12`) : retirer tous les sièges (→ `seats.none`) ; **créer l'exercice sans budget** (→ `scenario.budget` + `budget.exceeds` : **constaté**, 2 blocages pour Rising Waters car l'estimation haute vaut ≈ 304–328 appels pour un plafond par défaut de 199 ; le budget est un réglage légitime de l'exercice, **à fixer à la création**) ; décocher toutes les bases d'un agent (→ `agent.no_kb_grant`) ; exercice en *Modèle réel* sans `ALERTE_LLM_BASE_URL` (→ `agent.no_model_profile`/repli) ; siège `Humain` sans nom ; supprimer le siège d'un destinataire (→ `inject.recipient_without_seat`).
**Ne contournez jamais un blocage** : corrigez-le. *Vérification : [UI] première page de préparation (43 problèmes bloquants quand aucun siège n'est défini ; libellés) ; [API] budget, mandats, registre ; [TEST] le reste.* ***Correction apportée pendant cette mission** : le message affiche maintenant le code de l'institution (`CTD`) et non son identifiant technique ; le contrôle de budget du scénario tient compte du budget de l'exercice.*
**Quand c'est prêt** : « Prêt » ; cliquez **Marquer prêt** (toast « Exercice marqué prêt ») puis **Lancer l'exercice**.

---

## Étape 15 — Lancer l'exercice en autopilot

| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Jouer Rising Waters de bout en bout, tous sièges en agent |
| **Pré-requis** | Étape 14 : exercice *prêt* |
| **Navigation** | **Salle de simulation** (liste) → cliquer l'exercice ; ou le lien « Ouvrir la salle » |
| **Action** | **Lancer l'exercice** sur la page de préparation ; en **Rythme = Automatique** les événements s'enchaînent |
| **Saisie** | — |
| **Résultat attendu** | Bandeau **SANS IA — exécution scénarisée, ne prouve pas que l'IA fonctionne** ; état **terminé** en ≈ 16 s ; **Budget : 76/330 appels au modèle** ; 15 événements, 9 sièges |
| **Vérification** | Constaté : 284 entrées de ledger (15 `INJECT`, 38 `RETRIEVAL`, 38 `CITATION_CHECK`, 38 `DECISION`, 76 `TOOL_CALL`, 76 `LLM_CALL`) ; **38/38 citations vérifiées** ; **mesure T6 : 15,2 s** |
| **Erreur possible** | « budget épuisé » (exercice mis en pause) ; erreur fournisseur (mode Modèle réel) |
| **Correction** | **Reprendre** avec un budget étendu ; vérifier le fournisseur |
| **Étape suivante** | Étape 16 |

**À savoir sur le mode SANS IA** : l'agent scénarisé **cherche puis décide toujours « Agit »** en citant le meilleur passage récupéré ; il **ne poste jamais** de message : le *Tableau de coordination* reste vide. C'est un outil de test de la plateforme. Les échanges entre institutions (étape 18) se testent avec un siège humain ou un vrai modèle.
*Vérification : [API] et [UI] (la page de la salle s'ouvre sans erreur, le flux SSE répond) ; démarrage par bouton non cliqué.*

---

## Étape 16 — Tester le contrôle manuel et les événements (Simulation Room)

**Lecture de la salle** (titre = nom de l'exercice) : en-tête (état, **Temps simulé**, **Budget**, flux *En direct*) ; boutons **Pause · Reprendre · Pas · liste « Rythme » · Surprise · Arrêter** ; **Événements** (chronologie, badge *en cours*) ; **Sièges** (une carte par institution : décision, vérifié / non vérifié, **Trace de décision**) ; **Tableau de coordination** (filtres INFO / REQUEST / DECISION / OBJECTION / GAP_FLAG, **Tour**) ; **Lacunes émergentes (signaux)**.

| Action (clic) | Résultat attendu | Vérifié |
|---|---|---|
| Créer l'exercice avec **Rythme = Manuel (pas à pas)**, le lancer | état *en cours*, sous-état « idle entre deux injects » : **aucun** événement n'est diffusé | [API] |
| **Pas** | **un** événement est diffusé et traité (1 puis 2…) | [API] |
| **Pause** | état *en pause* ; plus d'avancement | [API] |
| **Reprendre** | retour en *en cours* (option « étendre le budget » côté API) | [API] |
| liste **Rythme** → *Automatique avec délai* / *Automatique* | **accélère/ralentit** par un **délai entre événements** (`delay_s`) — ce n'est **pas** un multiplicateur de temps simulé | [API] |
| **Surprise** | ajoute un événement ad hoc (titre, texte, destinataires = codes de sièges, étiquettes, panne) ; marqué « surprise » ; consigné dans le ledger | [API] |
| carte d'un siège → *Donner à l'agent IA / Donner à un humain* | **changement d'attribution** entre deux activations ; événement `SEAT` avec la raison | [API] |
| **correction** d'une décision ou d'un événement | **pas de bouton** dans l'interface [ABS en UI] ; l'API crée une entrée `CORRECTION` pointant la décision corrigée (jamais de remplacement silencieux) | [API] |
| **Arrêter** (confirmer) | arrêt **propre** à la fin de l'unité en cours ; état *arrêté* ; la détection finale des lacunes s'exécute | [API] |

Ne modifiez **jamais** le snapshot d'un exercice lancé : toute reconfiguration passe par un **nouvel** exercice (*Cloner et rejouer*).
**Distribution par institution** : l'agent MET ne reçoit que les événements 1, 2, 6, 8, 11, 15… ; une institution ne peut **pas** lire la boîte d'une autre (403 « un joueur ne lit que la boîte de son siège » constaté).
*Vérification : [API] toutes les commandes ci-dessus sur un exercice manuel (284… entrées de ledger, 11 entrées `FACILITATOR`, 2 `SEAT`, 1 `CORRECTION`) ; [UI] présence des boutons et du sélecteur.*

---

## Étape 17 — Tester le siège humain et l'observateur

### 17.1 Player Seat
| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Jouer l'institution `OPS` (ou `MET`) en tant qu'humain |
| **Pré-requis** | Étape 13, configuration B ; exercice lancé |
| **Navigation** | Le **lien de siège** `http://localhost:5173/play#t=pla_…` (ouvrir dans une fenêtre privée) |
| **Action** | Lire, rechercher, interroger, poster, décider (voir ci-dessous) |
| **Saisie** | Voir tableau |
| **Résultat attendu** | La **fiche de rôle** : « Votre rôle », « Vos bases de connaissances » (CM, GL), « Autres sièges », « Vos mandats documentés (n) », « Événement en cours », outils et limites |
| **Vérification** | Le fragment `#t=` disparaît de la barre d'adresse (jeton gardé en mémoire de l'onglet) |
| **Erreur possible** | « Ce lien est invalide ou a expiré » ; décision refusée (citation) |
| **Correction** | Demander un nouveau lien à l'animateur ; copier la citation **exacte** |
| **Étape suivante** | 17.2 |

| Bloc d'écran | Saisie d'exemple | Résultat attendu (constaté) |
|---|---|---|
| **Recherche** — *Interroger vos bases de connaissances* | `avis officiel de crue service météorologique` | liste (chunk, titre, article, page, extrait, score) **limitée à vos bases** |
| **Interroger le conseiller juridique** → **Demander** | `Le service météorologique peut-il ordonner une évacuation ?` | réponse en parties « Ce que disent les textes / Ce que les textes ne disent pas / Ce que font les autres / À vérifier » ; en mode SANS IA elle est marquée `[scripted/no-AI]` ; **décomptée de votre limite** |
| **Message à une autre institution** → **Préparer le message** | À `DPC`, type `INFO`, `Pluies intenses confirmées sur Douala.` | « Message préparé » ; envoyé à la **clôture de votre tour** |
| **Votre décision** | **Action** `Émettre un avis de vigilance…` · **Issue** `Agit` · **Niveau de preuve** `inferred` · **Justification publique** (≤ 280 car.) · **Base légale** : identifiant de l'extrait + **citation exacte** · **Confiance** `medium` → **Soumettre la décision** | citation **fausse** ⇒ refus « **citation non vérifiée** » (`decision.citation_failed`, raison `quote_not_in_chunk`) — **constaté** ; sans base légale ⇒ choisir l'issue **Aucune base légale trouvée** |

**Ce que le joueur sait / ne sait pas** : le formulaire n'a **pas** de champs « ce que je sais / ce que je ne sais pas » [ABS, présents dans la spec] ; il demande : action, issue, **options envisagées** (une par ligne), **base légale**, **confiance**, **niveau de preuve**, **justification**. Les `gap_flags` (hint + texte) permettent de signaler une lacune.
**Reprise par l'IA** : si l'humain ne répond pas avant `human_deadline_s`, l'agent du siège reprend. **Constaté** (délai réglé à 6 s par API) : événements `HUMAN task_opened` → `HUMAN expired (agent_takeover)` → `SEAT human→agent reason=deadline_expired`, tous dans le **ledger** (Audit : type `HUMAN`/`SEAT`).
**Confidentialité** : le joueur **ne peut pas** lire la boîte d'un autre siège (403), **ne peut pas** envoyer de commandes d'animateur (403), voit un ledger limité aux événements *publics* et *de son siège*.
*Vérification : [API] tout le flux (invitation, fiche, tâche, recherche, conseiller, message, décision refusée, 403, reprise) ; [UI] la page `/play` s'ouvre sans erreur (contrôle antérieur) ; la saisie par formulaire n'a pas été cliquée.*

### 17.2 Observer View
1. **Jetons d'accès** (propriétaire) → **Rôle** `observer`, **Libellé** `Juge Dubaï`, **Expire dans** `24` → **Créer** ; copiez le jeton (une seule fois). L'interface ne lie pas le jeton à un exercice ; l'API le permet (`exercise_id`).
2. Ouvrez `http://localhost:5173/watch#t=<jeton>`.
3. Attendu : état en direct, **vue publique en lecture seule**.
4. Vérifié : l'observateur **ne peut pas** donner de commande, poster, créer un agent (403 « rôle insuffisant »), **ni lire** une boîte privée (403 « boîtes privées non visibles ») ni le tableau de coordination ; il lit le **ledger public**.
5. **Choix de ce que voient les observateurs** (tout / seulement le public) : **non implémenté** [ABS] — la vue observateur est toujours la vue publique.

---

## Étape 18 — Tester la coordination

**Ce que le moteur fait** (code déterministe, deux tours d'échange maximum par événement) : il détecte `ORPHAN_REQUEST` (demande à laquelle personne ne répond), `NO_OWNER`, `CLAIM_OVERLAP`, `CONFLICTING_DECISIONS`, `MISSING_BASIS`, `NO_RESPONSE`, `AGENT_HYPOTHESIS`, `UNSUPPORTED_DECISION` (panneau **Lacunes émergentes (signaux)**, visible des animateurs/auditeurs). Ce sont des **signaux, pas des constats**.

| Test | Comment | Attendu | Vérifié |
|---|---|---|---|
| Demande → réponse | siège humain : **Message** de type `REQUEST` à `DPC` ; la réponse se poste avec **statut** *accepté / refusé / pas notre rôle* | le tableau affiche les messages avec leur type ; refus motivé et « absence de responsabilité » possibles | [TEST] `tests/simulation/test_coord.py`, [API] `post` humain |
| Demande sans réponse | `REQUEST` à un siège qui ne répond pas | signal `NO_RESPONSE` / `ORPHAN_REQUEST` | [TEST] |
| Objection | message `OBJECTION` | affiché ; compté | [TEST] |
| Limite d'échanges | plus de 2 tours | rejet « tour maximal dépassé » (`post.invalid`) | [TEST] |
| Deux décisions contradictoires / revendications | selon le scénario | `CONFLICTING_DECISIONS` / `CLAIM_OVERLAP` | [TEST] |

En **SANS IA** les agents ne postent pas : le tableau reste vide (constaté). Pour voir des échanges : un siège humain, ou un exercice « Modèle réel » (non validé avec un modèle de production).

---

## Étape 19 — Analyser les lacunes (Gap Analysis)

| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Lire, vérifier, valider ou rejeter chaque lacune |
| **Pré-requis** | Un exercice terminé |
| **Navigation** | **Analyser** → **Analyse des lacunes** (`/gaps`) |
| **Action** | Filtrer, cliquer une lacune, lire sa fiche, enregistrer une revue |
| **Saisie** | **Filtrer** : **Exercice** `EX-001`, **Institution**, **Code** `G1`, **Catégorie**, **Gravité** *(Élevée/Moyenne/Faible)*, **Statut de revue** *(proposed/confirmed/disputed/rejected)*, **Base de preuve** *(documented/observed/inferred/hypothesis)*, **Origine** *(rule/coordinator_signal/agent_hypothesis…)*, case « Inclure les lacunes de détections remplacées » |
| **Résultat attendu** | Tableau **Code · Lacune · Gravité · Nature · Institutions · Confiance** ; pour le baseline Rising Waters : **42 lacunes** |
| **Vérification** | Cliquez une lacune : fiche (titre, **Conséquence**, **Chaîne de preuves** numérotée *1. MANDAT 2. TEXTE (page/article/extrait) 3. ÉVÉNEMENT DU SCÉNARIO 4. RECHERCHE NÉGATIVE…*, **Références et précédents internationaux**, **Plan d'amélioration**, **Revue humaine**, **Historique des revues**) |
| **Erreur possible** | « Aucune lacune trouvée » (exercice non terminé) ; filtre trop strict |
| **Correction** | Terminer l'exercice ; relancer la détection (API `POST /exercises/{id}/detect-gaps`) |
| **Étape suivante** | Étape 20 |

**Filtres demandés mais absents** : *pays*, *domaine*, *niveau de confiance* [ABS en UI] (la confiance est affichée en colonne).
**Revue humaine** (fiche d'une lacune) : **Décision** *(Confirmer / Contester / Rejeter / Commenter seulement / Rouvrir)* · **La lacune reflète-t-elle la réalité ?** *(Réelle / Partiellement réelle / Non réelle)* · **Motif** (**obligatoire** pour contester ou rejeter : « Un motif est requis… ») → **Enregistrer la revue** ; l'**historique** garde chaque revue (rien n'est effacé). Une lacune reste **« proposed »** tant qu'un humain n'a pas confirmé ; **aucune** lacune n'est confirmée parce qu'un agent l'a dite. **Actions d'amélioration** : **Ajouter une action** (Responsable, Échéance, KPI) — séparées des constats.
**Règles G1–G10 réellement implémentées** (table de règles ; priorité P0 = G1, G2, G3, G8 ; P1 = G4–G7, G9, G10) :
| Règle | Déclencheur (étiquettes/mandats) | Observé sur Rising Waters |
|---|---|---|
| G1 Responsabilité orpheline | action exigée, aucun mandat validé (`power`/`duty`) | **22** (baseline) |
| G2 Mandats qui se chevauchent | ≥ 2 pouvoirs sans chef de file | 0 (non provoqué) |
| G3 Procédure manquante | détenteur(s) sans procédure spécifique | apparaît après validation de CM-L15 |
| G4 Dépendance manquante | un mandat dépend d'une pièce non prête | apparaît après validation de CM-L15 |
| G5 Objectifs contradictoires | deux devoirs liés par un conflit | 0 (exige des liens de conflit entre mandats) |
| G6 Dommages | tag `harm_possible`, aucun mandat `liability` | **8** |
| G7 Inclusion | tag `public_communication`, aucun mandat `inclusion` | **7** |
| G8 Supervision humaine de l'IA | tag `ai_output_used_in_decision`, aucun mandat `human_oversight` | **2** |
| G9 Canal exposé | tag `channel_abuse`, aucun mandat `channel_protection` | **1** |
| G10 Transfrontalier | tag `foreign_actor`, aucun mandat `international_agreement` | **2** |
Extensions : `X0` hypothèse d'agent, `X2` lacune signalée par un agent, `X4` observation opérationnelle. Une absence n'est affirmée que si le **registre est « revu complet »** ; sinon la lacune est « **déduite** » (badge *Déduite*), jamais « *Étayée par des documents* ».
**Séparation constats / hypothèses** : badges *Étayée par des documents*, *Déduite (non documentée)*, *Hypothèse (agent)*, *Signal observé* (jamais *observé* en mode SANS IA).
**Limites constatées** : (1) la **recherche négative en mode lexical** affiche parfois des passages **sans rapport** comme « contexte » (p. ex. un tableau de vaccin) : lisez-les comme « passages les plus proches trouvés », pas comme preuves ; (2) la **bibliothèque de références internationales est vide** (« Aucune référence associée ») et **n'est pas gérable depuis l'interface** [ABS] ; les lacunes affichent donc « sources insuffisantes (< 2 juridictions) » ; (3) l'affichage d'une lacune ne prouve rien sur la qualité d'un modèle.
*Vérification : [UI] liste, fiche d'une lacune (chaîne de preuves) et formulaire de revue relevés ; [API] règles, comptages, revue.*

---

## Étape 20 — Le test contrefactuel : montrer que les lacunes ne sont pas préprogrammées

**Principe.** On joue Rising Waters **sans** le texte qui crée un mandat, on observe la lacune et ses preuves ; on **ajoute** le texte, on valide le mandat, on republie la base, on rejoue ; la lacune **disparaît** ; on **retire** le texte, on republie, on rejoue : elle **réapparaît**. **Texte choisi** : la loi camerounaise n° 2024/017 sur la protection des données personnelles (document `CM-01`), **article 32** (transfert à l'étranger soumis à l'autorisation préalable de l'autorité), qui fonde le mandat `CM-L15` pour l'action `authorise_transfer_abroad` (événement 14).
**Pré-requis** : étapes 1–19 ; `CM-L15` **encore « proposé »** (étape 7.2) ; les registres peuvent rester **non revus** (7.3) : la lacune est alors qualifiée **« déduite », confiance basse** (constaté : G1 « autoriser le transfert de données personnelles à l'étranger », `inferred`, `low`), ce qui est honnête ; un exercice de référence terminé.
**Règle** : chaque exercice garde **son** snapshot ; on ne modifie jamais un exercice lancé, on en crée un nouveau (**Cloner et rejouer**, qui crée un exercice lié à l'original, même scénario, mêmes réglages).

| # | Action exacte | Résultat attendu |
|---|---|---|
| 1 | **Bases de connaissances** → `CM` → page du document `CM-01` → **Retirer le document** (confirmer) → onglet **Versions et index** → **Note** `v2 — sans la loi 2024/017` → **Publier** | version `# 2` publiée **sans** `CM-01` (15 documents contre 17 ; le retrait d'un document déjà publié est permis, l'ancienne version reste intacte) |
| 2 | **Exercices** → ligne de l'exercice de référence → **Cloner et rejouer** → ouvrir le nouvel exercice → **Marquer prêt** → **Lancer** | exercice « contrefactuel 1 » terminé (≈ 16 s) |
| 3 | **Analyse des lacunes** → filtre **Exercice** = le n° 1, **Code** `G1` | la lacune « **Responsabilité orpheline : autoriser le transfert de données personnelles à l'étranger** » (gravité 3, base *documented*) avec sa chaîne de preuves (événement 14, recherche négative, couverture) — **constaté** |
| 4 | **KB `CM`** → **Documents** → **Choisir des fichiers** → `alerte/data/docs/CM/CM-01_Law_No_2024-017_of_23_December_2024_on_the_Protection_of_Personal_Data.pdf` (lecture seule ; **ne rien modifier dans `alerte/`**) ; métadonnées : Titre `Loi 2024/017 du 23 décembre 2024 sur la protection des données personnelles`, Juridiction `CM`, Langue `fr`, Type `law`, Fiabilité `official` | barre de progression ≈ **3 min** (OCR) ; document `needs_review` (« pages à relire » 2–24), 71 chunks, qualité 0,88 — **constaté** |
| 5 | **Pays et institutions** → **Registre des mandats** → ligne `CM-L15` → source : **Base de connaissances** `CM`, **Texte à rechercher** `transfert de données à caractère personnel vers un État étranger autorisation préalable` → **Rechercher** → **Utiliser comme source** sur le **nouveau** document, **ARTICLE 32** → **Valider** | `CM-L15` passe à *validé* ; le texte de l'article est partiellement dégradé par l'OCR (normal, voir 5.4) |
| 6 | **Bases de connaissances** → `CM` → **Versions et index** → **Note** `v3 — avec la loi` → **Publier** | version `# 3` |
| 7 | **Cloner et rejouer** → **Marquer prêt** → **Lancer** | exercice « contrefactuel 2 » terminé |
| 8 | **Analyse des lacunes** → **Comparer des exercices** → **Exercice A** = n° 1, **Exercice B** = n° 2 | colonnes **Nouvelles / Persistantes / Résolues** : la lacune **G1** de l'étape 3 est **résolue** ; deux lacunes **nouvelles** apparaissent pour la même action : **G3 « Procédure manquante »** et **G4 « Dépendance vers une pièce manquante »** (le pouvoir existe désormais, mais sans procédure ni pièce préalable) — **constaté** (E : 43 lacunes dont G3 + G4 ; sans le texte : 42) |
| 9 | **Rapports** → générer un rapport pour chacun des exercices 1 et 2 | deux rapports avec, chacun, l'empreinte de **son** snapshot et de la **tête de son ledger** (la comparaison *d'exercices* en rapport existe côté API `GET /reports/compare-exercises` [ABS en UI] ; dans l'interface elle se fait à l'étape 8) |
| 10 | Retirer le **nouveau** document (étape 4) → **Publier** `v4 — sans la loi` → **Cloner et rejouer** → **Lancer** | exercice « contrefactuel 3 » : **G1 réapparaît** ; comparaison 2 → 3 : G1 *nouvelle*, G3 et G4 *résolues* — **constaté** |

**Ce que l'on démontre** : la lacune dépend des **documents et des mandats validés**, pas d'une liste écrite d'avance. **Honnêteté** : ce test porte sur les règles G1/G3/G4 appliquées au registre ; il ne dit rien sur la qualité d'un modèle (exercices SANS IA) ; et il n'est valable que pour les mandats **rattachés au texte retiré** (un mandat est lié à **une version précise** de document ; une base copiée a d'autres identifiants, donc ne réactive pas un mandat lié à l'ancienne base).
*Vérification : [API] la chaîne complète a été exécutée (retrait → publication → exercice → téléversement réel du PDF → validation → publication → exercice → retrait → exercice) avec comparaison ; [UI] les écrans et libellés ; les clics n'ont pas été automatisés.*

---

## Étape 21 — Générer les rapports

| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Produire un rapport versionné et immuable à partir d'un exercice |
| **Pré-requis** | Un exercice terminé |
| **Navigation** | **Analyser** → **Rapports** (« Centre de rapports ») |
| **Action** | Section **Générer un rapport** : liste **Exercice** → **Générer** ; ouvrir le rapport ; **Publier (verrouiller)** ; **Télécharger md / json / csv / xlsx / pdf** |
| **Saisie** | **Exercice** `EX-001 — Rising Waters CM — autopilot scripted (SANS IA)` |
| **Résultat attendu** | Un rapport « v1 » (brouillon) avec : **couverture** (bandeau **SANS IA**, empreintes du snapshot et de la **tête du ledger**), **synthèse** (42 constats ; 38/38 citations vérifiées), contexte (institutions, bases, modèles), **constats** et **hypothèses** séparés, références internationales, **plan d'amélioration** (séparé des constats), revues humaines, **limites** et annexes (inventaire des bases, couverture, index des preuves), scorecard, métriques |
| **Vérification** | Constaté (exercice Rising Waters) : MD 175 Ko, JSON 327 Ko, CSV 36 Ko, XLSX 34 Ko, **PDF 230 Ko** (tous « 200 ») ; en-têtes `X-Content-SHA256` et `X-Ledger-Head` |
| **Erreur possible** | Modifier une version **publiée** → refus `report.immutable` ; PDF indisponible si Pango absent |
| **Correction** | Un clic sur **Générer** crée toujours un **nouveau rapport** (v1). Une **nouvelle version du même rapport** (v2, liée à la v1 par `parent`, comparable v1↔v2) se crée **par l'API** (`POST /exercises/{id}/reports` avec `report_id`) [ABS en UI] ; l'écran du rapport permet ensuite de **comparer deux versions** |
| **Étape suivante** | Étape 22 |

**Bien distinguer** : *constats* (règle + preuves), *hypothèses* (agents), *références internationales* (aucune n'est seedée : voir limites étape 19), *actions d'amélioration* (un **plan**, jamais un constat), *validations humaines* (historique), *limites de l'analyse* (section dédiée : mode SANS IA, couverture du corpus, recherche lexicale…). **Importer un rapport antérieur** (bouton **Importer un rapport antérieur** : PDF/DOCX/MD ; conservé tel quel, étiqueté « analyse antérieure », jamais mélangé aux lacunes de l'exercice) : disponible ; non exercé ici [UI libellés].
**Correction apportée pendant cette mission** : la génération du **XLSX** échouait (erreur 500) dès qu'une lacune n'avait **aucune** référence internationale — cas normal ici ; corrigé et couvert par un test.
*Vérification : [API] génération, 5 formats, publication, immutabilité, v2, comparaisons ; [UI] page du Centre de rapports.*

---

## Étape 22 — Consulter l'évaluation et le scorecard

| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Lire les 13 dimensions AI Readiness et les métriques T1–T6, sans jamais confondre « non calculé » et zéro |
| **Pré-requis** | Un exercice terminé |
| **Navigation** | **Analyser** → **Évaluation** |
| **Action** | Choisir l'**Exercice** ; **Calculer** (chaque métrique) ; remplir le scorecard (réponses *Oui / Partiel / Non / Non évalué* + preuve) → **Enregistrer** |
| **Saisie** | Exercice `EX-001` ; pour T1 : **base testée** + un jeu de questions (≥ 40) ; pour T5 : **identifiants d'exercices clonés** (séparés par des virgules) |
| **Résultat attendu** (constaté) | **T2 citations vérifiées : 38/38 = 100 %, atteint** ; **T6 : 15,2 s, 76 appels, atteint** (note « mode SANS IA ») ; **T1 : « non calculée — aucun jeu de questions pour cette base »** ; T3/T4/T5/benchmark/contrôle négatif : « non calculée — non exécuté ». **Scorecard : 13 dimensions, toutes « non évaluée »**, score global « non calculé » |
| **Vérification** | Aucune case n'affiche 0 pour une mesure absente |
| **Erreur possible** | T1 sans jeu de questions ; T3 sans fixtures scellées |
| **Correction** | Importer des questions (≥ 40 pour avoir un verdict) ; sceller les lacunes attendues (`lacunes-attendues.PRIVE.json`) via l'API d'évaluation |
| **Étape suivante** | Étape 23 |

**Limites** : l'**évaluation automatique du scorecard par LLM répond 501** (non implémentée, prévue P1) ; les **28 questions du prototype** attendent des identifiants de documents obsolètes (`CM-S01`, …) et ne sont **pas utilisables** ; T2/T6 en mode SANS IA ne disent rien de la qualité d'un modèle. *[API]/[TEST] ; [UI] la page s'ouvre.*

---

## Étape 23 — Vérifier l'audit

| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Prouver que le journal n'a pas été modifié et lire chaque événement |
| **Pré-requis** | Un exercice terminé |
| **Navigation** | **Analyser** → **Audit et rejeu** → choisir l'exercice (ou lien « Audit et rejeu » depuis la salle) |
| **Action** | **Vérifier le ledger** ; filtrer la **Chronologie** (**Type**, **Siège**, **Contient le texte**) ; ouvrir une ligne ; **Exporter en JSONL** ; depuis la salle : **Trace de décision** d'un siège |
| **Saisie** | Type `DECISION` ; Siège `MET` |
| **Résultat attendu** | « **Ledger intact (284 entrées contrôlées)** » ; **Tête de chaîne** (hash), **Empreinte de rejeu**, **Ancres** (#17, #18…) ; chronologie (n°, Type, Acteur, Temps simulé, Visibilité, Résumé) ; export `.jsonl` (≈ 256 Ko) |
| **Vérification** | Les types d'événements affichés : `SNAPSHOT, STATE, INJECT, LLM_CALL, RETRIEVAL, TOOL_CALL, CITATION_CHECK, DECISION` |
| **Erreur possible** | « Ledger NON intact » + « Première entrée altérée : n° N » |
| **Correction** | Restaurer depuis une sauvegarde ; comparer avec la tête exportée |
| **Étape suivante** | Étape 24 |

**Test d'altération (sûr, sur une copie isolée)** : `cd backend && ALERTE_TOKEN=<jeton propriétaire> .venv/bin/python scripts/ledger_tamper_demo.py --data-dir ./data-demo --exercise <id>` copie la base, **modifie une entrée dans la copie**, puis vérifie : **copie → `ok:false, première entrée altérée n° 10, « colonnes incohérentes avec les octets canoniques »** ; **original → `ok:true`**. *Constaté.* **Limite honnête** : le journal est **inviolable en apparence (tamper-evident), pas infalsifiable** : un administrateur qui contrôle la base **et** les ancres pourrait le réécrire ; exportez la tête hors du serveur.
*Vérification : [API] vérification, export, ancres, altération détectée ; [UI] page et libellés.*

---

## Étape 24 — Rejouer l'exercice

Page **Audit et rejeu**, section **Rejeu** : le curseur « **Position dans le ledger : n sur 284** » reconstruit l'état (ce que chaque siège avait décidé, ce que le tableau affichait) **à partir du seul ledger**.
**Vérifié** : lire le ledger (y compris l'export) **n'appelle aucun modèle** : le compteur d'appels de l'exercice reste à **76** avant et après. La **empreinte de rejeu** (`replay-digest`) identifie l'état de façon stable.
**Ne confondez pas** : le rejeu **ne relance pas** l'exercice ; il le *relit*. Pour **rejouer avec les mêmes réponses de modèle**, il faut le mode « Rejeu de cassette » (cassettes nommées) [TEST]. *[API] ; [UI] curseur présent.*

---

## Étape 25 — Les tests extrêmes

Utilisez la **matrice** `matrice-tests-fonctionnels-et-extremes.md` (≈ 165 cas, identifiants et priorités). Procédure conseillée : **chaque défaillance séparément**, puis le scénario composé.

### 25.1 Défaillances séparées (exemples exécutés)
| Défaillance | Provocation par l'interface | Observé |
|---|---|---|
| Fournisseur de modèle indisponible | **Surprise** avec **Panne** = `llm_outage` (destinataire `OPS`) | événement `ERROR llm_provider « simulated outage »` puis décision de **repli** (`author=fallback`, issue *Renvoie*) |
| Humain silencieux | siège `Humain` + délai court (API) | reprise par l'agent consignée |
| Aucun texte pour agir | exercice sans le document (étape 20) | lacune G1 *documentée* |
| Budget épuisé | **Budget d'appels au modèle** très bas | exercice mis en **pause** ; **Reprendre** avec budget étendu [TEST] |
| Citation fausse | décision humaine avec citation inexacte | refus `decision.citation_failed` |
| Doc malveillant (« ignore tes règles ») | document contenant ce texte | **alerte d'injection** dans *Qualité* ; le texte est traité comme **donnée citée**, jamais comme ordre [TEST] |
| Accès croisé | autre espace / autre siège / observateur | **404 / 403** partout (constaté) |

### 25.2 Scénario composé (stress)
Rejouez Rising Waters en y combinant : (1) base sans la loi 2024/017 (étape 20) ; (2) **Surprise** `llm_outage` sur `OPS` ; (3) siège `ART` en **humain** laissé silencieux (reprise) ; (4) **Surprise** « canal exposé » (`spoofing`, tag `channel_abuse`) vers `ANTIC, ART` ; (5) un agent **sans** base accordée dans un **second exercice** (blocage de préparation attendu) ; (6) budget serré. **Attendu** : l'exercice reste **compréhensible** (bandeau SANS IA, repli étiqueté), **cohérent** (ledger vérifié), **sécurisé** (403/404), **auditable** (événements `ERROR`, `SEAT`, `HUMAN`) et **honnête** (lacunes *déduites* si registre non revu ; « non calculé »). **Non testable en SANS IA** : JSON invalide, agent hors rôle, citation fausse produite par un agent, hallucination : couverts par les tests automatisés ; à valider **avec un vrai modèle** sur une machine adaptée (non fait).

---

## Étape 26 — Le scénario jumeau : Émirats arabes unis

**Cohabitation dans un seul espace.** Les codes d'institution, d'agent et de scénario sont **uniques par espace** : le jumeau porte donc le préfixe **`AE-`** (`AE-MET`, `AE-DPC`…, agents `AG-AE-MET`, scénario `AE-01`). Les **actions** (catalogue) sont **communes**. Les bases `AE` et `CM` sont **distinctes** : les agents Émirats ne lisent que `AE` + `GL`, les agents Cameroun que `CM` + `GL` (vérifié : institutions, KB et mandats séparés).

| Élément | Ce que je veux lire |
|---|---|
| **Objectif** | Jouer la **même histoire** avec les institutions et les textes des Émirats |
| **Pré-requis** | Étapes 1–15 faites pour le Cameroun |
| **Navigation** | Mêmes écrans, nouvelles données |
| **Action** | **Raccourci** : `.venv/bin/python scripts/seed_rising_waters.py --token <jeton> --country AE --lang en --from 2 --until 8`. **Pas à pas** : (a) pays *Émirats arabes unis* `AE` ; (b) 10 institutions `AE-HYDRO, AE-MET, AE-DPC, AE-OPS, AE-ART, AE-MINSANTE, AE-DPA, AE-CTD, AE-ANTIC, AE-MOI` ; (c) importer `alerte-kb-AE.zip` (9 documents) puis **publier** ; (d) **Importer un CSV** `demo/rising-waters/mandats-ae.csv` (17 lignes) ; (e) agents + accès `AE` + `GL` ; (f) **Importer un YAML** `ae01-rising-waters-twin.en.alerte-scenario.yaml` ; (g) exercice + sièges ; (h) lancer |
| **Saisie** | Équivalences du scénario : MET → NCM ; DPC → NCEMA ; ART → TDRA ; MINSANTE → Ministère de la Santé et de la Prévention ; DPA → UAE Data Office ; CTD → Municipalité de Dubaï ; ANTIC → UAE Cybersecurity Council ; OPS → opérateur générique |
| **Résultat attendu** | Exercice jumeau terminé (constaté : **33 s**, 9 sièges, 17 mandats importés) |
| **Vérification** | Filtre **Exercice** dans l'Analyse des lacunes : institutions `AE-*` seulement ; l'exercice Cameroun n'affiche que `MET…` |
| **Erreur possible** | Mélange de menus (les listes affichent **toutes** les institutions de l'espace, `AE-` et sans préfixe) |
| **Correction** | Lire le préfixe ; ou créer un **espace dédié** « ALERTE — Demonstration (UAE) » |
| **Étape suivante** | Étape 27 |

**Le scénario Émirats n'existe qu'en anglais** (le prototype n'a pas de texte français). **Comparer avec le Cameroun** : ouvrez les deux exercices côte à côte dans **Analyse des lacunes** (filtre Exercice). **Limite** : l'outil **Comparer des exercices** apparie les lacunes par **empreinte** (institution + action + règle) ; entre **deux pays** les institutions diffèrent, il renvoie donc *« 42 nouvelles, 0 persistante, 42 résolues »* — **sans valeur d'alignement** [partiel]. L'outil est fait pour comparer deux exercices **du même pays** (avant/après). La comparaison de pays se lit à la main (mêmes règles, mêmes comptages de départ : 22 G1, 8 G6, 7 G7, 2 G8, 2 G10, 1 G9, car tous les mandats sont « proposés »).

---

## Étape 27 — Comparer les résultats et récupérer les livrables

| Livrable | Où le récupérer | Format |
|---|---|---|
| Rapport d'un exercice | **Rapports** → **Télécharger** | MD, JSON, CSV, XLSX, PDF |
| Journal de l'exercice | **Audit et rejeu** → **Exporter en JSONL** | NDJSON |
| Base de connaissances | page de la base → **Export / import** → **Assistant d'export** | ZIP (manifeste + SHA-256) ; *Publication ouverte* refusée si droits inconnus |
| Scénario | page du scénario → **Exporter en YAML** | YAML |
| Lacunes comparées | **Analyse des lacunes** → **Comparer des exercices** | affichage |
| Métriques / scorecard | **Évaluation** | affichage (pas d'export dédié) |

**Critère d'acceptation** (partir d'un espace propre → exercice rejoué) : atteignable avec ce guide en **mode SANS IA**. **Ce qui reste à valider** : un exercice avec un **vrai modèle de production** (non fait), le test automatique 20 activations `pytest -m model tests/agents`, les embeddings sur l'ensemble de la base (≈ 14–16 h sur le poste de développement : machine d'équipe requise).

---

## Annexe A — Couverture des cas d'utilisation UC-01 à UC-24

| UC | Cas | Dans l'interface ? | Où / comment | Statut |
|---|---|---|---|---|
| 01 | Ajouter la bibliothèque d'un pays | oui | **Bases de connaissances** (étape 5) | **Opérationnel** (pas de proposition automatique d'institutions/thèmes par passage ; pas d'exécution de questions de test en UI) |
| 02 | Carte des responsabilités | oui | **Registre des mandats** (étape 7) | **Partiel** : import CSV, saisie, validation/rejet ; **pas** de génération de lignes depuis les textes [ABS] ; correction/historique en API seulement |
| 03 | Écrire/modifier une histoire | oui | **Scénarios** (étapes 11–12) | **Opérationnel** (import YAML + éditeur ; pas de liste « lacunes attendues » dans le scénario, par conception) |
| 04 | Préparer un exercice | oui | **Exercices** (13–14) | **Opérationnel** (choix de la visibilité des observateurs [ABS]) |
| 05 | Inviter des joueurs | oui | sièges **Humain** + lien (13) | **Opérationnel** |
| 06 | Démarrer/pause/reprise/rythme/arrêt | oui | **Salle de simulation** (16) | **Opérationnel** (rythme = délai, pas multiplicateur) |
| 07 | Autopilot | oui | (15) | **Opérationnel en SANS IA** ; **avec un vrai modèle : non validé** |
| 08 | Jouer un siège humain | oui | `/play#t=…` (17) | **Opérationnel** [API] ; champs « je sais / je ne sais pas » absents |
| 09 | Recevoir un événement et décider | oui | (17) | **Opérationnel** |
| 10 | Demander à une institution | oui | message `REQUEST` (18) | **Opérationnel** [TEST] ; les agents scénarisés ne l'utilisent pas |
| 11 | Conseiller juridique | partiel | bouton « Interroger le conseiller juridique » **dans le siège** | **Partiel** : pas d'écran autonome pour animateur/observateur |
| 12 | Événement surprise | oui | **Surprise** (16) | **Opérationnel** |
| 13 | Observer | oui | `/watch#t=…` (17.2) | **Opérationnel** (vue publique seule) |
| 14 | Lire le rapport des lacunes | oui | **Analyse des lacunes** (19) | **Opérationnel** (filtres pays/domaine/confiance absents) |
| 15 | Vérifier les sources | oui | chaîne de preuves, **Trace de décision** | **Opérationnel** |
| 16 | Rejouer | oui | **Audit et rejeu** (24) | **Opérationnel** (relecture du ledger, sans modèle) |
| 17 | Intégrité du journal | oui | **Vérifier le ledger** (23) | **Opérationnel** (altération détectée) |
| 18 | Scorecard | oui | **Évaluation** (22) | **Partiel** (saisie humaine ; évaluation LLM 501) |
| 19 | Confirmer/rejeter par un expert | oui | **Revue humaine** (19) | **Opérationnel** |
| 20 | Exporter/partager le rapport | oui | **Rapports** (21) | **Opérationnel** (téléchargement ; pas d'envoi) |
| 21 | Comparer deux pays | partiel | (26) | **Partiel** (jumeau jouable ; comparaison automatique non alignée) |
| 22 | Avant/après un changement de loi | oui | (20) | **Opérationnel** (prévu « Later » dans la spec : déjà disponible) |
| 23 | Reconstruire un événement réel | non | — | **Hors périmètre de cette version** (« Later ») |
| 24 | Profil de défaillance d'un système d'IA avant achat | non | — | **Hors périmètre** (« Later ») ; les modes de panne et la sortie scriptée de HydroSense en sont une ébauche |

*Les cas « Later » (UC-23, UC-24, histoires hors inondations, branches conditionnelles, arabe) ne sont **pas** des fonctionnalités P0 manquantes ; UC-22 est livré en avance.*
