import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowRight, CheckCircle2, FlaskConical, Loader2, MonitorPlay, Plus, Sparkles, Trash2 } from 'lucide-react'
import { keys } from '@/api/keys'
import { useApiQuery } from '@/api/hooks'
import type { Exercise, GapBrief } from '@/api/loose'
import type { ActionItem, Gap, Institution } from '@/api/types'
import { Button, EmptyState, Field, PageHeader, QueryState, Select, Textarea } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { cn } from '@/lib/cn'
import { runWhatIf, type ReformInput, type WhatIfResult, type WhatIfStage } from './runWhatIf'

const KINDS = ['duty', 'lead', 'power', 'coordination', 'procedure']
const STAGES: Exclude<WhatIfStage, 'done'>[] = ['baseline', 'reform', 'compare']
const emptyRow = (p: Partial<ReformInput> = {}): ReformInput => ({ institution_id: '', action_code: '', kind: 'duty', has_deadline: true, description: '', ...p })

export function WhatIfPage() {
  const { t } = useTranslation()
  const q = useApiQuery<Exercise[]>(keys.exercises(), '/exercises')
  return (
    <>
      <PageHeader eyebrow={t('gaps.whatif.eyebrow')} title={t('gaps.whatif.title')} description={t('gaps.whatif.description')} />
      <QueryState q={q} what="(/exercises)">
        {(rows) => {
          // Référence : les exercices joués jusqu'au bout, hors runs « Et si » déjà générés (plus récents d'abord).
          const done = rows.filter((e) => e.state === 'completed').sort((a, b) => (b.started_at ?? '').localeCompare(a.started_at ?? ''))
          return done.length === 0 ? <EmptyState title={t('gaps.whatif.noBase')} hint={t('gaps.whatif.noBaseHint')} /> : <Lab exercises={done} />
        }}
      </QueryState>
    </>
  )
}

function Lab({ exercises }: { exercises: Exercise[] }) {
  const { t } = useTranslation()
  const [params] = useSearchParams()
  const [baseId, setBaseId] = useState(() => params.get('base') ?? exercises[0].id)
  const base = exercises.find((e) => e.id === baseId) ?? exercises[0]
  const [rows, setRows] = useState<ReformInput[]>(() => [emptyRow({ institution_id: params.get('inst') ?? '', action_code: params.get('action') ?? '' })])
  const [stage, setStage] = useState<WhatIfStage | null>(null)
  const [result, setResult] = useState<WhatIfResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const full = useApiQuery<Exercise>(keys.exercise(base.id), `/exercises/${base.id}`)
  const insts = useApiQuery<Institution[]>(keys.institutions(undefined, true), '/institutions', { query: { include_archived: true } })
  const actions = useApiQuery<ActionItem[]>(keys.actions, '/actions')
  const gaps = useApiQuery<Gap[]>(keys.gaps({ exercise: base.id }), '/gaps', { query: { exercise: base.id } })

  const seatInsts = useMemo(() => {
    const ids = new Set((full.data?.seats ?? []).map((s) => s.institution_id))
    return (insts.data ?? []).filter((i) => ids.has(i.id)).sort((a, b) => a.code.localeCompare(b.code))
  }, [full.data, insts.data])
  const actionLabel = (code: string) => actions.data?.find((a) => a.code === code)?.label ?? code
  const instCode = (id: string) => insts.data?.find((i) => i.id === id)?.code ?? id.slice(-6)
  // Suggestions : actions orphelines (G1) de l'exercice de référence.
  const orphanActions = useMemo(() => [...new Set((gaps.data ?? []).filter((g) => g.code === 'G1' && g.action_code).map((g) => g.action_code as string))], [gaps.data])

  const valid = rows.filter((r) => r.institution_id && r.action_code)
  const busy = stage !== null && stage !== 'done' && !error
  const set = (i: number, p: Partial<ReformInput>) => setRows(rows.map((r, k) => (k === i ? { ...r, ...p } : r)))

  const run = async () => {
    setError(null); setResult(null)
    const summary = valid.map((r) => `${instCode(r.institution_id)} → ${actionLabel(r.action_code)}`).join(' ; ')
    try {
      const res = await runWhatIf(base, valid, {
        baseline: t('gaps.whatif.baselineTitle', { code: base.code }), reform: t('gaps.whatif.reformTitle', { summary }).slice(0, 200),
      }, setStage)
      setResult(res)
    } catch (e) {
      setError(t('gaps.whatif.error', { msg: errorMessage(e, t) }))
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,30rem)_minmax(0,1fr)]">
      {/* Formulaire de réforme */}
      <section aria-label={t('gaps.whatif.reform')} className="panel flex flex-col gap-4 p-5">
        <Field label={t('gaps.whatif.base')}>
          <Select value={base.id} disabled={busy} onChange={(e) => { setBaseId(e.target.value); setResult(null); setStage(null) }}>
            {exercises.map((e) => <option key={e.id} value={e.id}>{e.code} — {e.title}</option>)}
          </Select>
        </Field>

        <div>
          <p className="eyebrow mb-2 flex items-center gap-1.5"><Sparkles className="h-3.5 w-3.5 text-brand" aria-hidden />{t('gaps.whatif.suggestions')}</p>
          {orphanActions.length === 0 ? <p className="text-sm text-muted">{t('gaps.whatif.noSuggestion')}</p> : (
            <ul className="flex flex-col gap-1.5">
              {orphanActions.map((a) => (
                <li key={a}>
                  <button type="button" disabled={busy} onClick={() => setRows([...rows.filter((r) => r.institution_id || r.action_code), emptyRow({ action_code: a })])}
                    className="w-full rounded-lg border border-danger/50 bg-dangersoft/50 px-3 py-2 text-left text-sm font-semibold text-danger transition hover:border-danger">
                    {t('gaps.whatif.suggest', { action: actionLabel(a) })}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <p className="eyebrow mb-2">{t('gaps.whatif.reform')}</p>
          <ol className="flex flex-col gap-3">
            {rows.map((r, i) => (
              <li key={i} className="rounded-xl border border-brand/40 bg-brandsoft/20 p-3">
                <div className="grid gap-2 sm:grid-cols-2">
                  <Field label={t('gaps.whatif.institution')}>
                    <Select value={r.institution_id} disabled={busy} onChange={(e) => set(i, { institution_id: e.target.value })}>
                      <option value="">—</option>{seatInsts.map((x) => <option key={x.id} value={x.id}>{x.code} — {x.name}</option>)}
                    </Select>
                  </Field>
                  <Field label={t('gaps.whatif.action')}>
                    <Select value={r.action_code} disabled={busy} onChange={(e) => set(i, { action_code: e.target.value })}>
                      <option value="">—</option>{actions.data?.map((a) => <option key={a.code} value={a.code}>{a.label}</option>)}
                    </Select>
                  </Field>
                  <Field label={t('gaps.whatif.kind')}>
                    <Select value={r.kind} disabled={busy} onChange={(e) => set(i, { kind: e.target.value })}>
                      {KINDS.map((k) => <option key={k} value={k}>{t(`gaps.matrix.kinds.${k}`)}</option>)}
                    </Select>
                  </Field>
                  <label className="mt-6 inline-flex items-center gap-2 text-sm"><input type="checkbox" className="h-4 w-4 accent-[var(--brand)]" disabled={busy} checked={r.has_deadline} onChange={(e) => set(i, { has_deadline: e.target.checked })} />{t('gaps.whatif.deadline')}</label>
                </div>
                <Field label={t('gaps.whatif.text')} className="mt-2"><Textarea rows={2} disabled={busy} value={r.description} placeholder={t('gaps.whatif.textPlaceholder')} onChange={(e) => set(i, { description: e.target.value })} /></Field>
                {rows.length > 1 && <Button size="sm" variant="ghost" className="mt-1" disabled={busy} onClick={() => setRows(rows.filter((_, k) => k !== i))} icon={<Trash2 className="h-4 w-4" aria-hidden />}>{t('gaps.whatif.removeRow')}</Button>}
              </li>
            ))}
          </ol>
          <Button size="sm" variant="ghost" className="mt-2" disabled={busy || rows.length >= 20} onClick={() => setRows([...rows, emptyRow()])} icon={<Plus className="h-4 w-4" aria-hidden />}>{t('gaps.whatif.addRow')}</Button>
        </div>

        <Button variant="primary" className="!min-h-12 !text-base" disabled={busy || valid.length === 0} loading={busy} onClick={() => void run()} icon={<FlaskConical className="h-5 w-5" aria-hidden />}>
          {busy ? t('gaps.whatif.running') : t('gaps.whatif.run')}
        </Button>
        {valid.length === 0 && <p className="-mt-2 text-xs text-muted">{t('gaps.whatif.needRow')}</p>}
      </section>

      {/* Progression et résultat */}
      <section aria-label={t('gaps.whatif.result')} className="flex flex-col gap-4">
        {stage && (
          <ol className="panel grid gap-2 p-4 sm:grid-cols-3" aria-label={t('gaps.whatif.running')}>
            {STAGES.map((s, i) => {
              const idx = stage === 'done' ? 3 : STAGES.indexOf(stage as (typeof STAGES)[number])
              const state = i < idx ? 'done' : i === idx && !error ? 'active' : 'todo'
              return (
                <li key={s} aria-current={state === 'active' ? 'step' : undefined} className={cn('flex items-center gap-2 rounded-lg border px-3 py-2 text-sm',
                  state === 'done' ? 'border-ok text-ok' : state === 'active' ? 'border-brand text-brand' : 'border-line text-muted')}>
                  {state === 'done' ? <CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden /> : state === 'active' ? <Loader2 className="spin h-4 w-4 shrink-0" aria-hidden /> : <span className="tabular">{i + 1}.</span>}
                  {t(`gaps.whatif.stage.${s}`)}
                </li>
              )
            })}
          </ol>
        )}
        {error && <p role="alert" className="rounded-lg border border-danger bg-dangersoft p-3 text-sm text-danger">{error}</p>}
        {result ? <Result r={result} /> : !stage && (
          <div className="panel grid min-h-64 place-items-center p-8 text-center">
            <div className="max-w-md">
              <FlaskConical className="mx-auto mb-3 h-10 w-10 text-brand" aria-hidden />
              <p className="text-muted">{t('gaps.whatif.description')}</p>
            </div>
          </div>
        )}
      </section>
    </div>
  )
}

function GapList({ title, items, tone, strike }: { title: string; items: GapBrief[]; tone: string; strike?: boolean }) {
  const { t } = useTranslation()
  return (
    <div className="panel p-4">
      <p className={cn('eyebrow mb-2', tone)}>{title} <span className="tabular">({items.length})</span></p>
      {items.length === 0 ? <p className="text-sm text-muted">{t('gaps.whatif.none')}</p> : (
        <ul className="flex flex-col gap-2">
          {items.map((g, i) => (
            <li key={g.id} className="rounded-lg border border-line bg-surface2/60 p-2.5 text-sm" style={{ animationDelay: `${300 + i * 250}ms` }}>
              <span className="mr-2 font-mono text-xs font-bold text-muted">{g.code}</span>
              <span className={cn(strike && 'gap-resolved')} style={strike ? { animationDelay: `${400 + i * 250}ms` } : undefined}>{g.title}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Result({ r }: { r: WhatIfResult }) {
  const { t } = useTranslation()
  const c = r.compare
  const before = c.summary.resolved + c.summary.persistent
  const after = c.summary.persistent + c.summary.new
  const verdict = c.summary.new > 0 ? 'verdictWorse' : c.summary.resolved > 0 ? 'verdictBetter' : 'verdictSame'
  return (
    <>
      <div className="panel relative overflow-hidden p-6">
        <span aria-hidden className={cn('absolute inset-x-0 top-0 h-1', after < before ? 'bg-ok' : after > before ? 'bg-danger' : 'bg-line')} />
        <p className="eyebrow mb-3">{t('gaps.whatif.result')}</p>
        <div className="flex flex-wrap items-center gap-6">
          <p><span className="block text-6xl font-black text-danger tabular">{before}</span><span className="text-sm text-muted">{t('gaps.whatif.gapsBefore')}</span></p>
          <ArrowRight className="h-10 w-10 text-muted" aria-hidden />
          <p><span className={cn('block text-6xl font-black tabular', after < before ? 'text-ok' : after > before ? 'text-danger' : 'text-ink')}>{after}</span><span className="text-sm text-muted">{t('gaps.whatif.gapsAfter')}</span></p>
          <p className={cn('ml-auto max-w-xs text-lg font-bold', verdict === 'verdictBetter' ? 'text-ok' : verdict === 'verdictWorse' ? 'text-danger' : 'text-muted')}>
            {t(`gaps.whatif.${verdict}`, { n: verdict === 'verdictWorse' ? c.summary.new : c.summary.resolved })}
          </p>
        </div>
        <div className="mt-5 flex flex-wrap gap-3 text-sm">
          <Link to={`/present/${r.reformId}`} className="inline-flex items-center gap-1.5 rounded-lg border border-brand/50 bg-brandsoft px-3 py-1.5 font-semibold text-brand no-underline hover:border-brand"><MonitorPlay className="h-4 w-4" aria-hidden />{t('gaps.whatif.present')}</Link>
          <Link to={`/room/${r.reformId}`}>{t('gaps.whatif.openRoom')}</Link>
          <Link to="/gaps">{t('gaps.whatif.openGaps')}</Link>
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <GapList title={t('gaps.whatif.resolved')} items={c.resolved} tone="text-ok" strike />
        <GapList title={t('gaps.whatif.persistent')} items={c.persistent.map((p) => p.b)} tone="text-muted" />
        <GapList title={t('gaps.whatif.new')} items={c.new} tone="text-danger" />
      </div>
      <p className="text-xs text-muted">{t('gaps.whatif.honesty')}</p>
    </>
  )
}
