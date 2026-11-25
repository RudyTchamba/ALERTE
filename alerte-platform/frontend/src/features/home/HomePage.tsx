import type { ComponentType, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowRight, BellOff, BellRing, Bot, Clock, Flag, Landmark, MonitorPlay, Radio, SearchCheck, ShieldAlert } from 'lucide-react'
import { keys } from '@/api/keys'
import { useApiQuery } from '@/api/hooks'
import type { Exercise, PublicAlerts, Ready } from '@/api/loose'
import type { Gap } from '@/api/types'
import { SetupChecklist } from '@/components/SetupChecklist'
import { useAuth } from '@/app/auth'
import { Badge, EmptyState, InfoTip, QueryState, StatusBadge } from '@/components/ui'
import { cn } from '@/lib/cn'
import { fmtDateTime } from '@/lib/format'
import { ApiError } from '@/api/client'
import { FlowDemo } from './FlowDemo'
import { humanDelay } from '@/features/citizen/siren'

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
type Tone = 'brand' | 'danger' | 'ok' | 'info'
const TONE_TEXT: Record<Tone, string> = { brand: 'text-brand', danger: 'text-danger', ok: 'text-ok', info: 'text-info' }
const TONE_SOFT: Record<Tone, string> = { brand: 'bg-brandsoft', danger: 'bg-dangersoft', ok: 'bg-oksoft', info: 'bg-infosoft' }

function Kpi({ label, value, sub, tone = 'brand', icon: Icon, to }: { label: string; value: ReactNode; sub?: ReactNode; tone?: Tone; icon: ComponentType<{ className?: string }>; to: string }) {
  return (
    <Link to={to} className="panel group relative flex items-center gap-4 overflow-hidden p-4 text-ink no-underline transition-colors hover:border-current">
      <span aria-hidden className={cn('absolute inset-y-0 left-0 w-1', TONE_SOFT[tone])} />
      <span aria-hidden className={cn('grid h-12 w-12 shrink-0 place-items-center rounded-xl', TONE_SOFT[tone], TONE_TEXT[tone])}><Icon className="h-6 w-6" /></span>
      <span className="min-w-0 flex-1">
        <span className={cn('block text-3xl leading-none font-black tabular', TONE_TEXT[tone])}>{value}</span>
        <span className="mt-1 block text-sm font-semibold text-ink">{label}</span>
        {sub && <span className="block text-sm text-muted">{sub}</span>}
      </span>
      <ArrowRight aria-hidden className="h-4 w-4 shrink-0 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-ink" />
    </Link>
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
      <Kpi icon={Flag} to="/studio/exercises" label={t('home.kpi.played')} value={played.length} sub={`${withAi} ${t('home.kpi.withAi')}`} />
      <Kpi icon={ShieldAlert} to="/gaps" label={t('home.kpi.gaps')} value={gaps.isError ? '—' : dash(g.length, gaps.isPending)} sub={`${pending} ${t('home.kpi.toReview')}`} tone="danger" />
      <Kpi icon={Landmark} to="/studio/countries" label={t('home.kpi.institutions')} value={dash(insts.data?.length, insts.isPending)} tone="info" />
      <Kpi icon={Bot} to="/studio/agents" label={t('home.kpi.agents')} value={dash(agents.data?.length, agents.isPending)} tone="ok" />
    </section>
  )
}

/* ---------- Bilan du dernier exercice : ce que l'exercice a révélé, en un coup d'œil ---------- */
export function LastExercise({ ex }: { ex: Exercise }) {
  const { t } = useTranslation()
  const alerts = useApiQuery<PublicAlerts>(['public-alerts', ex.id], `/exercises/${ex.id}/public-alerts`)
  const gaps = useApiQuery<Gap[]>(keys.gaps({}), '/gaps')
  const mine = (gaps.data ?? []).filter((g) => g.exercise_id === ex.id && g.validation_status !== 'rejected')
  const top = [...mine].sort((a, b) => b.severity - a.severity).slice(0, 3)
  const bySev = [3, 2, 1].map((s) => ({ s, n: mine.filter((g) => g.severity === s).length }))
  const a = alerts.data
  const delay = a?.first_alert?.delay_minutes
  const verdict = a?.verdict
  const vTone: Tone = verdict === 'alerted' ? (delay != null && delay > 60 ? 'danger' : 'ok') : verdict === 'silent' ? 'danger' : 'info'
  const VIcon = verdict === 'silent' ? BellOff : verdict === 'alerted' ? BellRing : Clock
  const SEV_TXT: Record<number, string> = { 3: 'text-danger', 2: 'text-warn', 1: 'text-info' }
  const SEV_BG: Record<number, string> = { 3: 'bg-danger', 2: 'bg-warn', 1: 'bg-info' }
  return (
    <section aria-labelledby="last-title" className="panel mb-6 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-surface2/50 px-5 py-3">
        <div className="min-w-0">
          <p className="eyebrow">{t('home.last.eyebrow')}</p>
          <h2 id="last-title" className="truncate text-lg font-bold"><span className="font-mono text-muted">{ex.code}</span> · {ex.title}</h2>
        </div>
        <span className="flex items-center gap-2"><StatusBadge status={ex.state} /><AiModeBadge mode={ex.ai_mode} />
          <Link to={`/room/${ex.id}`} className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-sm font-semibold text-brandfg no-underline hover:brightness-110">{t('home.last.openRoom')}<ArrowRight className="h-4 w-4" aria-hidden /></Link>
        </span>
      </div>
      <div className="grid gap-0 md:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
        {/* Alerte à la population */}
        <div className="border-line p-5 md:border-r">
          <p className="eyebrow mb-3">{t('home.last.alertTitle')}</p>
          {alerts.isPending ? <p className="text-muted">…</p> : !a ? <p className="text-muted">—</p> : (
            <div className="flex items-start gap-4">
              <span aria-hidden className={cn('grid h-14 w-14 shrink-0 place-items-center rounded-2xl', TONE_SOFT[vTone], TONE_TEXT[vTone])}><VIcon className="h-7 w-7" /></span>
              <div className="min-w-0">
                <p className={cn('text-2xl leading-tight font-black', TONE_TEXT[vTone])}>
                  {verdict === 'alerted' ? (delay != null ? humanDelay(delay, t) : t('home.last.alerted')) : t(`home.last.verdict.${verdict}`)}
                </p>
                <p className="mt-1 text-sm text-ink">
                  {verdict === 'alerted' ? t('home.last.alertedBy', { who: a.first_alert?.institution ?? '—' }) : t(`home.last.verdictHint.${verdict}`)}
                </p>
                {a.alerts.some((x) => x.status === 'blocked') && <p className="mt-1 text-sm text-warn">{t('home.last.blocked', { n: a.alerts.filter((x) => x.status === 'blocked').length })}</p>}
              </div>
            </div>
          )}
        </div>
        {/* Lacunes révélées */}
        <div className="border-t border-line p-5 md:border-t-0">
          <div className="mb-3 flex items-center justify-between gap-2">
            <p className="eyebrow">{t('home.last.gapsTitle', { n: mine.length })}</p>
            <Link to="/gaps" className="text-sm font-semibold">{t('home.last.seeGaps')} →</Link>
          </div>
          {mine.length > 0 && (
            <div className="mb-3 flex h-2.5 overflow-hidden rounded-full bg-surface2" role="img" aria-label={bySev.map((x) => `${t(`gaps.severity.${x.s}`)} : ${x.n}`).join(', ')}>
              {bySev.map((x) => x.n > 0 && <span key={x.s} className={SEV_BG[x.s]} style={{ width: `${(100 * x.n) / mine.length}%` }} />)}
            </div>
          )}
          {gaps.isPending ? <p className="text-muted">…</p> : top.length === 0 ? <p className="text-sm text-muted">{t('home.last.noGaps')}</p> : (
            <ul className="flex flex-col gap-2">
              {top.map((g) => (
                <li key={g.id} className="flex items-start gap-2.5 text-sm">
                  <span className={cn('mt-0.5 shrink-0 rounded-md border border-current px-1.5 font-mono text-xs font-bold', SEV_TXT[g.severity] ?? 'text-muted')}>{g.code}</span>
                  <span className="min-w-0 text-ink">{g.title}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
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
const STATE_ACCENT: Record<string, string> = { running: 'border-l-ok', paused: 'border-l-warn', completed: 'border-l-info', stopped: 'border-l-muted', interrupted: 'border-l-danger', ready: 'border-l-brand' }
function ExerciseCard({ e }: { e: Exercise }) {
  const { t } = useTranslation()
  const live = ['running', 'paused'].includes(e.state)
  return (
    <li>
      <Link to={exercisePath(e)} className={cn('panel group flex h-full flex-col gap-2 border-l-4 p-4 text-ink no-underline transition-colors hover:border-brand', STATE_ACCENT[e.state] ?? 'border-l-line')}>
        <div className="flex items-center justify-between gap-2">
          <span className="font-mono text-sm font-semibold text-muted">{e.code}</span>
          <span className="flex items-center gap-1.5">
            {live && <span className="live-dot is-live text-ok" aria-hidden />}
            <StatusBadge status={e.state} /><AiModeBadge mode={e.ai_mode} />
          </span>
        </div>
        <p className="line-clamp-2 font-semibold group-hover:text-brand">{e.title}</p>
        <p className="mt-auto flex items-center justify-between text-sm text-muted">
          <span>{fmtDateTime(e.started_at)}</span>
          <span className="inline-flex items-center gap-1 font-semibold text-brand">{t('home.open')}<ArrowRight className="h-3.5 w-3.5" aria-hidden /></span>
        </p>
      </Link>
    </li>
  )
}

/** Explication du Workspace : ce que c'est, pourquoi il en faut un, quoi faire ensuite. */
function WorkspaceExplainer() {
  const { t } = useTranslation()
  const { workspace, role } = useAuth()
  return (
    <section aria-label={t('home.whatIsWorkspace')} className="panel mb-6 p-4">
      <h2 className="text-lg font-bold">{t('home.whatIsWorkspace')}<InfoTip term="workspace" /></h2>
      <p className="mt-1 max-w-3xl text-sm">{t('home.workspaceText')}</p>
      <p className="mt-2 text-sm text-muted">{t('home.youAreIn', { name: workspace?.name ?? '', role: role ?? '' })}</p>
      <p className="mt-2 text-sm">{t('home.start')} <Link to="/help/glossary">{t('glossary.seeAll')}</Link></p>
    </section>
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
      <WorkspaceExplainer />
      <div className="mb-6"><SetupChecklist /></div>
      <KpiRow exercises={q.data ?? []} />
      {latestPlayed && <LastExercise ex={latestPlayed} />}
      <div className="mb-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <section aria-labelledby="latest-title">
          <div className="mb-3 flex items-center justify-between gap-2">
            <h2 id="latest-title" className="text-lg font-bold">{t('home.latest')}</h2>
            <Link to="/studio/exercises" className="text-sm font-semibold">{t('home.viewAll')} →</Link>
          </div>
          <QueryState q={q} what="(/exercises)">
            {(rows) => rows.length === 0
              ? <EmptyState title={t('home.noExercises')} hint={t('home.noExercisesHint')} action={<Link to="/studio/exercises">{t('nav.exercises')}</Link>} />
              : <ul className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">{[...rows].sort(byRecent).slice(0, 6).map((e) => <ExerciseCard key={e.id} e={e} />)}</ul>}
          </QueryState>
        </section>
        <div className="flex flex-col gap-6">
          <ProviderStatus />
        </div>
      </div>
      <section aria-labelledby="demo-title" className="mb-6">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
          <div className="max-w-3xl">
            <h2 id="demo-title" className="text-lg font-bold">{t('home.demo.title')}</h2>
            <p className="text-sm text-muted">{t('home.demo.sectionLead')}</p>
          </div>
          <span className="flex flex-wrap items-center gap-4">
            <Link to="/present" className="inline-flex items-center gap-1.5 rounded-lg border border-brand/50 bg-brandsoft px-3 py-1.5 text-sm font-semibold text-brand no-underline hover:border-brand"><MonitorPlay className="h-4 w-4" aria-hidden />{t('room.present.open')}</Link>
            {latestPlayed && <Link to={`/room/${latestPlayed.id}`} className="text-sm font-semibold">{t('home.demo.seeReal')} →</Link>}
          </span>
        </div>
        <FlowDemo />
      </section>
    </>
  )
}
