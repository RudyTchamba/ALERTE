# Réconciliation des modifications Git (après `git pull --rebase origin Rudy`)

Date de l'audit : 2026-11-24. Méthode : commandes Git **en lecture seule** (`status`, `branch -avv`, `log --graph`, `reflog`, `diff`, `show`, `merge-base`) ; aucun `pull`, `rebase`, `merge`, `reset`, `checkout`, `stash`, `cherry-pick`, commit ni push n'a été exécuté pendant cette phase. Les faits ci-dessous viennent de ces commandes ; ce document ne formule aucune hypothèse sur les intentions de qui que ce soit.

## 1. État initial du dépôt

* Remote : `origin` = `https://github.com/RudyTchamba/ALERTE.git` ; branche active **`Rudy`** (suit `origin/Rudy`, à jour).
* Branches : `Rudy` (`67a2525`), `main` locale (`5eb46fe`, **18 commits de retard** sur `origin/main`), `platform/rebuild` (`4be7e51`), distantes `origin/Rudy`, `origin/main` et `origin/pharaon` (`9419ec3`, identiques).
* Le `reflog` montre la chaîne exacte du `pull --rebase` (2026-11-23 17:59:58–59) : départ sur `7d0a694` (« Merge branch 'main' into Rudy », auteur RudyTchamba), un seul commit rejoué (`a608104` → `67a2525` « Update un the repo of alert »), retour sur `Rudy`.
* Modifications locales **non commitées** à l'ouverture de la session : 23 fichiers modifiés + 5 chemins non suivis (spécifications, rapport technique, `actions.csv`, dossier `alerte/` du prototype, non suivi par Git à la racine du dépôt).

## 2. Qui a fait quoi (vérifié par les auteurs des commits)

| Auteur | Commits | Période |
|---|---|---|
| **Landry Balekamen** (`pharaminusbaba@gmail.com`) | **18**, tous sur `origin/main` (de `ea908a3` à `9419ec3`), non fusionnés dans `main` locale | 22–23 nov. 2026 |
| RudyTchamba | 9 (dont le merge `7d0a694` et le commit rejoué `67a2525`) | 10–23 nov. 2026 |

Volume des 18 commits de Landry Balekamen par rapport à la base commune `5eb46fe` : **148 fichiers, +8 503 / −559 lignes** (42 fichiers `frontend/src/features`, 24 `i18n`, 9 `components`, 7 `backend/app/agents`, 6 `simulation`, 6 `knowledge`, 4 `gaps`, 4 `audit`, 2 `evaluation`, 1 migration, scripts, README, runbook AWS).
Le commit `c2032ee` (RudyTchamba) avait ajouté le dossier `alerte/` (prototype, 201 fichiers) que `a608104`/`67a2525` a retiré de l'index ; le dossier existe toujours sur disque, non suivi.

Constat important sur la **fusion** : `7d0a694` et le rebase ont laissé, côté frontend, des fichiers touchés des deux côtés dans un état incohérent (doublons d'imports, `PageHeader` sans `eyebrow`, espaces de noms i18n `citizen`/`reform` non enregistrés, 57 clés `home` et 12 clés `nav` perdues, dépendance `qrcode-generator` non installée). **Ce n'était pas une restauration d'anciennes versions** : c'est un mélange. Il a été réparé fichier par fichier (voir §6).

## 3. Les 18 commits par groupe fonctionnel — analyse et décision

Légende : **Conserver** · **Conserver après correction** · **Refactoriser** · **Retirer/remplacer** · **Reporter** · **À confirmer**.

| # | Commits (hash) | Contenu | Conformité V1 / spécification | Régression constatée | Décision |
|---|---|---|---|---|---|
| G1 | `ea908a3`, `1a08a7a` | Prompt agent v2 (règles/outils), citations vérifiables, langue des agents, ordre des injects (`inject.time_order`), démo sans embeddings | Conforme (citation vérifiée par le système, doc 08) ; l'avertissement d'ordre est un contrôle de Readiness de plus | aucune ; 539 tests backend verts | **Conserver** |
| G2 | `540916d`, `4978225` | Refonte visuelle « centre de crise », tailles de texte, `AppShell`, `Card`, `Button`, `Badge`, `Table`, page d'accueil, `EntryPage`, `RoomPage` | Navigation Préparer → Jouer → Analyser compatible avec les trois phases du document de référence ; accessibilité vérifiée (axe) par les tests existants | la fusion a cassé 3 fichiers (voir §2) ; l'accueil n'expliquait pas le Workspace | **Conserver après correction** (fait : fichiers rétablis + ajouts minimaux) |
| G3 | `1e141f0`, `9e831a9`, `7474b0c` | Flux animé de l'exercice, rejeu narré, mode présentation `/present`, QR « faire jouer le public », joueur humain sur téléphone | Extensions de démonstration ; ne contredisent pas V1 (siège humain = prévu) ; dépendance ajoutée : `qrcode-generator` | dépendance absente après le pull (corrigée par `npm ci`) | **Conserver** ; contenu fonctionnel **non audité en profondeur** (affichage vérifié) |
| G4 | `aeeb6ad`, `3186e24` | Carte des responsabilités (institutions × actions), simulateur « Et si… ? » (réforme sans toucher au registre) ; ajouts `simulation/common.py`, `snapshot.py` | Répond à la visibilité des relations institution/action ; ne modifie pas le registre | aucune | **Conserver** (ajoute 2 pages au menu : voir UX) |
| G5 | `741b841` | Moteur : l'arrêt ne fige plus l'exercice si la base est verrouillée ; `busy_timeout` 5 s → 30 s | Conforme ; atténue le « database is locked » connu | aucune | **Conserver** |
| G6 | `9d84c5f` | Alerte à la population (CAP 1.2, UIT-T X.1303) : `alerting.py`, page `/alerte` | Extension cohérente avec l'objet du hackathon (alerte précoce) | aucune | **Conserver** ; **à confirmer** : place dans la démo |
| G7 | `9e42697`, `dd879f9` (partie reform) | « Projet de texte vérifiable » : migration **0002** `reform_draft`, `gaps/reform.py`, pages `reform/` | Ajoute un schéma **additif** (table) via Alembic ; compatible V1 ; vérif. test migrations passe | aucune | **Conserver** ; **à confirmer** : appartient-il au périmètre V1 « Later » ? (doc 09) |
| G8 | `12cacce` | Juge IA du scorecard (`evaluation/judge.py`), signatures Ed25519 des ancres (`audit/signing.py`), prompts bruts, PDF de secours | Le guide précédent notait « juge IA : 501 » : c'est désormais implémenté. Signatures : renforcent « tamper-evident » **sans** le transformer en « tamper-proof » (clé locale `data/keys`) | aucune ; tests verts | **Conserver** ; à documenter (pas de revendication d'inviolabilité) |
| G9 | `dd879f9` | Corpus Cameroun « audité » : vrai décret 98/031, **recherche qui privilégie la loi** (pondération par autorité après RRF : officiel 1,0 / résumé 0,8 / non officiel 0,7 / non trouvé 0,6) et thésaurus de crise (`expand_query`, poids 0,5), scripts `fix_cameroon_kb.py`, `fix_cameroon_mandates.py`, PDF | La **portée** (scope) reste contrôlée à chaque recherche (re-vérification des chunks) : seul l'**ordre** change, rien n'est exclu. Cohérent avec doc 07 | à surveiller : un biais de classement est un choix produit | **Conserver** ; **à confirmer** : validation du poids par évaluation (aucune mesure fournie) |
| G10 | `9419ec3` | Modèle sur AWS (option A) : `providers.py`, `scripts/llm_target.py`, `setup_vllm.sh`, guide `aws-gpu-model.md` | Conforme (fournisseur configurable) ; **aucune ressource AWS créée** dans cette session | aucune | **Conserver** |
| G11 | `501fe3c`, `3310091`, `05a4eee` | README de compétition (EN), équipe | Documentation | le README affichait 517/56 tests (périmé) | **Conserver** ; chiffres mis à jour |

Aucun groupe n'a été **retiré**. Un seul élément a été **remplacé** : la liste « Préparation » de l'accueil (5 compteurs), voir §5.

## 4. Régressions identifiées (concrètes, mesurées)

1. Fusion : `AppShell.tsx`, `HomePage.tsx`, `EntryPage.tsx` non compilables ou doublonnés ; `Card.tsx`/`PageHeader` sans `eyebrow` ; i18n : namespaces `citizen`, `reform` non enregistrés, clés perdues. → **10 puis 3 tests frontend en échec** avant réparation.
2. Dépendance `qrcode-generator` déclarée dans `package.json` mais non installée localement → `npm ci`.
3. Backend : **aucune régression** (539 tests réussis, 2 ignorés — les deux tests marqués `-m model`).
4. **Écart d'expérience (pas une régression de code)** : l'interface ne permettait pas d'ajouter une source à un mandat **déjà importé** (bouton uniquement à la création) : c'est la cause réelle du blocage à l'étape 7.3 du guide.

## 5. Modifications conservées, corrigées, remplacées, reportées

* **Conservées telles quelles** : G1, G3, G4, G5, G6, G7, G8, G9, G10, G11 (voir tableau).
* **Corrigées** : fichiers frontend cassés par la fusion — version de l'équipe rétablie puis ajout **minimal** de la barre de parcours, du lien Glossaire, de l'encadré « Qu'est-ce qu'un espace de travail ? » ; union des fichiers i18n ; `PageHeader` = version de l'équipe + option `term`.
* **Remplacées** : l'ancienne liste « Préparation » de `HomePage` (5 briques « fait » dès qu'un objet existe) par `SetupChecklist` (10 étapes, états réels). Justification : le critère d'acceptation exige des statuts « issus des données réellement enregistrées ».
* **Reportées** : mesure du poids d'autorité de la recherche (G9) ; audit fonctionnel des pages G3/G4/G6/G7 ; décision de périmètre sur `reform` (G7) ; exécution de la CI (3 OS) toujours jamais lancée.

## 6. Ajouts de cette stabilisation (non commités — décision de commit à l'utilisateur)

Backend : `reference_statuses` en lot (suppression d'un N+1 sur `GET /gaps`) ; `POST /actions/import-csv` ; décodage UTF-8 → 422 ; script `seed_rising_waters.py` rattache la base nationale à son pays. Frontend : `app/setup.ts` (+ test), `useSetup.ts`, `SetupChecklist.tsx`, barre « À faire maintenant », dialogue **Sources** d'un mandat, colonne **Réf.**, colonne **Pays / juridiction** des bases, pays obligatoire pour une institution, panneau d'aide du registre, `?tab=` sur « Pays et institutions », textes i18n FR/EN. Documentation : les 4 runbooks, le guide pas à pas, ces audits.

## 7. Incidents de cette session (transparence)

* Un script de génération du pack (`rising_waters_pack.py`) a **supprimé** des fichiers de `demo/rising-waters/` puis a échoué (dossier du prototype introuvable). Les fichiers ont été recréés depuis `HEAD` (`git show`) ; le script ne supprime plus rien avant d'avoir généré. Une première tentative de restauration par `git restore` avait été **refusée** par le système et n'a pas été contournée.
* Une première version du message à l'utilisateur donnait un mauvais chemin pour le prototype : il est **à la racine du dépôt** (`<dépôt>/alerte/`, non suivi), trouvé automatiquement par les scripts.
