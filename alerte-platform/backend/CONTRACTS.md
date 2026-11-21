# Contrats entre modules (backend)

Document de référence pour le développement parallèle. **Ne pas modifier sans accord du coordinateur.**

## Règles communes
* Python 3.12, venv `backend/.venv` : toujours `backend/.venv/bin/python -m …` (Windows : `.venv\Scripts\python`). Jamais d'installation globale.
* Tests : `cd backend && .venv/bin/python -m pytest tests/<module> -q`. Chaque module livre ses tests. **Aucun test simulé n'est une preuve IA.**
* Un module n'écrit que **ses tables** ; il lit les autres via leurs **services** (fonctions listées ci-dessous). Les modèles SQLAlchemy sont dans `app/<module>/models.py` (Base = `app.core.db.Base`).
* Isolation : toute requête filtre par `workspace_id` ; un objet d'un autre espace → **404**.
* API : routeur FastAPI dans `app/<module>/router.py` (variable `router`, **sans** préfixe `/api/v1`, ajouté par `main.py`), schémas Pydantic dans `schemas.py`, logique dans `service.py`. Auth : `Depends(require_role(...))` de `app.core.auth` (`owner` toujours autorisé). Session : `Depends(get_session)`. Erreurs : `AppError`/`NotFound`/`Conflict`/`Unprocessable`/`Forbidden` de `app.core.errors`.
* Enregistrement au démarrage : `app/<module>/setup.py` avec `register(ctx)` (services dans `ctx.services[...]`).
* Identifiants : `app.core.ids.new_id()` (ULID texte 26). Dates : `app.core.db.utcnow()`. Blobs : `ctx.blobs` (`app.core.blobs.BlobStore`). Jobs : `ctx.jobs.submit(kind, fn, workspace_id=…)`.
* Ledger : `ctx.service("ledger").append(session, exercise_id, type, actor, payload, seat_id=…, sim_time=…, visibility=…)` — **seule la simulation écrit les événements d'exercice**.
* Pas de secrets ni de chemins absolus en base. Lint : `.venv/bin/python -m ruff check app tests`.

## Services exposés (signatures contractuelles)
* `workspaces.service` : `get_institution(session, workspace_id, id)`, `list_institutions(session, workspace_id, country_id=None, include_archived=False)`, `register_reference_guard(fn(session, kind, id)->bool)`.
* `knowledge` (enregistré `ctx.services["search"]` : objet implémentant `contracts.SearchService`) ; `ctx.services["knowledge"]` : `published_document_version_ids(session, workspace_id, kb_ids) -> set[str]`, `kb_overview(session, workspace_id, kb_id) -> dict`, `get_chunk(session, chunk_id) -> dict|None`, `chunk_in_scope(session, chunk_id, scope) -> bool`.
* `agents` (`ctx.services["agents"]`) : `export_agent_snapshot(session, workspace_id, agent_id) -> dict`, `kb_grants(session, workspace_id, agent_id) -> list[str]`, `runtime() -> AgentRuntimePort` (implémente `contracts.AgentRuntimePort`), `ask_legal`/outils internes au runtime.
* `scenarios` (`ctx.services["scenarios"]`) : `export_scenario_snapshot(session, workspace_id, scenario_id) -> dict`, `readiness_scenario_checks(session, workspace_id, scenario_id) -> list[dict]`.
* `mandates` (`ctx.services["mandates"]`) : `export_active_mandates(session, workspace_id, institution_ids, document_version_ids) -> list[dict]`, `registry_state(session, workspace_id, institution_id) -> str`.
* `simulation` : enregistre `ctx.services["exercise_guard"] = fn(session, principal, exercise_id)` (lève NotFound/Forbidden) ; appelle `ctx.services["gap_engine"].on_inject_closed(session, exercise_id, inject_ref)` et `.on_exercise_finished(session, exercise_id)` s'ils existent.
* `gaps` (`ctx.services["gap_engine"]`) : `on_inject_closed(...)`, `on_exercise_finished(...)`, `detect(session, exercise_id) -> list[dict]`.
* `reports`, `evaluation` : exposent leurs routeurs ; `evaluation.service.compute_t2(session, exercise_id)`, `compute_t6(...)`.

## Snapshot d'exercice (JSON canonique figé au lancement ; table `exercise_snapshot.payload`)
```json
{"workspace_id": "...", "exercise": {"id": "...", "code": "...", "title": "...", "ai_mode": "ai|scripted|cassette", "settings": {...}},
 "scenario": {"id": "...", "code": "...", "title": "...", "language": "fr",
   "injects": [{"inject_ref": "inj-001", "seq": 1, "sim_time": "D1 06:00", "title": "...", "body": "...", "from_actor": "...",
                "recipients": ["<institution_id>"], "tags": ["life_risk"], "demands": [{"action_code": "...", "derivation": "referential|scenario_author|agent_proposed", "justification": "..."}],
                "fault_mode": "none", "system_output": null}]},
 "institutions": [{"id": "...", "code": "MET", "name": "...", "kind": "agency", "country_id": "...", "domains": []}],
 "seats": [{"seat_id": "...", "code": "MET", "institution_id": "...", "controller": "agent|human|scripted", "agent": {"id": "...", "code": "...", "role_kind": "institution|ai_system|legal_adviser", "mission": "...", "instructions": "...", "tools": ["search_kb","ask_legal","post","decide"], "limits": {"max_steps": 4, "max_search_calls": 3, "max_legal_calls": 2}, "model_profile": {"provider": "...", "model": "..."}}}],
 "kb": [{"kb_id": "...", "code": "...", "name": "...", "document_version_ids": ["..."]}],
 "grants": {"<agent_id>": ["<kb_id>"]},
 "mandates": [{"id": "...", "institution_id": "...", "kind": "power|duty|lead|...", "action_code": "...", "description": "...", "procedure_status": "...", "sources": [{"document_version_id": "...", "chunk_id": "...", "article": "...", "page": 1, "quote": "..."}]}],
 "actions": [{"code": "...", "label": "...", "derivation": "...", "justification": "..."}]}
```
Le moteur de lacunes lit ce snapshot (jamais les tables vivantes de configuration) + le ledger.

## Charges utiles d'événements (ledger)
* `INJECT` (public) : `{inject_ref, seq, title, body, recipients:[seat_code], tags, fault_mode, surprise:false}`.
* `BOARD` (board) : `{msg_id, from, to, msg_type, body, in_reply_to, reply_status, inject_ref, round}`.
* `DECISION` (public) : `{decision_id, seat_code, inject_ref, round, action, action_code, outcome(act|decline|refer|no_legal_basis_found), confidence(low|medium|high), options_considered, gap_flags:[{hint,text}], rationale, evidence_tag(documented|inferred|assumed), legal_basis:[{chunk_id, article, quote, check(pass|fail), reason}], status(recorded|not_verified|not_recorded), author(agent|human|fallback)}`.
* `RETRIEVAL` (seat) : `{query, scope_hash, results:[{chunk_id, score, rank}], signals:{lexical, dense, degraded}}`.
* `LLM_CALL` (audit) : `{provider, model, endpoint, step_key, request_blob_sha256, response_blob_sha256, tokens_in, tokens_out, ms, valid, retried}`.
* `TOOL_CALL` (seat) : `{tool, args, rationale, ok, error}`. `CITATION_CHECK` (audit) : `{decision_id, citations:[{chunk_id, pass, reason}]}`.
* `GAP` (audit pour signaux, public pour constats validés) : `{origin_kind: rule|coordinator_signal|agent_hypothesis, signal, inject_ref, action_code, institutions:[institution_id], evidence:{...}, gap_id?}` avec `signal` ∈ `ORPHAN_REQUEST|NO_OWNER|CLAIM_OVERLAP|CONFLICTING_DECISIONS|MISSING_BASIS|NO_RESPONSE|AGENT_HYPOTHESIS|UNSUPPORTED_DECISION`.
* `STATE` (public) : `{from, to, reason}` ; `SNAPSHOT` (audit) : `{snapshot_sha256, commitment_sha256, ai_mode, readiness}` ; `SEAT`, `HUMAN`, `FACILITATOR`, `CORRECTION`, `ERROR` : voir doc 10 §10.2.

## Compléments de contrat
* `knowledge` expose aussi (`ctx.services["knowledge"]`) : `coverage(session, workspace_id, kb_ids) -> {"ratio": float|None, "expected": int, "present": int, "missing": [str]}` (couverture documentaire attendue vs présente), `document_meta(session, document_version_id) -> dict|None` (code, titre, type, juridiction, licence, redistribution).
* `mandates` expose aussi : `action_exists(session, workspace_id, code) -> bool`, `list_actions(session, workspace_id) -> list[dict]`.
* `jobs` : les routes `GET /jobs/{id}` et `GET /jobs/{id}/stream` (SSE de progression, `id` = compteur) sont définies dans `app/knowledge/router.py`.
* Jeton de flux SSE : `POST /exercises/{id}/stream-token` → jeton à usage unique de 60 s, passé en `?stream_token=` (jamais journalisé : `core.logging_setup` le masque).
* Pas de dépendance à un vrai modèle dans les tests unitaires ; les tests IA réels portent `@pytest.mark.model` et sont ignorés sauf si `ALERTE_LLM_BASE_URL` / `ALERTE_EMBED_BASE_URL` sont définis.
