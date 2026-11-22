import { describe, expect, it } from 'vitest'
import type { StreamEvent } from '@/api/sse'
import { BOARD, GAPS, SCENARIO, kbOf, seatVisuals, toSteps } from './narrate'

const ev = (seq: number, type: string, payload: Record<string, unknown>, seat: string | null = null): StreamEvent => ({
  seq, type, actor: seat ? `seat:${seat}` : 'coord', seat, sim_time: 'D1 06:00', real_time: '', visibility: 'public', payload,
})

describe('flow narration', () => {
  const events = [
    ev(1, 'INJECT', { title: 'Flood', recipients: ['MET', 'DPC'] }),
    ev(2, 'LLM_CALL', { model: 'm' }, 'MET'),
    ev(3, 'RETRIEVAL', { query: 'flood warning', results: [1, 2] }, 'MET'),
    ev(4, 'CITATION_CHECK', { citations: [{ pass: true }, { pass: false }] }, 'MET'),
    ev(5, 'DECISION', { seat_code: 'MET', action: 'Warn', status: 'not_verified', legal_basis: [{ article: 'Article 12' }] }, 'MET'),
    ev(6, 'BOARD', { from: 'MET', to: 'DPC', msg_type: 'REQUEST', body: 'Alert people' }, 'MET'),
    ev(7, 'GAP', { signal: 'NO_OWNER' }),
    ev(8, 'ERROR', { next_action: 'retry once' }, 'DPC'),
  ]
  const steps = toSteps(events)

  it('turns ledger events into visual steps with paths between nodes (model calls are not narrated)', () => {
    expect(steps.map((s) => s.kind)).toEqual(['inject', 'search', 'citation', 'decision', 'message', 'gap', 'error'])
    expect(steps[0].paths).toEqual([[SCENARIO, 'MET'], [SCENARIO, 'DPC']])
    expect(steps[1].paths).toEqual([['MET', kbOf('MET'), 'MET']])
    expect(steps[1].params).toMatchObject({ seat: 'MET', query: 'flood warning', n: 2 })
    expect(steps[4].paths).toEqual([['MET', BOARD, 'DPC']])
    expect(steps[5].paths).toEqual([[BOARD, GAPS]])
  })

  it('a partially valid citation check and an unverified decision are shown as refusals', () => {
    expect(steps[2]).toMatchObject({ say: 'citationKo', tone: 'danger', params: { ok: 1, n: 2 } })
    expect(steps[3]).toMatchObject({ say: 'decisionKo', tone: 'danger', params: { article: 'Article 12' } })
    expect(steps[6].say).toBe('errorRetry')
  })

  it('seat visuals: the last status wins and "thinking" only lasts for the current step', () => {
    expect(seatVisuals(steps, 1)).toEqual({ MET: 'thinking' })
    expect(seatVisuals(steps, 2)).toEqual({})
    expect(seatVisuals(steps, 3)).toEqual({ MET: 'refused' })
  })
})
