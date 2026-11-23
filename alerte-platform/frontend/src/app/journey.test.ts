import { describe, expect, it } from 'vitest'
import { PHASES, STEPS, stepFor, stepsOf } from './journey'

describe('parcours ALERTE', () => {
  it('chaque route de travail appartient à une étape et à une phase', () => {
    for (const [path, id, phase] of [['/studio/agents', 'agents', 'prepare'], ['/studio/knowledge/ABC/documents/D', 'knowledge', 'prepare'],
      ['/room/EX1', 'room', 'conduct'], ['/play', 'room', 'conduct'], ['/gaps/G1', 'gaps', 'analyse'], ['/audit/EX1', 'audit', 'analyse']]) {
      const r = stepFor(path)
      expect(r?.step.id, path).toBe(id)
      expect(r?.step.phase, path).toBe(phase)
    }
    expect(stepFor('/')).toBeNull()
    expect(stepFor('/help/glossary')).toBeNull()
  })
  it('les trois phases existent et la préparation est ordonnée', () => {
    expect(PHASES).toEqual(['prepare', 'conduct', 'analyse'])
    expect(stepsOf('prepare').map((s) => s.id)).toEqual(['institutions', 'knowledge', 'agents', 'access', 'scenarios', 'exercises'])
    expect(new Set(STEPS.map((s) => s.id)).size).toBe(STEPS.length)
  })
})
