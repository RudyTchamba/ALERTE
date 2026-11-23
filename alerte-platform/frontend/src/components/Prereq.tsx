import { useTranslation } from 'react-i18next'
import { keys } from '@/api/keys'
import { useApiQuery } from '@/api/hooks'
import { NeedsBanner, type Need } from '@/components/ui'

type Row = Record<string, unknown>
export type PrereqPage = 'agents' | 'access' | 'scenarios' | 'exercises' | 'room' | 'gaps' | 'reports'

/** Prérequis de chaque écran, calculés sur les données RÉELLES de l'espace (n'affiche rien quand tout est prêt). */
export function Prereq({ page }: { page: PrereqPage }) {
  const { t } = useTranslation()
  const insts = useApiQuery<Row[]>(keys.institutions(undefined, false), '/institutions')
  const kbs = useApiQuery<{ overview?: { published_version_no?: number | null } }[]>(keys.kbs(false), '/knowledge-bases')
  const agents = useApiQuery<Row[]>(keys.agents(false), '/agents')
  const scenarios = useApiQuery<Row[]>(keys.scenarios, '/scenarios')
  const exercises = useApiQuery<{ state: string }[]>(keys.exercises(), '/exercises')
  const has = (q: { data?: unknown[] }) => (q.data ? q.data.length > 0 : undefined)
  const published = kbs.data ? kbs.data.some((k) => k.overview?.published_version_no) : undefined
  const finished = exercises.data ? exercises.data.some((e) => ['completed', 'stopped', 'archived'].includes(e.state)) : undefined
  const N: Record<PrereqPage, Need[]> = {
    agents: [{ ok: has(insts), label: t('journey.needs.institution'), to: '/studio/countries' }],
    access: [{ ok: has(agents), label: t('journey.needs.agent'), to: '/studio/agents' }, { ok: has(kbs), label: t('journey.needs.kb'), to: '/studio/knowledge' }],
    scenarios: [{ ok: has(insts), label: t('journey.needs.institution'), to: '/studio/countries' }],
    exercises: [
      { ok: has(scenarios), label: t('journey.needs.scenario'), to: '/studio/scenarios' },
      { ok: has(agents), label: t('journey.needs.agent'), to: '/studio/agents' },
      { ok: published, label: t('journey.needs.publishedKb'), to: '/studio/knowledge' },
    ],
    room: [{ ok: has(exercises), label: t('journey.needs.exercise'), to: '/studio/exercises' }],
    gaps: [{ ok: finished, label: t('journey.needs.finished'), to: '/studio/exercises' }],
    reports: [{ ok: finished, label: t('journey.needs.finished'), to: '/studio/exercises' }],
  }
  return <NeedsBanner needs={N[page]} />
}
