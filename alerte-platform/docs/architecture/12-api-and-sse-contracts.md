# 12 — Contrats d'API REST et de flux SSE

> Brouillon de contrat : le schéma OpenAPI généré par FastAPI en sera la **source de vérité** une fois les schémas Pydantic écrits (doc 11 §11.3). Les corps JSON ci-dessous sont indicatifs.

## 12.1 Conventions

| Sujet | Règle |
|---|---|
| Préfixe / version | `/api/v1` ; SPA servie sur `/` |
| Format | JSON UTF-8 ; dates ISO 8601 UTC ; identifiants texte opaques (ULID) |
| Authentification | `Authorization: Bearer <jeton>` ; le jeton porte un **rôle** et un périmètre (espace, exercice, siège). Hash seulement en base. SSE : `EventSource` n'accepte pas d'en-têtes → **jeton de flux à usage unique, 60 s, lié à l'exercice et au rôle** (`?stream_token=`), obtenu par `POST /exercises/{id}/stream-token` ; les journaux d'accès **masquent** ce paramètre. **Liens de siège/observateur : jeton dans le *fragment* d'URL** (`/play#t=…`, jamais envoyé au serveur ni dans `Referer`) ; le SPA l'échange (`POST /sessions/exchange`) contre un cookie `HttpOnly; SameSite=Strict` ou un jeton de session court |
| Rôles | `owner` (tout dans l'espace), `facilitator` (exercices, scénarios, revues), `player` (un siège), `observer` (lecture), `auditor` (lecture + audit complet) |
| Erreurs | `{ "error": { "code": "kb.not_ready", "message": "…", "details": {…}, "request_id": "…" } }` ; statuts : 400 validation, 401/403 droits, 404, 409 état/transition interdit, 422 contrôle métier (ex. citation), 429 limites, 5xx |
| Pagination | `?limit=50&cursor=…` → `{items, next_cursor}` |
| Tâches longues | `202 Accepted` + `{ "job": {"id","status"} }` ; suivi `GET /jobs/{id}` ou `GET /jobs/{id}/stream` (SSE) |
| Idempotence | En-tête `Idempotency-Key` sur les créations coûteuses (export, génération de rapport, lancement) |
| Limites | Taille de requête et de fichier bornées ; rate-limit par jeton (outil de dev désactivable) |
| OpenAPI | `/api/v1/openapi.json` ; types TS générés par le frontend |

## 12.2 Ressources (tableau des endpoints)

> Les endpoints sont **figés au contrat** (samedi) mais implémentés selon la priorité du doc 14 : XLSX (P2), import de rapports et scorecard (P1), PDF serveur (P1), comparaisons (P1).

### Espace de travail, pays, institutions, mandats

| Méthode · chemin | Rôles | But |
|---|---|---|
| `POST /workspaces` | (bootstrap) | Crée l'espace et renvoie le jeton `owner` **une seule fois** |
| `GET /workspaces/current` · `PATCH` · `POST …/archive` | owner | Profil, archivage |
| `POST /tokens` · `GET /tokens` · `DELETE /tokens/{id}` | owner | Jetons facilitateur/observateur/auditeur |
| `GET/POST /countries` · `GET/PATCH/DELETE /countries/{id}` | owner, facilitator | CRUD ; `DELETE` refusé (409) si référencé par un exercice lancé → archiver |
| `GET/POST /institutions` · `GET/PATCH/DELETE /institutions/{id}` | owner, facilitator | CRUD, `?country_id=` |
| `GET/POST /actions` · `PATCH /actions/{id}` | owner, facilitator | Catalogue d'actions (avec `derivation`) |
| `GET/POST /mandates` · `GET/PATCH/DELETE /mandates/{id}` | owner, facilitator | Registre de mandats ; `POST /mandates/import-csv` |
| `POST /mandates/{id}/validate` · `/reject` | owner, facilitator | Validation humaine (enregistrée) |
| `PUT /institutions/{id}/registry-review` | owner, facilitator | `unreviewed\|partial\|reviewed_complete` |

### Bases de connaissances

| Méthode · chemin | But |
|---|---|
| `GET/POST /knowledge-bases` · `GET/PATCH /knowledge-bases/{id}` · `POST …/archive` | CRUD, archivage |
| `GET/POST /knowledge-bases/{id}/documents` (multipart) | Liste ; **upload** → `202` + job d'ingestion |
| `GET/PATCH /documents/{id}` | Métadonnées (fiabilité, validité, licence, redistribution, « remplacé par ») |
| `POST /documents/{id}/versions` (multipart) | Nouvelle version (remplace/met à jour) |
| `DELETE /documents/{id}` | Retire (version `retired`) — refusé si référencé |
| `GET /documents/{id}/versions/{v}/preview` · `/chunks` | Aperçu page par page, chunks |
| `GET /knowledge-bases/{id}/quality` | Rapport de qualité (couverture, OCR, pages à relire, alertes d'injection) |
| `POST /knowledge-bases/{id}/publish` | Publie une `kb_version` (fige l'ensemble des versions) |
| `POST /knowledge-bases/{id}/reindex` | Job de reconstruction d'index |
| `POST /knowledge-bases/{id}/search` | Recherche pour l'UI (`SearchScope` selon le rôle ; **pas** de paramètre d'identité) |
| `POST /knowledge-bases/{id}/exports` | Lance l'export (mode, sélection, options) → `202` job ; `GET /exports/{id}` ; `GET /exports/{id}/download` |
| `POST /knowledge-bases/import` (multipart) | Import en **dry-run** → rapport de validation ; `POST /imports/{id}/confirm` |

### Agents et droits

| Méthode · chemin | But |
|---|---|
| `GET/POST /model-profiles` · `PATCH /model-profiles/{id}` · `DELETE /model-profiles/{id}` · `POST /model-profiles/{id}/test` | Profils de modèle ; test d'appel (readiness). `DELETE` : 409 `model_profile.in_use` (avec les codes des agents) tant qu'un agent, archivé ou non, utilise le profil ; les exercices lancés portent une copie figée de leur profil et ne sont pas touchés |
| `GET/POST /agents` · `GET/PATCH /agents/{id}` · `POST …/archive` | CRUD agent |
| `GET /agents/{id}/prompt-preview` | Aperçu du prompt assemblé (sans secrets) |
| `PUT /agents/{id}/kb-grants` | Remplace la liste des KB accordées (matrice) |
| `GET /access-matrix` | Matrice agents × KB (pour la page) |

### Scénarios

| Méthode · chemin | But |
|---|---|
| `GET/POST /scenarios` · `GET/PATCH /scenarios/{id}` · `POST …/archive` | CRUD |
| `GET/POST /scenarios/{id}/injects` · `PATCH/DELETE /injects/{id}` · `PUT /scenarios/{id}/injects/order` | Injects, ordre |
| `PUT /injects/{id}/recipients` · `PUT /injects/{id}/demands` | Destinataires, demandes |
| `GET /scenarios/{id}/lint` | Avertissements (inégalité d'information, destinataire inconnu, budget estimé) |
| `GET /scenarios/{id}/export.yaml` · `POST /scenarios/import` | Confort (non obligatoire) |

### Exercices et simulation

| Méthode · chemin | Rôles | But |
|---|---|---|
| `POST /exercises` | owner, facilitator | Crée depuis un scénario (+ clone `?from=` pour contrefactuel/T5) |
| `GET /exercises` · `GET /exercises/{id}` | tous (selon rôle) | Liste, détail, état |
| `PUT /exercises/{id}/seats` | facilitator | Affecte IA/humain, nomme les humains |
| `POST /exercises/{id}/seats/{seat}/invite` | facilitator | Génère le lien de siège (jeton `player`) |
| `GET /exercises/{id}/readiness` | facilitator | Contrôles bloquants/avertissements |
| `POST /exercises/{id}/commands` | facilitator | `{kind: start\|pause\|resume\|step\|speed\|stop\|surprise\|seat_switch\|correction, args}` → `202` |
| `GET /exercises/{id}/snapshot` | auditor | Snapshot figé + hash |
| `GET /exercises/{id}/stream` (**SSE**) | selon rôle | Voir §12.4 |
| `GET /exercises/{id}/board` · `/decisions` · `/inbox?seat=` | selon visibilité | Lectures REST (reprise d'état) |
| `GET /seats/me` · `GET /seats/me/task` · `POST /seats/me/search` · `POST /seats/me/ask-legal` · `POST /seats/me/post` · `POST /seats/me/decision` | player | Interface du siège humain (mêmes validations que l'agent) |
| `POST /exercises/{id}/stream-token` | rôle quelconque | Jeton de flux à courte durée |

### Audit

| Méthode · chemin | But |
|---|---|
| `GET /exercises/{id}/ledger?after=&types=&seat=` | Événements (filtrés par visibilité) |
| `GET /exercises/{id}/ledger/verify` | `{ok, checked, first_bad_seq, anchor_mismatch, truncated_after_anchor}` |
| `GET /exercises/{id}/ledger/export` | JSONL avec empreintes |
| `GET /exercises/{id}/anchors` | Ancres de tête |
| `GET /exercises/{id}/replay?until_seq=` | État reconstruit |
| `GET /decisions/{id}/trace` | Trace de décision complète |
| `GET /blobs/{sha256}` | Prompt/réponse (auditor) |

### Lacunes, références, rapports, évaluation

| Méthode · chemin | But |
|---|---|
| `GET /gaps?exercise=&country=&institution=&domain=&category=&code=&severity=&status=&basis=` | Liste filtrable |
| `GET /gaps/{id}` | Détail avec preuves, recherches négatives, références, revues |
| `POST /gaps/{id}/reviews` | `{action: confirm\|dispute\|reject\|comment\|reopen, comment, reality_label}` (append-only) |
| `PATCH /gaps/{id}` | Édition humaine (titre, description, gravité avec motif) — journalisée en `gap_review` |
| `POST /gaps/{id}/references` · `PATCH /gap-references/{id}` | Associer/accepter/rejeter un précédent |
| `GET/POST /international-references` | Bibliothèque de références |
| `GET/POST /gaps/{id}/improvement-actions` · `PATCH /improvement-actions/{id}` | Plan d'amélioration |
| `GET /gaps/compare?a=exercise&b=exercise` | Nouvelle/persistante/résolue |
| `POST /exercises/{id}/detect-gaps` | Relance la détection finale (idempotente) |
| `GET/POST /reports` · `GET /reports/{id}` | Rapports (générés/importés) |
| `POST /exercises/{id}/reports` | Génère → `202` job → nouvelle `report_version` (draft) |
| `POST /report-versions/{id}/publish` · `GET /report-versions/{id}` · `GET …/artifacts/{md\|pdf\|csv\|xlsx\|json}` | Publier, lire, **télécharger** |
| `GET /reports/{id}/compare?a=v1&b=v2` | Diff de versions |
| `POST /reports/import` (multipart) · `POST /reports/{id}/findings` | Rapport antérieur + constats extraits |
| `GET /evaluation/exercises/{id}` · `POST /evaluation/exercises/{id}/run?metric=T1..T6` | Métriques |
| `GET/PUT /scorecard/exercises/{id}` · `POST …/assess` | Scorecard |
| `GET /health` · `GET /ready` | Sonde de vie / prêt (DB, dossier de données, fournisseur de modèle) |

## 12.3 Exemples de corps

```jsonc
// POST /knowledge-bases
{ "name": "Cameroon legal corpus", "description": "…", "country_id": "01J…", "domain": "early_warning",
  "kind": "national", "languages": ["fr","en"], "embedding_model": null,
  "chunking_params": {"strategy": "article-aware", "max_chars": 2000, "overlap_chars": 200} }

// POST /knowledge-bases/{id}/exports  → 202
{ "mode": "full_reimportable", "document_ids": null,
  "include": {"originals": true, "embeddings": false, "mandates": true, "references": true},
  "purpose": "private" }            // "open_publication" refuse restricted/unknown et renvoie 422 avec la liste

// PUT /agents/{id}/kb-grants
{ "kb_ids": ["01J…KB1", "01J…KB2"] }

// POST /exercises/{id}/commands
{ "kind": "pause" }  |  { "kind": "seat_switch", "args": {"seat": "DPC", "controller": "human", "human_name": "Marie"} }

// POST /seats/me/decision  (joueur humain)
{ "action": "Decline to compel operators; refer to the regulator",
  "action_code": "compel_operator_alert", "outcome": "refer", "confidence": "low",
  "legal_basis": [{"chunk_id": "01J…C42", "article": "33", "quote": "…texte exact du chunk…"}],
  "options_considered": ["…"], "gap_flags": [], "evidence_tag": "documented", "rationale": "…" }
// 422 si citation invalide : { "error": {"code": "decision.citation_failed", "details": {"failures": [{"chunk_id":"…","reason":"quote_not_in_chunk"}]}} }

// POST /gaps/{id}/reviews
{ "action": "dispute", "comment": "Le décret X confère ce pouvoir à l'institution Y", "reality_label": "partially_real" }
```

## 12.4 Contrat du flux SSE d'exercice

`GET /api/v1/exercises/{id}/stream?stream_token=…` — `Content-Type: text/event-stream`.

| Élément | Contrat |
|---|---|
| `id:` | `seq` du ledger (entier) — **identique** à l'identifiant d'événement d'audit |
| `event:` | Type d'événement du catalogue (`INJECT`, `BOARD`, `DECISION`, `RETRIEVAL`, `TOOL_CALL`, `LLM_CALL`, `CITATION_CHECK`, `GAP`, `HUMAN`, `SEAT`, `STATE`, `FACILITATOR`, `CORRECTION`, `ERROR`, `SNAPSHOT`) + `heartbeat` |
| `data:` | JSON `{ seq, type, actor, seat, sim_time, real_time, visibility, payload }` — le **payload est filtré** selon le rôle du jeton (jamais côté client) |
| `retry:` | 3000 ms |
| Reprise | `Last-Event-ID` (en-tête, automatique) ou `?after=<seq>` ; le serveur renvoie tous les `seq` > id **sans trou ni doublon** |
| Cadence | Lecture du ledger toutes les ~300 ms ; `heartbeat` toutes les 15 s |
| Filtre | `?types=DECISION,BOARD` (optionnel) ; la visibilité est imposée par le jeton, pas par le filtre |
| Fin | Événement `STATE` `completed\|stopped` puis fermeture ; le client peut rester pour les ré-ouvertures |
| Erreur | `event: error` avec `{code}` puis fermeture ; `401` si jeton expiré (le client redemande un jeton de flux) |

Exemple :

```
id: 128
event: DECISION
data: {"seq":128,"type":"DECISION","actor":"seat:OPS","seat":"OPS","sim_time":"D1 07:10","real_time":"2026-11-24T10:41:02Z","visibility":"public","payload":{"decision_id":"01J…","outcome":"refer","status":"recorded","confidence":"low","rationale":"No explicit power to compel operators found.","legal_basis":[{"chunk_id":"01J…","article":"33","pass":true}]}}
```

Le client **dérive** l'état (chronologie, cartes, tableau, lacunes) de ces événements ; pour une première charge il lit `GET /exercises/{id}/board` etc. puis ouvre le flux avec `after=<dernier seq>`.

### Flux de jobs

`GET /api/v1/jobs/{id}/stream` — événements `progress` `{pct, step, message}`, `done` `{result_ref}` ou `failed` `{error}` ; mêmes règles de reprise (`id` = compteur de progression). Utilisé par l'ingestion, l'export, l'import, la génération de rapport.

## 12.5 Erreurs métier standard (extraits)

| Code | Statut | Sens |
|---|---|---|
| `workspace.forbidden` | 403 | Hors espace ou rôle insuffisant |
| `kb.not_ready` | 409 | KB sans version publiée |
| `kb.export.restricted_documents` | 422 | Export « ouvert » contenant des documents restreints/inconnus (liste fournie) |
| `kb.import.integrity_failed` | 422 | Hash ou chemin invalide ; import refusé |
| `exercise.invalid_transition` | 409 | Commande interdite dans l'état courant |
| `exercise.readiness_blocked` | 409 | Contrôles bloquants (liste) |
| `decision.citation_failed` | 422 | Citation non vérifiée (raisons par citation) |
| `seat.not_assigned` | 409 | Siège non confié à ce jeton |
| `gap.review.reason_required` | 422 | Contestation/rejet sans motif |
| `budget.exhausted` | 409 | Plafond d'appels atteint (exercice mis en pause) |
