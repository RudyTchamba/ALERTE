/**
 * API coverage notes (last `npm run gen:api`). Every route the UI calls is served by the backend.
 *
 * Served since the last review:
 *   - GET /auth/me                                : role and scope of the token (replaces the old `GET /tokens` probe).
 *   - GET /exercises/{id}/llm-calls/{seq}         : raw prompt and response of a model call, integrity-checked
 *                                                   (facilitator/auditor; never an arbitrary blob by fingerprint).
 *   - POST /scorecard/exercises/{id}/assess       : AI judge of the 13-dimension scorecard (background job).
 *   - GET /ledger/public-key                      : Ed25519 key that signs ledger anchors (public).
 *
 * Deliberate design choices (not missing features):
 *   - Decision trace and replay are rebuilt client-side from the ledger events the caller may read: the ledger is the
 *     single source of truth, so no second, possibly divergent, server-side computation is needed.
 *   - Seat links carry a scoped, expiring token in the URL fragment (never sent to servers or logs) used as Bearer.
 *   - Endpoints listed in loose.ts return plain dicts; their shapes are typed by hand there.
 */
export {}
