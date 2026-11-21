# 15 — Décisions à valider et questions ouvertes

> Aucune implémentation ne démarre avant votre réponse. Les décisions sont classées par **urgence** : les **bloquantes pour samedi 21** conditionnent le démarrage ; les autres peuvent être tranchées en cours de route. Pour chacune : ma recommandation, l'alternative, et la conséquence d'un refus.

## 15.1 Bloquantes pour samedi 21 (à trancher ce soir ou demain matin)

| ID | Décision | Recommandation | Alternative | Si non tranchée |
|---|---|---|---|---|
| **V1** | **Node.js** | Utiliser l'installation **nvm existante** (vérifier `node`, `npm`, `nvm` et la version exigée par Vite/React/TypeScript) ; `.nvmrc` ; **jamais `sudo npm`** | Aucune réinstallation | **Tranchée** (brief du 2026-11-21) |
| **V2** | **Valider l'architecture** (monolithe modulaire, FastAPI sync + SQLite WAL, SSE sur ledger, boucle d'agent maison, `SearchScope` dans le SQL) | Valider tel quel | Voir les ADR 001-010 du doc 05 | Pas de gel des contrats |
| **V3** | **PDF des rapports** | P0 : page HTML d'impression (« Enregistrer en PDF ») ; P1 : PDF serveur WeasyPrint dans l'image | PDF serveur dès P0 (coûte une demi-journée de dépendances système) | Risque de glissement |
| **V4** | **Périmètre P0/P1/P2** (doc 14 §14.2) et **ordre de coupe** (§14.6) | Valider ; confirmer ce qui ne sera *jamais* coupé | Étendre P0 (au prix du calendrier) | Dérive de périmètre |
| **V5** | **Branche Git et dépôt** : `alerte-platform/` dans le même dépôt, sur une branche dédiée (ex. `platform/rebuild`) ; commits à chaque jalon **sur votre demande** | Branche dédiée | Dépôt séparé | — |
| **V6** | **Confirmer la nature du « rapport de lacunes »** à importer | `ALERTE_Technical_Report_v2.pdf` (section 6 : 6 lacunes de politique + 5 de standards) — c'est le seul rapport rédigé du projet (A3). Existe-t-il **un autre** rapport que vous avez en tête ? | Les `gaps.json` des anciens runs | Import de rapports mal ciblé |
| **V7** | **Modèle de test local** : télécharger un petit modèle (ex. 1,5–3B instruct) pour un smoke test du vrai chemin LLM | Oui, **aujourd'hui** (c'est le risque R1) ; je ne télécharge rien sans accord | Rien : tout en `scripted`, premier vrai test sur Sandbox jeudi | Premier vrai appel LLM tardif → risque de découvrir tard l'incompatibilité des sorties structurées |
| **V8** | **Contacter les organisateurs** sur la Sandbox (GPU ? modèles ? durée ? API hébergée autorisée ? fin d'accès le 28 ?) | Oui, aujourd'hui (je peux rédiger le message) | — | Plan A/B/C non départagé |

## 15.2 Arbitrages des spécifications (confirmer ou corriger)

| ID | Sujet | Arbitrage proposé |
|---|---|---|
| **V9** | Hiérarchie Simple / Spec (D-01) | Simple = comportement ; Spec = outils/schémas/règles/métriques ; **vos exigences prévalent** (doc 02 §2.1) |
| **V10** | **Licence du logiciel et licences du corpus** (D-29) | Choisir la licence du **code** (MIT dans l'ancien dépôt ?) ; **ne pas** l'appliquer aux textes ; qualifier chaque document (`redistribution`) — par défaut *inconnu* |
| **V11** | Siège humain **dans** le MVP (D-11) | Oui (version web) ; Slack hors périmètre |
| **V12** | Statuts de lacunes à deux axes + `evidence_basis` (D-06) | Oui (doc 09 §9.4) |
| **V13** | Langue : **interface anglaise complète en P0, français en P1** | Oui (jury anglophone) ; clés i18n dès le départ ; ou FR+EN en P0 (+ ≈ 0,5 j) |
| **V14** | **Parallélisation** : sessions séparées (une par worktree) ou outil *Workflow* (multi-agents, coût élevé, opt-in explicite) | Sessions séparées au début ; Workflow seulement si vous l'autorisez explicitement |
| **V15** | Création des agents `.claude/agents/{search,grep,audit}.md`, du *hook* de restriction d'écriture et d'un `CLAUDE.md` pour `alerte-platform/` | Les créer **après** validation, dans `alerte-platform/.claude/` (pas de modification des configurations globales) |
| **V16** | **Authentification** par jetons (pas de comptes) | Oui ; comptes utilisateurs en P2 |
| **V17** | **Hébergement d'API de modèles tiers** autorisé ? (question ouverte de la Spec L782, L930) | À confirmer auprès des organisateurs (V8) |
| **V18** | **Date de la finale** (8 vs 9 décembre) et obligation de la vidéo (obligatoire si retenu) | À confirmer ; sans effet sur le code |

## 15.3 Questions de fond qui conditionnent la qualité (non bloquantes pour samedi)

1. **Source d'autorité des demandes (`required_actions`)** : quel **référentiel externe** citer pour dériver les actions exigées par chaque inject (Sendai, Early Warnings for All, checklist ITU de télécommunications d'urgence) ? Sans référentiel, le rapport dira « dérivé de l'auteur du scénario » (risque de circularité, doc 09 §9.9).
2. **Qui valide le registre de mandats** (relecture humaine ligne par ligne, 31 lignes héritées + nouvelles) ? Sans validation, les lacunes sont étiquetées `inferred`.
3. **Qui qualifie les droits de redistribution** des 45 documents ? Sans cela l'export « ouvert » reste vide.
4. **Documents manquants** : AE-03 (charte IA — présente sous le nom AE-04), AE-07, document réel sur la chaîne d'alerte des EAU, CM-06, GL-08, GL-10, ITU-03/04 ; ceux-ci seront déclarés « manquants » dans les rapports de qualité (jamais inventés).
5. **Les 13 dimensions de l'AI Readiness** : relecture du rapport ITU v2.0 (le sous-agent n'a lu que les dimensions 5 et 6).
6. **Rapport technique de 5 pages** : à réécrire à partir de ce dossier (12 divergences relevées avec le rapport v2).
7. **Exercice « jumeau » CM/AE** : conserver (utile au contrefactuel et à la comparaison) ?

## 15.4 Ce que j'ai vérifié, et ce que je n'ai pas vérifié

| Vérifié (lu par moi ou par un sous-agent, selon la mention) | Non vérifié / à relire |
|---|---|
| Chemins réels, absence de `alerte-platform`, environnement (Node absent, Docker présent, Ollama sans modèle, CPU 4 cœurs) ; les 321 + ≈ 200 exigences (via sous-agents, avec relecture des sections clés) ; critères officiels du hackathon (via sous-agent) ; ID des modèles Claude et existence de `--advisor` (via sous-agent) | **NIST AI 600-1** (contenu) ; **PDF Y.3172** ; **HSEEP** (PDF), **ISO 22398**, **CAP**, **IFRC IDRL** ; pages **SQLite** (WAL/pragmas), `adr.github.io` ; vitesse **CPU** de BGE-M3, OCR arabe, tokenisation FTS5 arabe ; versions exactes (FastAPI 0.165, React 19.x, Vite 8.x) ; fiabilité des sorties structurées par modèle ; l'état des **tests de l'ancienne application** (la suite a expiré) ; le contenu détaillé des **13 dimensions** |
| Les décisions techniques majeures ont été soumises à **Opus 5.5** (revue critique, doc 14 §14.9) | Les recherches ont été réalisées par des sous-agents **Haiku** : les points décisifs sont marqués `[V]/[P]/[NV]` dans le doc 04 et les annexes ; aucune ne remplace votre relecture |

## 15.5 Statut après l'instruction du 2026-11-21

Les fondations de l'architecture V1 sont **validées** ; V2 (PostgreSQL cible, workers séparés, comptes) **n'est pas retenue**. **V3** (PDF) : WeasyPrint + repli, P1 du plan V1. **V5** : branche `platform/rebuild`. **V7** : sans objet (les tests IA réels se font sur une machine d'équipe). **V10** : licence du code à confirmer plus tard. **V14** : développement séquentiel centralisé, sous-agents pour recherches/audits. **V16** : authentification par jetons de l'architecture V1. Les autres décisions suivent le plan V1 ; les décisions ordinaires sont prises sans validation préalable (accord demandé seulement pour dépense, service payant externe, action irréversible, partage de données sensibles, push/publication, changement important de périmètre).
