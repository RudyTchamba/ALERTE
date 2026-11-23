/** Le parcours ALERTE : trois phases, une suite d'étapes. Sert à la barre de parcours, au menu et à la page d'accueil. */
export type PhaseId = 'prepare' | 'conduct' | 'analyse'

export interface Step {
  id: string
  phase: PhaseId
  /** clé i18n `journey.steps.<id>.{title,what,next}` */
  to: string
  /** préfixes de route qui appartiennent à l'étape */
  match: string[]
}

export const PHASES: PhaseId[] = ['prepare', 'conduct', 'analyse']

export const STEPS: Step[] = [
  { id: 'institutions', phase: 'prepare', to: '/studio/countries', match: ['/studio/countries'] },
  { id: 'knowledge', phase: 'prepare', to: '/studio/knowledge', match: ['/studio/knowledge'] },
  { id: 'agents', phase: 'prepare', to: '/studio/agents', match: ['/studio/agents'] },
  { id: 'access', phase: 'prepare', to: '/studio/access', match: ['/studio/access'] },
  { id: 'scenarios', phase: 'prepare', to: '/studio/scenarios', match: ['/studio/scenarios'] },
  { id: 'exercises', phase: 'prepare', to: '/studio/exercises', match: ['/studio/exercises'] },
  { id: 'room', phase: 'conduct', to: '/room', match: ['/room', '/play', '/watch'] },
  { id: 'gaps', phase: 'analyse', to: '/gaps', match: ['/gaps'] },
  { id: 'reports', phase: 'analyse', to: '/reports', match: ['/reports'] },
  { id: 'audit', phase: 'analyse', to: '/audit', match: ['/audit'] },
  { id: 'evaluation', phase: 'analyse', to: '/evaluation', match: ['/evaluation'] },
]

export function stepFor(pathname: string): { step: Step; index: number } | null {
  const index = STEPS.findIndex((s) => s.match.some((m) => pathname === m || pathname.startsWith(`${m}/`)))
  return index < 0 ? null : { step: STEPS[index], index }
}

export function stepsOf(phase: PhaseId): Step[] {
  return STEPS.filter((s) => s.phase === phase)
}
