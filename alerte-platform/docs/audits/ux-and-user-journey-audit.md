# Diagnostic de l'expérience utilisateur et du parcours (avant / après)

Date : 2026-11-24. Méthode : lecture du code des pages, parcours **dans un navigateur réel** (Chrome piloté) sur la copie des données de l'utilisateur et sur un espace neuf, captures d'écran avant/après, comparaison avec le modèle de données V1 (`docs/architecture/06-data-model.md`) et avec le schéma de relations demandé.

## 1. Relations entre ressources : ce qui est réellement enregistré

| Relation | Enregistrée en base ? | Champ / table | Visible et guidée dans l'interface (avant) | Après |
|---|---|---|---|---|
| Pays ↔ institutions | oui | `institution.country_id` (**facultatif** côté API) | liste « — » par défaut ; rien n'oblige | **pays obligatoire** quand un pays existe, **préchoisi** s'il est unique (backend inchangé : relation facultative conservée) |
| Pays ↔ bases de connaissances | oui | `knowledge_base.country_id` (facultatif) | champ facultatif, **absent de la liste**, **non modifiable après import** ; la base importée du Cameroun avait `country_id = null` (constaté sur les données de l'utilisateur) | colonne **Pays / juridiction**, menu **Rattacher à un pays**, avertissement pour une base **nationale** sans pays ; le script de démonstration rattache la base |
| Institution ↔ mandats | oui | `mandate.institution_id` | colonne « Institution » | + colonne **Réf.** (`CM-L10`) pour retrouver une ligne |
| Mandat ↔ source (passage d'un texte) | oui | `mandate_source.chunk_id / document_version_id` | **impossible d'ajouter une source à un mandat importé** (seulement à la création) | bouton **Sources** par ligne (rechercher, utiliser, enregistrer, retirer) |
| Agent ↔ institution | oui | `agent.institution_id` | champ « Institution » (liste « — ») | inchangé ; l'étape « Agents » de l'accueil signale « N sans institution » |
| Agent ↔ profil de modèle | oui | `agent.model_profile_id` | champ présent | inchangé |
| Agent ↔ KB autorisée | oui | table `agent_kb_grant` (exposée en `agent.kb_ids`) | page **Accès aux connaissances** (grille) | l'étape « Permissions » de l'accueil donne « X agents sur N ont au moins une base » |
| Scénario ↔ institutions / actions | oui (injects : `recipients`, `demands.action_code`) | snapshot de scénario | contrôles de Readiness (`inject.unknown_recipient`, `inject.unknown_action`) | inchangé |
| Exercice ↔ siège ↔ institution ↔ agent/humain | oui | `seat` | page Exercice | inchangé |
| Scénario ↔ **pays** | **non** (pas de `country_id` dans le scénario) | — | schéma demandé : « Pays concerné » | **écart assumé** : le lien passe par les institutions destinataires ; non modifié (pas de changement de modèle sans décision) |

Différences avec le schéma demandé (pas corrigées artificiellement) : (1) le scénario n'a pas de pays propre ; (2) « Documents sources / articles » n'est pas rattaché au mandat par un document mais par un **passage (chunk)** d'une version de document ; (3) l'institution et la base peuvent exister sans pays (champ facultatif dans l'API).

## 2. Problèmes constatés avant correction

| # | Problème | Preuve |
|---|---|---|
| U1 | Après la fusion, plusieurs écrans ne s'affichaient plus (voir [reconciliation](reconciliation-modifications-git.md)) | tests en échec, build cassé |
| U2 | L'accueil montrait 5 compteurs « Préparation » : **« fait » dès qu'un objet existe** (une base non publiée, sans pays ou sans mandat validé comptait comme faite) | capture « avant » : « Knowledge bases ✔ 2 » alors qu'une base est non publiée et que les deux n'ont pas de pays |
| U3 | **Aucun indicateur de la prochaine action** après une création ; la barre de parcours était statique | lecture de `JourneyBar` |
| U4 | **Étape 7.3 du guide impossible** : aucun bouton pour ajouter une source à un mandat importé | `MandatesTab.tsx` : `SourcePicker` seulement dans `MandateDialog` (création) ; validation d'un mandat sans source → « aucune source ne résout vers un chunk réel » |
| U5 | Le guide demandait de passer **9 institutions en « revu complet »** pour faire disparaître un avertissement | contraire à la règle « ne jamais déclarer un registre complet sans revue » |
| U6 | Mandat repéré par un code (`CM-L10`) **absent de la liste** | colonnes du tableau : pas de référence |
| U7 | KB importée sans pays et sans moyen de la rattacher | `country_id = null`, pas de contrôle dans la liste ni la page de détail |
| U8 | Institution créable sans pays (« — » par défaut) | formulaire |
| U9 | Le guide de test (27 étapes, tableaux de 10 lignes) est inadapté à une première découverte | demande de l'utilisateur ; arrêt à 7.3 |
| U10 | Onglets de « Pays et institutions » non adressables (`?tab=`) : impossible d'y renvoyer depuis une étape | `useState` local |

## 3. Améliorations réalisées (et comment elles ont été vérifiées)

| Amélioration | Fichiers | Vérification |
|---|---|---|
| **Checklist de préparation en 10 étapes à état réel** (Pays · Institutions · Bases · Mandats · Agents · Permissions · Scénario · Exercice · Préparation · Lancement/analyse) ; états *Fait / À compléter / À faire / Après : …* ; bouton d'action ; texte « pourquoi » sur l'étape suivante ; message si un rôle ne peut pas lire les données (pas de faux « rien configuré ») | `app/setup.ts`, `useSetup.ts`, `components/SetupChecklist.tsx`, `HomePage.tsx`, i18n | 9 tests unitaires ; **UI navigateur** sur espace neuf (pays → institution : « Ajouter un pays » → « Ajouter les institutions » → « Ouvrir les bases ») et sur les données utilisateur (« 2 base(s) · 1 publiée(s) · 2 sans pays ») |
| **« À faire maintenant »** sur chaque page de la phase Préparer | `JourneyBar.tsx` | UI ; mesuré : limité à Préparer pour ne pas ajouter 8 requêtes ailleurs |
| **Bouton Sources** par mandat + colonne **Réf.** + refus clair sans source | `MandatesTab.tsx` | **UI navigateur** : CM-L10 (Art. 7, CM-04), CM-L13 (Art. 24), CM-L14 (Art. 16) validés ; message « validation impossible : aucune source ne résout vers un chunk réel » |
| **Panneau d'aide du registre** : séquence importer → sourcer → valider → laisser le reste « proposé » → revue **réelle** ; trois états de revue ; pourquoi garder CM-L15 | `MandatesTab.tsx`, `geo.json` | affirmations relues par l'audit indépendant contre `mandates/service.py` |
| **Pays de la base visible et modifiable** | `KbListPage.tsx` | UI (capture après) |
| **Pays de l'institution obligatoire et préchoisi** | `InstitutionsTab.tsx` | UI : valeur préchoisie lue = identifiant du pays unique |
| **Onglet adressable** `?tab=countries|institutions|mandates` | `CountriesPage.tsx` | UI (routes smoke) |
| **Guide de démonstration court** (« Maintenant, voici ce que tu dois faire : … » à chaque étape) | `guide-demonstration-pas-a-pas.md` | libellés relus contre les fichiers de traduction ; étapes 1–3 et 6 rejouées dans le navigateur |

## 4. Ce qui n'est PAS fait (ouvert)

* **Formulaires « en petites étapes »** (§5.4 de la mission) : seuls la liste des bases (assistant en 3 étapes déjà existant) et les dialogues actuels sont conservés ; les autres formulaires (agent : nombreux champs) ne sont pas découpés.
* **Liens/boutons de correction directe** depuis chaque avertissement de Readiness : les messages indiquent déjà la cause ; un lien par avertissement n'a pas été ajouté.
* **Page « Pays » après création** : pas de bandeau « prochaine étape » propre à la page ; c'est la barre « À faire maintenant » qui joue ce rôle.
* **Pages de l'équipe** (`/present`, `/alerte`, `/what-if`, `/responsibilities`, vérification) : s'affichent sans erreur, **contenu non audité**.
* **Accessibilité** : revue ciblée par l'audit indépendant (labels, rôles) ; pas de passe axe complète sur les nouveaux composants (les tests axe existants passent).
