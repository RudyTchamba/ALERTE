> **Annexe — Inventaire du corpus, rapports de lacunes existants, ressources réutilisables.**
> Matériau de recherche brut produit le 2026-11-20 par un sous-agent (modèle Haiku 5.5), relu en diagonale par l'architecte. Les marqueurs « non vérifié » / `[NV]` / `[V]` / `[S]` sont ceux du sous-agent ; toute information utilisée dans le dossier principal est citée avec son niveau de vérification. Ce fichier est une pièce justificative, pas une spécification.

---

# Inventaire documentaire et rapports de lacunes : ALERTE

Dépôt : `/home/rtti/Documents/Github/ALERTE-for-ITUAIReadiness` (lecture seule ; aucun fichier du dépôt modifié).
Date d'analyse : 2026-11-20. Tous les chiffres ont été relevés sur les fichiers, sauf mention « non vérifié ».

## Tâche 1 : rapports de lacunes

### 1.1 Candidats

| # | Chemin | Taille | Nature | Lacunes listées | Champs par lacune |
|---|---|---|---|---|---|
| A | `/home/rtti/Documents/Github/ALERTE-for-ITUAIReadiness/ALERTE_Technical_Report_v2.pdf` | 193 KB, 5 p. | Rapport technique du projet (soumission hackathon, LibreOffice). Non suivi par git (`??`). | 6 lacunes de politique (G1, G2, G3/G8, G6, G7, G9) + 5 lacunes de standards | Nom de la lacune, règle (code G), preuves « UAE ; Cameroon », exemples mondiaux, « ce qui devrait changer ». Pas d'identifiant, pas de gravité, pas d'institutions. |
| B | `/home/rtti/Documents/Github/ALERTE-for-ITUAIReadiness/alerte/data/docs/ITU/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf` | 1,1 MB, 55 p. | Document source externe : ITU « AI Ready, Report 2.0 » (janv. 2026). Chapitre 4 « AI Readiness Gap Analysis » (p. 35-36 du rapport). | 3 catégories de lacunes (standards, implémentations, politiques), narratives | Aucun champ structuré. Pas une sortie d'ALERTE. |
| C | `/home/rtti/Documents/Github/ALERTE-for-ITUAIReadiness/alerte/runs/*/gaps.json` et `report.md` | 33 à 45 Ko par gaps.json | Sorties générées par l'ancienne application (moteur à règles, « brain offline ») | 17 à 23 lacunes par run (voir 1.3) | Schéma complet en 1.2 |
| D | `/home/rtti/Documents/Github/ALERTE-for-ITUAIReadiness/alerte/runs/demo-twin-comparison.md` | 1,7 Ko | Comparaison CM / AE du nombre de lacunes par type | Tableau de comptes | Non lu en entier (tête lue). |
| E | `ALERTE — Project Specification.md` et `ALERTE — The Project Explained Simply.md` (racine, non suivis) | - | Spécifications, pas un rapport. Contient une section « Three gaps we already know exist » (ligne 138 de la version « Explained »). | - | Non lu en détail. |

Non-candidats : `alerte/index/review_queue.md` et `extraction_report.json` (relecture OCR), `alerte/data/docs/ITU/ITU-S01_Hackathon_requirements_summary.md` (exigences : « policy, strategy and standards gap identification » est un critère d'évaluation, pas un rapport).

Recherche textuelle : « gap analysis », « gap register », « lacune », « évaluation institutionnelle » ont été cherchés dans les 45 PDF extraits et dans md/json/csv/yaml. Seuls le rapport racine et le rapport ITU 2.0 (section 4) constituent une analyse de lacunes au sens strict. Les PDF CM-18, GL-09, GL-13, GL-16 et GL-17 contiennent aussi la formule « gap analysis » mais sont des documents sources, non examinés en détail.

### 1.2 Rapport technique racine (A) : lecture intégrale

Lecture intégrale des 5 pages (pdftotext, 26 032 caractères).

- **Vision** : simulateur d'exercices de crise. Des agents jouent les institutions d'un pays pendant une inondation où un système IA d'alerte précoce échoue. Le moteur repère les lacunes dans les lois et règles. Cas 1 : EAU (primaire). Cas 2 : Cameroun. Le rapport précise que ce n'est ni un modèle de prévision, ni un vrai système d'alerte, ni un chatbot.
- **Architecture** : nœuds du pipeline ML selon ITU-T Y.3172 : MLFO (orchestrateur), SRC (base de connaissances, 43 documents annoncés), C (collecte pilotée par manifeste), PP (découpage par article, métadonnées, embeddings multilingues, OCR), M (six agents avec fiche de rôle et boîte privée), P (graphe de mandats, vérification des citations, règles G1 à G9), D (tableau de messages à cinq types : INFO, REQUEST, DECISION, OBJECTION, GAP_FLAG), SINK (interface à 4 écrans), registre à chaîne de hachage SHA-256.
- **Cibles d'acceptation** (« values to be inserted ») : bon article dans le top 5 pour ≥80 % des 40 questions ; ≥95 % de citations valides ; ≥80 % des lacunes prévues trouvées ; ≥85 % de fiches jugées réelles ; ≥80 % trouvées dans 2 runs sur 3.
- **Scénario « Rising Waters »** : 5 étapes (fausse alerte à Dubai/Douala, fausse alerte de sécurité, capteurs hors service à Al Ain, déplacements à grande échelle, test de stress où le fournisseur propose l'envoi automatique sans validation humaine).
- **Lacunes (section 6)** :
  - G1 : les opérateurs n'ont pas de devoir de relayer une alerte publique (preuves : rien trouvé aux EAU ; CM-02, CM-03, CM-07, CM-08 muets).
  - G2 : qui décide d'émettre l'alerte n'est pas défini (AE-05 donne à la Défense civile un devoir de mettre en place des systèmes, pas de désigner l'émetteur).
  - G3/G8 : aucun contrôle humain avant diffusion d'une alerte rédigée par l'IA.
  - G6 : personne ne répond du préjudice d'une fausse alerte IA.
  - G7 : pas de devoir de langues ni de couverture (TS040 impose anglais et arabe selon le résumé).
  - G9 : canal d'alerte non protégé contre l'usurpation.
  - Lacunes de standards : (1) noeud P de Y.3172 sans politique d'alerte publique ; (2) conditions de validité déclarées (5 capteurs sur 7) ; (3) provenance des alertes (CAP X.1303 sans profil marquant le contenu généré par IA) ; (4) métriques de préparation sans clarté des mandats ni responsabilité (Report 2.0) ; (5) format commun de traces d'agents IA.
- **Limites déclarées** : sources souvent des résumés ; « not found » signifie « non trouvé dans ces sources » ; les exemples viennent de juridictions différentes ; les lacunes sont des hypothèses à confirmer par expert.
- **Divergences avec l'implémentation (vérifiées)** :
  1. Embeddings : le rapport dit « multilingual embeddings » ; `index/extraction_report.json` indique `vectors: none`. Aucun index vectoriel n'a été construit.
  2. Questions d'évaluation : 40 annoncées ; `data/eval/questions.yaml` en contient 28.
  3. Graphe de mandats : « about 40–60 checked lines » ; `ae_mandates.csv` 17 lignes + `cm_mandates.csv` 14 lignes = 31.
  4. Base : « 43 listed documents : 15 UAE, 12 Cameroon, 12 global, 4 ITU » ; le manifest en compte 45 (AE 9 + SCN-02 ; CM 17 + SCN-01 ; GL 16 ; ITU-S01 ; le total inclut 2 fichiers ITU hors manifest). Les ID cités (AE-03, AE-07, AE-08, AE-13, AE-14, AE-15, CM-06, GL-08, GL-10) ne sont pas dans le manifest.
  5. « 57 seed documents of the ITU reference repository » : absents du dépôt.
  6. Lacunes : le rapport liste 7 règles (G1, G2, G3, G6, G7, G8, G9), conforme à `gap_rules` de `ae_core.yaml`. Or le run CM-01 produit aussi G4, G5 et G10 (définis dans `alerte/analysis/gaps.py`, lignes 19-26, et attendus par `cm01_rising_waters.yaml` lignes 180 et 193). Non mentionné dans le rapport.
  7. Règle « au moins deux précédents de juridictions différentes » : violée dans le run `ae-core-offline-20261119-021505-fcc8`, lacune G3-12 (un seul précédent, « International »).
  8. Métriques : « under 150 model calls », « 10 to 20 minutes » : les runs disponibles sont en mode `offline` (`ai_calls: 0`, 0,07 s). Aucune mesure avec un LLM n'est présente (non vérifié).
  9. Interface : « four screens » ; `alerte/alerte/ui/pages/` contient 8 modules de pages (readiness, live, replay, knowledge, decisions, adviser, gaps, about), plus `ui/architecture.py` et `ui/arena.py`.
  10. Sensors : le rapport dit « river sensors » ; le modèle HydroSense (SCN-02) dit « at least 5 of 7 wadi sensors ». Terminologie différente.
  11. Licences : le rapport annonce des « licence note » dans le manifest ; le manifest n'a pas de colonne licence.
  12. Source AE-03 : la spec cite la charte IA des EAU (AE-03). Le fichier présent sous le nom AE-04 est précisément cette charte (voir 2.3).

### 1.3 Sorties générées par l'ancienne application (C)

Répertoires `alerte/runs/` :

| Run | Lacunes | Types présents | Remarque |
|---|---|---|---|
| `demo-ae-core` | 18 (10 confirmées, 8 suspectées) | G1, G2, G3, G6, G7, G8, G9 | 14/14 lacunes prévues trouvées ; 8/8 citations vérifiées ; ledger intact (208 entrées) |
| `demo-ae01` | 21 | - | non examiné en détail |
| `demo-cm-core` | 17 | - | non examiné en détail |
| `demo-cm01` | 23 (15 confirmées, 8 suspectées) | G1 à G10 (tous les types, y compris G4, G5, G10 absents des runs AE) | 17/17 trouvées ; 10/10 citations ; ledger intact |
| `ae-core-offline-20261110-123505-6329` | - | - | seulement `ledger.jsonl` : run incomplet |
| `ae-core-offline-20261111-075912-f451` | 18 | - | `gaps.json` identique à celui des deux runs suivants (md5 07a5102c...) |
| `ae-core-offline-20261119-020307-6c79` | 18 | - | idem |
| `ae-core-offline-20261119-021505-fcc8` | 18 | - | idem ; une lacune à un seul précédent (G3-12) |

Chaque run contient : `assumptions.json`, `decisions.json`, `gaps.json`, `ledger.jsonl`, `messages.json`, `report.html`, `report.md`, `scenario.json`, `scorecard.json`, `summary.json`.

Lecture de `gaps.json` (liste JSON, une entrée par lacune). Schéma relevé sur les 18 + 23 entrées :

```
gap_id           str    "G8-01" (type-numéro)
type             str    "G1" ... "G10"
title            str    "AI unchecked: Check and validate an AI-generated forecast ..."
description      str    phrase « what is missing »
action           str    ex. "validate_ai_forecast", "decide_public_alert"
institutions     [str]  ex. ["HYDRO", "MET"]
event_ids        [int]  ex. [2, 8]
first_sim_time   str    "D1 06:20"
severity         int    1 à 3 (14 de 18 à 3 dans demo-ae-core)
confidence       str    "confirmed_by_text" | "suspected"
status           str    "confirmed" | "suspected"
texts_checked    [str]  ex. ["AE-S02", "AE-S03", "AE-S04", "AE-S06"]
evidence         [str]  ex. "Who-does-what map (AE): no institution holds 'validate_ai_forecast'"
signals          [str]  ex. "rule:G8", "agent/board signal"
precedents       [obj]  jurisdiction, instrument, article, what_it_does, fit_note, doc_id (GL-S0x), url, binding (bool)
review_note      str    vide dans les runs
```

Types : G1 Nobody in charge, G2 Two in charge, G3 No procedure, G4 Missing piece, G5 Conflicting goals, G6 Nobody answers for harm, G7 People left out, G8 AI unchecked, G9 Channel unprotected, G10 Cross-border (libellés dans `analysis/gaps.py`, traduits en français dans `GAP_TYPES_FR`).

Le rapport `report.md` regroupe par type avec, pour chaque lacune : type et gravité, moment, « What is missing », institutions, textes vérifiés, preuves, « How others handle it » (précédents avec liens et note « written for Cameroon »).

Exemples verbatim (run `demo-ae-core`) :
- `G8-01` : « No institution holds the power or duty to check and validate an AI-generated forecast before it is used for a public decision » (institutions HYDRO, MET ; gravité 3 ; confirmée par le texte).
- `G2-02` : « Several institutions hold 'decide to alert the public' and no text says who leads » (DPC, MOI ; suspectée).
- `G3-03` : « No institution holds the power or duty to approve an AI-drafted alert through a human validation step before release » (DPC, OPS).

Le schéma est propre et stable (même clés dans tous les runs). Les clés `review_note` restent vides : aucune relecture humaine n'est consignée.

### 1.4 Verdict Tâche 1

Le document le plus probable est **A, `ALERTE_Technical_Report_v2.pdf`** : c'est le seul rapport rédigé qui présente des « policy gaps and standards gaps » en un tableau, avec preuves et exemples. B est le rapport ITU source (chap. 4 « AI Readiness Gap Analysis ») et serait « un document relatif aux lacunes » au sens large, mais ce n'est pas un travail précédent du projet. C est la sortie générée par l'ancienne application. Les trois sont à présenter à l'utilisateur pour levée de doute.

## Tâche 2 : inventaire du corpus

### 2.1 Méthode

- Sources comparées : `alerte/data/manifest.csv` (45 lignes), fichiers réels sous `alerte/data/docs/**` (47 fichiers), `alerte/index/documents.json` (45 entrées, identiques au manifest), `alerte/index/chunks.jsonl` (4 235 passages, 45 doc_id), `alerte/index/extraction_report.json`.
- Texte réel des PDF : `pdftotext -layout`, puis lecture de l'en-tête de chaque document pour vérifier le titre et la nature.
- Doublons : md5 identiques entre fichiers = aucun. Doublons de contenu logique : AE-03 (charte IA des EAU) est présente sous le nom AE-04.
- Pages à relire : 19 documents, 141 pages au total (`review_queue.md`). Aucun fichier `.corrected.md` n'existe : la relecture n'a pas été faite.
- Licences : le manifest n'a pas de colonne licence. Ses colonnes sont `reliability` (official / summary / fictional) et `notes`. Droits de redistribution : **non vérifié** pour tous les documents. Points de vigilance : rapports de la Banque mondiale (GL-07, CM-17 : page « Rights and permissions »), article de Springer (AE-06), publications de l'OMS (GL-16, GL-17), union européenne (GL-01 à 03, réutilisables en principe, non vérifié), ITU (GL-11, GL-12, ITU-01, ITU-02 : conditions de l'UIT, non vérifié).

### 2.2 Tableau de l'inventaire (45 lignes du manifest + 2 fichiers non enregistrés)

Taille en MB arrondie à 0,01 près. « Passages indexés » = nombre de lignes de `chunks.jsonl` pour ce doc_id. Statuts : PRESENT-INDEXE, DOUTEUX, INCOMPLET, PRESENT-NON-INDEXE, ABSENT.

| ID | Titre (manifest) | Pays | Type | Langue | Fichier | Taille (MB) | Pages | Passages indexés | Statut | Réutilisabilité |
|---|---|---|---|---|---|---|---|---|---|---|
| AE-01 | Federal Decree-Law No. 45 of 2021 on the Protection of Personal Data | AE | law | en | `AE-01_Federal_Decree-Law_No_45_of_2021_on_the_Protection_of_Personal_Data.pdf` | 0.19 | 29 | 32 | PRESENT-INDEXE | Oui, démo AE (texte primaire) |
| AE-02 | UAE National Strategy for Artificial Intelligence 2031 | AE | strategy | en | `AE-02_UAE_National_Strategy_for_Artificial_Intelligence_2031.pdf` | 8.73 | 25 | 47 | PRESENT-INDEXE (OCR : 10 p. à relire) | Contexte seulement (stratégie IA, 8,7 MB) |
| AE-04 | How the UAE Public Alert Chain Works (UAE-Alert, Cell Broadcast, NCEMA, TDRA) | AE | report | en | `AE-04_How_the_UAE_Public_Alert_Chain_Works_UAE-Alert_Cell_Broadcast_NCEMA_TDRA.pdf` | 9.46 | 6 | 3 | DOUTEUX : mauvais fichier (charte IA 2024, pas l'explainer alerte) | Non en l'état : fichier à réaffecter à AE-03 (charte IA) |
| AE-05 | Federal Decree-Law No. 35 of 2024 on the Reorganisation of the Civil Defence Authority | AE | law | en | `AE-05_Federal_Decree-Law_No_35_of_2024_on_the_Reorganisation_of_the_Civil_Defence_Authority.pdf` | 0.10 | 11 | 13 | PRESENT-INDEXE | Oui, démo AE (texte primaire) |
| AE-06 | Record Rainfall of 16 April 2024 (NCM figures) | AE | report | en | `AE-06_Record_Rainfall_of_16_April_2024_NCM_Figures.pdf` | 4.13 | 23 | 44 | DOUTEUX : article scientifique (Natural Hazards 2025), pas des chiffres NCM | Contexte seulement ; droits de l'éditeur à vérifier |
| AE-09 | Federal Decree-Law No. 3 of 2003 Regulating the Telecommunications Sector, as amended | AE | law | en | `AE-09_Federal_Decree-Law_No_3_of_2003_Regulating_the_Telecommunications_Sector_as_Amended.pdf` | 0.23 | 34 | 30 | PRESENT-INDEXE | Oui, démo AE (texte primaire) |
| AE-10 | Federal Decree-Law No. 34 of 2021 on Countering Rumours and Cybercrimes | AE | law | en | `AE-10_Federal_Decree-Law_No_34_of_2021_on_Countering_Rumours_and_Cybercrimes.pdf` | 0.22 | 36 | 48 | PRESENT-INDEXE | Oui, démo AE (texte primaire) |
| AE-11 | Federal Decree-Law No. 6 of 2007 Establishing the National Centre of Meteorology, as amended | AE | law | en | `AE-11_Federal_Decree-Law_No_6_of_2007_Establishing_the_National_Centre_of_Meteorology_as_Amended_Latest_Amendment_2026.pdf` | 0.11 | 8 | 10 | PRESENT-INDEXE | Oui, démo AE (texte primaire) |
| AE-12 | TRA Technical Specification TS040: Cell-Broadcast Requirements for Handsets (Effective 1 Jan 2016) | AE | standard | en | `AE-12_TRA_Technical_Specification_TS040_Cell-Broadcast_Requirements_for_Handsets_Effective_1_January_2016.pdf` | 0.73 | 7 | 12 | PRESENT-INDEXE (OCR : 2 p. à relire) | Oui, démo AE (texte primaire) |
| CM-01 | Law No. 2024/017 of 23 December 2024 on the Protection of Personal Data | CM | law | fr | `CM-01_Law_No_2024-017_of_23_December_2024_on_the_Protection_of_Personal_Data.pdf` | 4.74 | 24 | 73 | DOUTEUX : scan, OCR quasi vide (804 car. pour 24 p.) | Oui après relecture OCR (16 pages à corriger) |
| CM-02 | Law No. 2010/013 of 21 December 2010 Regulating Electronic Communications in Cameroon | CM | law | en | `CM-02_Law_No_2010-013_of_21_December_2010_Regulating_Electronic_Communications_in_Cameroon.pdf` | 0.43 | 42 | 137 | PRESENT-INDEXE | Oui, démo CM (texte primaire) |
| CM-03 | Law No. 2015/006 of 20 April 2015 Amending Law No. 2010/013 | CM | law | fr | `CM-03_Law_No_2015-006_of_20_April_2015_Amending_Law_2010-013.pdf` | 0.09 | 10 | 21 | PRESENT-INDEXE | Oui, démo CM (texte primaire) |
| CM-04 | Law No. 2010/012 of 21 December 2010 on Cybersecurity and Cybercriminality | CM | law | en | `CM-04_Law_No_2010-012_of_21_December_2010_on_Cybersecurity_and_Cybercriminality.pdf` | 0.27 | 31 | 121 | PRESENT-INDEXE | Oui, démo CM (texte primaire) |
| CM-05 | Law No. 86/016 of 6 December 1986 on the General Reorganisation of Civil Protection | CM | law | fr | `CM-05_Law_No_86-016_of_6_December_1986_on_the_General_Reorganisation_of_Civil_Protection.pdf` | 0.08 | 2 | 15 | PRESENT-INDEXE | Oui, démo CM (texte primaire) |
| CM-07 | Decree No. 98/031 of 9 March 1998 on the Organisation of Emergency and Rescue Plans | CM | decree | fr | `CM-07_Decree_No_98-031_of_9_March_1998_on_the_Organisation_of_Emergency_and_Rescue_Plans.pdf` | 0.27 | 4 | 7 | INCOMPLET : scan sans couche texte, indexé par OCR seul | Oui après relecture OCR (décret central pour l'alerte) |
| CM-08 | Decree No. 2005/124 on Emergency Telecommunications (as cited by IFRC) | CM | decree | fr | `CM-08_Decree_No_2005-124_on_Emergency_Telecommunications_as_Cited_by_IFRC.pdf` | 0.31 | 48 | 94 | PRESENT : titre à vérifier (contenu = organisation du MINPOSTEL) | Oui (télécoms d'urgence), après vérification du titre |
| CM-09 | Law No. 90/047 of 19 December 1990 on the State of Emergency | CM | law | fr | `CM-09_Law_No_90-047_of_19_December_1990_on_the_State_of_Emergency.pdf` | 0.33 | 4 | 32 | PRESENT-INDEXE (OCR : 1 p. à relire) | Oui, démo CM (texte primaire) |
| CM-10 | National Contingency Plan (Plan National de Contingence, PNC) | CM | plan | fr | `CM-10_National_Contingency_Plan_Plan_National_de_Contingence_PNC.pdf` | 1.17 | 38 | 39 | PRESENT-INDEXE | Oui, démo CM (texte primaire) |
| CM-11 | Law No. 2019/024 of 24 December 2019 on the General Code of Regional and Local Authorities | CM | law | fr | `CM-11_Law_No_2019-024_of_24_December_2019_on_the_General_Code_of_Regional_and_Local_Authorities.pdf` | 0.81 | 123 | 566 | PRESENT-INDEXE | Oui, démo CM (texte primaire) |
| CM-12 | IFRC, Republic of Cameroon: Mapping of International Disaster Response Laws, Rules and Principles (2021) | CM | report | en | `CM-12_IFRC_Republic_of_Cameroon_Mapping_of_International_Disaster_Response_Laws_Rules_and_Principles_2021.pdf` | 0.34 | 15 | 38 | PRESENT-INDEXE | Oui, démo CM (texte primaire) |
| CM-13 | IFRC, Disaster Risk Management Law Template, Cameroon (2022) | CM | report | en | `CM-13_IFRC_Disaster_Risk_Management_Law_Template_Cameroon_2022.pdf` | 0.82 | 66 | 128 | PRESENT : titre douteux (contenu = Mapping of Legal and Policy Arrangements) | Oui, contexte juridique DRM |
| CM-14 | National Artificial Intelligence Strategy (SNIA), July 2025, MINPOSTEL | CM | strategy | fr | `CM-14_National_Artificial_Intelligence_Strategy_SNIA_July_2025_MINPOSTEL.pdf` | 2.17 | 9 | 6 | DOUTEUX : article de presse (investiraucameroun, 10/07/2025), pas le texte SNIA | Non : obtenir le texte officiel SNIA |
| CM-15 | Statement of Cameroon on Protection of Persons in the Event of Disasters, UN General Assembly Sixth Committee, 79th Session | CM | report | en | `CM-15_Statement_of_Cameroon_on_Protection_of_Persons_in_the_Event_of_Disasters_UN_General_Assembly_Sixth_Committee_79th_Session.pdf` | 0.18 | 6 | 6 | PRESENT-INDEXE | Oui, démo CM (texte primaire) |
| CM-16 | UNICEF Cameroon Floods Flash Update No. 5, Far North (24 October 2024) | CM | report | en | `CM-16_UNICEF_Cameroon_Floods_Flash_Update_No_5_Far_North_24_October_2024.pdf` | 0.50 | 3 | 7 | PRESENT-INDEXE | Oui, démo CM (texte primaire) |
| CM-17 | Gavi, Cholera in Cameroon: When Climate Disaster Unleashes an Epidemic | CM | report | en | `CM-17_Gavi_Cholera_in_Cameroon_When_Climate_Disaster_Unleashes_an_Epidemic.pdf` | 0.89 | 22 | 45 | DOUTEUX : ESCP de la Banque mondiale / MoPH, pas une publication Gavi | Faible : ESCP santé, droits Banque mondiale |
| CM-18 | Cholera Preparedness and Response Plan, Ministry of Public Health | CM | plan | fr | `CM-18_Cholera_Preparedness_and_Response_Plan_Ministry_of_Public_Health.pdf` | 6.27 | 202 | 330 | PRESENT-INDEXE (OCR : 20 p. à relire) | Oui, démo CM (texte primaire) |
| GL-01 | Directive (EU) 2018/1972 Establishing the European Electronic Communications Code (EECC) | EU | law | en | `GL-01_EU_Directive_2018-1972_Electronic_Communications_Code.pdf` | 1.43 | 150 | 308 | PRESENT-INDEXE | Oui, comparaisons internationales (GL) |
| GL-02 | Regulation (EU) 2024/1689 Laying Down Harmonised Rules on Artificial Intelligence (AI Act) | EU | law | en | `GL-02_EU_Regulation_2024-1689_Artificial_Intelligence_Act.pdf` | 2.58 | 144 | 417 | PRESENT-INDEXE | Oui, comparaisons internationales (GL) |
| GL-03 | Regulation (EU) 2016/679 on the Protection of Natural Persons (GDPR) | EU | law | en | `GL-03_EU_Regulation_2016-679_General_Data_Protection_Regulation.pdf` | 0.98 | 88 | 282 | PRESENT-INDEXE | Oui, comparaisons internationales (GL) |
| GL-04 | Republic Act No. 10639, Free Mobile Disaster Alerts Act (Philippines, 2014) | PH | law | en | `GL-04_Philippines_Republic_Act_10639_Free_Mobile_Disaster_Alerts_2014.pdf` | 0.15 | 3 | 11 | DOUTEUX (non vérifié) : impression e-Library, RA 10639 citée une seule fois | À vérifier avant tout usage (cas loi PH) |
| GL-05 | United States Wireless Emergency Alerts (47 CFR Part 10) and WARN Act | US | law | en | `GL-05_US_47_CFR_Part_10_Wireless_Emergency_Alerts.pdf` | 0.23 | 12 | 34 | PRESENT-INDEXE | Oui, comparaisons internationales (GL) |
| GL-06 | US FCC Final Report on Hawaii False Ballistic Missile Alert (April 2018) | US | report | en | `GL-06_US_FCC_Hawaii_False_Alert_Investigation_Report_2018.pdf` | 0.79 | 28 | 69 | PRESENT-INDEXE (OCR : 2 p. à relire) | Oui, comparaisons internationales (GL) |
| GL-07 | Japan J-Alert, National Instantaneous Warning System | JP | guidance | en | `GL-07_Japan_J-Alert_National_Instantaneous_Warning_System.pdf` | 63.30 | 166 | 184 | PRESENT : titre douteux (rapport Banque mondiale 2019 sur l'ICT en DRM au Japon) | Oui comme source J-Alert, mais titre et droits à corriger ; 63 MB |
| GL-09 | Early Warnings for All: Executive Action Plan 2023–2027 | INT | report | en | `GL-09_UN_Early_Warnings_for_All_Executive_Action_Plan_2023-2027.pdf` | 12.58 | 56 | 88 | PRESENT-INDEXE (OCR : 25 p. à relire) | Oui, comparaisons internationales (GL) |
| GL-11 | ITU Guidelines for National Emergency Telecommunication Plans | INT | guidance | en | `GL-11_ITU_Guidelines_for_National_Emergency_Telecommunication_Plans.pdf` | 3.73 | 106 | 162 | PRESENT-INDEXE (OCR : 5 p. à relire) | Oui, comparaisons internationales (GL) |
| GL-12 | Recommendation ITU-T X.1303, Common Alerting Protocol (CAP 1.2) | INT | standard | en | `GL-12_ITU-T_X.1303_Common_Alerting_Protocol_CAP_1.2.pdf` | 1.09 | 40 | 51 | PRESENT-INDEXE (OCR : 4 p. à relire) | Oui, comparaisons internationales (GL) |
| GL-13 | Sendai Framework for Disaster Risk Reduction 2015 to 2030 | INT | guidance | en | `GL-13_UNDRR_Sendai_Framework_for_Disaster_Risk_Reduction_2015-2030.pdf` | 1.02 | 37 | 72 | PRESENT-INDEXE (OCR : 4 p. à relire) | Oui, comparaisons internationales (GL) |
| GL-14 | African Union Convention on Cyber Security and Personal Data Protection (Malabo Convention, 2014) | AU | law | en | `GL-14_African_Union_Malabo_Convention_Cybersecurity_and_Data_Protection_2014.pdf` | 0.74 | 40 | 65 | PRESENT-INDEXE | Oui, comparaisons internationales (GL) |
| GL-15 | African Union Continental Artificial Intelligence Strategy (2024) | AU | strategy | en | `GL-15_African_Union_Continental_Artificial_Intelligence_Strategy_2024.pdf` | 2.57 | 66 | 116 | PRESENT-INDEXE (OCR : 3 p. à relire) | Oui, comparaisons internationales (GL) |
| GL-16 | WHO, Ethics and Governance of Artificial Intelligence for Health (2021) | INT | guidance | en | `GL-16_WHO_Ethics_and_Governance_of_Artificial_Intelligence_for_Health_2021.pdf` | 1.97 | 165 | 245 | PRESENT-INDEXE (OCR : 4 p. à relire) | Oui, comparaisons internationales (GL) |
| GL-17 | WHO International Health Regulations (2005) | INT | law | en | `GL-17_WHO_International_Health_Regulations_2005.pdf` | 0.81 | 67 | 132 | PRESENT-INDEXE (OCR : 1 p. à relire) | Oui, comparaisons internationales (GL) |
| GL-18 | NIST Artificial Intelligence Risk Management Framework 1.0 (2023) | US | guidance | en | `GL-18_NIST_Artificial_Intelligence_Risk_Management_Framework_1.0.pdf` | 1.95 | 48 | 79 | PRESENT-INDEXE (OCR : 3 p. à relire) | Oui, comparaisons internationales (GL) |
| ITU-S01 | AI for Good Lab Hackathon UAE (2026): requirements summary | INT | guidance | en | `ITU-S01_Hackathon_requirements_summary.md` | 0.00 | - | 4 | PRESENT : résumé rédigé par l'équipe, non officiel | Non comme source ; utile comme résumé d'exigences |
| SCN-01 | HydroSense model card (fictional AI system) | CM | fictional | en | `SCN-01_HydroSense_model_card.md` | 0.00 | - | 6 | PRESENT-INDEXE | Oui (matériel fictif) |
| SCN-02 | HydroSense model card, UAE configuration (fictional AI system) | AE | fictional | en | `SCN-02_HydroSense_UAE_model_card.md` | 0.00 | - | 6 | PRESENT-INDEXE | Oui (matériel fictif) |
| ITU-01 (non enregistré) | Recommendation ITU-T Y.3172 (06/2019) | INT | standard | en | `T-REC-Y.3172-201906-I!!PDF-E.pdf` | 1.15 | 34 | 0 | PRESENT-NON-INDEXE (absent de manifest et documents.json, 0 passage) | Oui, cadre (noeud MLFO / architecture ML) |
| ITU-02 (non enregistré) | AI Ready : Analysis Towards a Standardized Readiness Framework, Report 2.0 (janv. 2026) | INT | report | en | `T-AI4G-AI4GOOD-2025-6-PDF-E.pdf` | 1.11 | 55 | 0 | PRESENT-NON-INDEXE (absent de manifest et documents.json, 0 passage) | Oui, cadre 13 dimensions ; section 4 = gap analysis |

Résumé des statuts :
- Présent et indexé, sans défaut connu : la majorité des documents (voir le tableau).
- DOUTEUX (mauvais fichier ou contenu différent du titre) : AE-04, AE-06, CM-14, CM-17 ; à vérifier : GL-04.
- Titre douteux mais contenu utilisable : CM-08, CM-13, GL-07.
- INCOMPLET ou OCR médiocre : CM-01 (804 caractères pour 24 pages), CM-07 (aucune couche texte).
- PRESENT-NON-INDEXE : ITU-01 (Y.3172) et ITU-02 (Report 2.0), présents sur disque mais absents de `manifest.csv` et de `documents.json`.
- ABSENT (cité dans la spec ou le rapport, introuvable sur disque) : voir 2.3.

### 2.3 Identifiants de la spec absents, doublons et fichiers au nom trompeur

**IDs de la spec absents du manifest et du disque** (la spec les marque « To obtain » ou « Found in search » pour certains) :
- AE-03 : charte IA des EAU (2024). **Présente sur disque sous le nom AE-04** (voir ci-dessous).
- AE-07 (cadre NCEMA, « To obtain »), AE-08 (décret-loi 2/2011, NCEMA), AE-13 (spécification UAE-Alert), AE-14 (décret Dubai 4/2021), AE-15 (explications NCEMA 2026). AE-08, AE-13, AE-14 et AE-15 sont cités dans le rapport technique.
- CM-06 (décret 96/054 sur le Conseil national de protection civile, « To obtain » ; résumé dans CM-12).
- GL-08 (CAP Maurice, PreventionWeb) et GL-10 (flyer ITU EW4All 2026) : absents.
- ITU-01 : présent sur disque sous `ITU/T-REC-Y.3172-201906-I!!PDF-E.pdf`, non enregistré.
- ITU-02 : présent sur disque sous `ITU/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf`, non enregistré.
- ITU-03 (57 documents de seed du dépôt de référence CrashingGuru/ITUAIReadiness) : absents.
- ITU-04 (page et modèle de soumission du hackathon) : absents ; seul `ITU-S01` (résumé d'exigences rédigé par l'équipe, non officiel) est présent.

**Fichiers au nom trompeur ou au contenu différent** :
- `AE-04_How_the_UAE_Public_Alert_Chain_Works_...pdf` (9,5 MB, 6 p.) : contient « The UAE Charter for the Development & Use of Artificial Intelligence, July 2024 ». C'est la charte IA, qui correspond à AE-03. L'explainer sur la chaîne d'alerte (AE-04 de la spec) n'est pas présent. Le manifest indique une source Khaleej Times (article de presse) et une fiabilité « official ». Les deux sont erronées pour le contenu réel.
- `AE-06_Record_Rainfall_of_16_April_2024_NCM_Figures.pdf` (4,1 MB, 23 p.) : article scientifique (Natural Hazards, 2025, Springer, doi 10.1007/s11069-025-07156-9) sur la pluie record, et non des chiffres du NCM.
- `CM-14_National_Artificial_Intelligence_Strategy_SNIA_..._MINPOSTEL.pdf` (2,2 MB, 9 p.) : article de presse investiraucameroun.com du 10 juillet 2025 sur le lancement de la SNIA. Le manifest dit « Official text ».
- `CM-17_Gavi_Cholera_in_Cameroon_...pdf` (0,9 MB, 22 p.) : « Environmental and Social Commitment Plan » (ESCP) de la Banque mondiale pour le Health Security Program (Cameroun, négocié 19 août 2025). Pas une publication Gavi.
- `CM-13_IFRC_Disaster_Risk_Management_Law_Template_Cameroon_2022.pdf` : le manifest parle d'un modèle de loi ; le contenu est « Mapping of Legal and Policy Arrangements for Disaster Risk Management ».
- `CM-08_Decree_No_2005-124_on_Emergency_Telecommunications_as_Cited_by_IFRC.pdf` : le contenu est le décret 2005/124 portant organisation du Ministère des Postes et Télécommunications. Le titre « emergency telecommunications » doit être vérifié.
- `GL-07_Japan_J-Alert_...pdf` (63,3 MB, 166 p.) : rapport de la Banque mondiale (2019) « ICT for Disaster Risk Management in Japan ». J-Alert y est très présent (133 occurrences), mais ce n'est pas un document officiel sur J-Alert.
- `GL-04_Philippines_Republic_Act_10639...pdf` (3 p.) : impression d'une page e-Library (Manila Bulletin, « H. No. 353 »). La mention de la RA 10639 est unique. Contenu à vérifier.
- `CM-01_Law_No_2024-017...pdf` : scan dont la couche texte ne donne que 804 caractères pour 24 pages. Contenu lisible seulement via OCR ; 16 pages à relire.
- `CM-07_Decree_No_98-031...pdf` : scan sans couche texte ; 7 passages issus de l'OCR.

**Doublons** : aucun doublon d'octets. Trois runs `ae-core-offline` ont un `gaps.json` identique (même md5), ce qui n'est pas un doublon de corpus mais un résultat répétable.

**Données hors corpus** : `alerte/data/docs/ITU/ITU-S01_Hackathon_requirements_summary.md` et `SCN-01`/`SCN-02` (model cards fictives) sont des documents internes.

### 2.4 Taille du corpus

- `alerte/data/docs/` : 47 fichiers, **141,8 MB** au total (dont 2 PDF ITU non enregistrés).
- Plus gros fichiers :
  1. `GL/GL-07_Japan_J-Alert_National_Instantaneous_Warning_System.pdf` : 63,3 MB (rapport Banque mondiale, voir ci-dessus)
  2. `GL/GL-09_UN_Early_Warnings_for_All_Executive_Action_Plan_2023-2027.pdf` : 12,6 MB
  3. `AE/AE-04_How_the_UAE_Public_Alert_Chain_Works_...pdf` : 9,5 MB (en réalité la charte IA)
  4. `AE/AE-02_UAE_National_Strategy_for_Artificial_Intelligence_2031.pdf` : 8,7 MB
  5. `CM/CM-18_Cholera_Preparedness_and_Response_Plan_Ministry_of_Public_Health.pdf` : 6,3 MB (202 p.)
- Autres : `alerte/ocr/tessdata/` 31 MB ; `alerte/index/` 14 MB ; `alerte/runs/` 3,5 MB.

### 2.5 Réutilisabilité pour une plateforme générique

- **Réutilisable tel quel (démo AE, CM, GL)** : textes primaires officiels (AE-01, AE-05, AE-09, AE-10, AE-11, AE-12 ; CM-02, CM-03, CM-04, CM-05, CM-11 ; GL-01, GL-02, GL-03, GL-05, GL-12, GL-13, GL-14, GL-17, GL-18). Droits à confirmer.
- **Réutilisable après relecture OCR** : CM-01, CM-07, CM-09, CM-10, CM-18, AE-02, AE-12 (pages à corriger).
- **À réparer avant usage** : AE-04 (renommer en AE-03, acquérir l'explainer), AE-06 (remplacer par les vrais chiffres NCM), CM-14 (obtenir le texte SNIA officiel), CM-17 (retirer ou remplacer par la publication Gavi), GL-04 (vérifier la loi), GL-07 (renommer et vérifier les droits).
- **Matériel fictif** : SCN-01 et SCN-02 (model cards HydroSense), scénarios YAML : réutilisables comme exemples de démonstration, à étiqueter comme fictifs.
- **Cadre de référence** : PDF ITU-01 et ITU-02 et `data/framework/dimensions.json` (13 dimensions) : à réutiliser comme référentiel d'évaluation.


## Tâche 3 : ressources réutilisables hors documents

Chemins relatifs à `/home/rtti/Documents/Github/ALERTE-for-ITUAIReadiness/alerte/`. Aucun module métier (`sim/engine.py`, `sim/brain.py`) n'a été lu en profondeur.

### 3.1 Scénarios, rôles, mandats, actions, précédents, évaluation, cadre

| Ressource | Chemin | Contenu vérifié | Réutilisabilité |
|---|---|---|---|
| Scénarios | `data/scenarios/ae_core.yaml` (254 l.), `cm_core.yaml` (255 l.), `ae01_rising_waters_twin.yaml` (43 l.), `cm01_rising_waters.yaml` (211 l., avec `expected_gaps`) | Clés : id, title, country, language, profile, gap_rules, fictional_notice, summary, ai_system, roles_file, events. 12 événements pour ae_core. | Élevée : format de scénario générique (événements, destinataires, `expected_gaps`). Contenu spécifique aux inondations et aux deux pays. |
| Fiches de rôle | `data/scenarios/roles/ae.yaml`, `ae_core.yaml`, `cm.yaml`, `cm_core.yaml` (5 à 6 Ko chacune) | Non lu en détail. | Élevée pour le modèle de rôle (mandat, boîte privée). |
| Mandats | `data/mandates/ae_mandates.csv` (17 lignes), `data/mandates/cm_mandates.csv` (14 lignes) | Colonnes : line_id, country, institution, kind, action, description, source_doc, article, procedure, depends_on, dependency_ready, evidence, assumed_by. | Élevée : schéma de graphe de mandats (institution, pouvoir, source, preuve). Volume faible (31 lignes contre « 40–60 » annoncées). |
| Actions | `data/mandates/actions.yaml` | 25 actions sous la clé `actions`. | Élevée : vocabulaire d'actions contrôlé. |
| Précédents | `data/precedents.yaml` (22 Ko) | `by_action` : 21 actions, chacune avec des précédents (jurisdiction, instrument, article, what_it_does, fit_note, doc_id GL-S0x, url, binding). `by_gap_type` : G1 2, G2 3, G3 3, G6 2, G7 3, G8 1, G9 2. | Élevée, mais couverture des types G8 faible (1 précédent). |
| Questions d'évaluation | `data/eval/questions.yaml` | 28 questions (clés q, expect, country). Le rapport en annonce 40. | Moyenne : base de test pour la récupération (top 5). |
| Cadre ITU | `data/framework/dimensions.json` | framework_version 2.0, source ITU Report 2.0 (janv. 2026). 6 facteurs (data, research, deployment, standards, opensource, sandbox) et 13 dimensions, dont « Data/Model Marketplace », « Cross-Domain Correlation Analysis », « Digital Infrastructure ». | Très élevée : référentiel réutilisable tel quel. |
| Modèles de scénario de test | `data/eval/questions.yaml`, `alerte/data/docs/SCN/` | Voir ci-dessus. | Élevée pour les démos. |

### 3.2 OCR et données linguistiques

- `ocr/tessdata/` : `eng.traineddata` (15,4 MB), `fra.traineddata` (4,0 MB), `ara.traineddata` (12,6 MB). Total 31 MB. Utilisables si Tesseract est installé. Fonctionnement non vérifié (non exécuté).
- Pipeline d'extraction : `alerte/knowledge/extract/ocr.py` (559 lignes) et `alerte/knowledge/extract/images.py` (39 lignes). Dépendances de la machine non vérifiées.

### 3.3 Scripts et environnement

- Pas de dossier `scripts/` au sens strict. Scripts et mise en route : `alerte/setup.sh`, `alerte/setup.ps1`, `alerte/Dockerfile`, `alerte/docker-compose.yml`, `alerte/requirements.txt`, `alerte/requirements-full.txt`, `alerte/pyproject.toml`.
- Pipeline de fine-tuning (hors cœur) : `alerte/sandbox/finetune_lora.py`, `alerte/sandbox/serve_vllm.sh`, `alerte/sandbox/alerte_sandbox.ipynb`, `alerte/alerte/sft.py` (73 l.), `alerte/alerte/evaluation.py` (63 l.).
- CI : `.github/workflows/alerte-ci.yml` (racine du dépôt). Non lu.
- Tests : `alerte/tests/` (9 fichiers : test_ledger, test_knowledge, test_extraction, test_drill, test_exports, test_core_profile, test_llm_brain, test_ui, conftest). Non exécutés (pas d'installation autorisée) : **résultat non vérifié**.

### 3.4 Modules Python réutilisables (appréciation sur lecture d'en-tête et de taille)

| Module | Lignes | Rôle | Appréciation |
|---|---|---|---|
| `alerte/sim/ledger.py` | 90 | Journal append-only à chaîne SHA-256 (chaque ligne contient le hash de la précédente) ; `verify_ledger` détecte toute altération. | Très réutilisable. Docstring claire, petit périmètre, couvert par `tests/test_ledger.py`. Le plus sûr des modules. |
| `alerte/knowledge/chunk.py` | 106 | Découpage par article (FR, EN, AR), avec repli sur titres puis fenêtres de mots (256 mots, chevauchement 30). | Très réutilisable pour tout corpus juridique. Qualité jugée bonne d'après la docstring ; comportement sur AR non vérifié. |
| `alerte/knowledge/extract/pipeline.py` | 211 | Point d'entrée `extract_file(path) -> ExtractionResult` : correction humaine, cache, handler par format, drapeaux, cache. Un fichier n'est jamais ignoré silencieusement (champ `failed`). | Réutilisable. Bonne discipline (traçabilité des échecs). |
| `alerte/knowledge/extract/` (pdf.py 271 l., office.py 299 l., ocr.py 559 l., quality.py 74 l., synth.py 271 l., tools.py 127 l., result.py 93 l.) | ~1 700 | Extraction multi-format, OCR, contrôle qualité. | Réutilisable sous réserve : non lu. Contient la logique de relecture (`review`). |
| `alerte/analysis/gaps.py` | 186 | Détecteur de lacunes par règles (G1 à G10 définis, 7 règles actives dans `ae_core`). | Réutilisable comme patron de règles, mais le lien entre règles et textes reste à reprendre (voir 1.2, divergence 6). Non lu en détail. |
| `alerte/analysis/precedents.py` | 59 | Appariement lacune / précédents mondiaux. | Réutilisable. Non lu en détail. |
| `alerte/sim/citations.py` | 54 | Vérification des citations (article cité présent dans le texte). | Réutilisable : mécanisme « pas de citation sans source ». Non lu en détail. |
| `alerte/knowledge/mandates.py` | 68 | Chargement du graphe de mandats CSV. | Réutilisable. Non lu. |
| `alerte/knowledge/bm25.py` | 37 | Recherche lexicale BM25. | Réutilisable comme repli sans vecteurs (utile puisque `vectors: none`). Non lu. |
| `alerte/knowledge/embed.py` | 122 | Embeddings multilingues. | À réviser : aucun vecteur n'est produit dans l'index actuel. |
| `alerte/knowledge/store.py` (179 l.), `ingest.py` (295 l.), `fetch.py` (48 l.) | ~520 | Stockage, ingestion, téléchargement. | Réutilisables avec adaptation ; non lus. |
| `alerte/analysis/report.py` (185 l.), `scorecard.py` (61 l.) | ~250 | Rapport markdown/HTML et tableau de bord de préparation (13 dimensions). | Réutilisables pour la sortie. Non lus. |
| `alerte/config.py` (122 l.), `alerte/net.py` (55 l.), `alerte/textutil.py` (83 l.), `alerte/i18n.py` | ~300 | Configuration, réseau, texte, traduction. | Utilitaires généraux. Non lus. |
| `alerte/integrations/slack.py` | - | Intégration Slack. | Spécifique ; non lu. |

Modules à ne pas réutiliser sans reprise : `alerte/ui/` (interface Streamlit du projet, couplée aux runs), `alerte/sim/engine.py` et `alerte/sim/brain.py` (hors périmètre de ce rapport, non lus en détail).

## Points à signaler à l'utilisateur

1. Le rapport technique racine est le candidat le plus probable pour « le rapport relatif aux lacunes ». Le rapport ITU 2.0 (section 4) et les `runs/*/gaps.json` sont les deux autres candidats sérieux.
2. Trois documents du corpus sont mal nommés ou au mauvais contenu : AE-04 (charte IA), CM-14 (article de presse), CM-17 (ESCP Banque mondiale). À corriger avant toute publication du corpus.
3. Le rapport technique racine n'est pas aligné avec le dépôt sur plusieurs chiffres (documents, questions, lignes de mandats, embeddings). Il ne doit pas être cité tel quel comme état réel.
4. Aucun document n'a de colonne licence dans le manifest. Les droits de redistribution sont à vérifier avant publication.
