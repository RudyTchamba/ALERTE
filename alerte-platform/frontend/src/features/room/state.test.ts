import { describe, expect, it } from 'vitest'
import type { StreamEvent } from '@/api/sse'
import { initialRoomState, roomReducer } from './state'
import { buildTrace } from './trace'

const ev = (seq: number, type: string, payload: Record<string, unknown>, extra: Partial<StreamEvent> = {}): StreamEvent => ({
  seq, type, actor: 'coord', seat: null, sim_time: 'D1 06:00', real_time: 't', visibility: 'public', payload, ...extra,
})
const run = (events: StreamEvent[]) => roomReducer(initialRoomState, { type: 'events', events })

describe('room reducer', () => {
  it('derives timeline, decisions, board, signals, state and budget from events', () => {
    const s = run([
      ev(1, 'STATE', { from: 'ready', to: 'running' }),
      ev(2, 'INJECT', { inject_ref: 'inj-001', seq: 1, title: 'Flood', recipients: ['MET'], tags: [], fault_mode: 'none' }),
      ev(3, 'LLM_CALL', {}, { actor: 'seat:MET', seat: 'MET', visibility: 'audit' }),
      ev(4, 'BOARD', { msg_id: 'm1', from: 'MET', to: 'DPC', msg_type: 'REQUEST', body: 'hello', round: 1 }, { actor: 'seat:MET', seat: 'MET' }),
      ev(5, 'DECISION', { decision_id: 'd1', seat_code: 'MET', outcome: 'refer', status: 'not_verified', action: 'x', legal_basis: [] }, { actor: 'seat:MET', seat: 'MET' }),
      ev(6, 'GAP', { signal: 'ORPHAN_REQUEST', origin_kind: 'coordinator_signal', inject_ref: 'inj-001' }, { visibility: 'audit' }),
    ])
    expect(s.exerciseState).toBe('running')
    expect(s.injects.map((i) => i.title)).toEqual(['Flood'])
    expect(s.currentInject).toBe('inj-001')
    expect(s.llmCalls).toBe(1)
    expect(s.board[0]).toMatchObject({ type: 'REQUEST', from: 'MET', round: 1 })
    expect(s.decisions[0]).toMatchObject({ seat: 'MET', status: 'not_verified' })
    expect(s.signals[0].signal).toBe('ORPHAN_REQUEST')
    expect(s.lastSeq).toBe(6)
  })

  it('is idempotent: replayed or duplicated events change nothing', () => {
    const a = ev(1, 'INJECT', { inject_ref: 'i', title: 'T' })
    const once = run([a])
    const twice = roomReducer(once, { type: 'events', events: [a, a] })
    expect(twice).toBe(once)
  })

  it('tracks a human seat waiting then submitting', () => {
    let s = run([ev(1, 'HUMAN', { kind: 'task_opened', seat: 'DPC' }, { seat: 'DPC' })])
    expect(s.seats.DPC.awaitingHuman).toBe(true)
    s = roomReducer(s, { type: 'events', events: [ev(2, 'HUMAN', { kind: 'submitted', seat: 'DPC' }, { seat: 'DPC' })] })
    expect(s.seats.DPC.awaitingHuman).toBe(false)
  })

  it('builds a decision trace from the ledger events of the deciding seat', () => {
    const events = [
      ev(1, 'RETRIEVAL', { query: 'q0', results: [] }, { actor: 'seat:MET', seat: 'MET' }),
      ev(2, 'DECISION', { decision_id: 'd0', seat_code: 'MET' }, { actor: 'seat:MET', seat: 'MET' }),
      ev(3, 'RETRIEVAL', { query: 'q1', results: [{ chunk_id: 'C1', score: 0.9, rank: 1 }] }, { actor: 'seat:MET', seat: 'MET' }),
      ev(4, 'RETRIEVAL', { query: 'other', results: [] }, { actor: 'seat:DPC', seat: 'DPC' }),
      ev(5, 'LLM_CALL', { provider: 'p' }, { actor: 'seat:MET', seat: 'MET' }),
      ev(6, 'CITATION_CHECK', { decision_id: 'd1', citations: [{ chunk_id: 'C1', pass: true }] }, { actor: 'seat:MET', seat: 'MET' }),
      ev(7, 'DECISION', { decision_id: 'd1', seat_code: 'MET' }, { actor: 'seat:MET', seat: 'MET' }),
    ]
    const tr = buildTrace(events, 'd1')!
    expect(tr.retrievals.map((r) => r.payload.query)).toEqual(['q1'])
    expect(tr.llmCalls).toHaveLength(1)
    expect(tr.citationChecks).toHaveLength(1)
    expect(buildTrace(events, 'nope')).toBeNull()
  })
})
