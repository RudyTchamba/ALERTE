# Sources des mandats du Cameroun — lecture des PDF et vérification

Date : 2026-11-24. Objectif : retrouver, **dans les documents eux-mêmes**, quel texte donne (ou ne donne pas) chacun des 14 pouvoirs/devoirs du registre `CM-L01…CM-L15`, afin de ne lier que des sources réelles et de ne pas fausser la table des mandats.

**Rien n'a été modifié dans vos données** : ni la base de connaissances, ni les mandats, ni le registre. Les PDF ont été lus par extraction de texte (et par OCR pour les deux scans), dans un dossier temporaire ; aucune réingestion ni aucun calcul d'embeddings n'ont été lancés. Ce document est une **proposition** que vous appliquez ou non dans l'interface (bouton **Sources** de chaque mandat).

## 1. Ce qui a été lu, et ce qui ne l'a pas été

* **17 documents** `CM-01…CM-18` (il n'y a pas de `CM-06`), pas 15 : les 17 ont été ouverts et identifiés ; **les textes décisifs ont été lus en entier ou article par article** : décret 98/031 (version réelle), loi 86/016, loi 2024/017 (OCR, articles 9, 15, 22, 32, 53, 54), loi 2010/012 (art. 7, 48), loi 90/047 (art. 5), décret 2005/124 (art. 58), PNC (sections institutionnelles), IFRC (CM-12 : section institutionnelle).
* **Les gros rapports** (CM-18 : 202 pages ; CM-13 : 66 pages ; CM-11 : 123 pages ; CM-02 : 42 pages) ont été **fouillés par mots-clés ciblés** (protection civile, alerte, urgence, opérateur, évacuation, notification, météorologie…), **pas lus page à page**. Une disposition qui n'emploie aucun de ces mots a pu m'échapper.
* **Langue** : OCR de CM-01 et CM-07 avec le modèle anglais (pas de modèle français installé) : les accents sont perdus et quelques mots sont déformés ; les articles cités ont été relus sur le texte OCR et correspondent à la numérotation de la loi.
* Les numéros de page ci-dessous sont ceux du **PDF** : la base de connaissances de l'application **n'enregistre pas les pages** (champ vide) ; elle donne l'**article** quand il existe.

## 2. Alerte importante : le corpus contient des erreurs

Identité réelle de chaque document, relevée sur le PDF, comparée à son titre dans la base :

| Doc | Titre affiché dans votre base | Contenu réel du PDF | Remarque |
|---|---|---|---|
| **CM-07** | « Décret 98/031 … plans d'urgence » | **« Rapport du Cameroun sur la Décennie internationale de la prévention des catastrophes naturelles (IDNDR) »**, scan de 4 pages | **Mauvais fichier.** Le vrai décret (13 articles, 4 pages) existe dans `alerte-platform/backend/scripts/corpus_fixes/CM-07_Decree_No_98-031…pdf` ; la base n'a **aucun** chunk du décret (0 occurrence de « plan d'urgence ») |
| CM-08 | « Décret 2005/124 sur les télécommunications d'urgence (cité par l'IFRC) » | **Décret 2005/124 du 15 avril 2005 portant organisation du Ministère des Postes et Télécommunications** (48 pages) | titre faux ; contenu précieux (art. 58) |
| CM-13 | « Modèle de loi GRC de l'IFRC » | **Cartographie IFRC des cadres juridiques de gestion des risques** du Cameroun (66 pages) | titre faux ; source **secondaire** |
| CM-14 | « Stratégie nationale d'IA (SNIA), MINPOSTEL, officiel » | **article de presse** (Investir au Cameroun) | non officiel ; aucun mandat |
| CM-17 | « Gavi, le choléra au Cameroun » | **Plan d'engagement environnemental et social de la Banque mondiale** (Programme de sécurité sanitaire, MoPH) | titre faux ; aucun mandat |
| CM-12 | rapport IFRC 2021 | exact ; mais le document dit lui-même : « brouillon … ne doit pas être considéré comme faisant autorité » | secondaire |
| CM-01, CM-07, CM-09 | — | **scans** (CM-01 : 24 p. ; CM-09 : Journal officiel, couche texte bruitée) | qualité d'extraction à surveiller |
| CM-05 | loi 86/016 | exact, **2 pages**, recopiée depuis CamerLex (pas le JO) | complète mais de seconde main |
| CM-02, 03, 04, 10, 11, 15, 16, 18 | conformes | conformes | — |

L'équipe a déjà un script qui corrige ces défauts sur son espace (`scripts/fix_cameroon_kb.py`) : **il n'a pas été appliqué à votre base**. Tant que CM-07 contient le rapport IDNDR, **aucun mandat ne peut être fondé sur le décret 98/031**. Procédure sûre : dans **Bases de connaissances → Cameroun → document CM-07 → Téléverser une nouvelle version** avec le vrai PDF (l'ancienne version reste dans l'historique), puis republier la base. C'est une modification de vos données : je ne l'ai pas faite sans votre accord.

## 3. Verdict mandat par mandat

Légende : **FONDÉ** (un texte lu dit cela) · **PARTIEL** (le texte soutient une partie ou une autre institution) · **NON FONDÉ tel qu'écrit** (le texte dit autre chose, ou rien) · **SANS SOURCE** (rien dans les 17 documents). Ce n'est **pas** une conclusion juridique : l'absence d'un texte dans le corpus n'est pas l'absence d'un mandat.

| Réf. | Institution · action | Verdict | Meilleure source (base de votre application) | Ce que dit le texte | À faire |
|---|---|---|---|---|---|
| **CM-L01** | DPC · *chef de file* · coordonner la réponse | **FONDÉ (officiel, de seconde main)** | **CM-10** (PNC) p. 6 — passage « Direction de la Protection Civile (DPC) … chargée … de la coordination des moyens mis en œuvre pour la protection civile, notamment les secours, le sauvetage, la logistique, l'utilisation des forces supplétives et auxiliaires » | quasi mot pour mot la description du mandat | **Valider** avec cette source. Réserve : « chef de file » n'est écrit nulle part ; le CNPC a la même coordination (voir L02) → envisager `power` plutôt que `lead` |
| **CM-L02** | COORD · pouvoir · coordonner / proposer des mesures | **PARTIEL** | **CM-05** art. 3 (p. 1) : le Conseil national de la protection civile existe et assiste le Président, « composition et attributions fixées par décret » ; **CM-12** p. 2 (IFRC, résumé du décret 96/054 art. 1, 4, 6) : « propose les mesures préventives… coordonne les moyens… peut se constituer en cellule de crise » | l'**existence** est prouvée par la loi ; les **attributions** ne viennent que d'une source secondaire (le décret 96/054 n'est pas dans le corpus) | Valider seulement en acceptant le statut « déduit » ; **obtenir le décret 96/054** |
| **CM-L03** | DPC · devoir · décider d'alerter la population (« après activation des plans, décret 98/031 ») | **PARTIEL — attribution à corriger** | décret 98/031 art. 3(3) (vrai décret, p. 1) : l'action de **l'autorité compétente** comporte « la diffusion de l'alerte … l'information du public » ; **CM-10** p. 27 : « Diffusion de l'alerte (**Autorités administratives, DPC**) » | l'autorité compétente est le **préfet, le gouverneur ou le secrétaire général de la Présidence** (art. 3(1)), pas la DPC ; la DPC apparaît à côté des autorités administratives dans le PNC | Corriger la description ou ajouter les autorités administratives ; sourcer sur **CM-10 p. 27** en attendant le vrai décret |
| **CM-L04** | DPC · pouvoir · activer le plan d'urgence | **NON FONDÉ tel qu'écrit (biais)** | décret 98/031 art. 3(1) : « le déclenchement du plan d'urgence … se fait par le **préfet** au niveau du département ; par le **gouverneur** au niveau de la province ; par le **secrétaire général de la Présidence** au niveau national » | le pouvoir de déclencher n'est **pas** donné à la DPC | **Ne pas valider pour la DPC.** Laisser « proposé » ou réattribuer (voir §4) |
| **CM-L05** | DPC · pouvoir · évacuer une zone (« les autorités administratives ordonnent ») | **NON FONDÉ tel qu'écrit** | **CM-13** p. 28 : « il ne semble pas y avoir de procédure d'évacuation dans le PNC ou la législation » ; **CM-09** art. 5(4) (p. 3) : *sous état d'urgence déclaré*, les autorités administratives peuvent « instituer des zones de protection ou de sécurité où le séjour des personnes est réglementé » | aucun texte de droit commun ne donne un pouvoir d'évacuer ; le pouvoir apparent n'existe qu'en état d'urgence, et chez les autorités administratives | Laisser « proposé » (déduit) ; ne pas l'attribuer à la DPC |
| **CM-L06** | MET · devoir · émettre des alertes météo/crue | **SANS SOURCE** | aucune. Le PNC (p. 32) ne cite la direction de la météorologie que comme **fournisseur de données** | le décret d'organisation du service météo n'est pas dans le corpus | Laisser « proposé / supposé » ; **obtenir le texte** ; ne pas conclure à une lacune juridique |
| **CM-L07** | ONR · pouvoir · alerte météo/crue (« collecte et diffuse l'information, arrêté 037/PM ») | **PARTIEL** | **CM-10** p. 32 : « l'ONR est l'organe central en charge de la gestion de l'information sur les aléas et les menaces » ; p. 6 cite l'arrêté 037/PM ; p. 27 : chaîne collecte → analyse → stockage → **diffusion** | soutient la gestion de l'information sur les risques, **pas** « émettre l'alerte météo » ; le PNC (2011) dit l'ONR « créé mais non encore totalement opérationnel » | Valider seulement la partie « information sur les risques » ; l'action `issue_weather_warning` est trop large |
| **CM-L09** | OPS · pouvoir · envoyer des alertes de masse | **NON FONDÉ tel qu'écrit** | **CM-02** art. 9, 10, 28 (p. 11-12, 17) : « acheminement gratuit des communications électroniques d'urgence » (condition de licence) ; **CM-08** art. 58 (p. 36) : le service des télécommunications d'urgence du ministère « définit le rôle des opérateurs dans les télécommunications d'urgence » et participe à la coordination des « services d'alerte au public » | aucune disposition ne donne aux opérateurs le pouvoir ni le devoir de **diffuser des alertes publiques** ; leur rôle est encore « à définir » | Laisser « proposé » : c'est cohérent avec l'absence de pouvoir de contrainte sur les opérateurs (pas de L08). « Peut techniquement envoyer des SMS » est un fait technique, pas un pouvoir juridique |
| **CM-L10** | ANTIC · pouvoir · bloquer une fausse alerte | **PARTIEL** | **CM-04** art. 7(2) (p. 9) : l'Agence « assure … la régulation, le contrôle et le suivi des activités liées à la sécurité des systèmes d'information et des réseaux… », « veille technologique et émet des alertes et recommandations » ; art. 48(2) (p. 18) : « l'émission de messages électroniques en usurpant l'identité d'autrui est interdite » | la **supervision de la sécurité** est fondée ; le pouvoir de **bloquer** ne l'est pas | Valider avec art. 7 en précisant dans la description « contrôle et alerte sécurité », sans « blocage » |
| **CM-L11** | CTD · pouvoir · agir sur une alerte locale | **FONDÉ (texte primaire) pour la prévention et l'intervention** | **CM-11** art. 157 (p. 38) : « élaboration et mise en œuvre des plans communaux spécifiques de prévention des risques et d'intervention d'urgence en cas de catastrophes » ; art. 218 d) (p. 55) : prévention et intervention en cas de « fléaux calamiteux, tels que les incendies, les **inondations** … les maladies épidémiques », avec recours au représentant de l'État | « recevoir les alertes transmises » n'est pas écrit | **Valider** avec art. 218 d) (et art. 157) ; reformuler « prévention et intervention » |
| **CM-L12** | MINSANTE · devoir · choléra : détecter, évaluer, notifier | **PARTIEL** | **GL-17** (RSI 2005, base GL) art. 5 et 6 (p. 8) : chaque **État Partie** développe les capacités de détection et « notifie à l'OMS … dans les 24 heures » ; **CM-18** p. 26 : le plan du MINSANTE « résulte de la volonté de s'arrimer aux exigences du RSI 2005 » | l'obligation pèse sur **l'État** ; son exercice par le MINSANTE ne ressort que de son propre plan (le décret d'organisation du MINSANTE, 2002/209, n'est pas dans le corpus) | Valider avec **GL-17 art. 6 + CM-18 p. 26** en gardant « déduit » |
| **CM-L13** | DPA · devoir · faire appliquer la loi 2024/017 | **FONDÉ (primaire)** | **CM-01** art. 53 (p. 19) : l'Autorité est « un organisme public indépendant chargé … de veiller à l'application de la présente loi… de délivrer les autorisations… de traiter les réclamations… et enquêter » ; art. 54 (p. 19-20) : mise en demeure, injonction sous astreinte, suspension, retrait d'autorisation | « audit » n'est pas écrit mot pour mot | **Valider** avec art. 53 (+ art. 54) |
| **CM-L14** | OPS · devoir · sécuriser les données et respecter le consentement | **FONDÉ (primaire, portée générale)** | **CM-01** art. 22(2) (p. 10) : mesures de protection techniques et organisationnelles (chiffrement, accès restreints) ; art. 15 (p. 8) ; art. 9 (p. 7) : consentement préalable | la loi vise **tout** responsable de traitement / sous-traitant ; les opérateurs ne sont pas nommés (inférence) | **Valider** avec art. 22 ; statut « déduit » pour la qualité de responsable de traitement de l'opérateur |
| **CM-L15** | DPA · pouvoir · autoriser le transfert à l'étranger | **FONDÉ (primaire)** | **CM-01** art. 32(1) (p. 13) : « le transfert de données à caractère personnel vers un État étranger… est subordonné à l'obtention d'une autorisation préalable délivrée par l'Autorité » | exact | **Valider** (à l'étape contrefactuelle du guide) |

**Bilan** : 5 fondés (L01, L11, L13, L14, L15), 5 partiels (L02, L03, L07, L10, L12), 3 non fondés tels qu'écrits (L04, L05, L09), 1 sans source (L06).

## 4. Biais détectés dans la table des mandats

1. **Pouvoirs attribués à la DPC que le texte donne à d'autres** : déclencher le plan d'urgence (L04) et décider/diffuser l'alerte (L03) reviennent, dans le décret 98/031 art. 3, au **préfet, au gouverneur ou au secrétaire général de la Présidence**. Aucune de ces institutions n'est dans votre registre (11 institutions) : la table survalorise la DPC. *(Les institutions « Gouverneur » etc. existent dans l'espace de l'équipe, pas dans le vôtre.)*
2. **Institution omise : ART / MINPOSTEL** : le décret 2005/124 art. 58 lui donne la « participation à la coordination de la prestation des services d'alerte au public » et la définition du rôle des opérateurs. Votre registre n'a **aucun mandat pour ART** : candidat à ajouter (CM-08 p. 36).
3. **Deux organes fusionnés sous « COORD »** : le **Conseil national de la protection civile** (loi 86/016 art. 3 ; décret 96/054) et le **Comité national de crise** (décret 98/031 art. 4-7, présidé par le secrétaire général de la Présidence, composé de ministres dont le ministre de la Santé) sont deux instances distinctes.
4. **Chevauchement réel** : le CNPC (L02) et la DPC (L01) « coordonnent les moyens … secours, sauvetage, logistique, forces auxiliaires » : c'est la règle G2 (pouvoirs qui se chevauchent) qui devrait le signaler, pas un « chef de file » posé sans texte.
5. **Mandats « devoir » qui sont en réalité des obligations de l'État** (L12) ou des **lacunes réelles du corpus** (L06, L09) : à garder « proposés » plutôt que de forcer une source.
6. **Mauvaise base documentaire** : tant que CM-07 est le rapport IDNDR, tout lien vers « le décret » serait un faux (voir §2).

## 5. Textes primaires manquants (à obtenir avant de conclure)

| Texte | Pour quel mandat | Pourquoi |
|---|---|---|
| **Décret 98/031** (vrai, 13 articles) — **déjà disponible** dans `scripts/corpus_fixes/` | L03, L04 | remplacer CM-07 |
| Décret **96/054** du 12 mars 1996 (composition et attributions du CNPC) | L02 | attributions de première main |
| Arrêté **037/PM** du 9 mars 2003 (Observatoire national des risques) | L07 | pouvoirs de l'ONR |
| Décret **2005/103** (organisation du MINATD) / **98/147** | L01 | statut de la DPC |
| Décret d'organisation du service de la **météorologie nationale** | L06 | aucun texte dans le corpus |
| Décret **2002/209** (organisation du MINSANTE) | L12 | rôle du ministère |
| Cadre de la diffusion d'alertes aux opérateurs (arrêté/cahier des charges) | L09 | rôle « à définir » (CM-08 art. 58) |

CM-15 (déclaration officielle du Cameroun à l'ONU, p. 3-4) **liste** les décrets 96/054, 98/031, 98/147, l'arrêté 037/PM et la création de la DPC en 1995-96 : c'est une preuve officielle de leur **existence**, pas de leur **contenu**.

## 6. Comment l'appliquer dans l'interface (requêtes vérifiées)

> **Mise à jour 2026-11-24 (corpus reconstruit à partir des PDF)** : les requêtes ci-dessous ont été **revérifiées sur la base reconstruite** (recherche lexicale, `knowledge_bases/` — voir `docs/knowledge-base/`). Toutes donnent le passage attendu au **rang 1**, sauf L07 (rang 2). **CM-01 · Article 53** : l'OCR a lu « ARTICLE §3 » ; le passage est donc dans un chunk **sans numéro d'article** qui commence par « TITRE V DE L'AUTORITE DE PROTECTION DES DONNEES… » (le pipeline signale désormais ce défaut : « suite des articles interrompue »). Les noms de bases sont désormais « Cameroun » et « Références globales et internationales ».

**Pourquoi la recherche « ne trouvait rien »** : la fenêtre **Sources** était pré-remplie avec la **description anglaise** du mandat, et les textes du Cameroun sont en **français** ; la recherche est lexicale (mots exacts, pas de traduction). Test sur vos données : avec ce texte pré-rempli, seul `CM-L15` ramenait le bon article (CM-01 art. 32, 2ᵉ résultat) ; les 8 autres cibles étaient absentes des 5 premiers résultats. **Corrigé** : le champ est maintenant vide, avec une aide « cherchez avec des mots français du texte », un message quand rien n'est trouvé, et 8 résultats au lieu de 5.

Pour chaque mandat : **Pays et institutions → Registre des mandats → ligne (colonne Réf.) → Sources**, base **Cameroun** (sauf L12a : **Pratiques mondiales**), saisir la requête, **Rechercher**, puis **Utiliser comme source** sur le résultat indiqué. Chaque requête a été **testée sur l'API de recherche de l'application** (rang 1 = premier résultat).

| Réf. | Requête à saisir (testée) | Résultat à choisir (rang 1) | Comment le reconnaître |
|---|---|---|---|
| L01 | `Direction de la Protection Civile coordination des moyens` | **CM-10** (sans article) | texte « … de la coordination des moyens mis en œuvre pour la protection civile, notamment les secours, le sauvetage, la logistique… » |
| L02 | `Conseil National de la Protection Civile` | **CM-05 · Article 3** | « Dans exercice de ces prérogatives, le Président de la République est assisté d'un Conseil National de la Protection Civile… » (le passage CM-12 est difficile à faire remonter : ne lier que l'article 3) |
| L03 | `diffusion de l'alerte autorités administratives DPC` | **CM-10** (sans article) | « Activation du système d'alerte — Diffusion de l'alerte (Autorités administratives, DPC) » |
| L07 | `Observatoire National des Risques organe central gestion de l'information` | **CM-10** (sans article) | « l'Observatoire National des Risques (ONR) est l'organe central en charge de la gestion de l'information… » |
| L10 | `Agence Nationale des Technologies de l'Information régulation activités de sécurité électronique` | **CM-04 · Article 7** | « L'Agence Nationale des Technologies de l'Information et de la Communication… est chargée de la régulation des activités de sécurité électronique » |
| L11 | `fléaux calamiteux incendies inondations` | **CM-11 · ARTICLE 218** | « La police municipale a pour objet d'assurer le bon ordre, la sûreté… » |
| L12 (1) | `Article 6 Notification État Partie 24 heures` (base **Pratiques mondiales**, à publier d'abord) | **GL-17 · Article 6** | « Chaque État Partie … notifie à l'OMS … dans les 24 heures » |
| L12 (2) | `arrimer exigences Règlement Sanitaire International Stratégie Sectorielle de la Santé` | **CM-18** (sans article) | « … s'arrimer aux exigences du Règlement Sanitaire International (RSI) 2005 » |
| L13 | `veiller à l'application de la présente loi délivrer les autorisations réclamations` | **CM-01, chunk sans numéro d'article** (Article 53 : « ARTICLE §3 » à l'OCR) | « TITRE V DE L'AUTORITE DE PROTECTION… L'Autorité de protection des données… est un organisme public indépendant chargé… » |
| L14 | `violation des données informer sans délai Autorité mesures de protection techniques` | **CM-01 · ARTICLE 22** | « Dès connaissance de toute violation… est tenu d'informer sans délai l'Autorité » |
| L15 | `transfert de données à caractère personnel vers un État étranger autorisation préalable` | **CM-01 · ARTICLE 32** | « Le transfert de données … vers un État étranger… est subordonné à l'obtention d'une autorisation préalable » |

Conseils : un passage **sans article** (CM-10, CM-18) se reconnaît à son texte, pas à une étiquette ; **vérifiez toujours le texte du résultat avant de cliquer** ; les textes numérisés (CM-01) ont des mots abîmés par l'OCR, d'où des requêtes courtes et en mots entiers ; si rien ne sort, retirez un mot. Résultats vérifiés sur la **copie de vos données** faite le 2026-11-24 ; si vous avez republié la base depuis, les rangs peuvent changer.

**Ne rien lier** pour L04, L05, L06, L09 : laissez « proposé ». Pour la revue du registre : laissez « non revu » (aucun registre n'est complet : 5 mandats sur 14 seulement sont solidement fondés).

## 7. Décisions qui vous reviennent

1. Remplacer CM-07 par le vrai décret 98/031 (nouvelle version du document, republication de la base) ? — je recommande oui ; c'est la condition pour fonder L03/L04.
2. Ajouter au registre les institutions « Préfet », « Gouverneur », « Secrétariat général de la Présidence » (et un mandat pour ART/MINPOSTEL) ou reformuler L03/L04 ? — change la table, donc le scénario et les lacunes ; à décider.
3. Corriger les titres/fiabilités de CM-08, CM-13, CM-14, CM-17 (le script de l'équipe le fait) ?
4. Reformuler les descriptions de L03, L07, L10, L11 pour qu'elles ne disent pas plus que le texte ?

Je peux préparer ces changements en une seule fois, **sur une copie** de vos données d'abord, pour que vous voyiez l'effet sur les lacunes avant de toucher l'original.
