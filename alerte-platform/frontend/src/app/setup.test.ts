import { describe, expect, it } from 'vitest'
import { computeSetup, nextStep, type SetupInput } from './setup'

const empty: SetupInput = { countries: [], institutions: [], kbs: [], mandates: [], reviews: [], agents: [], scenarios: [], exercises: [] }
const st = (d: Partial<SetupInput>) => Object.fromEntries(computeSetup({ ...empty, ...d }).map((s) => [s.id, s.status]))

describe('computeSetup', () => {
  it('workspace vide : pays à faire, le reste verrouillé', () => {
    const s = st({})
    expect(s.country).toBe('todo')
    expect(s.institutions).toBe('locked')
    expect(s.mandates).toBe('locked')
    expect(s.run).toBe('locked')
    expect(nextStep(computeSetup(empty))?.id).toBe('country')
  })
  it('KB non publiée ou sans pays = partielle, pas terminée', () => {
    expect(st({ kbs: [{ id: 'k', country_id: null, overview: { published_version_no: 1 } }] }).kb).toBe('partial')
    expect(st({ kbs: [{ id: 'k', country_id: 'c', overview: { published_version_no: null } }] }).kb).toBe('partial')
    expect(st({ kbs: [{ id: 'k', country_id: 'c', overview: { published_version_no: 2 } }] }).kb).toBe('done')
  })
  it('une base mondiale sans pays reste terminée', () => {
    expect(st({ kbs: [{ id: 'k', kind: 'global_practices', country_id: null, overview: { published_version_no: 1 } }] }).kb).toBe('done')
  })
  it('mandats : importés sans validation = partiel ; validé sans source ne compte pas', () => {
    const base = { countries: [{ id: 'c' }], institutions: [{ id: 'i' }], kbs: [{ id: 'k', country_id: 'c', overview: { published_version_no: 1 } }] }
    expect(st({ ...base, mandates: [{ institution_id: 'i', validation: 'proposed', sources: [] }] }).mandates).toBe('partial')
    expect(st({ ...base, mandates: [{ institution_id: 'i', validation: 'validated', sources: [] }] }).mandates).toBe('partial')
    expect(st({ ...base, mandates: [{ institution_id: 'i', validation: 'validated', sources: [{}] }, { institution_id: 'i', validation: 'proposed', sources: [] }] }).mandates).toBe('done')
  })
  it('permissions : partielles tant que tous les agents n\'ont pas une KB', () => {
    const a = [{ id: '1', institution_id: 'i', kb_ids: ['k'] }, { id: '2', institution_id: 'i', kb_ids: [] }]
    expect(st({ agents: a }).access).toBe('partial')
    expect(st({ agents: [a[0]] }).access).toBe('done')
  })
  it('exercice : prêt puis terminé', () => {
    expect(st({ exercises: [{ id: 'e', state: 'draft' }] }).readiness).toBe('todo')
    expect(st({ exercises: [{ id: 'e', state: 'ready' }] }).readiness).toBe('done')
    expect(st({ exercises: [{ id: 'e', state: 'completed' }] }).run).toBe('done')
  })
})
