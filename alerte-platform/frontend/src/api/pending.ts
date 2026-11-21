/**
 * Contracts for endpoints that are NOT in the backend OpenAPI yet. Everything here is `TODO(api)`:
 * when the endpoint appears in `GET /api/v1/openapi.json`, run `npm run gen:api`, move the type to `types.ts`
 * (alias of the generated schema) and delete it from this file.
 *
 * Status at the last `gen:api`: reports, evaluation, scorecard, gaps, simulation, knowledge, agents, scenarios, mandates
 * and audit are all served. What is still missing (doc 12) and therefore NOT called by the UI:
 *   - TODO(api) GET /decisions/{id}/trace        : the Room/Audit decision trace is rebuilt client-side from ledger events.
 *   - TODO(api) GET /blobs/{sha256}              : raw prompts/outputs cannot be shown (hashes only).
 *   - TODO(api) GET /exercises/{id}/replay       : replay is computed client-side from the ledger (no model call).
 *   - TODO(api) POST /sessions/exchange          : seat links use the fragment token directly as Bearer.
 *   - TODO(api) role of the caller (GET /auth/me): the UI probes `GET /tokens` (owner-only) to detect the owner role.
 *   - TODO(api) response_model for the endpoints listed in loose.ts (plain dict responses).
 */
export {}
