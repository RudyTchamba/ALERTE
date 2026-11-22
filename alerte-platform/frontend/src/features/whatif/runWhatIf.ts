/**
 * Simulateur « Et si… ? » : joue deux exercices clones de l'exercice de base, en mode SCÉNARISÉ (rapide, sans IA),
 * l'un sans réforme (référence) et l'autre avec les mandats hypothétiques, puis compare leurs lacunes.
 * Seule la réforme diffère entre les deux runs : l'écart observé lui est imputable. Le registre réel n'est jamais modifié
 * (les hypothèses vivent dans `settings.reform_mandates` de l'exercice « avec réforme »).
 */
import { api } from '@/api/client'
import type { Exercise, GapCompare } from '@/api/loose'

export interface ReformInput {
  institution_id: string
  action_code: string
  kind: string
  has_deadline: boolean
  description: string
}

export type WhatIfStage = 'baseline' | 'reform' | 'compare' | 'done'

export interface WhatIfResult { baselineId: string; reformId: string; compare: GapCompare }

const FINAL = ['completed', 'stopped', 'failed', 'interrupted']

async function playScripted(base: Exercise, title: string, reforms: ReformInput[], opts: { pollMs: number; timeoutMs: number }): Promise<string> {
  const settings = { ...base.settings, reform_mandates: reforms }
  const ex = await api.post<Exercise>('/exercises', { ai_mode: 'scripted', title, settings, pace: 'auto' }, { query: { from: base.id } })
  await api.post(`/exercises/${ex.id}/ready`)
  await api.post(`/exercises/${ex.id}/commands`, { kind: 'start', args: {} })
  const end = Date.now() + opts.timeoutMs
  for (;;) {
    const cur = await api.get<Exercise>(`/exercises/${ex.id}`)
    if (FINAL.includes(cur.state)) {
      if (cur.state !== 'completed') throw new Error(`exercise ${cur.code} ended in state ${cur.state}`)
      break
    }
    if (Date.now() > end) throw new Error(`exercise ${ex.code} timed out`)
    await new Promise((r) => setTimeout(r, opts.pollMs))
  }
  await api.post(`/exercises/${ex.id}/detect-gaps`)
  return ex.id
}

export async function runWhatIf(base: Exercise, reforms: ReformInput[], labels: { baseline: string; reform: string },
  onStage: (s: WhatIfStage) => void, opts = { pollMs: 700, timeoutMs: 180_000 }): Promise<WhatIfResult> {
  onStage('baseline')
  const baselineId = await playScripted(base, labels.baseline, [], opts)
  onStage('reform')
  const reformId = await playScripted(base, labels.reform, reforms, opts)
  onStage('compare')
  const compare = await api.get<GapCompare>('/gaps/compare', { query: { a: baselineId, b: reformId } })
  onStage('done')
  return { baselineId, reformId, compare }
}
