import { describe, expect, it } from 'vitest'
import { mockFetch } from '@/test/utils'
import type { Exercise } from '@/api/loose'
import { runWhatIf } from './runWhatIf'

const ID = (n: string) => n.padEnd(26, '0')
const B1 = ID('B1'), R1 = ID('R1')
const base = { id: ID('BASE'), code: 'EX-1', title: 'Base', state: 'completed', settings: { max_llm_calls: 199 } } as unknown as Exercise

describe('runWhatIf', () => {
  it('plays a scripted baseline and a scripted reform run cloned from the base, then compares them', async () => {
    let n = 0
    const { calls } = mockFetch({
      'POST /exercises': () => ({ status: 201, body: { id: ++n === 1 ? B1 : R1, code: `EX-${n + 1}` } }),
      'POST /exercises/:id/ready': { id: 'x' },
      'POST /exercises/:id/commands': { status: 202, body: { id: 'c' } },
      'GET /exercises/:id': { state: 'completed', code: 'EX' },
      'POST /exercises/:id/detect-gaps': { gaps: [] },
      'GET /gaps/compare': { a: B1, b: R1, new: [], persistent: [], resolved: [{ id: 'g', code: 'G1', title: 'Orphan' }], summary: { new: 0, persistent: 0, resolved: 1 } },
    })
    const stages: string[] = []
    const reform = { institution_id: 'I2', action_code: 'alert', kind: 'duty', has_deadline: true, description: 'DPC alerts within 15 min' }
    const res = await runWhatIf(base, [reform], { baseline: 'Ref', reform: 'What if' }, (s) => stages.push(s), { pollMs: 1, timeoutMs: 1000 })
    expect(stages).toEqual(['baseline', 'reform', 'compare', 'done'])
    expect(res).toMatchObject({ baselineId: B1, reformId: R1, compare: { summary: { resolved: 1 } } })
    const creates = calls.filter((c) => c.method === 'POST' && c.path.endsWith('/exercises'))
    expect(creates.map((c) => c.query)).toEqual([`?from=${ID('BASE')}`, `?from=${ID('BASE')}`])
    expect(creates.map((c) => (c.body as { settings: { reform_mandates: unknown[] } }).settings.reform_mandates)).toEqual([[], [reform]])
    expect(creates.every((c) => (c.body as { ai_mode: string }).ai_mode === 'scripted')).toBe(true)
    expect(calls.find((c) => c.path === '/gaps/compare')?.query).toBe(`?a=${B1}&b=${R1}`)
  })
})
