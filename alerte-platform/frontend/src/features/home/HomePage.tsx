import type { ComponentType, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowRight, BookOpenText, Bot, CheckCircle2, Circle, Flag, Landmark, Radio, SearchCheck, Workflow } from 'lucide-react'
import { keys } from '@/api/keys'
import { useApiQuery } from '@/api/hooks'
import type { Exercise, Ready } from '@/api/loose'
import type { Gap } from '@/api/types'
import { useAuth } from '@/app/auth'
import { Badge, EmptyState, QueryState, StatusBadge } from '@/components/ui'
import { cn } from '@/lib/cn'
import { fmtDateTime } from '@/lib/format'
import { ApiError } from '@/api/client'

export function exercisePath(e: Pick<Exercise, 'id' | 'state'>): string {
  return ['running', 'paused', 'interrupted', 'completed', 'stopped', 'archived'].includes(e.state) ? `/room/${e.id}` : `/studio/exercises/${e.id}`
}

const byRecent = (a: Exercise, b: Exercise) => (b.started_at ?? '').localeCompare(a.started_at ?? '') || b.code.localeCompare(a.code)

function AiModeBadge({ mode }: { mode: string }) {
  const { t } = useTranslation()
  return mode === 'ai' ? <Badge tone="ok">AI</Badge> : <Badge tone="warn">{mode === 'cassette' ? t('common.replayShort', 'REPLAY') : t('common.noAiShort')}</Badge>
}

/* ---------- Hero : ce que fait ALERTE, en une phrase, et où aller. ---------- */
function Hero({ latest }: { latest: Exercise | undefined }) {
  const { t } = useTranslation()
  const steps: { k: 'prepare' | 'play' | 'analyze'; icon: ComponentType<{ className?: string }> }[] = [
    { k: 'prepare', icon: Landmark }, { k: 'play', icon: Radio }, { k: 'analyze', icon: SearchCheck },
  ]
  return (
    <section aria-labelledby="hero-title" className="panel relative mb-6 overflow-hidden p-6 lg:p-8">
      <div aria-hidden className="pointer-events-none absolute -top-24 -right-24 h-72 w-72 rounded-full border border-brand/20" />
      <div aria-hidden className="pointer-events-none absolute -top-10 -right-10 h-44 w-44 rounded-full border border-brand/30" />
      <div aria-hidden className="pointer-events-none absolute top-6 right-6 h-16 w-16 rounded-full bg-brand/10 blur-xl" />
      <div className="relative grid gap-8 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
        <div>
          <p className="eyebrow mb-3 flex items-center gap-2 text-brand"><span className="live-dot is-live text-brand" aria-hidden />{t('home.hero.eyebrow')}</p>
          <h1 id="hero-title" className="max-w-2xl text-3xl leading-tight font-black tracking-tight sm:text-4xl">{t('home.hero.title')}</h1>
          <p className="mt-4 max-w-2xl text-base text-muted">{t('home.hero.lead')}</p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link to={latest ? `/room/${latest.id}` : '/room'} className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-brand px-5 font-semibold text-brandfg no-underline shadow-[0_6px_24px_-8px_var(--brand)] hover:brightness-110">
              <Radio className="h-4 w-4" aria-hidden />{t('home.hero.ctaRoom')}
            </Link>
            <Link to="/studio/scenarios" className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-line bg-surface2 px-5 font-medium text-ink no-underline hover:border-muted">
              {t('home.hero.ctaPrepare')}<ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
            <Link to="/gaps" className="inline-flex min-h-11 items-center gap-2 rounded-lg px-3 font-medium text-ink no-underline hover:underline">
              {t('home.hero.ctaGaps')}
            </Link>
          </div>
        </div>
        <div>
          <h2 className="eyebrow mb-3">{t('home.how.title')}</h2>
          <ol className="relative flex flex-col gap-3">
            <span aria-hidden className="absolute top-5 bottom-5 left-[1.15rem] w-px bg-line" />
            {steps.map(({ k, icon: Icon }, i) => (
              <li key={k} className="relative flex gap-3 rounded-lg border border-line bg-surface2/60 p-3">
                <span className="relative z-10 grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-brand/40 bg-surface text-brand"><Icon className="h-4 w-4" aria-hidden /></span>
                <span>
                  <span className="block text-sm font-bold"><span className="text-brand tabular">{i + 1}.</span> {t(`nav.${k}`)}</span>
                  <span className="block text-sm text-muted">{t(`home.how.${k}`)}</span>
                </span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  )
}

/* ---------- Chiffres clés ---------- */
function Kpi({ label, value, sub, tone = 'brand' }: { label: string; value: ReactNode; sub?: ReactNode; tone?: 'brand' | 'danger' | 'ok' | 'info' }) {
  const color = { brand: 'text-brand', danger: 'text-danger', ok: 'text-ok', info: 'text-info' }[tone]
  return (
    <div className="panel relative overflow-hidden p-4">
      <span aria-hidden className={cn('absolute inset-x-0 top-0 h-0.5 bg-current opacity-70', color)} />
      <p className="eyebrow">{label}</p>
      <p className={cn('mt-1 text-3xl font-black tabular', color)}>{value}</p>
      {sub && <p className="text-xs text-muted">{sub}</p>}
    </div>
  )
}

function KpiRow({ exercises }: { exercises: Exercise[] }) {
  const { t } = useTranslation()
  const gaps = useApiQuery<Gap[]>(keys.gaps({}), '/gaps')
  const insts = useApiQuery<unknown[]>(keys.institutions(undefined, false), '/institutions')
  const agents = useApiQuery<unknown[]>(keys.agents(false), '/agents')
  const played = exercises.filter((e) => ['completed', 'stopped'].includes(e.state))
  const withAi = played.filter((e) => e.ai_mode === 'ai').length
  const g = gaps.data ?? []
  const pending = g.filter((x) => x.validation_status === 'proposed').length
  const dash = (v: number | undefined, pendingQ: boolean) => (pendingQ ? '…' : (v ?? '—'))
  return (
    <section aria-label={t('home.kpi.title')} className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Kpi label={t('home.kpi.played')} value={played.length} sub={`${withAi} ${t('home.kpi.withAi')}`} />
      <Kpi label={t('home.kpi.gaps')} value={dash(g.length, gaps.isPending)} sub={`${pending} ${t('home.kpi.toReview')}`} tone="danger" />
      <Kpi label={t('home.kpi.institutions')} value={dash(insts.data?.length, insts.isPending)} tone="info" />
      <Kpi label={t('home.kpi.agents')} value={dash(agents.data?.length, agents.isPending)} tone="ok" />
    </section>
  )
}

/* ---------- Préparation : où en est-on, quelle est la prochaine étape ---------- */
function SetupChecklist() {
  const { t } = useTranslation()
  const insts = useApiQuery<unknown[]>(keys.institutions(undefined, false), '/institutions')
  const kbs = useApiQuery<unknown[]>(keys.kbs(false), '/knowledge-bases')
  const agents = useApiQuery<unknown[]>(keys.agents(false), '/agents')
  const scenarios = useApiQuery<unknown[]>(keys.scenarios, '/scenarios')
  const exercises = useApiQuery<unknown[]>(keys.exercises(), '/exercises')
  const steps = [
    { to: '/studio/countries', k: 'institutions', q: insts, icon: Landmark }, { to: '/studio/knowledge', k: 'knowledge', q: kbs, icon: BookOpenText },
    { to: '/studio/agents', k: 'agents', q: agents, icon: Bot }, { to: '/studio/scenarios', k: 'scenarios', q: scenarios, icon: Workflow },
    { to: '/studio/exercises', k: 'exercises', q: exercises, icon: Flag },
  ]
  const isDone = (n: number | undefined) => typeof n === 'number' && n > 0
  const next = steps.findIndex((s) => !s.q.isPending && !isDone(s.q.data?.length))
  return (
    <section aria-labelledby="setup-title" className="panel p-5">
      <h2 id="setup-title" className="text-lg font-bold">{t('home.setupTitle')}</h2>
      <p className="mb-4 text-sm text-muted">{t('home.setupLead')}</p>
      <ol className="flex flex-col gap-2">
        {steps.map((s, i) => {
          const n = s.q.data?.length
          const done = isDone(n)
          const Icon = s.icon
          return (
            <li key={s.to}>
              <Link to={s.to} aria-current={i === next ? 'step' : undefined}
                className={cn('flex items-center gap-3 rounded-lg border px-3 py-2.5 text-ink no-underline transition-colors hover:bg-surface2',
                  i === next ? 'border-brand bg-brandsoft/60' : 'border-line')}>
                <span className={cn('grid h-7 w-7 shrink-0 place-items-center rounded-full border text-xs font-bold tabular',
                  done ? 'border-ok bg-oksoft text-ok' : i === next ? 'border-brand text-brand' : 'border-line text-muted')}>
                  <span className="sr-only">{t('home.step', { n: i + 1 })}</span>
                  {done ? <CheckCircle2 className="h-4 w-4" aria-hidden /> : <span aria-hidden>{i + 1}</span>}
                </span>
                <Icon className="h-4 w-4 shrink-0 text-muted" aria-hidden />
                <span className="min-w-0 flex-1 truncate text-sm font-semibold">{t(`home.setupItems.${s.k}`)}</span>
                {s.q.isPending ? <span className="text-muted">…</span>
                  : done ? <span className="rounded-md bg-oksoft px-1.5 text-xs font-bold text-ok tabular" title={t('home.count', { n })}>{n}<span className="sr-only"> — {t('home.count', { n })}</span></span>
                  : <span className={cn('inline-flex items-center gap-1 text-xs font-semibold whitespace-nowrap', i === next ? 'text-brand' : 'text-muted')}><Circle className="h-3.5 w-3.5" aria-hidden />{i === next ? t('home.next') : t('home.todo')}</span>}
              </Link>
            </li>
          )
        })}
      </ol>
    </section>
  )
}

function ProviderStatus() {
  const { t } = useTranslation()
  const q = useApiQuery<Ready>(keys.ready, '/ready')
  // /ready answers 503 with a body when a check fails: the client reports it as an error; we show it as such.
  let body: ReactNode
  if (q.isPending) body = <Badge tone="neutral">{t('home.checking')}</Badge>
  else if (q.isError) {
    const e = q.error
    body = <Badge tone="danger">{e instanceof ApiError && e.status === 503 ? t('home.notReady') : t('home.unreachable')}</Badge>
  } else {
    const embedder = (q.data.checks.knowledge as { embedder?: { configured?: boolean } } | undefined)?.embedder
    body = (
      <ul className="flex flex-col gap-2 text-sm">
        {Object.entries(q.data.checks).map(([k, v]) => (
          <li key={k} className="flex items-center justify-between gap-2">
            <span>{t(`home.checks.${k}`, k)}</span>
            <Badge tone={v.ok === false ? 'danger' : 'ok'}>{v.ok === false ? t('home.down') : t('home.up')}</Badge>
          </li>
        ))}
        {embedder && (
          <li className="flex items-center justify-between gap-2 border-t border-line pt-2">
            <span>{embedder.configured ? t('home.checks.hybrid') : t('home.checks.lexical')}</span>
            <Badge tone={embedder.configured ? 'ok' : 'warn'}>{embedder.configured ? t('home.up') : t('home.down')}</Badge>
          </li>
        )}
      </ul>
    )
  }
  return (
    <section aria-labelledby="sys-title" className="panel p-5">
      <h2 id="sys-title" className="mb-3 text-lg font-bold">{t('home.system')}</h2>
      {body}
    </section>
  )
}

/* ---------- Derniers exercices ---------- */
function ExerciseCard({ e }: { e: Exercise }) {
  const { t } = useTranslation()
  const live = ['running', 'paused'].includes(e.state)
  return (
    <li>
      <Link to={exercisePath(e)} className="panel group flex h-full flex-col gap-2 p-4 text-ink no-underline transition-colors hover:border-brand">
        <div className="flex items-center justify-between gap-2">
          <span className="font-mono text-xs text-muted">{e.code}</span>
          <span className="flex items-center gap-1.5">
            {live && <span className="live-dot is-live text-ok" aria-hidden />}
            <StatusBadge status={e.state} /><AiModeBadge mode={e.ai_mode} />
          </span>
        </div>
        <p className="line-clamp-2 font-semibold group-hover:text-brand">{e.title}</p>
        <p className="mt-auto flex items-center justify-between text-xs text-muted">
          <span>{fmtDateTime(e.started_at)}</span>
          <span className="inline-flex items-center gap-1 font-semibold text-brand">{t('home.open')}<ArrowRight className="h-3.5 w-3.5" aria-hidden /></span>
        </p>
      </Link>
    </li>
  )
}

export function HomePage() {
  const { t } = useTranslation()
  const { workspace } = useAuth()
  const q = useApiQuery<Exercise[]>(keys.exercises(), '/exercises')
  const sorted = [...(q.data ?? [])].sort(byRecent)
  const latestPlayed = sorted.find((e) => e.state !== 'draft' && e.state !== 'ready')
  return (
    <>
      <p className="sr-only">{t('home.title', { name: workspace?.name ?? '' })}</p>
      <Hero latest={latestPlayed} />
      <KpiRow exercises={q.data ?? []} />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <section aria-labelledby="latest-title">
          <div className="mb-3 flex items-center justify-between gap-2">
            <h2 id="latest-title" className="text-lg font-bold">{t('home.latest')}</h2>
            <Link to="/studio/exercises" className="text-sm">{t('home.viewAll')}</Link>
          </div>
          <QueryState q={q} what="(/exercises)">
            {(rows) => rows.length === 0
              ? <EmptyState title={t('home.noExercises')} hint={t('home.noExercisesHint')} action={<Link to="/studio/exercises">{t('nav.exercises')}</Link>} />
              : <ul className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">{[...rows].sort(byRecent).slice(0, 6).map((e) => <ExerciseCard key={e.id} e={e} />)}</ul>}
          </QueryState>
        </section>
        <div className="flex flex-col gap-6">
          <SetupChecklist />
          <ProviderStatus />
        </div>
      </div>
    </>
  )
}
