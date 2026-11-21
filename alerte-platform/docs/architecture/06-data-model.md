# 06 — Modèle de données (ERD)

> SQLAlchemy 2.0, SQLite. Clés primaires : **UUID v7 ou ULID** en texte (triables, non devinables), plus un `code` lisible par humain là où l'interface l'affiche. Toutes les tables portent `created_at` (UTC) ; les tables mutables portent `updated_at`. `workspace_id` est présent (dénormalisé) sur toute table de premier niveau pour le filtrage d'isolation ; **aucune requête de service ne peut omettre le filtre d'espace** (dépendance FastAPI `current_workspace` + test canari FR-01). Les dates sont ISO 8601 UTC ; les JSON sont validés par des modèles Pydantic à l'écriture.

## 6.1 Espaces de travail, pays, institutions, mandats

```mermaid
erDiagram
  WORKSPACE ||--o{ COUNTRY : has
  WORKSPACE ||--o{ INSTITUTION : has
  COUNTRY ||--o{ INSTITUTION : hosts
  WORKSPACE ||--o{ ACCESS_TOKEN : issues
  WORKSPACE ||--o{ ACTION_ITEM : defines
  INSTITUTION ||--o{ MANDATE : holds
  MANDATE ||--o{ MANDATE_SOURCE : "cites"
  MANDATE }o--o| MANDATE : "depends_on / conflicts_with"
  ACTION_ITEM ||--o{ MANDATE : "concerns"
  INSTITUTION ||--o| REGISTRY_REVIEW : "coverage"

  WORKSPACE {
    text id PK
    text name
    text slug
    datetime archived_at
  }
  ACCESS_TOKEN {
    text id PK
    text workspace_id FK
    text role
    text label
    text token_hash
    text exercise_id
    text seat_id
    datetime expires_at
    datetime revoked_at
  }
  COUNTRY {
    text id PK
    text workspace_id FK
    text iso2
    text name
    json languages
    text notes
    datetime archived_at
  }
  INSTITUTION {
    text id PK
    text workspace_id FK
    text country_id FK
    text code
    text name
    text name_local
    text kind
    json domains
    text description
    datetime archived_at
  }
  ACTION_ITEM {
    text id PK
    text workspace_id FK
    text code
    text label
    text domain
    text derivation
    text reference_note
  }
  MANDATE {
    text id PK
    text workspace_id FK
    text institution_id FK
    text action_id FK
    text kind
    text description
    text procedure_status
    bool has_deadline
    text dependency_text
    text depends_on_id FK
    text conflicts_with_id FK
    text evidence_tag
    text validation
    text origin
    text created_by
  }
  MANDATE_SOURCE {
    text id PK
    text mandate_id FK
    text document_version_id FK
    text chunk_id FK
    text article
    int page
    text quote
    text quote_sha256
  }
  REGISTRY_REVIEW {
    text id PK
    text institution_id FK
    text status
    text reviewer
    text note
    datetime reviewed_at
  }
```

| Table | Remarques |
|---|---|
| `access_token` | Rôles : `owner`, `facilitator`, `player` (lié à un `seat_id`), `observer`, `auditor`. Seul le **hash** du jeton est stocké. Jetons de siège/observateur liés à un exercice ; expiration et révocation. |
| `institution.kind` | `ministry \| agency \| regulator \| operator \| local_authority \| ai_system \| advisory \| other` ; `ai_system` désigne le système IA testé (comportement scénarisé). |
| `action_item` | Catalogue d'actions (« ce que la situation exige », ex. « valider une prévision IA avant diffusion »). `derivation` ∈ `referential \| scenario_author \| agent_proposed` ; `reference_note` cite le référentiel externe (Sendai, checklist ITU, etc.). Règle d'intégrité : une action dont `derivation = scenario_author` est signalée dans le rapport. |
| `mandate.kind` | `power \| duty \| lead \| coordination \| information_sharing \| procedure \| human_oversight \| liability \| inclusion \| channel_protection \| international_agreement \| prohibition`. Les règles G1–G10 testent la **présence ou l'absence** d'un mandat d'un `kind` donné pour une action ou un domaine (doc 09). |
| `mandate.validation` | `proposed \| validated \| rejected` ; seules les lignes `validated` comptent comme preuve **documentée** ; `proposed` donne une preuve de confiance moindre. |
| `mandate_source` | Un mandat actif **doit** pointer vers un chunk réel (test CI). Un mandat est *actif dans un exercice* si la version de document de sa source figure dans le snapshot (c'est ce qui rend le test contrefactuel possible). |
| `registry_review` | Par institution : `unreviewed \| partial \| reviewed_complete`. Sans `reviewed_complete`, une absence de mandat produit une lacune d'`evidence_basis=inferred`, pas `documented` (doc 09 §9.3). |

## 6.2 Bases de connaissances

```mermaid
erDiagram
  WORKSPACE ||--o{ KNOWLEDGE_BASE : owns
  COUNTRY ||--o{ KNOWLEDGE_BASE : "concerns"
  KNOWLEDGE_BASE ||--o{ DOCUMENT : contains
  KNOWLEDGE_BASE ||--o{ KB_EXPECTED_DOCUMENT : "expects (coverage)"
  DOCUMENT ||--o{ DOCUMENT_VERSION : "versions (append-only)"
  DOCUMENT_VERSION ||--o{ CHUNK : "split into"
  CHUNK ||--o| CHUNK_VECTOR : embeds
  KNOWLEDGE_BASE ||--o{ KB_VERSION : publishes
  KB_VERSION ||--o{ KB_VERSION_ITEM : lists
  DOCUMENT_VERSION ||--o{ KB_VERSION_ITEM : "included in"
  KNOWLEDGE_BASE ||--o{ KB_EXPORT : "exported as"
  DOCUMENT_VERSION }o--|| BLOB : "original file"
  JOB ||--o{ KB_EXPORT : produces

  KNOWLEDGE_BASE {
    text id PK
    text workspace_id FK
    text country_id FK
    text code
    text name
    text description
    text domain
    text kind
    json languages
    text embedding_model
    json chunking_params
    text status
    datetime archived_at
  }
  DOCUMENT {
    text id PK
    text kb_id FK
    text code
    text title
    text doc_type
    text doc_number
    date doc_date
    text jurisdiction
    text language
    text source_url
    text reliability
    text validity
    text replaced_by_id FK
    text license_spdx
    text redistribution
    text evidence_default
    date accessed_at
    text current_version_id FK
  }
  DOCUMENT_VERSION {
    text id PK
    text document_id FK
    int version_no
    text blob_sha256 FK
    text mime
    int bytes
    text extraction_method
    real extraction_quality
    json pages_to_review
    text status
    text supersedes_id FK
    text note
  }
  CHUNK {
    text id PK
    text document_version_id FK
    text kb_id
    text doc_title
    int ordinal
    int page_start
    int page_end
    text article
    text section
    text language
    text text
    text text_sha256
    int char_start
    int char_end
    text evidence_tag
    json topics
  }
  CHUNK_VECTOR {
    text chunk_id PK
    text model
    int dim
    blob vector
  }
  KB_VERSION {
    text id PK
    text kb_id FK
    int version_no
    text note
    text manifest_sha256
  }
  KB_VERSION_ITEM {
    text kb_version_id FK
    text document_version_id FK
  }
  KB_EXPECTED_DOCUMENT {
    text id PK
    text kb_id FK
    text title
    text jurisdiction
    text citation
    text status
    text matched_document_id FK
  }
  KB_EXPORT {
    text id PK
    text kb_id FK
    text kb_version_id FK
    text mode
    json options
    text job_id FK
    text blob_sha256
    text status
  }
  BLOB {
    text sha256 PK
    int bytes
    text mime
    text path
  }
  JOB {
    text id PK
    text workspace_id
    text kind
    text status
    real progress
    json payload
    json result
    text error
  }
```

| Point | Détail |
|---|---|
| **Ajout seul** | Un document modifié = nouvelle `document_version` (l'ancienne reste, `supersedes_id`). Supprimer un document marque la version `retired` ; les chunks sont conservés tant qu'une `kb_version` publiée ou un exercice les référence. |
| `knowledge_base.kind` | `national \| global_practices \| scenario \| prior_reports \| mixed`. `global_practices` alimente les précédents ; `prior_reports` héberge les rapports de lacunes importés (doc 09). |
| `document.reliability` | `official \| summary \| unofficial \| not_found` ; `validity` : `in_force \| replaced \| unknown` (+ `replaced_by_id`) — D-07. |
| `document.redistribution` | `allowed \| restricted \| unknown` + `license_spdx` (ou `LicenseRef-…`). Défaut `unknown` ; l'export « ouvert » exclut `restricted` et `unknown`. |
| `chunk.kb_id` | Dénormalisé : sert au pré-filtrage de sécurité dans les requêtes FTS/vecteurs. |
| Index FTS5 | Table virtuelle `chunk_fts(text, doc_title, article, content='chunk')` (`doc_title` dénormalisé dans `chunk`) + colonnes non indexées (`kb_id`, `document_version_id`). Création par SQL brut (non gérée par l'ORM) ; reconstruction = job `reindex`. |
| `kb_version` | Publier = figer l'ensemble des `document_version_id` ; `manifest_sha256` = empreinte canonique de l'ensemble (identité de la version). |
| `blob` | Stockage adressé par contenu (`/data/blobs/ab/abcdef….bin`) : originaux, archives, rapports, prompts et réponses LLM. |

## 6.3 Agents, scénarios, exercices, ledger

```mermaid
erDiagram
  WORKSPACE ||--o{ MODEL_PROFILE : configures
  INSTITUTION ||--o{ AGENT : "represented by"
  MODEL_PROFILE ||--o{ AGENT : uses
  AGENT ||--o{ AGENT_KB_GRANT : "may read"
  KNOWLEDGE_BASE ||--o{ AGENT_KB_GRANT : "readable by"
  WORKSPACE ||--o{ SCENARIO : defines
  SCENARIO ||--o{ INJECT : sequences
  INJECT ||--o{ INJECT_DEMAND : requires
  ACTION_ITEM ||--o{ INJECT_DEMAND : "is demanded"
  INJECT ||--o{ INJECT_RECIPIENT : "delivered to"
  INSTITUTION ||--o{ INJECT_RECIPIENT : receives
  SCENARIO ||--o{ EVAL_FIXTURE : "hidden ground truth"
  SCENARIO ||--o{ EXERCISE : "run as"
  EXERCISE ||--|| EXERCISE_SNAPSHOT : "frozen by"
  EXERCISE ||--o{ SEAT : has
  SEAT ||--o{ SEAT_ASSIGNMENT : "history"
  EXERCISE ||--o{ STEP : "idempotent steps"
  EXERCISE ||--o{ COMMAND : "facilitator commands"
  EXERCISE ||--o{ LEDGER_EVENT : "append-only"
  EXERCISE ||--o{ LEDGER_ANCHOR : "head checkpoints"
  EXERCISE ||--o{ BOARD_MESSAGE : holds
  SEAT ||--o{ INBOX_ITEM : receives
  SEAT ||--o{ DECISION : records
  DECISION ||--o{ DECISION_CITATION : cites
  SEAT ||--o{ HUMAN_TASK : "awaits"
  EXERCISE ||--o{ RETRIEVAL : logs

  MODEL_PROFILE {
    text id PK
    text workspace_id FK
    text name
    text provider
    text base_url_env
    text model
    real temperature
    int max_tokens
    int timeout_s
    json extra
  }
  AGENT {
    text id PK
    text workspace_id FK
    text institution_id FK
    text code
    text name
    text role_kind
    text mission
    text instructions
    text model_profile_id FK
    json tools
    json limits
    datetime archived_at
  }
  AGENT_KB_GRANT {
    text agent_id FK
    text kb_id FK
    text mode
  }
  SCENARIO {
    text id PK
    text workspace_id FK
    text country_id FK
    text code
    text title
    text description
    text language
    int version
    text status
  }
  INJECT {
    text id PK
    text scenario_id FK
    int seq
    text sim_time
    text title
    text body
    text from_actor
    json tags
    text fault_mode
    json system_output
    text source_note
  }
  INJECT_DEMAND {
    text id PK
    text inject_id FK
    text action_id FK
    text note
  }
  INJECT_RECIPIENT {
    text inject_id FK
    text institution_id FK
  }
  EVAL_FIXTURE {
    text id PK
    text scenario_id FK
    text expected_gap_key
    text rationale
    text sealed_sha256
  }
  EXERCISE {
    text id PK
    text workspace_id FK
    text scenario_id FK
    text parent_exercise_id FK
    text code
    text title
    text state
    text pace
    json settings
    datetime started_at
    datetime ended_at
    text snapshot_sha256
    text commitment_sha256
  }
  EXERCISE_SNAPSHOT {
    text exercise_id PK
    json payload
    text payload_sha256
    json document_version_ids
  }
  SEAT {
    text id PK
    text exercise_id FK
    text code
    text institution_ref
    text agent_snapshot_key
    text controller
    text human_name
  }
  SEAT_ASSIGNMENT {
    text id PK
    text seat_id FK
    text controller
    text human_name
    text reason
    text by_actor
  }
  STEP {
    text id PK
    text exercise_id FK
    text step_key
    text kind
    text status
    datetime started_at
    datetime finished_at
  }
  COMMAND {
    text id PK
    text exercise_id FK
    text kind
    json args
    text status
    text issued_by
  }
  LEDGER_EVENT {
    text id PK
    text exercise_id FK
    int seq
    text type
    text actor
    text seat_id
    text sim_time
    datetime real_time
    text visibility
    json payload
    text prev_hash
    text hash
  }
  LEDGER_ANCHOR {
    text id PK
    text exercise_id FK
    int seq
    text hash
    text kind
    text signature
    datetime created_at
  }
  BOARD_MESSAGE {
    text id PK
    text exercise_id FK
    text inject_id
    int round
    text from_seat FK
    text to_seat FK
    text msg_type
    text body
    text in_reply_to FK
    text reply_status
    int ledger_seq
  }
  INBOX_ITEM {
    text id PK
    text exercise_id FK
    text seat_id FK
    text source
    text ref_id
    int delivered_seq
    bool read
  }
  DECISION {
    text id PK
    text exercise_id FK
    text seat_id FK
    text inject_id
    int round
    text action
    text action_code
    text outcome
    text confidence
    json options_considered
    json gap_flags
    text rationale
    text evidence_tag
    text author
    text status
    int ledger_seq
  }
  DECISION_CITATION {
    text id PK
    text decision_id FK
    text chunk_id
    text document_version_id
    text article
    text quote
    text check_status
    text check_reason
  }
  HUMAN_TASK {
    text id PK
    text exercise_id FK
    text seat_id FK
    text inject_id
    int round
    text status
    datetime deadline_at
    text fallback
  }
  RETRIEVAL {
    text id PK
    text exercise_id FK
    text seat_id FK
    text query
    text scope_hash
    json results
    int ledger_seq
  }
```

| Point | Détail |
|---|---|
| `agent.role_kind` | `institution \| ai_system \| legal_adviser` (le coordinateur n'est **pas** un agent : c'est du code, FR-32). `ai_system` est joué par `system_output` des injects (comportement scénarisé du système IA testé). |
| `agent.tools` | Sous-ensemble de `search_kb, ask_legal, post, decide` ; `limits` : `max_steps` (défaut 4), `max_legal_calls_per_inject` (défaut 2), `max_search_calls` (défaut 3). |
| `agent_kb_grant` | **Seule** source de droits de lecture. Copiée dans le snapshot au lancement. `mode=read` (seul mode au MVP). Le conseiller juridique reçoit par défaut toutes les KB de l'exercice (configurable). |
| `inject.fault_mode` | Panne injectée : `none \| over_trust \| silent_institution \| misinformation \| llm_outage \| …` (12 « failure modes » de la Spec L275-290 comme catalogue extensible). |
| `inject.tags` | Étiquettes normalisées lues par les règles : `life_risk, rights_risk, harm_possible, ai_output_used_in_decision, public_communication, channel_abuse, foreign_actor, time_critical, …`. |
| `eval_fixture` | `expected_gap_key` est calculée **comme `gap.fingerprint`** (code · action · institutions · domaine) pour permettre l'appariement. **Table isolée** (sous-module `evaluation`), jamais lue par `gaps`, `agents` ni `simulation`. `sealed_sha256` = empreinte horodatée de la fixture, consignée avant les runs (doc 09 §9.9). |
| `exercise_snapshot.payload` | JSON canonique de : pays, institutions, agents (copie), profils de modèle (sans secrets), droits agent→KB, scénario et injects, actions, mandats **validés** actifs, paramètres, `document_version_ids`. Son SHA-256 est inscrit dans le premier événement du ledger. |
| `seat.controller` | `agent \| human \| scripted` ; historique complet dans `seat_assignment` (événement `SEAT` au ledger). |
| `step` | Clé unique `inject:{n}:round:{r}:seat:{code}` etc. : une étape terminée est sautée à la reprise (idempotence, BP-14). |
| `command` | Commandes de l'animateur (`start, pause, resume, step, speed, stop, surprise, seat_switch, correction`) consommées par l'exécuteur entre deux étapes. |
| `ledger_event` | `UNIQUE(exercise_id, seq)`. `visibility` : `public \| board \| seat \| audit` (+ `seat_id` pour `seat`). Les prompts et réponses LLM complets sont dans `blob` ; le ledger porte `prompt_sha256`, `response_sha256` (voir doc 10). |
| `board_message.reply_status` | `accepted \| refused \| not_our_role \| null` quand le message répond à un REQUEST (D-31). |
| `decision.status` | `recorded \| not_verified \| not_recorded` : `not_verified` = citations échouées après relance (visible, rouge) ; `not_recorded` = JSON invalide deux fois (une entrée ERROR l'accompagne). Jamais de disparition silencieuse. |
| `decision.outcome` | `act \| decline \| refer \| no_legal_basis_found` (nul si `status=not_recorded`). `author` ∈ `agent \| human \| fallback`. `legal_basis` n'est pas une colonne : il est **reconstruit** depuis `decision_citation`. |
| `decision_citation.check_status` | `pass \| fail` + `check_reason` (chunk absent, hors droits, hors retrieval de l'activation, article incohérent, citation introuvable dans le texte). |

## 6.4 Lacunes, références, rapports, évaluation

```mermaid
erDiagram
  EXERCISE ||--o{ GAP : "yields"
  GAP ||--o{ GAP_EVIDENCE : "supported by"
  GAP ||--o{ GAP_REVIEW : "reviewed (append-only)"
  GAP ||--o{ GAP_REFERENCE : "compared with"
  INTERNATIONAL_REFERENCE ||--o{ GAP_REFERENCE : "cited as"
  GAP ||--o{ IMPROVEMENT_ACTION : "leads to"
  GAP ||--o{ GAP_PRIOR_LINK : "relates to"
  IMPORTED_FINDING ||--o{ GAP_PRIOR_LINK : "relates to"
  EXERCISE ||--o{ NEGATIVE_SEARCH : records
  WORKSPACE ||--o{ REPORT : owns
  REPORT ||--o{ REPORT_VERSION : "versions (immutable)"
  REPORT_VERSION ||--o{ REPORT_ARTIFACT : "rendered as"
  REPORT ||--o{ IMPORTED_FINDING : "extracted (kind=imported)"
  EXERCISE ||--o{ ASSESSMENT : scores
  RUBRIC_DIMENSION ||--o{ RUBRIC_CRITERION : defines
  RUBRIC_CRITERION ||--o{ ASSESSMENT : "answered by"
  EXERCISE ||--o{ EVAL_RUN : measures
  KNOWLEDGE_BASE ||--o{ EVAL_QUESTION : "tested by"

  GAP {
    text id PK
    text workspace_id FK
    text exercise_id FK
    text fingerprint
    text code
    text rule_id
    text category
    text title
    text description
    text domain
    json institution_ids
    text action_id FK
    text evidence_basis
    text confidence
    int severity
    text consequence
    text recommendation_draft
    text cause
    real corpus_coverage
    text validation_status
    text origin
    text registry_state
  }
  GAP_EVIDENCE {
    text id PK
    text gap_id FK
    text kind
    json ref
    text excerpt
    text role
  }
  NEGATIVE_SEARCH {
    text id PK
    text exercise_id FK
    json kb_ids
    json queries
    json languages
    int corpus_documents
    real corpus_coverage
    json top_hits
    text verdict
    datetime run_at
  }
  GAP_REVIEW {
    text id PK
    text gap_id FK
    text reviewer
    text action
    text from_status
    text to_status
    text reality_label
    text comment
  }
  INTERNATIONAL_REFERENCE {
    text id PK
    text workspace_id
    text jurisdiction
    text instrument
    text article
    text summary
    bool binding
    json domains
    json gap_codes
    text document_version_id FK
    text chunk_id FK
    text url
    text evidence_tag
  }
  GAP_REFERENCE {
    text id PK
    text gap_id FK
    text reference_id FK
    text fit_note
    real fit_score
    text status
  }
  IMPROVEMENT_ACTION {
    text id PK
    text gap_id FK
    text owner_institution_id FK
    text description
    date due_date
    text status
    text kpi
  }
  IMPORTED_FINDING {
    text id PK
    text report_id FK
    text title
    text body
    text code_hint
    int severity_hint
    int source_page
    text status
  }
  GAP_PRIOR_LINK {
    text gap_id FK
    text imported_finding_id FK
    text relation
  }
  REPORT {
    text id PK
    text workspace_id FK
    text exercise_id FK
    text kind
    text title
    text document_version_id FK
  }
  REPORT_VERSION {
    text id PK
    text report_id FK
    int version_no
    text status
    json content
    text content_sha256
    int ledger_head_seq
    text ledger_head_hash
    text generator_version
    text parent_version_id FK
  }
  REPORT_ARTIFACT {
    text id PK
    text report_version_id FK
    text format
    text blob_sha256
    int bytes
  }
  RUBRIC_DIMENSION {
    text id PK
    int number
    text name
    text factor
    text question
  }
  RUBRIC_CRITERION {
    text id PK
    text dimension_id FK
    text text
    real weight
  }
  ASSESSMENT {
    text id PK
    text exercise_id FK
    text criterion_id FK
    text answer
    json evidence
    text assessor
    text reviewed_by
    text note
  }
  EVAL_QUESTION {
    text id PK
    text kb_id FK
    text question
    text expected_doc_code
    text expected_article
    text lang
  }
  EVAL_RUN {
    text id PK
    text exercise_id
    text kb_id
    text metric
    json result
    text status
    datetime run_at
  }
```

| Point | Détail |
|---|---|
| `gap.fingerprint` | `sha256(code \| action_code \| institutions triées \| domaine)` : identifie « la même lacune » entre exercices (comparaison, persistance, résolution). |
| `gap.code` / `category` | `code` ∈ `G1…G10` ou `X…` (extensions) ; `category` ∈ typologie de 17 catégories (doc 09 §9.2). |
| Trois axes (FR-52) | `evidence_basis` : `documented \| observed \| inferred \| hypothesis` · `confidence` : `high \| medium \| low` · `validation_status` : `proposed \| confirmed \| disputed \| rejected` (le **statut** ne peut passer à `confirmed` que par une `gap_review` humaine). |
| `gap.registry_state` | État du registre au moment de la détection (`reviewed_complete` / `partial` / `unreviewed`) — affiché dans le rapport. |
| `gap_evidence.kind` | `mandate \| chunk \| event \| message \| decision \| negative_search \| imported_finding \| coordinator_signal` ; `role` : `supports \| counter \| context` (les contre-preuves sont conservées, pas masquées). |
| `negative_search` | Enregistre les requêtes standardisées lancées pour tester une absence : `verdict` ∈ `no_hit \| weak_hit \| strong_hit` ; nombre de documents du corpus, langues, meilleurs scores. |
| `gap_review` | **Append-only** ; `reality_label` ∈ `real \| partially_real \| not_real` alimente T4. |
| `international_reference` | Bibliothèque de précédents (par espace, ou globale). **Chaque entrée doit référencer un `chunk`** d'une KB `global_practices` *ou* une URL + `evidence_tag=summary` explicite. Pas d'entrée sans source. |
| `report.kind` | `generated \| imported`. Un rapport importé n'est jamais mêlé aux lacunes générées ; `gap_prior_link` en garde la relation (`previously_identified \| newly_emerged \| contradicts`). |
| `report_version` | Immuable une fois `published` ; `content` JSON structuré = source unique ; `ledger_head_*` lie le rapport à l'état du ledger au moment de la génération. |
| `rubric_*`, `assessment` | `answer` ∈ `yes \| partial \| no \| not_assessed` ; **score = dérivé** des réponses ; `not_assessed` n'est jamais 0. |
| `eval_run.status` | `computed \| not_computed` (I6). |

Notes : `gap_rule` n'est **pas** une table : les règles sont une table de règles **en code** (`gaps/rules/`), versionnée avec le moteur ; `import_map` (correspondance d'identifiants à l'import d'une archive : `{archive_id, local_id, kind}`) est une table du module `knowledge`.

## 6.5 Contraintes d'intégrité transverses

* `ledger_event`, `gap_review`, `seat_assignment`, `report_version` (publiée), et le **contenu** de `document_version`/`chunk` (fichier, texte, hash) : **pas de `UPDATE`/`DELETE` applicatif**. Seules des colonnes de **cycle de vie** sont mutables (`document_version.status`, `archived_at`), chaque changement étant écrit comme événement de cycle de vie (journalisé) ; test qui parcourt les services et échoue si une mise à jour est tentée. (SQLite n'ayant pas de droits par table, des **triggers** `BEFORE UPDATE/DELETE … RAISE(ABORT)` sont posés sur `ledger_event` et `gap_review`.)
* Suppression : un pays/institution/KB/agent/scénario *référencé par un exercice lancé* ne peut être que **archivé** (`archived_at`) ; seuls les brouillons non référencés sont supprimables (U§8).
* Clés étrangères activées (`PRAGMA foreign_keys=ON`) ; index sur `(exercise_id, seq)`, `(workspace_id, …)`, `chunk(kb_id)`, `chunk(document_version_id)`, `gap(fingerprint)`.
* Aucun chemin absolu en base : les fichiers sont désignés par `blob.sha256` ; le répertoire de données est configuré par `ALERTE_DATA_DIR`.

## 6.6 Compléments (corrections ciblées du 2026-11-21)

| Élément | Précision |
|---|---|
| `kb_expected_document` | Liste *attendue* par KB (titre, juridiction, citation, statut `present \| missing \| replaced`) ; alimente `negative_search.corpus_coverage` et `gap.corpus_coverage` |
| `gap.cause` | `institutional \| documentary \| artifact \| undetermined` ([09](09-gap-analysis-and-reports.md) §9.9) |
| `exercise.commitment_sha256` | Pré-engagement : empreinte des règles, demandes, registre et catalogue d'actions au lancement |
| `action_item.derivation` | `referential \| scenario_author \| agent_proposed` + **justification obligatoire** ; seule une action `referential` est présentée comme « attente documentée » |
| Embeddings | Stockés dans SQLite (source de vérité) avec l'**empreinte complète de l'embedder** ; l'index Chroma en est dérivé et reconstructible |
