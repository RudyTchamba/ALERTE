> **Annexe — Recherche : critères officiels du hackathon, méthodes d'exercice (HSEEP...), typologie de lacunes.**
> Matériau de recherche brut produit le 2026-11-20 par un sous-agent (modèle Haiku 5.5), relu en diagonale par l'architecte. Les marqueurs « non vérifié » / `[NV]` / `[V]` / `[S]` sont ceux du sous-agent ; toute information utilisée dans le dossier principal est citée avec son niveau de vérification. Ce fichier est une pièce justificative, pas une spécification.

---

# 07 — Recherche : hackathon ITU (UAE) et méthodes de référence

Date de la recherche : 2026-11-20. Auteur : sous-agent `search`. Aucune modification du dépôt.

Légende : **[V]** vérifié sur la page ou le document cité ; **[S]** vérifié seulement par extrait de moteur de recherche ; **[NV]** non vérifié (non lu ou inféré).

---

## 1. Hackathon ITU « AI for Good Lab Hackathon: United Arab Emirates » (2026)

### 1.1 Sources lues

| Page | URL | Statut |
|---|---|---|
| Événement | https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/ | [V] lue via WebFetch (extraction par modèle, citations courtes) |
| Propositions de projets (formulaire) | https://aiforgood.itu.int/ai-for-good-sandbox-project-proposals-united-arab-emirates/ | [V] lue (formulaire d'inscription, critères) |
| Hackathon Kenya (sœur) | https://aiforgood.itu.int/event/ai-readiness-hackathon-kenya/ | [V] lue (extraction) |
| Recommandation ITU-T Y.3172 (fiche) | https://www.itu.int/rec/T-REC-Y.3172-201906-I et /en | [V] statut et titre ; contenu [NV] (page sans résumé) |
| Rapport ITU « AI Ready – Analysis Towards a Standardized Readiness Framework » v2.0, janv. 2026 | local : `/home/rtti/Documents/Github/ALERTE-for-ITUAIReadiness/alerte/data/docs/ITU/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf` | [V] pages de couverture, sommaire, dimensions 5 et 6 ; reste [NV] |
| Résumé d'équipe local | `/home/rtti/Documents/Github/ALERTE-for-ITUAIReadiness/alerte/data/docs/ITU/ITU-S01_Hackathon_requirements_summary.md` | Paraphrase, daté du 2026-10-02 |

### 1.2 Critères d'évaluation (verbatim, page événement, [V])

Source : https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/ (2026-11-20)

1. **Knowledge base quality** : « completeness, accuracy, and structure of ingested national material »
2. **Agent capability** : « relevance and accuracy of agent responses during simulated error scenarios »
3. **Policy, strategy, standards gap identification** : « unclear responsibilities, standards, technology and legislative gaps, coordination problems, conflicts between objectives »
4. **Auditability** : « transparency of agent reasoning through logs, chain-of-thought traces, and source attribution »
5. **Alignment with ITU standards** : « reflection of » le pipeline Y.3172 et l'AI Readiness Framework « in the solution architecture »

**FAQ** : « Accuracy of the AI Prototype does not fall under any evaluation criteria. »

Écart avec le résumé local : le résumé regroupe les critères en une liste sans les formulations exactes ; il ne signale pas la FAQ sur l'exactitude du prototype, qui est importante.

### 1.3 Critères du formulaire de proposition (verbatim, [V])

Source : https://aiforgood.itu.int/ai-for-good-sandbox-project-proposals-united-arab-emirates/

- « Relevance to AI solutions in government services using agentic AI technologies »
- « Contribution to regional perspective in AI technology »
- « Contribution to the open local dataset and model building »
- « Contribution to Standards and Policy gaps »
- « Clarity and completeness of the project proposal and implementation strategies »

Livrable de proposition : résumé de **5 pages maximum**, PDF ou DOCX, qui doit « Clearly describe the project and its implementation strategies ». Champ optionnel « Reference Links ».

### 1.4 Exigences sur la base de connaissances (verbatim, [V])

- « Make sure that the solution is mapped to and adhere to the published and open documents provided by the country »
- Base « vectorized, distributed knowledge base hosted in the ITU AI for Good Lab », construite avec le code de référence ITU.
- Sources attendues : lois, stratégies nationales IA / numérique / cybersécurité, législation sur la protection des données, régimes de PI.

### 1.5 Agents et rôles institutionnels (verbatim, [V])

Quatre options de solution listées :
- « Innovative AI solution »
- « Policy and legal adviser »
- « Institutional participant » : un agent qui « assumes the role of a specific government actor »
- « Multi-agent coordination » : « Inter-agent coordination protocols should orchestrate the interaction. »

Le résumé local dit « multi-agent coordination with agents receiving different information and operating under different mandates » : c'est une paraphrase fidèle, mais le mot « mandates » n'apparaît pas sur la page.

### 1.6 Scénarios progressifs (verbatim, [V])

« Design and administer interactive error scenarios with sequenced, chunked events released progressively (not all at once) »

### 1.7 Lacunes de politique et standards, bonnes pratiques (verbatim, [V])

- « the relevance of the gaps and accuracy of the global policy examples would be a critical part of the evaluation »
- « Rather than analysing specific geographies or country specific recommendations, participants should focus on domain specific policy gaps »
- Recommandations « could be based on global best practices and policy examples. »

Point d'attention : la consigne est de travailler sur les lacunes par domaine et non sur des recommandations propres à un pays. Le rapport ALERTE doit donc citer des exemples mondiaux, pas seulement UAE.

### 1.8 Auditabilité (verbatim, [V])

« audit logging and chain-of-thought tracing » pour que décisions, raisonnements et références de politique soient « transparent and reviewable ».

### 1.9 Livrables attendus à la finale ([V])

- **Rapport technique : 5 pages maximum**, sur modèle fourni.
- **Dépôt GitHub**.
- **Base de connaissances** de politiques, règlements et stratégies.
- **Vidéo de démonstration optionnelle, 7 minutes maximum** ; elle devient **obligatoire pour les équipes retenues** après la première évaluation. Contenu attendu (FAQ) : mise en place matérielle et logicielle, fonctions principales, résultats attendus par scénario, résultats réels.
- Code (FAQ) : on peut ne publier que les parties essentielles ; cela « might or might not influence the judges' decision ».
- **Non précisé sur la page** : licence open source, format de présentation finale au-delà de GitHub, poids des critères.

Note sur la licence : la page n'impose pas de licence. Le résumé local ne mentionne pas de licence non plus. À demander aux organisateurs si l'on veut publier sous licence ouverte.

### 1.10 Calendrier ([V] page événement, FAQ)

| Date | Étape | Statut au 2026-11-20 |
|---|---|---|
| Samedis 3, 10, 17, 24, 31 oct. et 7 nov. 2026, 10h–11h CEST | Sessions de mentorat | passé |
| **10 nov. 2026** | Date limite de soumission | **passée** |
| 11–18 nov. 2026 | Première évaluation | **passée** |
| **18 nov. 2026** | Annonce de la liste retenue (shortlist) | **passée** : l'équipe doit savoir si elle est retenue (si oui, la vidéo de démo devient obligatoire) |
| **8 déc. 2026** | Évaluation finale, « Onsite in Dubai during the GITEX Global » | à venir |
| **9 déc. 2026**, 09h–17h GST, Dubai | Fiche événement « In person » | à venir |
| 10 déc. 2026, Dubai | Cérémonie de remise des prix | à venir |

**Incohérence** : la page indique l'évaluation finale le **8 déc.** et la fiche événement le **9 déc.** Non résolu : à confirmer auprès des organisateurs.

Le résumé local ne donne pas le calendrier. La page ne donne pas non plus de date d'accès au Sandbox.

### 1.11 Ressources Sandbox ([V] page événement)

- Crédits cloud : « Use the cloud credits in the Sandbox to fine-tune AI models ».
- Accès : les équipes sélectionnées obtiennent « ITU AI for Good Lab and sandbox ».
- **Non précisé** : type de GPU, montant des crédits, modèles disponibles, dates d'accès, durée du Sandbox.

### 1.12 Règles de jugement ([V])

- Prix du jury : « based on the level of engagement, future potential in terms of research, development, innovation, or standards potential ».
- Équipes : 4 personnes maximum ; un seul prix par équipe.
- Prix spécial équipes féminines : seulement si l'équipe a une femme comme leader.
- Certificat : seulement pour les équipes ayant soumis une solution valide.
- Prix (CHF) : 1500 / 1000 / 600 ; prix spécial féminin 600 ; prix du jury 1000.
- **Non précisé** : composition du jury, méthode de notation, traitement des égalités.

### 1.13 Comparaison avec le résumé local

| Point | Résumé local | Page officielle |
|---|---|---|
| Critères | Liste sans verbatim | 5 critères verbatim + FAQ « accuracy not a criterion » (absente du résumé) |
| Livrables | Non détaillés | Rapport 5 p., dépôt GitHub, base de connaissances, vidéo 7 min (obligatoire si retenu) |
| Calendrier | Absent | Dates complètes ; soumission et shortlist déjà passées |
| Sandbox | Absent | Crédits cloud pour fine-tuning ; GPU et durée non précisés |
| Domaines | « healthcare, education, telecom and public services » | Formulaire : government services (agentic AI), telecom, healthcare, education |
| Lacunes | « mapped to global best practices » | Ajoute « relevance of gaps and accuracy of global policy examples » comme élément critique |

Conclusion : le résumé local est fidèle sur le fond mais incomplet sur les livrables, les dates et la règle de la FAQ.

### 1.14 Pages sœurs et contexte

- **Hackathon Kenya** (Nairobi, 21 mai 2026, [V] extraction) : thèmes agriculture, éducation, santé, finance ; critères : « Clear description of use case with respect to ITU T Y.3172 machine learning pipeline », « Clear mapping to ITU AI Readiness factors and dimensions », « Contribution to knowledge base, reviewed by ITU experts », « Input to AI strategies and policies, reviewed by policymakers and dignitaries ». Fichiers attendus : liens de références vers des politiques IA nationales. Équipes de 4 au maximum.
- **Cameroun** : pas de page hackathon spécifique trouvée [S]. Le Cameroun est un des pays pilotes du Sandbox AI for Good Lab (avec Inde, Mozambique, Népal, Pérou, Tanzanie, UAE, Ouzbékistan, Zambie, Zimbabwe) [S].
- **AI for Good Lab** lancé le 8 juillet 2026 [S].

---

## 2. Cadres ITU

### 2.1 ITU-T Y.3172

- Titre : « Architectural framework for machine learning in future networks including IMT-2020 ». Approuvé le 22 juin 2019 (Y.3172 (06/19)), statut « In force » [V] (fiche ITU).
- Portée : exigences architecturales et composants pour satisfaire ces exigences, dont le **pipeline ML** et les **fonctions de gestion et d'orchestration ML** [S] (extrait de moteur, non lu dans la fiche).
- Le sandbox ML n'est pas dans Y.3172. Un projet séparé, Y.ML-IMT2020-SANDBOX (« Architectural framework for Machine Learning Sandbox in future networks including IMT-2020 »), a été envoyé à consentement en juillet 2022 ; son statut d'approbation est **[NV]**.
- Lecture du PDF Y.3172 : [NV], non obtenu. Les couches détaillées du pipeline ne sont donc pas vérifiées.

### 2.2 AI Readiness (rapport ITU, v2.0, janvier 2026) — lecture locale

- Sommaire lu [V] : 1 Introduction (p. 7) ; 2 ITU AI Readiness Basic Framework (p. 12) avec cinq volets : **Data, Digital Infrastructure, Digital Skills, Innovation Ecosystem, AI Policy** ; 3 Structural Approach (p. 17) : **Factors** (p. 17) et **Dimensions** (p. 18) ; **4 AI Readiness Gap Analysis (p. 35)** ; 5 AI Readiness Framework Engagement, dont **AI Readiness Toolkit** (p. 37) ; 6 Future work (p. 43) ; annexes FAQ.
- Dimensions lues [V] : « Dimension 5: Level of Integration of AI in Workflows » (mappée au facteur Standards : « Integrating different AI techniques into various domain workflows needs standards to guarantee their interoperability ») ; « Dimension 6: Human Interface » (mappée Standards et facteurs de déploiement) ; « Contextualization & Regional Impact » (p. 22, dimension dont le numéro n'a pas été vu [NV]).
- Liste complète des **13 dimensions** : [NV]. La recherche a donné « 13 » dans plusieurs sources [S], mais je n'ai pas lu la liste complète. Il ne faut pas la citer tant qu'elle n'est pas lue (pages 18–34 du rapport).
- Le chapitre 4 « AI Readiness Gap Analysis » (p. 35) est le plus utile pour le module Gap Analysis. Non lu [NV] : il faut le lire avant de l'utiliser.
- Le rapport est « intended for informational purposes only » et ne donne pas de notation ou de classement ; il présente l'Index comme une aide à la coopération [S].

---

## 3. Méthodes de référence pour exercices et analyse de lacunes

### 3.1 HSEEP (FEMA, programme d'exercices de sécurité intérieure, révision 2020)

Sources : https://www.fema.gov/hseep ; fiche HSEEP 2020 (https://www.fema.gov/sites/default/files/2020-04/HSEEP-Information-Sheet-20200203.pdf) — **PDF non lisible** (cf. section 4). Éléments obtenus via gabarits d'État (Missouri, Indiana, Massachusetts) [S].

Ce qu'il apporte :
- **Structure AAR/IP** : le gabarit AAR/IP (Rev. 2020) comprend un résumé exécutif, la présentation de l'exercice, une **analyse des capacités** (tableau objectifs → core capabilities → notes de performance), puis les **observations** (« areas for improvement »), puis un **plan d'amélioration** en annexe [S]. Les versions varient (Rev. 2017 au Massachusetts) : à vérifier selon le cadre retenu.
- **Séparation observation / recommandation** : une observation énonce le problème ou la lacune ; la recommandation (action corrective) va dans le plan d'amélioration [S].
- **Notes de performance** : une échelle à quatre niveaux, dont « Unable to be Performed (U) » [S]. Les trois autres niveaux (performed without challenges / with some challenges / with major challenges) : [NV] sur la source, à confirmer.
- **Plan d'amélioration** : colonnes : core capability, problème (issue), action corrective, élément de capacité, organisation responsable principale, point de contact, dates de début et de fin [S]. Il n'y a pas de colonne « statut » dans ces gabarits : à ajouter.
- **Actions correctives SMART** : spécifiques, mesurables, atteignables, pertinentes, datées [S].
- Core capabilities : le nombre et la liste des capacités essentielles de la Stratégie nationale de préparation (National Preparedness Goal) n'ont pas été lus [NV].

Adoptable pour ALERTE : le couple « observation (lacune) → plan d'amélioration (action, responsable, échéance, statut) » ; les notes de performance comme base de gravité ; la règle SMART pour les actions.

### 3.2 ISO 22398:2013 (Lignes directrices pour exercices de sécurité sociétale)

Sources : https://www.iso.org/fr/standard/50294.html ; texte intégral non lu [NV].

- Portée [S] : lignes directrices pour planifier, conduire et améliorer un **programme d'exercices** et des **projets d'exercice** ; applicable à tout type d'organisation, publique ou privée ; adaptable.
- Annexes informatives sur les exercices dans un système de management, et sur les exercices stratégiques nationaux [S].
- Confirmée en vigueur (revue 2022) [S].
- Adoptable : le cycle plan → conduite → amélioration, et le fait de traiter l'exercice comme un programme (une simulation ALERTE = un projet d'exercice dans un programme). Ne pas citer de clauses précises sans lecture du texte.

### 3.3 OMS (WHO)

- **WHO Simulation Exercise Manual** (WHO-WHE-CPI-2017.10) : guide pratique pour planifier, conduire et évaluer des exercices de simulation [S].
- **Country implementation guidance on AARs and SimEx under the IHR MEF** (WHO-WHE-CPI-2018.48) [S].
- **Participants' manual for working group AAR**, sept. 2019 [S] : atelier structuré en cinq séances ; les résultats d'AAR alimentent le plan d'action national et des évaluations comme la JEE.
- Lien avec la JEE (Joint External Evaluation) : les AAR et simulations sont des **tests fonctionnels** qui complètent les auto-évaluations et les évaluations externes [S].
- Adoptable : l'idée que la simulation est un **test fonctionnel de capacité**, distinct de l'évaluation documentaire (mandat écrit). C'est exactement la distinction entre G1–G3 (textes) et les défaillances observées pendant la simulation.

### 3.4 UNDRR / WMO — Early Warnings for All (EW4All)

Source : https://www.undrr.org/early-warning-for-all ; https://wmo.int/ (lancement 2022, objectif fin 2027) [S].

Quatre piliers (chaîne d'alerte précoce) :
1. **Connaissance des risques de catastrophe** : UNDRR [S].
2. **Détection, observation, suivi, analyse et prévision** : WMO [S].
3. **Diffusion et communication des alertes** : **ITU** [S].
4. **Préparation à la réponse** : IFRC [S].

Intérêt pour ALERTE : le pilier 3 est tenu par l'ITU. Les lacunes de diffusion (G1, G7, G9) peuvent donc être rattachées explicitement au pilier 3, ce qui relie le projet au mandat de l'ITU. Les lacunes de connaissance des risques et de prévision se rattachent aux piliers 1 et 2.

### 3.5 CAP — Common Alerting Protocol (OASIS, v1.2)

Sources : https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2.html ; spécification OS : https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html [S, non lue].

- Norme OASIS approuvée le 1er juillet 2010, indépendante du réseau [S].
- Profils nationaux : US IPAWS, Canada CAP-CP [S].
- Les éléments (alert, info, resource, area) n'ont pas été lus [NV].
- Adoptable : une lacune technique « alerte non formatée CAP » (G3 ou technique) ; une lacune de « profil national absent » (G4). À vérifier sur la spécification.

### 3.6 IFRC — IDRL et Disaster Law

- **Lignes directrices IDRL** (2007, 30e Conférence internationale) : recommandations aux États sur la préparation de leurs lois et plans pour les problèmes réglementaires des opérations de secours internationales [S].
- **Checklist IDRL** (novembre 2017) : outil d'auto-évaluation pour autorités nationales, qui confronte la législation existante aux recommandations [S]. Public : législateurs, organismes nationaux de gestion des catastrophes, ministères sectoriels.
- **Checklist on Law and Disaster Risk Reduction** (2015, IFRC/PNUD) [S].
- **Checklist on Law and Disaster Preparedness and Response (DPR)** (2019) [S].
- Adoptable : une grille d'auto-évaluation réglementaire (catégorie « réglementaire »), à croiser avec G1, G3, G4.

---

## 4. Typologie de lacunes proposée

Catégories (proposition, à valider par l'architecte) et rapprochement avec G1–G10 (définitions lues dans `ALERTE — Project Specification.md`, l. 553–566) :

| Catégorie | Définition | Règle(s) G | Source de référence |
|---|---|---|---|
| Mandat absent | Action requise sans institution qui détient le pouvoir | G1 | Lignes directrices IFRC (IDRL), HSEEP « mandate » [NV] |
| Chevauchement | Deux institutions ont le même pouvoir, aucun texte ne désigne le chef de file | G2 | Clarification de la coordination, OMS JEE [S] |
| Procédure | Pouvoir sans procédure, délai ou formulaire | G3 | HSEEP plan d'amélioration [S], CAP profil national [S] |
| Dépendance | Pouvoir qui dépend d'un texte d'application absent ou non prêt | G4 | IFRC Checklist (auto-évaluation) [S] |
| Conflit d'objectifs | Deux obligations opposées | G5 | Y.3172 (compromis architecture) [NV] |
| Responsabilité | Dommage possible, personne n'en répond | G6 | Gabarits AAR (observations) [S] |
| Inclusion | Pas d'obligation sur langues, accessibilité, sans téléphone | G7 | Pilier 3 EW4All (ITU) [S] ; AI Readiness dimension Human Interface [V] |
| Supervision IA | Sortie IA utilisée sans contrôle humain, journal ou conditions de validité | G8 | Critère « audit logging » du hackathon [V] ; AI Readiness Dimension 5 [V] |
| Sécurité du canal | Canal détournable sans devoir de protection | G9 | Y.3172 (sécurité) [NV] |
| Transfrontalier | Action nécessitant un acteur étranger sans accord | G10 | IFRC/OCHA, accords [NV] |
| Capacité / technique | Ressource, outil ou protocole manquant (ex. pas de format CAP) | hors G1–G10, à ajouter | CAP [S], Y.3172 [S] |

Pour la capacité et la technique, il manque une règle G dédiée : c'est une proposition d'ajout (G11 « capacité absente » ou catégorie technique), à arbitrer.

### 4.1 Table de sévérité proposée

Base : le repère déjà employé dans les rapports ALERTE (« 3 = risque pour la vie ou les droits », « 2 = retard ou surcoût ») ; complété par l'échelle HSEEP (performance U à P) et le principe SMART. Échelle proposée, à valider :

| Niveau | Libellé | Critère | Exemple ALERTE |
|---|---|---|---|
| 3 | Critique | Risque pour la vie ou les droits ; aucune institution responsable (G1, G6, G8 ayant un impact vie/droits) | Personne ne peut obliger les opérateurs à envoyer l'alerte (inject 4) |
| 2 | Majeure | Retard, surcoût, ou mauvaise coordination sans risque direct (G2, G3, G4, G5, G9) | Deux institutions « alertent la population » sans chef de file |
| 1 | Mineure | Amélioration de qualité ou d'inclusion sans effet immédiat (G7 partiel, documentation) | Message non traduit dans une langue secondaire |

Performance HSEEP correspondante : U = non réalisé (sévérité 3) ; M = réalisé avec difficultés majeures (2) ; S = réalisé avec difficultés (1–2) ; P = réalisé sans difficulté (pas de lacune). Les libellés S/M/P sont [NV].

Confiance (repris du rapport ALERTE) : « confirmé par le texte » / « suspecté » ; l'exercice complète la preuve par la défaillance observée.

### 4.2 Suivi des actions correctives

Champs proposés, inspirés du plan d'amélioration HSEEP [S] et de SMART [S] :
- `owner` (organisation responsable principale) : obligatoire ;
- `contact` (point de contact) ;
- `due_date` (date d'achèvement) ;
- `start_date` ;
- `status` : ouvert / en cours / fait / vérifié à l'exercice suivant (ajouté : absent des gabarits) ;
- `capability` / pilier EW4All ;
- `evidence` (lien vers la règle G et la source) ;
- `kpi` (critère SMART mesurable).

---

## 5. Matrice critère → fonctionnalité ALERTE (à remplir par l'architecte)

Colonnes à remplir : fonctionnalité | module | preuve de test | statut.

| # | Critère officiel (hackathon) | Fonctionnalité ALERTE à construire | Module / fichier | Preuve |
|---|---|---|---|---|
| C1 | Knowledge base quality : « completeness, accuracy, and structure of ingested national material » | | | |
| C2 | Agent capability : « relevance and accuracy of agent responses during simulated error scenarios » | | | |
| C3 | Policy, strategy, standards gap identification : « unclear responsibilities, standards, technology and legislative gaps, coordination problems, conflicts between objectives » | | | |
| C4 | Auditability : « transparency of agent reasoning through logs, chain-of-thought traces, and source attribution » | | | |
| C5 | Alignment with ITU standards : « reflection of » Y.3172 et AI Readiness Framework « in the solution architecture » | | | |
| E1 | Exigence : mapping and adherence to « published and open documents provided by the country » | | | |
| E2 | Exigence : base vectorisée hébergée (ITU reference code) | | | |
| E3 | Exigence : agents institutionnels « assumes the role of a specific government actor » | | | |
| E4 | Exigence : coordination inter-agents « Inter-agent coordination protocols » | | | |
| E5 | Exigence : scénarios « sequenced, chunked events released progressively » | | | |
| E6 | Exigence : gaps « domain specific » ; exemples mondiaux « global policy examples » | | | |
| E7 | Livrable : rapport technique 5 pages | | | |
| E8 | Livrable : dépôt GitHub | | | |
| E9 | Livrable : base de connaissances publiée | | | |
| E10 | Livrable : vidéo démo 7 min (obligatoire si retenu) | | | |
| E11 | Proposition : « Contribution to regional perspective » ; « open local dataset and model building » | | | |

Note pour l'architecte : la FAQ indique que l'exactitude du prototype n'est pas un critère. Les critères C1–C5 sont donc à couvrir, pas la performance du modèle.

---

## 6. Méthodes à adopter (résumé)

1. **Structure du rapport** : résumé exécutif → périmètre et scénario → observations (lacunes, à partir des G1–G10) → plan d'amélioration (owner, dates, statut) → annexes preuves. Suit HSEEP AAR/IP [S].
2. **Observation sans recommandation** dans la section lacunes ; recommandations uniquement dans le plan [S].
3. **Notes de sévérité** : échelle 1–3 (repère ALERTE) + échelle de performance HSEEP U/M/S/P [S/NV].
4. **Suivi** : champs owner, due_date, status, evidence [S].
5. **Cadre de référence** : EW4All (pilier 3 = ITU) pour rattacher les lacunes de diffusion ; CAP pour les formats ; IFRC IDRL pour le réglementaire [S].
6. **Test fonctionnel** : la simulation est un test de capacité complémentaire à l'analyse documentaire (OMS) [S].

---

## 7. URLs non lisibles ou non vérifiées

| URL | Problème |
|---|---|
| https://www.itu.int/rec/T-REC-Y.3172-201906-I (et /en, http, variante) | Fiche lue (titre, statut) mais sans portée ni architecture |
| Texte intégral Y.3172 (PDF/EPUB) | Non obtenu |
| Y.ML-IMT2020-SANDBOX (statut) | Non vérifié |
| https://www.fema.gov/sites/default/files/2020-04/HSEEP-Information-Sheet-20200203.pdf | Échec d'extraction : le PDF n'a pas été lu (réponse : données binaires) |
| https://www.fema.gov/hseep | Non lu directement ; seuls extraits de moteur |
| Gabarit HSEEP 2020 officiel | Non lu ; gabarits d'États seulement [S] |
| https://www.iso.org/fr/standard/50294.html | Page de vente, texte non lu |
| https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html | Non lu ; éléments CAP [NV] |
| WHO Simulation Exercise Manual (WHO-WHE-CPI-2017.10) | Non lu ; référence seulement |
| IFRC Guidelines IDRL 2007 et Checklist 2017 (PDF) | Non lus ; extraits de moteur seulement |
| Liste complète des 13 dimensions AI Readiness | Non lue (pages 18–34 du PDF local) |
| Chapitre 4 AI Readiness Gap Analysis (p. 35+) | Non lu |
| Pages Hackathon Cameroun | Aucune trouvée |
| Hackathon ITU : page Kenya | Lue, mais la page ne donne pas la liste des prix en CHF |
| Prix Kenya | Incohérents sur la page (USD 600/400/250 dans un bloc, 500/300/225 dans un autre) : à vérifier |

---

Fin du fichier.
