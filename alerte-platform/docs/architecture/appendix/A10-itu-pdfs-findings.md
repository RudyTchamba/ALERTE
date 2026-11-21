> **Annexe — Lecture intégrale du rapport AI Readiness 2.0 et de l'ITU-T Y.3172 (PDF locaux).**
> Matériau de recherche brut produit le 2026-11-21 par un sous-agent (modèle Haiku 5.5), relu en partie par l'architecte. Les marqueurs « non vérifié » / `[NV]` / `[V]` / `[P]` / `[S]` / `[LU]` / `[SUPPOSÉ]` sont ceux du sous-agent. Pièce justificative, pas une spécification.

---

# Findings ITU : AI Readiness Report 2.0 (a) et Y.3172 (b)

Date de la lecture : 2026-11-21. Périmètre : deux PDF locaux lus en intégralité via `pdftotext -layout` (texte extrait dans le scratchpad), plus rendu PNG de trois figures de Y.3172 (Fig. 3, Fig. 4, Fig. I.1) pour lire leur contenu graphique.

Conventions :
- **[LU]** = lu dans le PDF (texte ou figure). Les numéros de page sont les folios imprimés.
- **[SUPPOSÉ]** = inférence de ma part, non écrite dans le texte.
- Citations verbatim entre guillemets, en anglais comme dans le document source.
- Je n'ai pas consulté la documentation du projet ALERTE ; la liste des nœuds « attribués à Y.3172 » vient du brief (SRC, C, PP, M, P, D, SINK, MLFO, ML sandbox, ML intent). Pour les dimensions, je compare aux 13 libellés fournis dans le brief.

---

## Partie (a) : « AI Ready – Analysis Towards a Standardized Readiness Framework », Report 2.0, ITU, janvier 2026, 55 p.

### a.0 Structure [LU]

- Ch. 1 Introduction (p. 7-11). Ch. 2 Basic Framework (p. 12-16). Ch. 3 Structural Approach : factors et dimensions (p. 17-34). Ch. 4 AI Readiness Gap Analysis (p. 35-36). Ch. 5 Toolkit « AI Readiness Enablement Toolkit » (AI-RE Toolkit) et exigences ITU-AI-RE-Toolkit-REQ-001 à 028 (p. 37-42). Ch. 6 Future work (p. 43). FAQ (p. 46-50). Références (p. 51-52).
- Le texte est à « Report 2.0 » ; la dernière version du texte date de janvier 2026, mais la disclaimer indique « Information provided is correct as of June 2025 » (p. ii).

### a.1 Factors, « piliers » et dimensions

**Six facteurs** (liste d'introduction, p. 7, puis Ch. 3 p. 17-18) :

| Intro, p. 7 (Sept. 2024) | Ch. 3, p. 17-18 (préliminaire mai 2024) |
|---|---|
| Open Data | Data (« Accessibility and quality of datasets ») |
| Research | Research |
| Deployment | Deployment Support |
| Standards | Standards |
| Open source | Open source and Code |
| Sandbox | Sandbox Environments |

Incohérence de libellés relevée [LU] : « Open Data » vs « Data », « Deployment » vs « Deployment Support », « Open source » vs « Open source and Code », « Sandbox » vs « Sandbox Environments ». La date de la version préliminaire diffère aussi (Sept. 2024 p. 7 ; mai 2024 p. 17).

**Cinq « pillars » de Ch. 2** (p. 12-16) : Data ; Digital Infrastructure ; Digital Skills ; Innovation Ecosystem ; AI Policy. Chaque pilier a des « Indices » puis des « Metrics » (tableau p. 12-13). Le mot « Dimensions » du tableau de Ch. 2 désigne ces 5 piliers, alors que Ch. 3 appelle « dimensions » les 13 entrées. **Ambiguïté terminologique du rapport** [LU].

Dans Ch. 2 p. 16 : « The AI Policy dimension evaluates the maturity of institutional frameworks... » ; dans Ch. 2 p. 15 : Innovation Ecosystem annoncé comme « six key dimensions: standards, Engagement in Open source, R&D, investment, GenAI Content, and AI Technology market size », alors que le tableau n'en liste que cinq (pas de « GenAI content ») [LU].

**Treize dimensions** (Ch. 3, p. 18-34) — noms exacts, pages de début :

1. Dimension 1: Data/model Marketplace (p. 18)
2. Dimension 2: Generated Content Marketplace (p. 19)
3. Dimension 3: Cross-domain correlation analysis (p. 20)
4. Dimension 4: Contextualization and Regional Impact (p. 21)
5. Dimension 5: Level of Integration of AI in Workflows (p. 22)
6. Dimension 6: Human Interface (p. 23)
7. Dimension 7: Strategy Alignment (p. 24)
8. Dimension 8: Collaboration with AI (p. 25)
9. Dimension 9: Impacts of Humans in AI Integration (p. 26)
10. Dimension 10: AI & Policies (p. 28)
11. Dimension 11: AI for Inclusion (p. 29)
12. Dimension 12: Granular Priorities (p. 32)
13. Dimension 13: Digital Infrastructure (p. 33)

Rattachement aux facteurs, tel qu'écrit dans le texte [LU] :
- D1 : « mapped to the factor of open data and open source » (p. 19).
- D2 : « mapped to the open data and open-source factor » (p. 20).
- D3 : « mapped to open data and standards » (p. 21).
- D4 : « mapped to open data, research, and deployment » (p. 22).
- D5 : « mapped to the Standards factor » (p. 23).
- D6 : « mapped to Standards and deployment factors » (p. 24).
- D7 : « mapped to the Standards factor due to the need for a standardized format for intent coordination » (p. 25).
- D8 : « mapped to the open-source and Standards factor » (p. 26).
- D9 : « could be mapped with the Sandbox factor » (p. 27, formulation hypothétique).
- D10 : « mapped to Sandbox and deployment factors » (p. 28).
- D11 : « mapped with the Sandbox factor » (p. 30).
- D12 : « mapped to the deployment factor » (p. 32).
- D13 : « mapped to deployment » (p. 33).

Conséquence [LU + SUPPOSÉ] : le facteur **Research** n'a de rattachement explicite que pour D4. Le facteur **Deployment** est le plus fréquent (D4, D6, D10, D12, D13).

**Sélection des dimensions** [LU] : « The dimensions are chosen based on whether they fit some axis (e.g., X, Y) and whether it is possible to plot the progress of different levels of entities across these axes » (p. 17).

**Indices** [LU] (p. 17) : deux types, « (1) 0/1 filter, (2) weightage, which goes from 0-1 ». Les pondérations « reflect the relative importance given to different metrics and dimensions in different countries or companies ». **Métriques** : « domain-specific Key Performance Indicators (KPIs) under each dimension, which will be designed and reviewed by domain experts » (p. 17).

### a.2 Tableau de correspondance : dimensions de notre projet vers le rapport

Les libellés de notre projet viennent du brief. Je n'ai pas pu comparer leur contenu détaillé (métriques, rattachements) car je n'ai pas lu le projet.

| # | Dimension de notre projet | Dimension du rapport (page) | Correspondance | Remarque |
|---|---|---|---|---|
| 1 | Data/model marketplace | Dimension 1: Data/model Marketplace (p. 18) | Identique | Le FAQ 25 (p. 49-50) propose de renommer ; réponse : « Data is not a product but an asset » ; le rapport cite ITU-T Y.3176 pour la définition de « machine learning marketplace ». |
| 2 | Generated content marketplace | Dimension 2: Generated Content Marketplace (p. 19) | Identique (casse) | Définie comme écosystème de création de nouveaux datasets/modèles (p. 19), distincte de D1 (FAQ 2, p. 47). |
| 3 | Cross-domain correlation | Dimension 3: Cross-domain correlation analysis (p. 20) | Libellé proche | Ajouter « analysis ». |
| 4 | Contextualisation and regional impact | Dimension 4: Contextualization and Regional Impact (p. 21) | Identique (orthographe) | FAQ 3 (p. 47) : distinction avec Dimension 12. |
| 5 | Integration of AI in workflows | Dimension 5: Level of Integration of AI in Workflows (p. 22) | Libellé proche | Ajouter « Level of ». |
| 6 | Human interface | Dimension 6: Human Interface (p. 23) | Identique | — |
| 7 | Strategy alignment | Dimension 7: Strategy Alignment (p. 24) | Identique | Concept d'« intent distribution » en 6 étapes (p. 24). Attention : « intent » a ici un sens organisationnel, différent de « ML intent » de Y.3172. |
| 8 | Collaboration with AI | Dimension 8: Collaboration with AI (p. 25) | Identique | — |
| 9 | Impacts of humans in AI integration | Dimension 9: Impacts of Humans in AI Integration (p. 26) | Identique (casse) | — |
| 10 | AI and policies | Dimension 10: AI & Policies (p. 28) | Libellé proche | « & » vs « and ». |
| 11 | AI for inclusion | Dimension 11: AI for Inclusion (p. 29) | Identique (casse) | — |
| 12 | Granular priorities | Dimension 12: Granular Priorities (p. 32) | Identique | — |
| 13 | Digital infrastructure | Dimension 13: Digital Infrastructure (p. 33) | Identique | Le rapport a aussi un pilier « Digital Infrastructure » en Ch. 2 (p. 15) avec d'autres sous-indices. |

**Bilan** : 13 dimensions sur 13 correspondent par libellé. Les différences sont uniquement de casse, d'orthographe ou de mots ajoutés. **Différence de fond** : le rapport ne fixe pas de rattachement unique par dimension (plusieurs facteurs parfois), et Ch. 2 propose une autre répartition en 5 piliers, avec d'autres sous-indices. Cela doit être gardé en tête si notre projet utilise l'une ou l'autre hiérarchie.

### a.3 Exigences et recommandations sur les thèmes demandés

Toutes les citations sont [LU]. « REQ » = exigence de Ch. 5 ; l'exigence est formulée par « it is required that » sauf mention contraire.

**Knowledge records (format, forme)**
- p. 37 : « Users provide unstructured data ... The materials will be transformed into knowledge records using the standardized ITU AI Readiness record format. The knowledge records will be stored in the ITU AI Readiness Knowledge Base, which serves as the brain and the foundation of the toolkit. »
- REQ-024 (p. 41) : « the knowledge base uses a uniform/standard record format for the storage and processing of knowledge records. NOTE: knowledge records are a processed form of data inputs. An example of a knowledge record format is vectorized data records. »
- Ambiguïté : le format « standardized ITU AI Readiness record format » n'est **jamais défini** dans le rapport (aucun schéma, aucun champ). Il n'existe que la note « vectorized data records » comme exemple.
- REQ-023 (p. 41) : données structurées « machine-readable properties ».

**Vectorisation** : seule mention = l'exemple « vectorized data records » (REQ-024 NOTE, p. 41). Aucune exigence sur l'embedding, son modèle, ou la réversibilité. [SUPPOSÉ] : le rapport ne traite pas du fait qu'un vecteur peut conserver une part d'information de la source (donc de données privées). Ce point est à traiter par nous, non par le rapport.

**Bases de connaissances distribuées vs centrales** (tensions) :
- REQ-015 (p. 40) : « it is required that the knowledge base be hosted in the ITU AI4G Sandbox. » (KB centrale.)
- REQ-025 (p. 41) : « it is required that the knowledge base be distributed, and the consumers of the knowledge base select, process the knowledge records from the distributed knowledge base based on user preferences/priorities. »
- REQ-026 (p. 41) : « it is required that the toolkit be used locally, and data not be moved from the country of use. NOTE: knowledge base is updated in the ITU AI4G Sandbox with AI Readiness Record formats. »
- REQ-007 NOTE (p. 39) : « multiple instances of the toolkit can exist at the same time, being connected to the ITU AI4G Sandbox in parallel (for KB records transfer only). Since these instances do not transfer data between each other, there are no data privacy concerns between the users. »
- p. 43 (Ch. 6) : « Toolkit and models would be hosted locally using ITU standards-based Sandbox, providing a trusted and secure environment ... »
- **Tension** [LU + SUPPOSÉ] : le rapport décrit à la fois une KB **hébergée au centre** (REQ-015), une KB **distribuée** (REQ-025), un usage **local** sans transfert de données (REQ-026), et des instances qui **transfèrent des enregistrements de KB** vers la sandbox (REQ-007). Il ne dit pas : quelle copie fait autorité ; si un « knowledge record » (donnée transformée) est une donnée au sens de REQ-026 (le rapport lui-même dit qu'il est « a processed form of data inputs ») ; ni comment les records remontent à la KB centrale.

**Localisation / souveraineté des données / traitement local**
- REQ-026 (ci-dessus) : traitement local, « data not be moved from the country of use ».
- REQ-027 (p. 41) : « local rules be respected for data privacy and governance. NOTE: regular compliance reports would be produced for this by agents. »
- REQ-028 (p. 41) : « the only persistent records in the toolkit be knowledge base Records, and input materials be stored only temporarily during training and fine-tuning and be deleted immediately afterwards. »
- Metric p. 29 : « Data sovereignty metrics: policies related to ownership and movement of data. » (métrique, pas exigence).
- Pilote (p. 43) : « Pilot users would be chosen and encouraged to run the toolkit locally. »
- **Tension** : FAQ 16 (p. 48) : « Even if private data is used to train the model, it will only be stored in the knowledge base temporarily and will be deleted when the training is done. » Contradiction apparente avec REQ-028 (seuls les records persistent), puisque ici des données privées sont « stored in the knowledge base temporarily ».
- Tension : user story 1 (p. 38) : « The materials are handled in a trusted sandbox and analyzed by the ITU AI RE Toolkit. » Alors que REQ-026 demande le traitement local.

**Hébergement / sandbox**
- Notre projet et le rapport parlent d'un « ITU AI4G Sandbox » (REQ-015, REQ-016, p. 40) : c'est une plateforme nommée, pas un concept générique.
- Le mot « sandbox » recouvre au moins cinq sens dans le rapport : (i) le **facteur** « Sandbox Environments: Platforms for AI experimentation and validation » (p. 18) ; (ii) la **plateforme** ITU AI4G Sandbox (p. 40, 43) ; (iii) une « **trusted sandbox** » pour le traitement des entrées (p. 38) ; (iv) des « **vertical sandboxes** » de simulation de politiques (p. 29) ; (v) des **simulateurs** et « virtual sandbox for policy » (p. 28, FAQ 6 p. 46-47). Le rapport n'établit pas de lien avec ML sandbox de Y.3172 (voir partie b).
- REQ-016 (p. 40) : « it is recommended that the toolkit interface with the ITU AI4G Sandbox with input data or simulated data in the sandbox. » NOTE : usages = simuler des interventions réglementaires, évaluer des applications dans un cadre contrôlé, fournir des gap analyses et recommandations basées sur des scénarios.

**Interopérabilité**
- Standards factor (p. 18) : « Standards: Ensuring trust, interoperability, and compliance. »
- Dimension 5 (p. 22) : « A standardized interface to host the APIs will be needed. »
- Dimension 7 (p. 24-25) : « A standard template for tasks should be developed. »
- Index « Data Interoperability: Standard data formats » (p. 12). Métrique « Standards-compliant data formats » (p. 19). Le rapport ne nomme aucun format précis.
- FAQ 13 (p. 48-49) : « interoperability between existing platforms and the ITU AI-RE Toolkit can be realized using ITU standards. » Et : « The AI Readiness project itself does not provide or use platforms such as Hugging Face for data/model exchange. »

**Open data / open source**
- Factor Open data : « Accessibility and quality of datasets for analysis of AI applications » (p. 17) ; « public data, open for analysis by anyone, requires cleaning and anonymization to remove confidential or personal information » (p. 17).
- Factor Open source : « Enabling rapid adoption through an open developer ecosystem » (p. 18).
- Insight 9 (p. 9) : « Open-source technologies lower entry barriers for AI adoption worldwide. »
- Index « Open Datasets and models » (p. 12).
- Dimension 8 (p. 26) : « The collaboration may require both open-source and closed-source models. »
- Ch. 6 (p. 43) : « Open standards development processes, such as ITU, increase the trust among stakeholders ... » et « ITU AI Readiness Challenge ... to crowdsource solutions for building an open knowledge base » (p. 43).
- Pas d'exigence de licence ouverte pour les sorties du toolkit ; les licences apparaissent comme métrique (« license metrics (types of licenses) », p. 19).

**Gouvernance des données**
- Pilier Data : « Data Governance » (index, p. 12) ; « lack of data governance frameworks limits effective and trustworthy data use » (Insight 6, p. 9).
- Metric p. 19 : « Data governance metrics, such as: the percentage of datasets under partner agreements ... »
- REQ-010 (p. 39) : « verify 1) dataset metadata and provenance verification, 2) model training, tuning, versioning, and deployment lifecycle assessment, and 3) data privacy, security, and ethical compliance tracking consistent with international standards. »

**Provenance**
- REQ-010 (ci-dessus, p. 39) : « dataset metadata and provenance verification ».
- p. 15 : « Transparency mechanisms: disclosure of data provenance and labeling practices ».
- p. 28 : « new policies may be recommended, related to new sources of data: datasets, provenance of data, models, and risk assessment via Sandbox/Policy/SINK as per ITU-T Y.3172. » (Note : le rapport cite SINK comme sortie de Y.3172 ici.)

**Partage de modèles et de données**
- Dimension 1 (p. 18-19) : « The number of open datasets and downloads from the data marketplace » ; « Metrics and Properties of open-source models, such as openly published weights ».
- Dimension 1 : « Privacy and security — ... Authentication, Authorization mechanisms, and just-in-time deletion of private data. »
- Dimension 1 : « Data collection sources (location: home/enterprise/public ...) ».
- Standard mentionné : « Standards on personal data protection. » (p. 19).
- Pas d'exigence de partage fédéré de modèles dans le toolkit ; la seule mention est l'exigence de génération de modèle fine-tuné (REQ-005, p. 39).

**AI Lab** : absent (0 occurrence dans le rapport).

**Agents** : trois occurrences [LU] — REQ-027 NOTE (« regular compliance reports would be produced for this by agents », p. 41) ; p. 31 (« Use of agents for the user interface, e.g., question answers on the domain, such as navigation » ; l'agent est une métrique d'inclusion). Aucune définition ni contrôle des agents.

**Sandbox** : cf. ci-dessus et dimensions 9, 10, 11 (p. 27-31). Exigence explicite : REQ-016 (recommended), REQ-015 (required). Pour l'IA des politiques : « AI is used in the sandbox to provide implications of policy in the verticals » (FAQ 7, p. 47) ; « Feedback and advice on the policy, per se, are provided by domain experts ... Hence, the use of AI in policies is limited to validating the impact. » Ce point est un garde-fou explicite : humains pour les décisions.

**Garde-fous humains** [LU] : p. 29 « This includes accountability of final decisions, which remains with humans. » ; Dimension 9 (p. 26) « There are scenarios when AI decisions are referred back to domain experts to guarantee the accountability of the decision. »

### a.4 Chapitre « AI Readiness Gap Analysis » (Ch. 4, p. 35-36)

**Méthode** [LU] (p. 35) : approche « bottom-up » : analyse des cas d'usage, puis plugfests, puis consultation d'experts. Les 13 dimensions et métriques sont « derived from the plugfest project reports » après « several rounds of consultation with experts ». **Pas de calcul de gap quantitatif**. Le « gap » est une comparaison qualitative entre statu quo et cible.

**Trois catégories de lacunes** (p. 35-36) :
1. **Gaps in international standards** — exemples : « data harmonization, generative AI, and energy readiness for AI ». Sous-points : Data Readiness (qualité des datasets, pipeline de collecte/prétraitement multimodal, « discoverability, reusability, and customization of datasets »), GenAI Readiness (fine-tuning local, confiance), Energy AI Readiness (métriques énergétiques, « energy cost of data collection »).
2. **Gaps in implementations** — « some countries achieve high efficiency of AI technology, yet due to the lack of supporting infrastructure, suggestions and predictions provided by AI could not be transformed into effective applications » ; « lack of digitalized datasets and models » (p. 36).
3. **Gaps in policies** — « Approaches to framing AI policies, especially for cross-domain AI governance and policies for domain-specific integration of AI, differ between countries » ; besoin d'alignement entre ministères (p. 36).

**Réutilisable pour une typologie de lacunes** [SUPPOSÉ pour la formulation] : la triple typologie standards / mise en œuvre / politiques est simple et explicite, et chaque catégorie cite des exemples. Autres briques réutilisables : la notion de « compound gap » (REQ-012, p. 40 NOTE : « a combined or interconnected gap that arises when multiple dimensions interact ») ; la distinction « status quo / gap / recommandations » (Ch. 5, p. 37) ; et la possibilité de pondérer les gaps par indices (p. 37-38).

### a.5 Échelles et critères de maturité

- Le rapport demande de les évaluer : REQ-004 (p. 39) : « it is required that the maturity levels per dimension be evaluated. » **Aucune échelle n'est définie** dans le texte.
- Une mention « basic level of assessment, as defined in the levels, is the first level of adoption » (FAQ 24, p. 49) renvoie à des « levels » non définis.
- Trois niveaux de compétences IA sont donnés comme **exemple d'indice** (p. 38) : « AI literacy level » (basique) ; « Specialized AI skills » (intermédiaire) ; « Workforce upskilling » (le plus haut). Ce ne sont pas des niveaux de maturité d'une dimension.
- Agrégation : REQ-021 (p. 40) : « composite scoring is calculated by aggregating weighted metrics within each dimension. » Pas de formule.
- Pondération : indices 0/1 ou 0-1 (p. 17, p. 37). Pour un classement fondé sur les pondérations, le rapport exige : « (1) publishing the weightages in a policy paper, (2) results from the baseline foundational model » (p. 37-38).
- Le rapport n'a donc **pas** d'échelle de maturité ni de scoring figé. Tout score de maturité devra être conçu par nous.

---

## Partie (b) : Recommandation ITU-T Y.3172 (06/2019), « Architectural framework for machine learning in future networks including IMT-2020 », 34 p.

### b.0 Caractère normatif [LU]

- « Compliance with this Recommendation is voluntary. However, the Recommendation may contain certain mandatory provisions ... » (p. ii).
- Mots-clés normatifs : « is required to » (obligatoire), « is recommended » (recommandé), « can optionally » (optionnel) ; « shall/should/may » sont à interpréter de la même façon, sauf dans les annexes (p. 3).
- Appendix I et II : « does not form an integral part of this Recommendation » (informatif).
- Mots-clés listés : « Architectural framework, high-level architecture, IMT-2020, intent, machine learning, ML, orchestrator, overlay, pipeline, requirements, sandbox, training, underlay » (p. i).

### b.1 Définitions (clause 3.2) [LU]

- 3.2.2 **machine learning function orchestrator (MLFO)** : « A logical node with functionalities that manage and orchestrate the nodes in a machine learning pipeline. » (p. 2)
- 3.2.3 **machine learning model** : modèle issu de l'apprentissage, utilisable pour des prédictions sur de nouvelles données. (p. 2)
- 3.2.4 **machine learning overlay** : « A loosely coupled deployment model of machine learning functionalities whose integration and management with network functions are standardised. » (p. 2)
- 3.2.5 **machine learning pipeline** : « A set of logical nodes, each with specific functionalities, that can be combined to form a machine learning application in a telecommunication network. » (p. 2)
- 3.2.6 **machine learning sandbox** : « An environment in which machine learning models can be trained, tested and their effects on the network evaluated. » NOTE : « designed to prevent a machine learning application from affecting the network, or to restrict the usage of certain machine learning functionalities. » (p. 2)
- 3.2.7 **machine learning underlay network** : réseau de télécommunication (ex. IMT-2020) interfacé avec des overlays ML. (p. 2)

Note : **« ML intent » n'est pas défini en clause 3**.

### b.2 Nœuds et composants : définitions et présence [LU]

Clause 8.1 « High-level architectural components » (p. 14-16) et Figure 3 (p. 14). Figure 3 légende : « PP : Pre-producer » (coquille dans la figure ; le texte dit « PP (preprocessor) »).

- **SRC (source)** (8.1, item 1) : « This node is the source of data that can be used as input to the ML pipeline. » NOTE 2 : UE, SMF, AF.
- **C (collector)** : « This node is responsible for collecting data from one or more SRC nodes. » NOTE 3 : peut configurer les SRC (RRC pour UE ; OAM vendeur pour SMF).
- **PP (preprocessor)** : « This node is responsible for cleaning data, aggregating data or performing any other preprocessing needed for the data to be in a suitable form so that the ML model can consume it. »
- **M (model)** : « This is a machine learning model, in a form which is usable in a machine learning pipeline. » NOTE 4 : ex. algorithme ML implémenté comme NF.
- **P (policy)** : « This node enables the application of policies to the output of the model node. » NOTE 5 : « Specific rules can be put in place by a network operator to safeguard the sanity of the network, e.g., major upgrades may be done only at night time or when data traffic in the network is low. »
- **D (distributor)** : « This node is responsible for identifying the SINK(s) and distributing the output of the M node to the corresponding SINK nodes. » NOTE 6 : peut configurer les SINK (RRC pour UE).
- **SINK** : « This node is the target of the ML output on which it takes action. » NOTE 7 : ex. UE qui ajuste la périodicité de mesure.
- **Service egress / ingress points** (NOTE 8 ; symbole Figure 2, p. 4) : egress = rôle producteur ; ingress = rôle consommateur.
- Incohérence [LU] : le texte 8.3 (p. 19) décrit la chaîne « collector → preprocessor → model → policy → SINK » **sans D** ; D n'apparaît que dans 8.1 et les figures.

**MLFO** (8.1, item 2, p. 15) : « a logical node with functionalities that manage and orchestrate the nodes of ML pipelines based on ML Intent and/or dynamic network conditions. » NOTE 9 : « selects and reselects the ML model based on, e.g., its performance. » NOTE 10 : placement responsibility. NOTE 11 : chaining. **Dans les clauses 7.x** le mot « MLFO » n'apparaît pas : les exigences parlent d'« orchestration functionality » (REQ-ML-MNG-004, p. 13) ou de « management and orchestration functions » (REQ-ML-DEP-003, p. 8). Le lien est fait par Table II.1 (p. 23).

**ML sandbox** (8.1, item 3, p. 15) : « An ML sandbox is an isolated domain which allows the hosting of separate ML pipelines to train, test and evaluate them before deploying them in a live network. For training or testing, the ML sandbox can use data generated from simulated ML underlay networks and/or live networks. » NOTE 13 : supervised ML pour entraîner les modèles dans la sandbox.

**ML intent** (NOTE 12 sous MLFO, p. 16) : « Figure 4 includes ML Intent to emphasise its important role as input to the MLFO. ML Intent is a declarative description which is used to specify an ML application. ML Intent does not specify any technology-specific network functions to be used in the ML application and provides a basis for mapping ML applications to diverse technology-specific network functions. ML Intent may use a metalanguage specific for machine learning to define ML applications. »

### b.3 Présence des nœuds et composants attribués à Y.3172 (tableau demandé)

| Nœud / composant (notre projet) | Présent dans le texte ? | Où (clause / page) | Remarque |
|---|---|---|---|
| SRC (source) | Oui, défini | 8.1 item 1 (p. 14-15) ; Fig. 3 ; Fig. 4 | Défini comme source de données ; instancié sur UE, SMF, AF (NOTE 2). |
| C (collector) | Oui, défini | 8.1 item 1 (p. 14) ; NOTE 3 | Collecte depuis SRC ; peut configurer SRC. |
| PP (preprocessor) | Oui, défini | 8.1 item 1 (p. 15) ; abréviations (p. 3) | Figure 3 écrit « Pre-producer » (coquille). |
| M (model) | Oui, défini | 8.1 item 1 (p. 15) ; abréviations (p. 3) | Le terme générique « machine learning model » est en 3.2.3 (p. 2). |
| P (policy) | Oui, défini | 8.1 item 1 (p. 15) ; NOTE 5 | Exemple de règle opérateur (heures creuses). |
| D (distributor) | Oui, défini | 8.1 item 1 (p. 15) ; NOTE 6 ; Fig. 3 | Absent de la chaîne de 8.3 (p. 19). |
| SINK | Oui, défini | 8.1 item 1 (p. 15) ; NOTE 7 | Cible de la sortie ML. |
| MLFO | Oui, défini | 3.2.2 (p. 2) ; 8.1 item 2 (p. 15) ; 8.2 (p. 17-19) ; Table II.1 (p. 23) | Absent des exigences de clause 7 (qui parlent d'« orchestration functionality »). |
| ML sandbox | Oui, défini | 3.2.6 (p. 2) ; 8.1 item 3 (p. 15) ; 8.2 « ML sandbox subsystem » (p. 18-19) ; 8.3 (p. 19) ; Table II.1 (p. 23) | Le mot « sandbox » n'apparaît pas dans les exigences de clause 7 ; « isolated environment » apparaît en REQ-ML-DEP-002 NOTE 1 et REQ-ML-MNG-004. |
| ML intent | Oui, mais **non défini en clause 3** | NOTE 12 sous 8.1 item 2 (p. 15) ; 8.2 (p. 17, 18) ; 8.3 (p. 19) ; App. I (p. 22) ; Table II.1 (p. 24) | Absent des exigences de clause 7 (qui parlent de « declarative specification »). Le mot « intent » apparaît en clause 3 seulement dans l'expression « no normative intent » (p. 3, hors sens). |

Autres termes rencontrés dans Y.3172 (non demandés mais utiles) : ML pipeline (3.2.5), ML overlay (3.2.4), ML underlay network (3.2.7), data handling reference points (8.1), SBA (8.1, « may be used »).

Termes du rapport AI Readiness et leur présence dans Y.3172 [LU] : « knowledge record », « vectoriz », « AI Lab », « agent », « provenance », « explain », « privacy », « audit » (une seule occurrence : « network security auditing » dans l'introduction, p. 4), « trace », « record » : **absents** de Y.3172.

### b.4 Points de référence et interfaces [LU]

- **Figure 4** (p. 17), lu sur image : 1, 2 = points de référence de traitement des données entre réseaux sous-jacents simulés et pipeline ML en sandbox ; 3 = sandbox ↔ pipeline ML ; 4 = pipeline ML ↔ réseaux sous-jacents ML ; 5, 6 = management ↔ pipeline ML et management ↔ sandbox ; 7 = MLFO ↔ autres fonctions M&O (ex. Y.3111) ; 8, 9 = points de référence entre nœuds de pipeline situés à des niveaux différents. Dans la figure, le « ML intent » alimente le MLFO, qui est dans le « Management subsystem ».
- Trois sous-systèmes (8.2) : management subsystem (MLFO + M&O) ; ML pipeline subsystem ; ML sandbox subsystem.
- SBA ([b-ETSI TS 129 500]) : « may be used » (8.1, p. 15-16 ; 8.2 NOTE 3). Figure 3 : les « Service ingress/egress points » sont des points de service, pas des points de référence normatifs.
- Points de référence de traitement des données : « Using these reference points, any impact to the ML underlay networks is localised to the source of data and target of configurations » (8.1, p. 16).
- Exigences d'interface : REQ-ML-DEP-001 (recommended, « Well-defined reference points ... are required », p. 7) ; REQ-ML-INT-003 (recommended ; a) protocoles standards existants ; b) interfaces/API spécifiques aux NF ; c) interfaces logiques entre fonctions ML multi-niveaux) (p. 9-10).

### b.5 Exigences (clause 7) [LU]

Tableau des exigences avec le type de conformité (tel que l'exigence est formulée dans le texte) :

| ID | Type | Contenu (résumé fidèle) | Page |
|---|---|---|---|
| REQ-ML-COR-001 | recommended | Correler les données de sources multiples | 5 |
| REQ-ML-COR-002 a) | required | Supporter plusieurs technologies (IMT-2020) | 6 |
| REQ-ML-COR-002 b) | recommended | Interfacer avec des entités externes non IMT-2020 | 6 |
| REQ-ML-COR-003 | required | Instanciation distribuée à plusieurs niveaux | 6 |
| REQ-ML-DEP-001 | recommended | Définir les points d'interaction ML / NF sous-jacentes (description : « Well-defined reference points ... are required ») | 7 |
| REQ-ML-DEP-002 | required | Déploiement divisé ou combiné entre NF sous-jacentes ; NOTE 1 : entraînement GPU dans un environnement isolé | 7 |
| REQ-ML-DEP-003 | required (texte : « should provide the ability ») | Placement flexible des fonctions ML, coordonné avec M&O | 8 |
| REQ-ML-DEP-004 | required | Ajouter/retirer sources de données ou cibles de configuration à chaud | 8 |
| REQ-ML-INT-001 | recommended | Transfert de modèles entraînés entre niveaux | 9 |
| REQ-ML-INT-002 | required | Transfert de données pour entraînement ou test entre niveaux | 9 |
| REQ-ML-INT-003 | recommended | Interfaces standards, API spécifiques, interfaces logiques | 9-10 |
| REQ-ML-INT-004 | recommended | Partage de données entre fonctions ML via « distributed data sharing mechanisms » | 10 |
| REQ-ML-SPEC-001 | required | Représentation standard des applications ML, traduisible en fonctions ML | 10 |
| REQ-ML-SPEC-002 | required | Spécifier sources de données, dépôts de modèles, cibles de sortie, contraintes ressources et délais | 10 |
| REQ-ML-SPEC-003 | required | Split flexible selon les spécifications | 11 |
| REQ-ML-SPEC-004 | required | Spécification par des tiers (sources, dépôts de modèles, cibles, contraintes) | 11 |
| REQ-ML-MNG-001 | required | Sélection de modèle au set-up ; sélection dynamique pour nouvelles sources | 12 |
| REQ-ML-MNG-002 | required | Entraînement et mise à jour de modèles sans impact réseau | 12 |
| REQ-ML-MNG-003 | required | Surveiller l'effet du ML sur le réseau ; mettre à jour modèles et/ou politiques sans impact | 12 |
| REQ-ML-MNG-004 | required | Fonction d'orchestration pour gérer toutes les fonctions ML ; reconfiguration si seuil de performance franchi ; comparaison en environnement isolé | 13 |
| REQ-ML-MNG-005 | required | Chaînage flexible multi-niveaux | 13 |

Notes : la conformité repose sur le texte « is required to » (5 et suivants) ; les formulations internes peuvent diverger (ex. DEP-001, DEP-003). Les exigences sont décrites à l'aide de « NOTE » qui sont informatives.

### b.6 Sécurité, traçabilité, politiques (utile pour notre journal d'audit et nos garde-fous) [LU]

Clause 9 (p. 19-20) : c'est le seul paragraphe de sécurité, sans identifiant d'exigence : « It is required to prevent from unauthorized access to, and data leaking from, an ML pipeline, whether or not they have a malicious intention, with implementation of mechanisms regarding authentication and authorization, external attack protection, etc. » Et : les exigences générales de sécurité IP-based networks « should be applied [ITU-T Y.2701] [ITU-T Y.3101] ».

Éléments utilisables comme garde-fous :
- **Isolation** : définition de la sandbox « designed to prevent a machine learning application from affecting the network » (3.2.6) ; « isolated environment » pour entraînement GPU (REQ-DEP-002 NOTE 1) et comparaison des modèles (REQ-MNG-004).
- **Gate de politique** : nœud P qui applique des règles opérateur à la sortie du modèle avant SINK (8.1 ; NOTE 5 : « major upgrades may be done only at night time or when data traffic in the network is low »). REQ-DEP-001 NOTE 1 : « Such application of ML output may be controlled by network operator policies. »
- **Surveillance et reconfiguration** : REQ-MNG-003 (surveiller l'effet, mise à jour sans impact) ; REQ-MNG-004 (seuil de performance → reconfiguration ; sélection selon « internal policies »).
- **Spécification déclarative = traçabilité d'intention** : REQ-SPEC-001/002 ; NOTE 12 (ML intent décrit l'application sans fonctions techniques). Une trace du ML intent et de sa traduction par le MLFO serait cohérente avec ce modèle, mais Y.3172 ne l'impose pas.
- **Chaînage déclaré** : NOTE 11 (chaîne déclarée dans la spécification d'application, implémentée par le MLFO).
- **Interfaces contrôlées** : service egress/ingress points (NOTE 8) ; SBA (optionnelle).
- **Tiers** : REQ-ML-SPEC-004 (spécification par des tiers) : pas de contrôle de droit décrit.

**Absences notables** [LU] : pas d'exigence d'audit log, de trace, d'enregistrement des décisions, de versionnage des modèles (la seule occurrence de « version » est dans la bibliographie), de provenance des données, d'explicabilité, de chiffrement, de vie privée/consentement, de conservation/suppression des données, ni d'intervention humaine. Le rapport AI Readiness a ces sujets (REQ-010 provenance et versionnage ; REQ-028 suppression des inputs) mais ne les tire pas de Y.3172.

---

## Synthèse des points d'attention pour le projet

1. **Nommage** : le mot « intent » a deux sens. Dans AI Readiness (Dimension 7), c'est une intention organisationnelle décomposée en sous-intentions (p. 24). Dans Y.3172, c'est une description déclarative d'une application ML (NOTE 12, p. 16). À distinguer dans notre documentation.
2. **Y.3172 n'est pas une source pour les « knowledge records », la vectorisation, les agents, l'AI Lab ou la provenance.** Ces concepts viennent du rapport AI Readiness.
3. **Local vs distribué** : le rapport lui-même est contradictoire (REQ-015, REQ-025, REQ-026, REQ-007, FAQ 16, p. 43). Ne pas le citer comme une règle unique.
4. **Format des records** : non défini dans le rapport. La seule piste est « vectorized data records » (REQ-024 NOTE).
5. **Pas d'échelle de maturité** dans le rapport (REQ-004 seulement). Le scoring est aussi non spécifié (REQ-021).
6. **Dimension 9** : le rattachement à Sandbox est hypothétique (« could be mapped ») ; ne pas l'affirmer comme acquis.
7. **Figure I.1 et Figure 4** sont des figures ; les rendus PNG sont dans le scratchpad (`figB_p23-23.png`, `figB_p27-27.png`, `figB_p20-20.png`).

## Fichiers

- Texte extrait AI Readiness : `/tmp/claude-1000/-home-rtti-Documents-Github-ALERTE-for-ITUAIReadiness/47bfe664-a298-43d9-bfe6-a48c60d63119/scratchpad/a_ai_ready.txt`
- Texte extrait Y.3172 : `/tmp/claude-1000/-home-rtti-Documents-Github-ALERTE-for-ITUAIReadiness/47bfe664-a298-43d9-bfe6-a48c60d63119/scratchpad/b_y3172.txt`
- Figures Y.3172 (PNG) : `/tmp/claude-1000/-home-rtti-Documents-Github-ALERTE-for-ITUAIReadiness/47bfe664-a298-43d9-bfe6-a48c60d63119/scratchpad/figB_p20-20.png`, `.../figB_p23-23.png`, `.../figB_p27-27.png`
