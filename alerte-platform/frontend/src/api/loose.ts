/**
 * Response shapes the backend returns WITHOUT an OpenAPI response model (plain `dict` returns).
 * They are derived from the backend source (routers/services) as of this writing and are the ONLY hand-written
 * shapes for existing endpoints.
 * TODO(api): ask the backend to declare `response_model` for these so that `gen:api` produces them; then
 * replace each interface here with an alias in `types.ts`.
 */
import type { Agent, Country as _C, Inject, KBKind } from './types'

export type _Unused = _C | Agent | Inject

export interface KbOverview {
  id: string
  code: string
  name: string
  kind: string
  domain: string | null
  languages: string[]
  status: string
  country_id: string | null
  published_version_no: number | null
  published_version_id: string | null
  documents: number
  chunks: number
  embedded_chunks: number
  embedder_key: string | null
  coverage: Coverage
}
export interface Coverage {
  ratio: number | null
  expected: number
  present: number
  missing: string[]
}
export interface Kb {
  id: string
  code: string
  name: string
  description: string | null
  country_id: string | null
  domain: string | null
  kind: KBKind | string
  languages: string[]
  embedder_key: string | null
  embedder_fingerprint: string | null
  chunking_params: Record<string, unknown> | null
  status: string
  archived_at: string | null
  overview?: KbOverview
}
export interface DocVersion {
  id: string
  version_no: number
  status: string
  bytes: number | null
  blob_sha256: string | null
  original_name: string | null
  extraction_method: string | null
  extraction_quality: number | null
  pages_to_review: number[]
  supersedes_id: string | null
  note: string | null
  created_at: string
  quality_report?: Record<string, unknown> | null
}
export interface Doc {
  id: string
  kb_id: string
  code: string
  title: string
  doc_type: string | null
  doc_number: string | null
  jurisdiction: string | null
  language: string | null
  source_url: string | null
  reliability: string | null
  validity: string | null
  replaced_by_id: string | null
  license_spdx: string | null
  redistribution: string | null
  evidence_default: string | null
  current_version_id: string | null
  doc_date: string | null
  accessed_at: string | null
  version?: DocVersion
}
export interface DocList {
  items: Doc[]
  next_cursor: string | null
}
export interface JobRef {
  id: string
  status: string
}
export interface Job {
  id: string
  kind: string
  status: 'queued' | 'running' | 'done' | 'failed' | string
  progress: number
  message: string | null
  result: Record<string, unknown> | null
  error: string | null
  created_at: string | null
  started_at: string | null
  finished_at: string | null
}
export interface Chunk {
  id: string
  doc_code: string | null
  doc_title: string | null
  article: string | null
  section: string | null
  page_start: number | null
  page_end: number | null
  language: string | null
  text: string
  ordinal: number
  evidence_tag: string | null
  validity: string | null
}
export interface ChunkList {
  items: Chunk[]
  next_cursor: number | null
}
export interface Preview {
  version: DocVersion
  total_pages: number
  page: number
  pages: unknown[]
}
export interface KbQualityItem {
  document_id: string
  code: string
  title: string
  status: string
  extraction_quality: number | null
  pages: number | null
  ocr_pct: number | null
  articles_detected: number | null
  pages_to_review: number[]
  injection_flags: unknown[]
  warnings: string[]
  missing_metadata: string[]
}
export interface KbQuality {
  kb_id: string
  documents: number
  avg_extraction_quality: number | null
  totals: Record<string, number>
  pct_documents_with_articles: number | null
  languages: Record<string, number>
  redistribution: Record<string, number>
  duplicates: unknown[]
  alerts: string[]
  coverage: Coverage
  items: KbQualityItem[]
}
export interface KbVersion {
  id: string
  version_no: number
  manifest_sha256: string
  note: string | null
  created_at: string
}
export interface ExpectedDoc {
  id: string
  title: string
  jurisdiction: string | null
  citation: string | null
  status: string
  matched_document_id: string | null
}
export interface ExpectedList {
  items: ExpectedDoc[]
  coverage: Coverage
}
export interface SearchHit {
  chunk_id: string
  document_version_id: string
  doc_code: string | null
  doc_title: string | null
  article: string | null
  page: number | null
  score: number
  snippet: string
  text: string
  signals: { lexical?: unknown; dense?: unknown; degraded?: boolean; [k: string]: unknown }
}
export interface SearchResult {
  scope_hash: string
  degraded: boolean
  label: string
  hits: SearchHit[]
}
export interface ExportStart {
  job: JobRef
  export: { id: string; status: string; mode: string }
  warnings: unknown[]
}
export interface ExportInfo {
  id: string
  kb_id: string
  mode: string
  status: string
  error: string | null
  job_id: string | null
  bytes: number | null
  filename: string | null
  blob_sha256: string | null
}
export interface ImportInfo {
  id: string
  status: string
  report: {
    ok?: boolean
    errors?: unknown[]
    warnings?: unknown[]
    [k: string]: unknown
  } | null
  result_kb_id: string | null
  import_map: Record<string, unknown> | null
  job_id: string | null
}
export interface AccessMatrix {
  agents: { id: string; code: string; name: string; institution_id: string | null; role_kind: string; archived: boolean }[]
  knowledge_bases: { id: string; code: string | null; name: string | null }[]
  grants: { agent_id: string; kb_id: string; mode: string }[]
}
export interface ProfileTest {
  ok: boolean
  provider: string
  model: string | null
  ai_involved: boolean
  endpoint: string | null
  ms: number
  error: string | null
  label?: string
}
export interface PromptPreview {
  version: string
  system_prompt: string
  approx_tokens: number
  mandates_included: number
  granted_kb_ids: string[]
}
export interface FaultMode {
  code: string
  origin: string
  label: string
  description: string
}
export interface LintIssue {
  severity: 'error' | 'warning' | string
  code: string
  message: string
  inject_id: string | null
  seq: number | null
  [k: string]: unknown
}
export interface LintReport {
  scenario_id: string
  ok: boolean
  issues: LintIssue[]
  stats: {
    injects: number
    recipients_total: number
    fault_modes: string[]
    distinct_fault_modes: number
    estimated_llm_calls: { max: number; typical: number; cap: number; formula: string }
  }
}
export interface ScenarioImportResult {
  scenario: { id: string; code: string; title: string }
  warnings: string[]
}
export interface SeatOut {
  code: string
  institution_id: string
  agent_id: string | null
  controller: string
  human_name: string | null
}
export interface Exercise {
  id: string
  code: string
  title: string
  state: string
  substate: string | null
  pace: string
  ai_mode: 'ai' | 'scripted' | 'cassette' | string
  scenario_id: string
  parent_exercise_id: string | null
  settings: Record<string, unknown>
  started_at: string | null
  ended_at: string | null
  snapshot_sha256: string | null
  commitment_sha256: string | null
  llm_calls_used: number
  seats: SeatOut[] | null
}
export interface ReadinessCheck {
  level: 'blocking' | 'warning' | 'info' | string
  code: string
  message: string
  subject: string | null
}
export interface Readiness {
  ok: boolean
  blocking: ReadinessCheck[]
  warnings: ReadinessCheck[]
  [k: string]: unknown
}
export interface InviteResult {
  token: string
  link: string
  seat: string
  human_name: string
  expires_at: string | null
  token_id: string
}
export interface CommandResult {
  id: string
  kind: string
  status: string
  exercise_state: string
}
export interface StreamToken {
  stream_token: string
  expires_in: number
  exercise_id: string
  role: string
}
export interface BoardMessage {
  msg_id: string
  from: string
  to: string
  msg_type: string
  body: string
  in_reply_to: string | null
  reply_status: string | null
  inject_ref: string | null
  round: number | null
}
export interface Decision {
  decision_id: string
  seat_code: string | null
  inject_ref: string | null
  round: number | null
  action: string
  action_code: string | null
  outcome: string | null
  confidence: string | null
  options_considered: string[] | null
  gap_flags: { hint?: string | null; text: string }[] | null
  rationale: string | null
  evidence_tag: string | null
  author: string | null
  status: 'recorded' | 'not_verified' | 'not_recorded' | string
  seq: number | null
  legal_basis: { chunk_id: string; article: string | null; quote: string; check: string | null; reason: string | null }[]
}
export interface InboxItem {
  item_id: string
  source: string
  ref_id: string | null
  inject_ref: string | null
  round: number | null
  [k: string]: unknown
}
export interface SeatCard {
  exercise: { id: string; code: string; title: string; state: string; ai_mode: string }
  seat: { code: string; human_name: string | null; controller: string }
  institution: { id: string | null; code: string | null; name: string | null; kind: string | null }
  role: { mission: string | null; instructions: string | null; tools: string[] | null; limits: Record<string, number> | null }
  mandates: {
    id?: string
    kind?: string
    action_code?: string | null
    description?: string
    sources?: { article?: string | null; page?: number | null; quote?: string | null; chunk_id?: string }[]
    [k: string]: unknown
  }[]
  knowledge_bases: { kb_id: string; code: string; name: string }[]
  seat_codes: string[]
}
export interface SeatTask {
  exercise_state: string
  task: null | {
    id: string
    status: string
    round: number
    inject_ref: string
    deadline_at: string
    fallback: string
    inject: { inject_ref: string; sim_time: string; title: string; body: string; from_actor: string; tags: string[] }
    inbox: Record<string, unknown>[]
    board: BoardMessage[]
    own_decisions: Record<string, unknown>[]
    staged_posts: Record<string, unknown>[]
    usage: Record<string, unknown>
    limits: Record<string, unknown>
  }
}
export interface SeatSearch {
  hits: {
    chunk_id: string
    title?: string | null
    doc_code?: string | null
    doc_title?: string | null
    article?: string | null
    page?: number | null
    score?: number
    excerpt?: string
    snippet?: string
    text?: string
    [k: string]: unknown
  }[]
  warning?: string
  [k: string]: unknown
}
export interface LegalAnswer {
  ok: boolean
  reason: string | null
  answer: string
  structured?: Record<string, unknown>
}
export interface MandateHistory {
  actor: string
  action: string
  from: string | null
  to: string | null
  note: string | null
  changes: Record<string, unknown> | null
  at: string
}
export interface GapCompare {
  a: string
  b: string
  new: GapBrief[]
  resolved: GapBrief[]
  persistent: { a: GapBrief; b: GapBrief; severity_changed: boolean; status_changed: boolean }[]
  summary: { new: number; persistent: number; resolved: number }
}
export interface GapBrief {
  id: string
  fingerprint: string
  code: string
  action_code: string | null
  title: string
  severity: number
  validation_status: string
  evidence_basis: string
}
export interface RefSuggestion {
  reference_id: string
  jurisdiction: string
  instrument: string
  fit_score: number
}
export interface Ready {
  ready: boolean
  checks: Record<string, { ok?: boolean; [k: string]: unknown }>
}

// ---- evaluation / scorecard (responses are plain dicts in the backend; shapes from evaluation/service.py, scorecard.py)
export interface EvalMetric {
  metric: 'T1' | 'T2' | 'T3' | 'T4' | 'T5' | 'T6' | string
  status: 'computed' | 'not_computed' | string
  value: number | null
  passed: boolean | null
  reason: string | null
  threshold: { op?: string; value?: number; label?: string; max_seconds?: number; max_llm_calls?: number; min_questions?: number } | null
  run_id?: string
  run_at?: string
  [k: string]: unknown
}
export interface EvaluationResult {
  exercise_id: string
  thresholds: Record<string, unknown>
  metrics: Record<string, EvalMetric>
}
export interface ScorecardCriterion {
  criterion_id: string
  text: string
  weight: number
  answer: 'yes' | 'partial' | 'no' | 'not_assessed' | string
  evidence: unknown[]
  assessor: string | null
  reviewed_by: string | null
  note: string | null
}
export interface ScorecardDimension {
  dimension_id: string
  number: number
  name: string
  short_name: string | null
  factor: string | null
  question: string | null
  criteria: ScorecardCriterion[]
  score: number | null
  status: 'assessed' | 'not_assessed' | string
  assessed: number
  total: number
}
export interface Scorecard {
  exercise_id: string
  scale: string
  independent_of_gaps: boolean
  overall_score: number | null
  overall_status: string
  dimensions_assessed: number
  dimensions_total: number
  note: string
  dimensions: ScorecardDimension[]
}

// ---- reports (plain dict responses; shapes from backend/app/reports/router.py + service.py)
export interface ReportVersionSummary {
  id: string
  report_id: string
  version_no: number
  status: 'draft' | 'published' | string
  content_sha256: string
  ledger_head_seq: number | null
  ledger_head_hash: string | null
  parent_version_id: string | null
  generator_version: string | null
  created_at: string
  published_at: string | null
}
export interface ReportVersion extends ReportVersionSummary {
  content: Record<string, unknown>
  artifacts: { format: string; sha256: string; bytes: number; renderer: string | null }[]
}
export interface ReportFinding {
  id: string
  report_id: string
  title: string
  body: string
  code_hint: string | null
  severity_hint: number | null
  source_page: number | null
  status: string
  origin?: string
}
export interface Report {
  id: string
  kind: 'generated' | 'imported' | string
  title: string
  exercise_id: string | null
  confidentiality: string
  origin: string
  versions: number
  document: { sha256: string | null; filename: string | null; media_type: string | null; bytes: number | null; provenance: unknown } | null
  created_at: string | null
  version_list?: ReportVersionSummary[]
  findings?: ReportFinding[]
}
export interface ReportCompare {
  report_id: string
  a: { id: string; version_no: number; content_sha256: string }
  b: { id: string; version_no: number; content_sha256: string }
  diff: unknown
}
