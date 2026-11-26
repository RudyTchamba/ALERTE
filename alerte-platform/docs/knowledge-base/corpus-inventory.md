# Inventaire du corpus PDF

Généré par `backend/scripts/kb_inventory.py` à partir des **44 PDF** trouvés récursivement dans `alerte/` (lecture seule) : **2133 pages**, **141.8 Mo**, **64 pages sans couche texte exploitable** (candidates à l'OCR). Doublons exacts (SHA-256) : **0** ; quasi-doublons : **0** ; illisibles : **0**.

Par collection : **AE** 9, **CM** 17, **GL** 16, **ITU** 2.

Les titres, types, dates, langues viennent du **registre de curation** (`knowledge_bases/curation/documents.curation.json`), établi en lisant la première page de chaque PDF : le manifeste du prototype n'a pas été repris (plusieurs de ses titres sont faux, voir « Écarts »). Aucune URL de source n'est renseignée tant qu'elle n'est pas établie ; la fiabilité n'est `official` que lorsque le PDF lui-même montre une publication officielle.

| Code | Titre (lu dans le PDF) | Type | Langue | Pages | Sans couche texte | SHA-256 (début) | Fiabilité | Droits |
|---|---|---|---|---|---|---|---|---|
| AE-01 | Federal Decree-Law No. (45) of 2021 concerning the Protection of Personal Data | law | en | 29 | 0 | `d5d5f9e93bd6` | unknown | unknown |
| AE-02 | UAE National Strategy for Artificial Intelligence 2031 | strategy | en | 25 | 3 | `821045059671` | unknown | unknown |
| AE-04 | The UAE Charter for the Development and Use of Artificial Intelligence (juillet 2024) | charter | en | 6 | 0 | `2f1de5776449` | unknown | unknown |
| AE-05 | Federal Decree-Law No. (35) of 2024 on the Reorganization of the Civil Defence Authority | law | en | 11 | 0 | `73a75bfec06b` | unknown | unknown |
| AE-06 | Unprecedented rainfall in the United Arab Emirates (Natural Hazards 121, 2025) | paper | en | 23 | 0 | `d56162b99a34` | unofficial | unknown |
| AE-09 | Federal Decree-Law No. (3) of 2003 Regulating Telecommunications | law | en | 34 | 0 | `ad162193811d` | unknown | unknown |
| AE-10 | Federal Decree-Law No. (34) of 2021 on Countering Rumors and Cybercrimes | law | en | 36 | 0 | `f438fdf264b9` | unknown | unknown |
| AE-11 | Federal Decree-Law No. (6) of 2007 regarding the Establishment and Regulation of the National Center of Meteorology (NCM) | law | en | 8 | 0 | `ead65388c821` | unknown | unknown |
| AE-12 | TRA Technical Specification — Enabling Cell Broadcast for National Public Warning Service (UAE-Alert), TS FS 001 v2.0 | standard | en | 7 | 0 | `a57767424396` | unknown | unknown |
| CM-01 | Loi n°2024/017 du 23 décembre 2024 relative à la protection des données à caractère personnel | law | fr | 24 | 23 | `3fd7aea48aa8` | official | unknown |
| CM-02 | Loi n°2010/013 du 21 décembre 2010 régissant les communications électroniques au Cameroun | law | fr | 42 | 0 | `849f64c6dab7` | unknown | unknown |
| CM-03 | Loi n°2015/006 du 20 avril 2015 modifiant et complétant certaines dispositions de la loi n°2010/013 | law | fr | 10 | 0 | `35d81ac3176b` | unknown | unknown |
| CM-04 | Loi n°2010/012 du 21 décembre 2010 relative à la cybersécurité et la cybercriminalité au Cameroun | law | fr | 31 | 0 | `7c964708430f` | unknown | unknown |
| CM-05 | Loi n°86/016 du 6 décembre 1986 portant réorganisation générale de la protection civile | law | fr | 2 | 0 | `248c90fc2b85` | unofficial | unknown |
| CM-07 | Rapport du Cameroun sur la Décennie internationale de la prévention des catastrophes naturelles (IDNDR) | report | fr | 4 | 4 | `bdc591f5ed82` | unknown | unknown |
| CM-08 | Décret n°2005/124 du 15 avril 2005 portant organisation du Ministère des Postes et Télécommunications | decree | fr | 48 | 0 | `3f9134bceaa3` | unknown | unknown |
| CM-09 | Loi n°90/047 du 19 décembre 1990 relative à l'état d'urgence | law | fr | 4 | 0 | `f23dd8250aeb` | unknown | unknown |
| CM-10 | Plan national de contingence du Cameroun, livre premier (avril 2011) | plan | fr | 38 | 1 | `2b2c5e2f40b3` | unknown | unknown |
| CM-11 | Loi n°2019/024 du 24 décembre 2019 portant Code général des collectivités territoriales décentralisées | law | fr | 123 | 1 | `84ec86039a6f` | unknown | unknown |
| CM-12 | IFRC — Republic of Cameroon: Mapping of International Disaster Response Laws, Rules and Principles (mai 2021, brouillon) | report | en | 15 | 0 | `8307b2700847` | summary | unknown |
| CM-13 | IFRC — Republic of Cameroon: Mapping of Legal and Policy Arrangements for Disaster Risk Management, including Public Health Emergencies and international disaster assistance | report | en | 66 | 0 | `fa25a29ed03e` | summary | unknown |
| CM-14 | Article de presse (Investir au Cameroun) sur la Stratégie nationale d'intelligence artificielle | press | fr | 9 | 1 | `e4178b8c0faf` | unofficial | unknown |
| CM-15 | Déclaration du Cameroun, 79e session de l'Assemblée générale des Nations unies, Sixième Commission : protection des personnes en cas de catastrophe | statement | fr | 6 | 0 | `a8c363e36314` | unknown | unknown |
| CM-16 | UNICEF Cameroon — Floods Flash Update No. 5, Far North (24 octobre 2024) | report | en | 3 | 0 | `f6cdcbf14ee1` | summary | unknown |
| CM-17 | Banque mondiale / MoPH Cameroun — Environmental and Social Commitment Plan, Health Security Program in Western and Central Africa, Phase III (P508837) | report | en | 22 | 0 | `a3bdb7afc758` | unknown | unknown |
| CM-18 | Plan de préparation et de riposte au choléra, Ministère de la Santé publique | plan | fr | 202 | 3 | `b2b578077dee` | unknown | unknown |
| GL-01 | Directive (EU) 2018/1972 establishing the European Electronic Communications Code (version consolidée EUR-Lex du 18.10.2024) | law | en | 150 | 0 | `c45f95e828d6` | summary | unknown |
| GL-02 | Regulation (EU) 2024/1689 laying down harmonised rules on artificial intelligence (AI Act) | law | en | 144 | 0 | `bba630444b32` | official | unknown |
| GL-03 | Regulation (EU) 2016/679 on the protection of natural persons with regard to the processing of personal data (GDPR) | law | en | 88 | 0 | `bd84e63f5b62` | official | unknown |
| GL-04 | Republic Act No. 10639 (20 juin 2014) mandating telecommunications service providers to send free mobile alerts | law | en | 3 | 0 | `7b04402a8868` | unofficial | unknown |
| GL-05 | 47 CFR Part 10 — Wireless Emergency Alerts (extrait) | regulation | en | 12 | 0 | `3968d93b5000` | official | allowed |
| GL-06 | FCC — Report and Recommendations: Hawaii Emergency Management Agency, January 13, 2018 False Alert | report | en | 28 | 0 | `d19c432a20ac` | official | allowed |
| GL-07 | World Bank / GFDRR — Information and Communication Technology for Disaster Risk Management in Japan (octobre 2019) | report | en | 166 | 12 | `ea1da360405c` | summary | restricted |
| GL-09 | UN — Early Warnings for All: Executive Action Plan 2023-2027 | plan | en | 56 | 1 | `beb647f4ba2a` | official | unknown |
| GL-11 | ITU — Guidelines for national emergency telecommunication plans | guideline | en | 106 | 4 | `4c765c9c919d` | official | unknown |
| GL-12 | ITU-T X.1303 bis (03/2014) — Common alerting protocol (CAP 1.2) | standard | en | 40 | 2 | `79ec13413942` | official | unknown |
| GL-13 | UNDRR — Sendai Framework for Disaster Risk Reduction 2015-2030 | framework | en | 37 | 5 | `8a2875d4b6d5` | official | unknown |
| GL-14 | African Union Convention on Cyber Security and Personal Data Protection (EX.CL/846(XXV)) | treaty | en | 40 | 0 | `b3d09f4d736d` | unknown | unknown |
| GL-15 | African Union — Continental Artificial Intelligence Strategy: Harnessing AI for Africa's Development and Prosperity | strategy | en | 66 | 1 | `c5429f73786c` | unknown | unknown |
| GL-16 | WHO — Ethics and governance of artificial intelligence for health | guideline | en | 165 | 0 | `dc5697ab8ba8` | official | unknown |
| GL-17 | Règlement sanitaire international (2005) — document A77/A/CONF./14 de la 77e Assemblée mondiale de la Santé (1er juin 2024) | treaty | fr | 67 | 0 | `99079cf20a0d` | official | unknown |
| GL-18 | NIST AI 100-1 — Artificial Intelligence Risk Management Framework (AI RMF 1.0) | framework | en | 48 | 0 | `7576edb531d9` | official | unknown |
| ITU-AI4G-2025-6 | ITU — AI Ready: Analysis towards a Standardized Readiness Framework (AI4GOOD-2025-6) | report | en | 55 | 0 | `71191768d46b` | official | unknown |
| ITU-Y.3172 | ITU-T Y.3172 (06/2019) — Architectural framework for machine learning in future networks including IMT-2020 | standard | en | 34 | 3 | `e42f9a3be3f9` | official | unknown |

## Écarts entre les noms de fichiers du dossier source et le contenu réel

| Fichier | Contenu réel |
|---|---|
| CM-07 (« Decree 98/031 ») | rapport du Cameroun sur la Décennie internationale de prévention des catastrophes (IDNDR) |
| CM-08 (« télécommunications d'urgence, cité par l'IFRC ») | décret 2005/124 d'organisation du ministère des Postes et Télécommunications |
| CM-13 (« modèle de loi GRC ») | cartographie IFRC des cadres juridiques de gestion des risques |
| CM-14 (« stratégie SNIA officielle ») | article de presse |
| CM-17 (« Gavi, choléra ») | plan d'engagement environnemental et social de la Banque mondiale |
| AE-04 (« chaîne d'alerte UAE-Alert ») | Charte de l'IA des Émirats (juillet 2024) |
| AE-06 (« chiffres du NCM ») | article scientifique (Natural Hazards 2025) |
| AE-12 (« TS040 ») | spécification TRA TS FS 001 v2.0 (cell broadcast UAE-Alert) |
| GL-07 (« J-Alert ») | rapport Banque mondiale / GFDRR sur les TIC pour la gestion des risques au Japon |

Documents attendus mais absents : voir `knowledge_bases/<COL>/expected_documents.jsonl` et `build-report.md`.
