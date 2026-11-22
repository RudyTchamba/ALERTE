import { describe, expect, it } from 'vitest'
import { buildMatrix, cellOf, summarize, type MMandate } from './matrix'

const insts = [{ id: 'I1', code: 'MET', name: 'Met' }, { id: 'I2', code: 'DPC', name: 'Civil protection' }]
const actions = [{ code: 'warn', label: 'Issue warning' }, { code: 'alert', label: 'Alert the public' }, { code: 'evac', label: 'Evacuate' }]
const m = (id: string, inst: string, action: string, kind: string, active = true, validation = 'validated'): MMandate => ({ id, institution_id: inst, action_code: action, kind, active, validation })

describe('responsibility matrix', () => {
  it('classifies cells: lead > owner kinds > ancillary > proposed > none', () => {
    expect(cellOf([m('a', 'I1', 'warn', 'lead')]).state).toBe('lead')
    expect(cellOf([m('a', 'I1', 'warn', 'duty')]).state).toBe('responsible')
    expect(cellOf([m('a', 'I1', 'warn', 'information_sharing')]).state).toBe('involved')
    expect(cellOf([m('a', 'I1', 'warn', 'duty', false, 'proposed')]).state).toBe('proposed')
    expect(cellOf([m('a', 'I1', 'warn', 'duty', false, 'rejected')]).state).toBe('none')
    expect(cellOf([]).state).toBe('none')
  })

  it('an action without owner is "nobody" only when every registry was declared complete', () => {
    const mandates = [m('1', 'I1', 'warn', 'duty'), m('2', 'I1', 'evac', 'power'), m('3', 'I2', 'evac', 'duty')]
    const partial = buildMatrix(actions, insts, mandates, new Set(['I1']))
    expect(partial.map((r) => r.state)).toEqual(['covered', 'undetermined', 'overlap'])
    const complete = buildMatrix(actions, insts, mandates, new Set(['I1', 'I2']))
    expect(complete.map((r) => r.state)).toEqual(['covered', 'orphan', 'overlap'])
    expect(summarize(complete)).toMatchObject({ total: 3, covered: 1, overlap: 1, orphan: 1, coverage: 67 })
  })

  it('a designated lead resolves an overlap', () => {
    const rows = buildMatrix([actions[2]], insts, [m('1', 'I1', 'evac', 'lead'), m('2', 'I2', 'evac', 'duty')], new Set())
    expect(rows[0].state).toBe('covered')
    expect(rows[0].owners).toEqual(['I1', 'I2'])
  })
})
