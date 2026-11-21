import { beforeEach, describe, expect, it, vi } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { apiError, axeViolations, FakeEventSource, mockFetch, renderPage } from '@/test/utils'
import { EntryPage } from './access/EntryPage'
import { CountriesPage } from './geo/CountriesPage'
import { KbListPage } from './kb/KbListPage'
import { AccessPage } from './agents/AccessPage'
import { ScenarioBuilderPage } from './scenarios/ScenarioBuilderPage'
import { ExercisePage } from './scenarios/ExercisePage'
import { RoomPage } from './room/RoomPage'
import { PlayerPage } from './room/PlayerPage'
import { GapsPage } from './gaps/GapsPage'
import { AuditPage } from './audit/AuditPage'
import { EvaluationPage } from './evaluation/EvaluationPage'
import { ReportsPage } from './reports/ReportsPage'

const ID = (n: string) => n.padEnd(26, '0').toUpperCase()
const ws = { id: ID('W'), name: 'Demo', slug: 'demo', created_at: '2026-01-01T00:00:00Z', archived_at: null }
const base = { 'GET /workspaces/current': ws, 'GET /tokens': [] }
const iso = '2026-01-01T00:00:00Z'

describe('Entry', () => {
  it('creates a workspace and shows the owner token ONCE with a warning and a copy button', async () => {
    const user = userEvent.setup()
    const { calls } = mockFetch({ 'POST /workspaces': { status: 201, body: { workspace: ws, owner_token: 'owner-secret-123' } } })
    renderPage(<EntryPage />, { token: null, path: '/', route: '/' })
    await user.type(screen.getByLabelText(/workspace name/i), 'Demo')
    await user.click(screen.getByRole('button', { name: /create workspace/i }))
    expect(await screen.findByText('owner-secret-123')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(/shown only once/i)
    expect(screen.getByRole('button', { name: /copy/i })).toBeInTheDocument()
    expect(calls[0].body).toEqual({ name: 'Demo' })
    expect(calls[0].headers.get('authorization')).toBeNull()
    expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled()
    expect(sessionStorage.getItem('alerte.token')).toBeNull() // not stored until the user confirms
  })

  it('rejects an invalid token with a clear message and stores nothing', async () => {
    const user = userEvent.setup()
    mockFetch({ 'GET /workspaces/current': apiError(401, 'auth.invalid_token', 'x') })
    renderPage(<EntryPage />, { token: null })
    await user.type(screen.getByLabelText(/access token/i), 'wrong-token-1')
    await user.click(screen.getByRole('button', { name: /^sign in$/i }))
    expect(await screen.findByText(/invalid, expired or revoked/i)).toBeInTheDocument()
    expect(sessionStorage.getItem('alerte.token')).toBeNull()
  })

  it('has no axe violation', async () => {
    mockFetch({})
    const { container } = renderPage(<EntryPage />, { token: null })
    expect(await axeViolations(container)).toEqual([])
  })
})

describe('Countries & institutions', () => {
  const country = { id: ID('C1'), name: 'Cameroon', iso2: 'CM', languages: ['fr', 'en'], notes: null, created_at: iso, archived_at: null }
  it('lists countries and creates one with validated fields', async () => {
    const user = userEvent.setup()
    const { calls } = mockFetch({ ...base, 'GET /countries': [country], 'POST /countries': { status: 201, body: { ...country, id: ID('C2'), name: 'UAE' } } })
    renderPage(<CountriesPage />)
    expect(await screen.findByText('Cameroon')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /new country/i }))
    await user.click(screen.getByRole('button', { name: /^save$/i }))
    expect(await screen.findByText(/this field is required/i)).toBeInTheDocument()
    await user.type(screen.getByLabelText(/^name/i), 'UAE')
    await user.type(screen.getByLabelText(/alpha-2/i), 'AE')
    await user.type(screen.getByLabelText(/languages/i), 'ar, en')
    await user.click(screen.getByRole('button', { name: /^save$/i }))
    await waitFor(() => expect(calls.find((c) => c.method === 'POST')?.body).toEqual({ name: 'UAE', iso2: 'AE', languages: ['ar', 'en'], notes: null }))
  })

  it('explains a 409 on delete and offers to archive instead', async () => {
    const user = userEvent.setup()
    const { calls } = mockFetch({
      ...base, 'GET /countries': [country], 'DELETE /countries/:id': apiError(409, 'country.in_use', 'referenced by an exercise'),
      'POST /countries/:id/archive': { ...country, archived_at: iso },
    })
    renderPage(<CountriesPage />)
    await screen.findByText('Cameroon')
    await user.click(screen.getByRole('button', { name: /^delete$/i }))
    const dlg = await screen.findByRole('dialog', { name: /cannot delete/i })
    expect(dlg).toHaveTextContent(/archive it instead/i)
    await user.click(within(dlg).getByRole('button', { name: /archive instead/i }))
    await waitFor(() => expect(calls.some((c) => c.method === 'POST' && c.path.endsWith('/archive'))).toBe(true))
  })
})

describe('Knowledge bases', () => {
  it('lists KBs with publication state and documentary coverage', async () => {
    mockFetch({ ...base, 'GET /knowledge-bases': [{
      id: ID('K1'), code: 'KB-1', name: 'Cameroon corpus', description: null, country_id: null, domain: null, kind: 'national', languages: ['fr'], embedder_key: null, embedder_fingerprint: null, chunking_params: null, status: 'active', archived_at: null,
      overview: { published_version_no: null, documents: 3, chunks: 40, embedded_chunks: 0, coverage: { ratio: 0.5, expected: 4, present: 2, missing: ['x'] } },
    }] })
    renderPage(<KbListPage />, { route: '/studio/knowledge', path: '/studio/knowledge' })
    expect(await screen.findByText('Cameroon corpus')).toBeInTheDocument()
    expect(screen.getByText('unpublished')).toBeInTheDocument()
    expect(screen.getByText(/50 % \(2\/4\)/)).toBeInTheDocument()
  })
})

describe('Knowledge access matrix', () => {
  it('is keyboard-operable: toggling a cell PUTs the full grant list for that agent and announces it', async () => {
    const user = userEvent.setup()
    const { calls } = mockFetch({
      ...base,
      'GET /access-matrix': { agents: [{ id: ID('A1'), code: 'MET', name: 'Met agent', institution_id: null, role_kind: 'institution', archived: false }, { id: ID('A2'), code: 'DPC', name: 'Civil prot.', institution_id: null, role_kind: 'institution', archived: false }], knowledge_bases: [], grants: [{ agent_id: ID('A1'), kb_id: ID('K1'), mode: 'read' }] },
      'GET /knowledge-bases': [{ id: ID('K1'), name: 'National', archived_at: null }, { id: ID('K2'), name: 'Global', archived_at: null }],
      'PUT /agents/:id/kb-grants': ({ body }: { body: unknown }) => ({ body }),
    })
    renderPage(<AccessPage />)
    const cell = await screen.findByRole('checkbox', { name: 'MET may read Global' })
    expect(screen.getByRole('checkbox', { name: 'MET may read National' })).toBeChecked()
    expect(screen.getByRole('alert')).toHaveTextContent(/DPC/) // agent without KB is flagged
    cell.focus()
    await user.keyboard(' ')
    await waitFor(() => expect(calls.find((c) => c.method === 'PUT')?.body).toEqual({ kb_ids: [ID('K1'), ID('K2')] }))
    expect(await screen.findByText('MET can now read Global')).toBeInTheDocument()
  })
})

describe('Scenario builder', () => {
  it('shows injects, who-receives-what and live lint results', async () => {
    mockFetch({
      ...base,
      'GET /scenarios/:id': { id: ID('S1'), code: 'FLOOD', title: 'River flood', description: '', language: 'en', version: 1, status: 'draft', country_id: null, is_template: false, cloned_from_id: null },
      'GET /scenarios/:id/injects': [
        { id: ID('I1'), scenario_id: ID('S1'), seq: 1, sim_time: 'D1 06:00', title: 'Rain', body: '', from_actor: 'MET', fault_mode: 'none', system_output: null, source_note: null, recipients: [ID('N1')], tags: ['life_risk'], demands: [] },
        { id: ID('I2'), scenario_id: ID('S1'), seq: 2, sim_time: 'D1 07:00', title: 'Dam', body: '', from_actor: 'OPS', fault_mode: 'false_alarm', system_output: null, source_note: null, recipients: [], tags: [], demands: [] },
      ],
      'GET /institutions': [{ id: ID('N1'), code: 'MET', name: 'Met', name_local: null, country_id: null, kind: 'agency', domains: [], description: null, created_at: iso }],
      'GET /scenarios/:id/lint': { scenario_id: ID('S1'), ok: false, issues: [{ severity: 'error', code: 'inject.no_recipient', message: 'inject 2 without recipient', inject_id: ID('I2'), seq: 2 }], stats: { injects: 2, recipients_total: 1, fault_modes: ['false_alarm'], distinct_fault_modes: 1, estimated_llm_calls: { max: 16, typical: 4, cap: 199, formula: 'f' } } },
    })
    renderPage(<ScenarioBuilderPage />, { route: `/studio/scenarios/${ID('S1')}`, path: '/studio/scenarios/:scenarioId' })
    expect(await screen.findByText('River flood')).toBeInTheDocument()
    expect(await screen.findByText('inject 2 without recipient')).toBeInTheDocument()
    expect(screen.getByText('Blocking issues')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /move “rain” down/i })).toBeEnabled()
    expect(screen.getByRole('button', { name: /move “rain” up/i })).toBeDisabled()
    expect(screen.getByRole('table', { name: /who receives what/i })).toBeInTheDocument()
  })
})

describe('Participants & readiness', () => {
  it('lists blocking checks and keeps launch disabled until ready', async () => {
    const ex = { id: ID('E1'), code: 'EX1', title: 'Flood run', state: 'draft', substate: null, pace: 'manual', ai_mode: 'scripted', scenario_id: ID('S1'), parent_exercise_id: null, settings: {}, started_at: null, ended_at: null, snapshot_sha256: null, commitment_sha256: null, llm_calls_used: 0, seats: [{ code: 'MET', institution_id: ID('N1'), agent_id: null, controller: 'agent', human_name: null }] }
    mockFetch({ ...base, 'GET /exercises/:id': ex, 'GET /institutions': [], 'GET /agents': [], 'GET /scenarios/:id/injects': [],
      'GET /exercises/:id/readiness': { ok: false, blocking: [{ level: 'blocking', code: 'seat.no_controller', message: 'agent seat without agent', subject: 'MET' }], warnings: [] } })
    renderPage(<ExercisePage />, { route: `/studio/exercises/${ID('E1')}`, path: '/studio/exercises/:exerciseId' })
    expect(await screen.findByText('agent seat without agent', { exact: false })).toBeInTheDocument()
    expect(screen.getByText(/NO AI — scripted run/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /launch the exercise/i })).toBeDisabled()
  })
})

describe('Simulation Room', () => {
  beforeEach(() => { FakeEventSource.reset(); vi.stubGlobal('EventSource', FakeEventSource) })
  const ex = { id: ID('E1'), code: 'EX1', title: 'Flood run', state: 'running', substate: null, pace: 'manual', ai_mode: 'scripted', scenario_id: ID('S1'), parent_exercise_id: null, settings: { max_llm_calls: 199 }, started_at: iso, ended_at: null, snapshot_sha256: 'a', commitment_sha256: 'b', llm_calls_used: 41, seats: [{ code: 'MET', institution_id: ID('N1'), agent_id: null, controller: 'agent', human_name: null }, { code: 'DPC', institution_id: ID('N2'), agent_id: null, controller: 'human', human_name: 'Marie' }] }

  it('shows header, budget, NO-AI banner, and derives cards/board/signals from the SSE stream; opens the trace', async () => {
    const user = userEvent.setup()
    mockFetch({ ...base, 'GET /exercises/:id': ex, 'POST /exercises/:id/stream-token': { body: { stream_token: 'one-time', expires_in: 60, exercise_id: ex.id, role: 'owner' } } })
    renderPage(<RoomPage />, { route: `/room/${ex.id}`, path: '/room/:exerciseId' })
    expect(await screen.findByText('Flood run')).toBeInTheDocument()
    expect(screen.getByText(/NO AI — scripted run/i)).toBeInTheDocument()
    expect(screen.getByText('41/199')).toBeInTheDocument()
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1))
    const es = FakeEventSource.instances[0]
    expect(es.url).toContain('stream_token=one-time')
    expect(es.url).not.toMatch(/token=test-token/)
    es.open()
    es.emit(1, 'INJECT', { inject_ref: 'inj-1', seq: 1, title: 'River rising', recipients: ['MET'], tags: [], fault_mode: 'none' }, { sim_time: 'D1 07:10' })
    es.emit(2, 'BOARD', { msg_id: 'm1', from: 'MET', to: 'DPC', msg_type: 'REQUEST', body: 'Please evacuate zone B', round: 1 }, { actor: 'seat:MET', seat: 'MET' })
    es.emit(3, 'RETRIEVAL', { query: 'evacuation power', results: [{ chunk_id: 'CH1', score: 0.8123, rank: 1 }] }, { actor: 'seat:MET', seat: 'MET', visibility: 'seat' })
    es.emit(4, 'DECISION', { decision_id: 'D1', seat_code: 'MET', action: 'Refer to DPC', outcome: 'refer', status: 'not_verified', confidence: 'low', legal_basis: [{ chunk_id: 'CH1', article: '33', quote: 'q', check: 'fail', reason: 'quote_not_in_chunk' }] }, { actor: 'seat:MET', seat: 'MET' })
    es.emit(5, 'GAP', { signal: 'ORPHAN_REQUEST', origin_kind: 'coordinator_signal', inject_ref: 'inj-1' }, { visibility: 'audit' })
    es.emit(6, 'HUMAN', { kind: 'task_opened', seat: 'DPC' }, { seat: 'DPC', visibility: 'seat' })
    expect(await screen.findByText(/River rising/)).toBeInTheDocument()
    expect(screen.getByText(/D1 07:10 — River rising/)).toBeInTheDocument()
    expect(screen.getByText('D1 06:00')).toBeInTheDocument() // header clock = sim_time of the latest event
    expect(await screen.findByText('Please evacuate zone B')).toBeInTheDocument()
    expect(screen.getByText('Not verified')).toBeInTheDocument() // verified/unverified is a word, not only a colour
    expect(screen.getByText('Orphan request')).toBeInTheDocument()
    expect(screen.getByText('Waiting for a human')).toBeInTheDocument()
    await user.click(screen.getAllByRole('button', { name: /decision trace/i })[0])
    const dlg = await screen.findByRole('dialog', { name: /decision trace/i })
    expect(dlg).toHaveTextContent('0.8123')
    expect(dlg).toHaveTextContent('quote_not_in_chunk')
  })

  it('sends commands through the API and filters the board by message type', async () => {
    const user = userEvent.setup()
    const { calls } = mockFetch({ ...base, 'GET /exercises/:id': ex, 'POST /exercises/:id/stream-token': { body: { stream_token: 't', expires_in: 60 } }, 'POST /exercises/:id/commands': { status: 202, body: { id: 'c', kind: 'pause', status: 'queued', exercise_state: 'running' } } })
    renderPage(<RoomPage />, { route: `/room/${ex.id}`, path: '/room/:exerciseId' })
    await screen.findByText('Flood run')
    await user.click(screen.getByRole('button', { name: /^pause$/i }))
    await waitFor(() => expect(calls.find((c) => c.path.endsWith('/commands'))?.body).toEqual({ kind: 'pause' }))
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1))
    const es = FakeEventSource.instances[0]
    es.emit(1, 'BOARD', { msg_id: 'a', from: 'MET', to: 'DPC', msg_type: 'INFO', body: 'info msg', round: 1 })
    es.emit(2, 'BOARD', { msg_id: 'b', from: 'DPC', to: 'MET', msg_type: 'OBJECTION', body: 'objection msg', round: 2 })
    await screen.findByText('objection msg')
    await user.click(screen.getByRole('checkbox', { name: 'INFO' }))
    expect(screen.queryByText('info msg')).toBeNull()
    expect(screen.getByText('objection msg')).toBeInTheDocument()
  })
})

describe('Player seat', () => {
  it('reads the token from the URL fragment, strips it from the address bar and never sends it in a URL', async () => {
    window.history.replaceState(null, '', '/play#t=seat-token-xyz')
    const user = userEvent.setup()
    const card = { exercise: { id: ID('E1'), code: 'EX1', title: 'Flood run', state: 'running', ai_mode: 'ai' }, seat: { code: 'DPC', human_name: 'Marie', controller: 'human' }, institution: { id: ID('N2'), code: 'DPC', name: 'Civil protection', kind: 'agency' }, role: { mission: 'Protect people', instructions: null, tools: ['search_kb'], limits: null }, mandates: [], knowledge_bases: [{ kb_id: ID('K1'), code: 'KB', name: 'National' }], seat_codes: ['MET'] }
    const { calls } = mockFetch({
      'GET /seats/me': card,
      'GET /seats/me/task': { exercise_state: 'running', task: { id: 't1', status: 'pending', round: 1, inject_ref: 'inj-1', deadline_at: iso, fallback: 'agent_takeover', inject: { inject_ref: 'inj-1', sim_time: 'D1 07:10', title: 'River rising', body: 'Water level 5 m', from_actor: 'MET', tags: [] }, inbox: [], board: [], own_decisions: [], staged_posts: [], usage: {}, limits: {} } },
      'POST /exercises/:id/stream-token': { body: { stream_token: 'st', expires_in: 60 } },
      'POST /seats/me/decision': apiError(422, 'decision.citation_failed', 'citation', { failures: [{ chunk_id: 'CH9', reason: 'quote_not_in_chunk' }] }),
    })
    vi.stubGlobal('EventSource', FakeEventSource)
    renderPage(<PlayerPage />, { token: null, route: '/play', path: '/play' })
    expect(await screen.findByText(/It is your turn/)).toBeInTheDocument()
    expect(window.location.hash).toBe('')
    expect(calls.every((c) => !c.url.includes('seat-token-xyz'))).toBe(true)
    expect(calls[0].headers.get('authorization')).toBe('Bearer seat-token-xyz')
    await user.type(screen.getByLabelText(/action taken or refused/i), 'Evacuate')
    await user.type(screen.getByLabelText(/public rationale/i), 'Because')
    await user.click(screen.getByRole('button', { name: /add citation/i }))
    await user.type(screen.getByPlaceholderText('chunk_id'), 'CH9')
    await user.type(screen.getByLabelText(/exact quote/i), 'made up')
    await user.click(screen.getByRole('button', { name: /submit decision/i }))
    const err = await screen.findByText(/the quote is not in the chunk text/i)
    expect(err.closest('[role=alert]')).toHaveTextContent('CH9')
  })

  it('shows an invalid-link message when there is no token', async () => {
    window.history.replaceState(null, '', '/play')
    mockFetch({})
    renderPage(<PlayerPage />, { token: null, route: '/play', path: '/play' })
    expect(await screen.findByText(/link is invalid or has expired/i)).toBeInTheDocument()
  })
})

describe('Gap analysis', () => {
  const gap = { id: ID('G1'), exercise_id: ID('E1'), fingerprint: 'f', code: 'G1', rule_id: 'r', category: 'mandate_absent_or_incomplete', title: 'No institution may compel operators', description: 'desc', domain: null, institution_ids: [], action_code: 'compel', evidence_basis: 'documented', confidence: 'medium', severity: 3, auto_severity: 3, consequence: null, validation_status: 'proposed', origin: 'rule', registry_state: 'partial', cause: 'institutional', corpus_coverage: 0.5, demand_derivation: 'scenario_author', inject_refs: [], detail: {}, is_current: true, created_at: iso }
  it('lists gaps with their nature in words', async () => {
    mockFetch({ ...base, 'GET /gaps': [gap], 'GET /exercises': [], 'GET /institutions': [] })
    renderPage(<GapsPage />, { route: '/gaps', path: '/gaps' })
    expect(await screen.findByText('No institution may compel operators')).toBeInTheDocument()
    expect(screen.getByText('Deduced from a rule')).toBeInTheDocument()
    expect(screen.getByText('Supported by documents')).toBeInTheDocument()
    expect(screen.getByText('To review')).toBeInTheDocument()
    expect(within(screen.getByRole('table', { name: /gap analysis/i })).getByText('High')).toBeInTheDocument()
  })

  it('shows the evidence chain, "insufficient sources" as is, and requires a reason to dispute', async () => {
    const user = userEvent.setup()
    const { calls } = mockFetch({
      ...base, 'GET /gaps': [gap], 'GET /exercises': [], 'GET /institutions': [],
      'GET /gaps/:id': { ...gap, evidence: [
        { id: 'e1', kind: 'mandate', role: 'context', ref: { mandate_id: 'M1' }, excerpt: 'Power to alert', is_agent: false },
        { id: 'e2', kind: 'decision', role: 'supports', ref: { decision_id: 'D1' }, excerpt: 'Refer to regulator', is_agent: false },
      ], negative_searches: [{ id: 'n1', action_code: 'compel', kb_ids: [], queries: ['compel operators'], languages: ['fr'], corpus_documents: 3, corpus_coverage: 0.5, coverage_missing: ['Decree 2020/12'], top_hits: [], verdict: 'confirmed_absent', run_at: iso, statement: 'not found in corpus K (3 documents; languages fr; queries 1)' }],
        references: [], reviews: [], improvement_actions: [], reference_status: { status: 'insufficient_sources', message: 'international sources insufficient: 1 found (minimum 2 jurisdictions)', count: 1 } },
      'GET /gaps/:id/reference-suggestions': [],
      'POST /gaps/:id/reviews': { status: 201, body: { id: 'r1' } },
    })
    renderPage(<GapsPage />, { route: `/gaps/${gap.id}`, path: '/gaps/:gapId' })
    expect(await screen.findByText('1. Mandate')).toBeInTheDocument()
    expect(screen.getByText('2. Decision')).toBeInTheDocument()
    expect(screen.getByText(/not found in corpus K/)).toBeInTheDocument()
    expect(screen.getByText(/Decree 2020\/12/)).toBeInTheDocument()
    expect(screen.getByText(/international sources insufficient: 1 found/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Refer to regulator/ }))
    expect(screen.getByRole('link', { name: /open decision trace/i })).toHaveAttribute('href', `/audit/${ID('E1')}?decision=D1`)
    await user.selectOptions(screen.getByLabelText(/^decision$/i), 'dispute')
    const submit = screen.getByRole('button', { name: /record review/i })
    expect(submit).toBeDisabled() // a reason is mandatory for dispute / reject
    await user.type(screen.getByLabelText(/^reason/i), 'Decree X gives this power')
    expect(submit).toBeEnabled()
    await user.click(submit)
    await waitFor(() => expect(calls.find((c) => c.path.endsWith('/reviews'))?.body).toMatchObject({ action: 'dispute', comment: 'Decree X gives this power' }))
  })
})

describe('Audit & replay', () => {
  const ex = { id: ID('E1'), code: 'EX1', title: 'Flood run', state: 'completed', substate: null, pace: 'auto', ai_mode: 'ai', scenario_id: ID('S1'), parent_exercise_id: null, settings: {}, started_at: iso, ended_at: iso, snapshot_sha256: 'a', commitment_sha256: 'b', llm_calls_used: 3, seats: [] }
  const ledger = [
    { seq: 1, type: 'INJECT', actor: 'coord', seat_id: null, sim_time: 'D1 06:00', real_time: iso, visibility: 'public', payload: { inject_ref: 'i', title: 'Rain' }, hash: 'h1' },
    { seq: 2, type: 'DECISION', actor: 'seat:MET', seat_id: 's', sim_time: 'D1 06:00', real_time: iso, visibility: 'public', payload: { decision_id: 'D1', seat_code: 'MET', action: 'Refer', outcome: 'refer', status: 'recorded', legal_basis: [] }, hash: 'h2' },
  ]
  const routes = (verify: unknown) => ({ ...base, 'GET /exercises/:id': ex, 'GET /exercises/:id/ledger': ledger, 'GET /exercises/:id/anchors': [], 'GET /exercises/:id/replay-digest': { replay_digest: 'abc', events: 2 }, 'GET /exercises/:id/ledger/verify': verify })
  it('verifies an intact ledger', async () => {
    const user = userEvent.setup()
    mockFetch(routes({ ok: true, checked: 2, first_bad_seq: null, reason: null, anchor_mismatch: false, truncated_after_anchor: false, head_seq: 2, head_hash: 'h2' }))
    renderPage(<AuditPage />, { route: `/audit/${ex.id}`, path: '/audit/:exerciseId' })
    await screen.findAllByText('Rain', { exact: false })
    await user.click(screen.getByRole('button', { name: /verify the ledger/i }))
    expect(await screen.findByText(/Ledger intact \(2 entries checked\)/)).toBeInTheDocument()
    expect(screen.getByText(/tamper-evident, not tamper-proof/i)).toBeInTheDocument()
  })
  it('reports the first altered entry', async () => {
    const user = userEvent.setup()
    mockFetch(routes({ ok: false, checked: 2, first_bad_seq: 2, reason: 'hash mismatch', anchor_mismatch: false, truncated_after_anchor: false, head_seq: 2, head_hash: 'h2' }))
    renderPage(<AuditPage />, { route: `/audit/${ex.id}`, path: '/audit/:exerciseId' })
    await screen.findAllByText('Rain', { exact: false })
    await user.click(screen.getByRole('button', { name: /verify the ledger/i }))
    expect(await screen.findByText('First altered entry: #2')).toBeInTheDocument()
  })
  it('opens a decision trace from the timeline', async () => {
    const user = userEvent.setup()
    mockFetch(routes({}))
    renderPage(<AuditPage />, { route: `/audit/${ex.id}`, path: '/audit/:exerciseId' })
    await user.click(await screen.findByRole('link', { name: /refer — decision trace/i }))
    expect(await screen.findByRole('dialog', { name: /decision trace/i })).toBeInTheDocument()
  })
})

describe('Evaluation', () => {
  it('shows "not computed" as such (never 0) and the scorecard "not assessed"', async () => {
    const user = userEvent.setup()
    const ex = { id: ID('E1'), code: 'EX1', title: 'Flood run', state: 'completed', scenario_id: ID('S1'), settings: {}, ai_mode: 'ai', pace: 'auto', substate: null, parent_exercise_id: null, started_at: iso, ended_at: iso, snapshot_sha256: null, commitment_sha256: null, llm_calls_used: 0, seats: [] }
    const nc = (m: string) => ({ metric: m, status: 'not_computed', value: null, passed: null, reason: 'not run', threshold: { label: 'target' } })
    mockFetch({
      ...base, 'GET /exercises': [ex], 'GET /knowledge-bases': [], 'GET /scenarios': [],
      'GET /evaluation/exercises/:id': { exercise_id: ex.id, thresholds: {}, metrics: { T1: nc('T1'), T2: { metric: 'T2', status: 'computed', value: 0.96, passed: true, reason: null, threshold: { label: '≥ 95 %' } }, T3: nc('T3'), T4: nc('T4'), T5: nc('T5'), T6: nc('T6') } },
      'GET /scorecard/exercises/:id': { exercise_id: ex.id, scale: '0-5', independent_of_gaps: true, overall_score: null, overall_status: 'not_assessed', dimensions_assessed: 0, dimensions_total: 1, note: 'n', dimensions: [{ dimension_id: 'd1', number: 1, name: 'Governance', short_name: 'Gov', factor: null, question: null, criteria: [], score: null, status: 'not_assessed', assessed: 0, total: 0 }] },
    })
    renderPage(<EvaluationPage />)
    await screen.findByRole('option', { name: /EX1/ })
    await user.selectOptions(screen.getByLabelText(/^exercise$/i), ex.id)
    expect(await screen.findByText('96.0 %')).toBeInTheDocument()
    expect((await screen.findAllByText('not computed')).length).toBeGreaterThanOrEqual(5)
    expect(screen.queryByText('0.0 %')).toBeNull()
    expect(screen.getAllByText('not assessed').length).toBeGreaterThan(0)
    expect(screen.getByRole('img', { name: /radar chart/i })).toBeInTheDocument()
  })
})

describe('Reports', () => {
  it('shows an explicit "backend not available yet" state when the route is missing (no invented data)', async () => {
    mockFetch({ ...base, 'GET /exercises': [] })
    renderPage(<ReportsPage />, { route: '/reports', path: '/reports' })
    expect(await screen.findByText(/backend not available yet/i)).toBeInTheDocument()
  })
  it('lists reports, flags imported ones as a prior analysis', async () => {
    mockFetch({ ...base, 'GET /exercises': [], 'GET /reports': [{ id: ID('R1'), title: 'Technical report v2', kind: 'imported', versions: 0, created_at: iso }, { id: ID('R2'), title: 'Run 1', kind: 'generated', versions: 2, created_at: iso }] })
    renderPage(<ReportsPage />, { route: '/reports', path: '/reports' })
    expect(await screen.findByText('Technical report v2')).toBeInTheDocument()
    expect(screen.getByText('Prior analysis')).toBeInTheDocument()
  })
})
