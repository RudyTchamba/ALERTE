# ALERTE — Première démonstration pas à pas (Rising Waters, Cameroun)

**Pour qui** : une personne qui découvre ALERTE. Aucune connaissance de React, d'API, de JSON, de SQL, de Git ou de code n'est nécessaire pour suivre le parcours ; seule la préparation des fichiers (étape 0) demande de copier-coller deux commandes dans un terminal.
**Durée** : environ 2 h (dont ≈ 25 min d'import automatique des PDF) en saisissant tout à la main (30 min si les institutions et agents sont déjà créés).
**À savoir** : tout est **fictif** (bandeau « Exercice fictif ») et l'exercice est joué en mode **« Scénarisé (SANS IA) »** : il montre le déroulement et l'analyse, pas la qualité d'un modèle d'IA. Le test d'agents IA réels est dans le [guide complet](guide-test-complet-interface.md), étape 15.

## Deux façons de faire — laquelle suivre ?

| | Méthode **recommandée** : l'interface | Méthode alternative : scripts (techniciens) |
|---|---|---|
| Pour qui | découvrir ALERTE, comprendre les liens entre les ressources | préparer vite un espace de démonstration |
| Comment | ce guide, du début à la fin | `python scripts/seed_rising_waters.py --until N` (voir [lancement-local.md](lancement-local.md) §6) |
| Contrepartie | plus long (saisie des institutions et des agents) | on ne voit pas où cliquer ni pourquoi |

**Suis ce guide. N'utilise pas les scripts en même temps** : ils créent un autre espace de travail.

## Comment ALERTE est organisé (30 secondes)

```
Espace de travail
 ├─ Pays ─ Institutions ─ Mandats (qui doit/peut faire quoi, avec sa source)
 │                    └─ Agent IA (joue l'institution)
 ├─ Bases de connaissances (textes de loi d'un pays) ── lues par les agents autorisés
 └─ Scénario (événements + actions exigées)
        └─ Exercice ─ Sièges (institution + agent ou humain) ─ Lacunes ─ Rapport ─ Audit
```

L'accueil affiche **« Votre préparation, étape par étape »** : 10 étapes dont l'état est calculé sur ce qui est **réellement enregistré** (pas sur les pages ouvertes). En haut de chaque page, la barre « **À faire maintenant** » te dit toujours la prochaine action. Si tu te perds : clique **Accueil**.

---

## Étape 0 — Préparer les fichiers et lancer l'application

1. Dans un terminal, depuis le dossier `alerte-platform/backend` (les dépendances sont déjà installées) :
   ```bash
   OMP_THREAD_LIMIT=1 .venv/bin/python -m uvicorn app.main:app_factory --factory --port 8000   # OMP_THREAD_LIMIT=1 : OCR rapide sur machine chargée
   ```
   *(Les modèles OCR français/arabe sont à installer une fois : [rebuilding-the-knowledge-base.md](../knowledge-base/rebuilding-the-knowledge-base.md) §2.)*
2. Dans un second terminal, depuis `alerte-platform/frontend` : `. ~/.nvm/nvm.sh && nvm use && npm run dev`
3. Ouvre **http://localhost:5173/access** dans ton navigateur.

Les fichiers de la démonstration sont déjà dans `alerte-platform/demo/rising-waters/` : `actions.csv`, `mandats-cm.csv`, `cm01-rising-waters.fr.alerte-scenario.yaml`.

**Maintenant, voici ce que tu dois faire : à l'écran « Créer un espace de travail », passe à l'étape 1.**

## Étape 1 — Créer l'espace de travail

*Pourquoi* : c'est le conteneur de tout ton projet ; deux espaces ne se voient jamais.

1. Dans **Nom de l'espace de travail**, saisis `Démo Rising Waters`.
2. Clique **Créer l'espace de travail**.
3. Un **jeton propriétaire** s'affiche, **une seule fois**. Copie-le dans un fichier de notes : il est introuvable ensuite.
4. Coche **J'ai copié et conservé le jeton propriétaire**, puis clique **Continuer vers l'espace de travail**.

*Tu dois voir* : l'accueil, le bandeau « Exercice fictif », et « **À faire maintenant : Ajouter un pays** ».

**Maintenant, voici ce que tu dois faire : clique « Pays et institutions » dans le menu de gauche (groupe Préparer).**

## Étape 2 — Le pays

*Pourquoi* : le pays est le périmètre juridique. Les institutions et les bases de textes s'y rattachent.

1. Onglet **Pays** → bouton **Nouveau pays**.
2. **Nom** : `Cameroun` · **ISO 3166-1 alpha-2** : `CM` · **Langues** : `fr, en`.
3. Clique **Enregistrer**.

*Tu dois voir* : le pays dans la liste, et « **À faire maintenant : Ajouter les institutions** ».

**Maintenant, voici ce que tu dois faire : ouvre l'onglet Institutions.**

## Étape 3 — Les institutions

*Pourquoi* : chaque agent IA jouera **une** institution ; chaque institution appartient à **un** pays (le formulaire le demande et préchoisit le Cameroun quand c'est le seul pays).

Pour chaque ligne du tableau : bouton **Nouvelle institution**, saisis **Code** et **Nom**, vérifie **Pays = Cameroun**, choisis le **Type**, clique **Enregistrer**.

| Code | Nom (à copier) | Type |
|---|---|---|
| HYDRO | HydroSense (système d'IA fictif de prévision des crues) | Système d'IA |
| MET | Direction de la météorologie nationale | Agence |
| DPC | Direction de la protection civile | Agence |
| OPS | Opérateur de téléphonie mobile (générique) | Opérateur |
| ART | Agence de régulation des télécommunications | Régulateur |
| MINSANTE | Ministère de la Santé publique | Ministère |
| DPA | Autorité de protection des données personnelles | Régulateur |
| CTD | Collectivités locales (Douala, communes de l'Extrême-Nord) | Collectivité locale |
| ANTIC | Agence nationale des technologies de l'information et de la communication | Agence |
| COORD | Conseil national de protection civile (comité de crise) | Agence |
| ONR | Observatoire national des risques | Agence |

*Tu dois voir* : 11 institutions listées ; l'accueil indique « 11 institutions ».

**Maintenant, voici ce que tu dois faire : ouvre « Bases de connaissances » dans le menu.**

## Étape 4 — Les bases de connaissances

*Pourquoi* : une base est une collection de textes **d'un pays**. Un agent ne peut citer que les bases **publiées** qu'on lui autorise. Les bases sont construites **à partir des PDF originaux** par le pipeline d'ALERTE (ce n'est plus l'archive du prototype).

1. Dans un terminal (voir [rebuilding-the-knowledge-base.md](../knowledge-base/rebuilding-the-knowledge-base.md)), lance la construction avec la **CLI** (le script `kb_build.py` est retiré) : commandes #10 à #17 du [catalogue](catalogue-commandes-et-fichiers.md) (`workspace create`, `knowledge kb-create`, `sources-migrate`, `adopt`, `curate`, `build --country CM`, `publish`). Aujourd'hui seule la base **CM** est construite (17 documents, 1 351 passages) ; GL, AE et ITU ne le sont pas.
2. Dans l'interface, ouvre **Bases de connaissances** : tu vois 4 bases, « Version publiée : v1 », et pour la base **Cameroun** le pays rattaché. Ouvre-la : **17 documents**, certains en « à relire » (pages difficiles à lire, ou « suite des articles interrompue »).
3. Ouvre le document **CM-01** : c'est un scan, vérifie les pages signalées avant de t'y fier.
4. *Droits* : la plupart des documents ont des droits « inconnus » ; ils restent **en local** et ne sont pas publiés.

*Tu dois voir* : 4 bases publiées. La recherche est **lexicale (dégradée)** tant que les embeddings ne sont pas calculés (étape « Calculer les embeddings » de la page de la base) : cherche avec des mots **de la langue du texte**.

**Maintenant, voici ce que tu dois faire : retourne dans « Pays et institutions », onglet « Registre des mandats ».**

## Étape 5 — Le catalogue d'actions, puis les mandats

*Pourquoi* : un mandat dit « telle institution doit/peut faire **telle action** ». L'action doit exister dans le catalogue **avant** l'import des mandats (sinon : « action absente du catalogue »).

1. Lis le panneau **Comment utiliser le registre des mandats** en haut de l'onglet : il résume cette étape.
2. Descends à **Catalogue d'actions** → **Importer un CSV** → choisis `demo/rising-waters/actions.csv` → **Essai à blanc** (tu lis « 25 créés, 0 erreurs ») → **Importer pour de bon**.
3. Remonte à la section **Mandats** → **Importer un CSV** → `demo/rising-waters/mandats-cm.csv` → **Essai à blanc** (« 14 créés, 0 erreurs ») → **Importer pour de bon**.

*Tu dois voir* : 14 mandats, tous **proposés**, tous « **aucune source** » : ils ne sont **pas encore documentés**.

**Maintenant, voici ce que tu dois faire : passe à l'étape 6 pour justifier trois mandats par leur texte.**

## Étape 6 — Valider les mandats qui ont une source (l'étape qui bloquait avant)

*Pourquoi* : un mandat n'est « documenté et actif » que s'il pointe vers un vrai passage d'un texte. Tu en justifies **trois** ; **les 11 autres restent « proposés »** et c'est normal.

Pour **CM-L10** puis **CM-L13** :

1. Dans la liste **Mandats**, trouve la ligne grâce à la colonne **Réf.**
2. Clique **Sources**. La fenêtre indique « aucune source ».
3. **Base de connaissances** : `Cameroun`. **Texte à rechercher** : saisis la phrase du tableau, **en français** (les textes sont en français ; une phrase anglaise ne trouve rien). Clique **Rechercher**.
4. Sous le bon passage (document + article du tableau), clique **Utiliser comme source**, puis **Enregistrer les sources**.
5. **Fermer**, puis **Valider** sur la ligne. Le statut devient **validée**.

| Réf. | Institution | Texte à rechercher | Passage à choisir |
|---|---|---|---|
| CM-L10 | ANTIC | `Agence Nationale des Technologies de l'Information régulation activités de sécurité électronique` | CM-04 · Article 7 |
| CM-L13 | DPA | `veiller à l'application de la présente loi délivrer les autorisations réclamations` | CM-01, passage « TITRE V DE L'AUTORITE DE PROTECTION… » (c'est l'article 53 ; l'OCR l'a lu « §3 », d'où l'absence de numéro) |

*Source partielle pour CM-L10* : l'article 7 fonde le **contrôle de la sécurité** par l'ANTIC, pas le pouvoir de **bloquer** une fausse alerte ; la validation reste honnête si tu précises « contrôle et alerte sécurité » dans la description. Le détail des 14 mandats (lesquels sont fondés, partiels ou sans source) est dans [sources-des-mandats-cameroun.md](../audits/sources-des-mandats-cameroun.md) : **lis-le avant de valider d'autres mandats**.

*Essai utile* : clique **Valider** sur `CM-L01` sans source → message « validation impossible : aucune source ne résout vers un chunk réel ». Le système refuse de valider sans preuve.

**Laisse `CM-L15` « proposé »** : il sert au test contrefactuel du [guide complet](guide-test-complet-interface.md) (étape 20) : tant qu'il n'est pas justifié, l'analyse signale une lacune ; une fois validé, un **nouvel** exercice ne la signale plus (l'exercice déjà joué ne change jamais).

### Et la « revue du registre » ?
Dans la section **Revue du registre par institution**, laisse **non revu** (`unreviewed`) partout. `revu complet` signifie « une personne a examiné **tous** les mandats de l'institution et la liste est complète » : ce n'est pas vrai ici (3 mandats sur 14 ont une source). Conséquence **normale** : plus tard, la préparation affichera des avertissements « registre non 'reviewed_complete' » et les lacunes seront qualifiées « déduites » (confiance basse), jamais « documentées ». C'est l'honnêteté voulue du système : **n'utilise jamais « revu complet » pour faire disparaître un avertissement**.

**Maintenant, voici ce que tu dois faire : ouvre « Agents » dans le menu.**

## Étape 7 — Les agents (un par institution)

*Pourquoi* : l'agent est l'acteur IA qui représente l'institution pendant l'exercice.

Pour chaque institution **sauf COORD et ONR** (elles n'ont pas de siège : elles ne reçoivent pas d'événement) : **Nouvel agent** → **Code** `AG-<code>` (ex. `AG-MET`), **Nom** `Agent <code>`, **Rôle** : *Institution* (pour HYDRO : *Système d'IA*), **Institution** : celle de la ligne, **Enregistrer**. Laisse les autres champs vides : en mode « Scénarisé (SANS IA) », le profil de modèle n'est pas utilisé.

Agents à créer : AG-HYDRO, AG-MET, AG-DPC, AG-OPS, AG-ART, AG-MINSANTE, AG-DPA, AG-CTD, AG-ANTIC (9).

**Maintenant, voici ce que tu dois faire : ouvre « Accès aux connaissances ».**

## Étape 8 — Les accès : quel agent lit quelle base

*Pourquoi* : sans accès, un agent ne peut rien chercher ni citer.

Dans la grille agents × bases, coche **CM** pour les 9 agents, et **GL** pour tous **sauf** AG-HYDRO et AG-CTD. Chaque case coche s'enregistre aussitôt (« AG-MET peut désormais lire CM »).

*Tu dois voir* : « Chaque agent a au moins une base de connaissances ».

**Maintenant, voici ce que tu dois faire : ouvre « Scénarios ».**

## Étape 9 — Le scénario

1. **Importer un YAML** → `demo/rising-waters/cm01-rising-waters.fr.alerte-scenario.yaml`.
2. Tu lis « Scénario importé (0 avertissement(s)) ». Ouvre-le : 15 événements en 3 actes (fausse alerte à Douala ; crue manquée dans l'Extrême-Nord ; conséquences sanitaires et transfert de données).

**Maintenant, voici ce que tu dois faire : ouvre « Exercices ».**

## Étape 10 — L'exercice et ses sièges

1. **Nouvel exercice** → **Scénario** : *Rising Waters — Cameroun* ; **Mode d'exécution** : *Scénarisé (SANS IA)* ; **Budget d'appels au modèle** : `330` (Rising Waters a 41 activations : avec le budget par défaut, la préparation est bloquée « appels estimés > 1,5 × plafond ») ; titre libre. Enregistre.
2. Ouvre l'exercice → **Sièges** → **Ajouter un siège** pour chacun des 9 agents : l'institution et l'agent correspondants, **Joué par** : *Agent*. **Enregistrer les sièges**.

**Maintenant, voici ce que tu dois faire : contrôle la préparation, étape suivante.**

## Étape 11 — Vérifier la préparation, puis lancer

1. Dans « Préparation de l'exercice », clique **Revérifier**. Tu ne dois avoir **aucun bloquant**. Les **avertissements** attendus : registres non revus, redistribution inconnue des textes, recherche lexicale seule (pas de vecteurs). Chacun indique quoi corriger.
2. Clique **Marquer prêt**, puis **Lancer l'exercice**. Le mode autopilote déroule les 15 événements (environ 15 à 60 s).
3. Ouvre **Salle de simulation** pour regarder.

*Tu dois voir* : un bandeau « SANS IA », les 9 sièges qui s'activent, des décisions avec citations vérifiées, puis l'état « terminé ».

**Maintenant, voici ce que tu dois faire : ouvre « Analyse des lacunes ».**

## Étape 12 — Lire les résultats

* **Analyse des lacunes** : une liste de lacunes (règles G1–G10) avec leurs preuves ; faute de revue de registre, elles sont « déduites ». Ouvre-en une pour voir l'évidence.
* **Rapports** : génère le rapport (PDF/HTML/…).
* **Audit et rejeu** : vérifie l'intégrité de la chaîne (« intègre ») et rejoue l'exercice **sans appel de modèle**.

**Maintenant, voici ce que tu dois faire : c'est fini pour la première démonstration. Pour aller plus loin (siège humain, observateur, événements surprise, test contrefactuel, jumeau Émirats, tests extrêmes), suis le [guide de test complet](guide-test-complet-interface.md).**

---

## Si tu es bloqué

| Symptôme | Cause | Que faire |
|---|---|---|
| « action absente du catalogue » à l'import des mandats | catalogue d'actions non importé | étape 5.2 |
| « validation impossible : aucune source… » | le mandat n'a pas de source | étape 6 (bouton **Sources**) |
| « institution inconnue : 'ONR' » | institution non créée | étape 3 |
| Étape grisée « Après : … » sur l'accueil | un prérequis manque | ouvre l'étape citée |
| « Préparation bloquée : appels estimés… » | budget d'appels trop bas | étape 10, champ **Budget d'appels au modèle** = 330 |
| Page lente | machine chargée / mode développement | voir [audit de performance](../audits/frontend-backend-performance-audit.md) ; `npm run build` puis servir `frontend/dist` par le backend |

## Ce qui a été vérifié (honnêteté)

* **[UI, navigateur réel — cette version]** création de l'espace, d'un pays et d'une institution (pays préchoisi), barre « À faire maintenant » et checklist de l'accueil ; étape 6 (refus sans source, ajout de source, validation) sur trois mandats ; les 23 routes principales s'affichent sans erreur.
* **[API/script, session précédente]** l'import d'archives, les mandats, les agents et accès, le scénario, l'exercice scripté (≈ 56 s sur machine chargée), les lacunes, l'audit.
* **[Non pilotés au clic dans cette session]** les étapes 4, 7 à 12 telles que décrites ici : les libellés des boutons ont été relevés dans les fichiers de traduction de l'interface ; signale tout écart.
