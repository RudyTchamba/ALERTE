import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { keys } from '@/api/keys'
import { useApiQuery } from '@/api/hooks'
import type { Exercise, Ready } from '@/api/loose'
import { useAuth } from '@/app/auth'
import { CheckCircle2, Circle } from 'lucide-react'
import { PHASES, STEPS, stepsOf } from '@/app/journey'
import { Badge, Card, EmptyState, InfoTip, PageHeader, QueryState, Section, StatusBadge, Table, TBody, Td, Th, THead, Tr } from '@/components/ui'
import { fmtDateTime } from '@/lib/format'
import { ApiError } from '@/api/client'

export function exercisePath(e: Pick<Exercise, 'id' | 'state'>): string {
  return ['running', 'paused', 'interrupted', 'completed', 'stopped', 'archived'].includes(e.state) ? `/room/${e.id}` : `/studio/exercises/${e.id}`
}

type Row = Record<string, unknown>

/** Le parcours en trois phases, avec l'état RÉEL de l'espace de travail (compteurs lus sur le serveur) et la prochaine étape. */
function JourneyChecklist() {
  const { t } = useTranslation()
  const insts = useApiQuery<Row[]>(keys.institutions(undefined, false), '/institutions')
  const mandates = useApiQuery<Row[]>(keys.mandates(), '/mandates')
  const kbs = useApiQuery<{ overview?: { published_version_no?: number | null } }[]>(keys.kbs(false), '/knowledge-bases')
  const agents = useApiQuery<Row[]>(keys.agents(false), '/agents')
  const matrix = useApiQuery<{ grants: Row[] }>(keys.accessMatrix, '/access-matrix')
  const scenarios = useApiQuery<Row[]>(keys.scenarios, '/scenarios')
  const exercises = useApiQuery<{ state: string }[]>(keys.exercises(), '/exercises')
  const gaps = useApiQuery<Row[]>(keys.gaps(), '/gaps')
  const reports = useApiQuery<Row[]>(keys.reports, '/reports')
  const n = (q: { data?: unknown[] }) => q.data?.length
  const published = kbs.data?.filter((k) => k.overview?.published_version_no).length
  const validated = mandates.data?.filter((m) => m.validation === 'validated').length
  const started = exercises.data?.filter((e) => ['running', 'paused', 'interrupted', 'completed', 'stopped', 'archived'].includes(e.state)).length
  const rows: { step: string; detail: string | null; done: boolean | undefined }[] = [
    { step: 'institutions', detail: insts.data ? t('home.counts.institutions', { i: n(insts), m: n(mandates) ?? 0, v: validated ?? 0 }) : null, done: insts.data ? insts.data.length > 0 : undefined },
    { step: 'knowledge', detail: kbs.data ? t('home.counts.knowledge', { k: n(kbs), p: published ?? 0 }) : null, done: kbs.data ? (published ?? 0) > 0 : undefined },
    { step: 'agents', detail: agents.data ? t('home.counts.agents', { n: n(agents) }) : null, done: agents.data ? agents.data.length > 0 : undefined },
    { step: 'access', detail: matrix.data ? t('home.counts.access', { n: matrix.data.grants.length }) : null, done: matrix.data ? matrix.data.grants.length > 0 : undefined },
    { step: 'scenarios', detail: scenarios.data ? t('home.counts.scenarios', { n: n(scenarios) }) : null, done: scenarios.data ? scenarios.data.length > 0 : undefined },
    { step: 'exercises', detail: exercises.data ? t('home.counts.exercises', { n: n(exercises) }) : null, done: exercises.data ? exercises.data.length > 0 : undefined },
    { step: 'room', detail: exercises.data ? t('home.counts.room', { n: started ?? 0 }) : null, done: exercises.data ? (started ?? 0) > 0 : undefined },
    { step: 'gaps', detail: gaps.data ? t('home.counts.gaps', { n: n(gaps) }) : null, done: gaps.data ? gaps.data.length > 0 : undefined },
    { step: 'reports', detail: reports.data ? t('home.counts.reports', { n: n(reports) }) : null, done: reports.data ? reports.data.length > 0 : undefined },
  ]
  const firstTodo = rows.findIndex((r) => r.done === false)
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {PHASES.map((p, pi) => (
        <Card key={p}>
          <h3 className="text-base font-bold">{t(`journey.phases.${p}.short`, { n: 'ABC'[pi] })} — {t(`journey.phases.${p}.name`)}</h3>
          <p className="mb-2 text-sm text-muted">{t(`journey.phases.${p}.desc`)}</p>
          <ol className="flex flex-col gap-2">
            {rows.filter((r) => stepsOf(p).some((s) => s.id === r.step)).map((r) => {
              const step = STEPS.find((s) => s.id === r.step)!
              const isNext = rows.indexOf(r) === firstTodo
              return (
                <li key={r.step} className={isNext ? 'rounded-md border border-brand bg-brandsoft p-2' : 'p-2'}>
                  <div className="flex items-start gap-2">
                    {r.done ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-ok" aria-label={t('home.done')} /> : <Circle className="mt-0.5 h-4 w-4 shrink-0 text-muted" aria-label={t('home.todo')} />}
                    <div className="min-w-0">
                      <Link to={step.to} className="font-semibold">{t(`journey.steps.${r.step}.title`)}</Link>
                      {isNext && <Badge tone="info">{t('home.nextStep')}</Badge>}
                      <p className="text-sm text-muted">{r.detail ?? '…'}</p>
                    </div>
                  </div>
                </li>
              )
            })}
          </ol>
        </Card>
      ))}
    </div>
  )
}

function WorkspaceExplainer() {
  const { t } = useTranslation()
  const { workspace, role } = useAuth()
  return (
    <section aria-label={t('home.whatIsWorkspace')} className="mb-6 rounded-md border border-line bg-surface p-4">
      <h2 className="text-lg font-semibold">{t('home.whatIsWorkspace')}<InfoTip term="workspace" /></h2>
      <p className="mt-1 max-w-3xl text-sm">{t('home.workspaceText')}</p>
      <p className="mt-2 text-sm text-muted">{t('home.youAreIn', { name: workspace?.name ?? '', role: role ?? '' })}</p>
      <p className="mt-2 text-sm">{t('home.start')} <Link to="/help/glossary">{t('glossary.seeAll')}</Link></p>
    </section>
  )
}

function ProviderStatus() {
  const { t } = useTranslation()
  const q = useApiQuery<Ready>(keys.ready, '/ready')
  // /ready answers 503 with a body when a check fails: the client reports it as an error; we show it as such.
  if (q.isPending) return <Badge tone="neutral">{t('home.checking')}</Badge>
  if (q.isError) {
    const e = q.error
    return <Badge tone="danger">{e instanceof ApiError && e.status === 503 ? t('home.notReady') : t('home.unreachable')}</Badge>
  }
  return (
    <ul className="flex flex-wrap gap-2">
      {Object.entries(q.data.checks).map(([k, v]) => <li key={k}><Badge tone={v.ok === false ? 'danger' : 'ok'}>{k}: {v.ok === false ? t('home.down') : t('home.up')}</Badge></li>)}
    </ul>
  )
}

export function HomePage() {
  const { t } = useTranslation()
  const { workspace } = useAuth()
  const q = useApiQuery<Exercise[]>(keys.exercises(), '/exercises')
  return (
    <>
      <PageHeader title={t('home.title', { name: workspace?.name ?? '' })} description={t('home.description')} />
      <Section title={t('home.system')}><ProviderStatus /></Section>
      <WorkspaceExplainer />
      <Section title={t('home.journey')}><JourneyChecklist /></Section>
      <Section title={t('home.exercises')}>
        <QueryState q={q} what="(/exercises)">
          {(rows) => rows.length === 0 ? <EmptyState title={t('home.noExercises')} hint={t('home.noExercisesHint')} action={<Link to="/studio/exercises">{t('nav.exercises')}</Link>} /> : (
            <Table caption={t('home.exercises')}>
              <THead><Tr><Th>{t('common.code')}</Th><Th>{t('home.exTitle')}</Th><Th>{t('common.status')}</Th><Th>{t('home.mode')}</Th><Th>{t('home.started')}</Th></Tr></THead>
              <TBody>{rows.map((e) => (
                <Tr key={e.id}>
                  <Td className="font-mono">{e.code}</Td>
                  <Td><Link to={exercisePath(e)}>{e.title}</Link></Td>
                  <Td><StatusBadge status={e.state} /></Td>
                  <Td>{e.ai_mode === 'ai' ? <Badge tone="ok">AI</Badge> : <Badge tone="warn">{e.ai_mode === 'cassette' ? t('common.replayShort', 'REPLAY') : t('common.noAiShort')}</Badge>}</Td>
                  <Td>{fmtDateTime(e.started_at)}</Td>
                </Tr>
              ))}</TBody>
            </Table>
          )}
        </QueryState>
      </Section>
    </>
  )
}
