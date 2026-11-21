import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { keys } from '@/api/keys'
import { useApiQuery } from '@/api/hooks'
import type { Exercise, Ready } from '@/api/loose'
import { useAuth } from '@/app/auth'
import { Badge, Card, EmptyState, PageHeader, QueryState, Section, StatusBadge, Table, TBody, Td, Th, THead, Tr } from '@/components/ui'
import { fmtDateTime } from '@/lib/format'
import { ApiError } from '@/api/client'

export function exercisePath(e: Pick<Exercise, 'id' | 'state'>): string {
  return ['running', 'paused', 'interrupted', 'completed', 'stopped', 'archived'].includes(e.state) ? `/room/${e.id}` : `/studio/exercises/${e.id}`
}

function SetupChecklist() {
  const { t } = useTranslation()
  const insts = useApiQuery<unknown[]>(keys.institutions(undefined, false), '/institutions')
  const kbs = useApiQuery<unknown[]>(keys.kbs(false), '/knowledge-bases')
  const agents = useApiQuery<unknown[]>(keys.agents(false), '/agents')
  const scenarios = useApiQuery<unknown[]>(keys.scenarios, '/scenarios')
  const exercises = useApiQuery<unknown[]>(keys.exercises(), '/exercises')
  const steps = [
    { to: '/studio/countries', k: 'institutions', q: insts }, { to: '/studio/knowledge', k: 'knowledge', q: kbs },
    { to: '/studio/agents', k: 'agents', q: agents }, { to: '/studio/scenarios', k: 'scenarios', q: scenarios },
    { to: '/studio/exercises', k: 'exercises', q: exercises },
  ]
  return (
    <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
      {steps.map((s, i) => {
        const n = s.q.data?.length
        const done = typeof n === 'number' && n > 0
        return (
          <li key={s.to}>
            <Card>
              <p className="text-xs font-semibold text-muted uppercase">{t('home.step', { n: i + 1 })}</p>
              <Link to={s.to} className="font-semibold no-underline hover:underline">{t(`home.setupItems.${s.k}`)}</Link>
              <p className="mt-1 text-sm">{s.q.isPending ? '…' : <Badge tone={done ? 'ok' : 'neutral'}>{done ? t('home.count', { n }) : t('home.todo')}</Badge>}</p>
            </Card>
          </li>
        )
      })}
    </ol>
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
      <Section title={t('home.setup')}><SetupChecklist /></Section>
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
