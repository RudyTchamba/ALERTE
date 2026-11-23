import { useMemo, useState } from 'react'
import { useQueries } from '@tanstack/react-query'
import { api } from '@/api/client'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, BookMarked, CheckCircle2, Circle, CircleDashed, Crown, FlaskConical, HelpCircle, Layers, Users } from 'lucide-react'
import { keys } from '@/api/keys'
import { useApiQuery } from '@/api/hooks'
import type { ActionItem, Country, Gap, Institution, Mandate, RegistryReview } from '@/api/types'

interface ScenarioLite { id: string; country_id: string | null }
interface InjectLite { demands?: { action_code: string | null }[] }
import { EmptyState, Field, PageHeader, QueryState, Select } from '@/components/ui'
import { cn } from '@/lib/cn'
import { buildMatrix, summarize, type CellState, type MMandate, type Row, type RowState } from './matrix'

const ROW_STYLE: Record<RowState, { text: string; bg: string; border: string; icon: typeof CheckCircle2 }> = {
  covered: { text: 'text-ok', bg: 'bg-oksoft', border: 'border-l-ok', icon: CheckCircle2 },
  overlap: { text: 'text-warn', bg: 'bg-warnsoft', border: 'border-l-warn', icon: Layers },
  orphan: { text: 'text-danger', bg: 'bg-dangersoft', border: 'border-l-danger', icon: AlertTriangle },
  undetermined: { text: 'text-muted', bg: 'bg-neutralsoft', border: 'border-l-line', icon: HelpCircle },
}
const CELL_STYLE: Record<CellState, string> = {
  lead: 'border-ok bg-ok text-[var(--bg)]',
  responsible: 'border-ok bg-oksoft text-ok',
  proposed: 'border-dashed border-warn bg-transparent text-warn',
  involved: 'border-info bg-infosoft text-info',
  none: 'border-line bg-surface2/40 text-transparent',
}
const CELL_ICON: Record<CellState, typeof CheckCircle2> = { lead: Crown, responsible: CheckCircle2, proposed: CircleDashed, involved: Users, none: Circle }

function CellIcon({ state }: { state: CellState }) {
  const I = CELL_ICON[state]
  return <I className="h-5 w-5" aria-hidden />
}

export function ResponsibilityPage() {
  const { t } = useTranslation()
  const countries = useApiQuery<Country[]>(keys.countries(false), '/countries')
  const insts = useApiQuery<Institution[]>(keys.institutions(undefined, false), '/institutions')
  const actions = useApiQuery<ActionItem[]>(keys.actions, '/actions')
  const mandates = useApiQuery<Mandate[]>(keys.mandates(), '/mandates')
  const reviews = useApiQuery<RegistryReview[]>(keys.registryReviews, '/registry-reviews')
  const gaps = useApiQuery<Gap[]>(keys.gaps({}), '/gaps')
  const scenarios = useApiQuery<ScenarioLite[]>(keys.scenarios, '/scenarios')
  const [countryPick, setCountryPick] = useState('')
  const [sel, setSel] = useState<{ action: string; inst: string } | null>(null)

  // Pays par défaut : celui qui a le plus de mandats.
  const defaultCountry = useMemo(() => {
    const cs = countries.data ?? []
    const count = (cid: string) => (mandates.data ?? []).filter((m) => insts.data?.find((i) => i.id === m.institution_id)?.country_id === cid).length
    return [...cs].sort((a, b) => count(b.id) - count(a.id))[0]?.id ?? ''
  }, [countries.data, mandates.data, insts.data])
  const country = countryPick || defaultCountry

  const institutions = useMemo(() => (insts.data ?? []).filter((i) => i.country_id === country).sort((a, b) => a.code.localeCompare(b.code)), [insts.data, country])
  // Actions qui concernent CE pays : demandées par ses scénarios ou portées par ses mandats (le catalogue est commun à l'espace).
  const countryScenarios = useMemo(() => (scenarios.data ?? []).filter((x) => x.country_id === country), [scenarios.data, country])
  const injectQs = useQueries({ queries: countryScenarios.map((x) => ({ queryKey: ['scenario-injects', x.id], queryFn: () => api.get<InjectLite[]>(`/scenarios/${x.id}/injects`) })) })
  const relevant = new Set((mandates.data ?? []).filter((m) => institutions.some((i) => i.id === m.institution_id)).map((m) => m.action_code))
  for (const r of injectQs) for (const inj of r.data ?? []) for (const d of inj.demands ?? []) if (d.action_code) relevant.add(d.action_code)
  const countryActions = (actions.data ?? []).filter((a) => relevant.has(a.code))
  const reviewed = useMemo(() => new Set((reviews.data ?? []).filter((r) => r.status === 'reviewed_complete').map((r) => r.institution_id)), [reviews.data])
  const rows = buildMatrix(countryActions, institutions, (mandates.data ?? []) as MMandate[], reviewed)
  const sum = summarize(rows)
  const gapsByAction = useMemo(() => {
    const m = new Map<string, Set<string>>()
    // Seulement les lacunes qui concernent une institution de ce pays.
    const ids = new Set(institutions.map((i) => i.id))
    for (const g of gaps.data ?? []) {
      if (g.action_code && (g.institution_ids as string[]).some((id) => ids.has(id))) m.set(g.action_code, (m.get(g.action_code) ?? new Set()).add(g.code))
    }
    return m
  }, [gaps.data, institutions])
  const nReviewed = institutions.filter((i) => reviewed.has(i.id)).length

  const selRow = sel ? rows.find((r) => r.action.code === sel.action) : undefined
  const selInst = sel ? institutions.find((i) => i.id === sel.inst) : undefined

  return (
    <>
      <PageHeader eyebrow={t('gaps.matrix.eyebrow')} title={t('gaps.matrix.title')} description={t('gaps.matrix.description')}
        actions={<Field label={t('gaps.matrix.country')} className="w-56"><Select value={country} onChange={(e) => { setCountryPick(e.target.value); setSel(null) }}>{countries.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</Select></Field>} />
      <QueryState q={actions} what="(/actions)">
        {() => countryActions.length === 0 ? <EmptyState title={t('gaps.matrix.noActions')} hint={t('gaps.matrix.noActionsHint')} action={<Link to="/studio/countries">{t('nav.countries')}</Link>} /> : (
          <>
            {/* Synthèse */}
            <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
              <Tile label={t('gaps.matrix.summary.actions')} value={sum.total} />
              <Tile label={t('gaps.matrix.summary.covered')} value={sum.covered} tone="text-ok" />
              <Tile label={t('gaps.matrix.summary.overlap')} value={sum.overlap} tone={sum.overlap ? 'text-warn' : undefined} />
              <Tile label={t('gaps.matrix.summary.orphan')} value={sum.orphan} tone={sum.orphan ? 'text-danger' : undefined} />
              <Tile label={t('gaps.matrix.summary.undetermined')} value={sum.undetermined} />
              <div className="panel px-4 py-3">
                <p className="eyebrow">{t('gaps.matrix.summary.coverage')}</p>
                <p className="text-2xl font-black tabular">{sum.coverage} %</p>
                <div className="mt-1 flex h-1.5 overflow-hidden rounded bg-surface2" aria-hidden>
                  {(['covered', 'overlap', 'orphan', 'undetermined'] as const).map((s) => <span key={s} className={cn('h-full', { covered: 'bg-ok', overlap: 'bg-warn', orphan: 'bg-danger', undetermined: 'bg-line' }[s])} style={{ width: `${sum.total ? (sum[s] / sum.total) * 100 : 0}%` }} />)}
                </div>
              </div>
            </div>
            <p className="mb-3 text-xs text-muted">{t('gaps.matrix.registry', { n: nReviewed, total: institutions.length })} · <Link to="/studio/countries">{t('gaps.matrix.addMandate')}</Link></p>

            {institutions.length === 0 ? <EmptyState title={t('gaps.matrix.noInstitutions')} /> : (
              <div className="grid gap-4 min-[1800px]:grid-cols-[minmax(0,1fr)_24rem]">
                <div className="panel overflow-x-auto">
                  <table className="w-full border-collapse text-sm">
                    <caption className="sr-only">{t('gaps.matrix.title')}</caption>
                    <thead>
                      <tr className="text-xs text-muted">
                        <th scope="col" className="sticky left-0 z-10 bg-surface px-4 py-3 text-left font-semibold tracking-wide uppercase">{t('gaps.matrix.action')}</th>
                        {institutions.map((i) => (
                          <th key={i.id} scope="col" className="px-2 py-3 text-center" title={i.name}>
                            <span className="font-mono text-sm font-black text-ink">{i.code}</span>
                            <span className="block max-w-28 truncate text-xs font-normal">{i.name}</span>
                          </th>
                        ))}
                        <th scope="col" className="px-4 py-3 text-left font-semibold tracking-wide uppercase">{t('gaps.matrix.status')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((r) => <MatrixRow key={r.action.code} r={r} institutions={institutions} gapCodes={[...(gapsByAction.get(r.action.code) ?? [])].sort()} sel={sel} onPick={(inst) => setSel({ action: r.action.code, inst })} />)}
                    </tbody>
                  </table>
                  <Legend />
                </div>
                <Detail row={selRow} inst={selInst} />
              </div>
            )}
          </>
        )}
      </QueryState>
    </>
  )
}

function Tile({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return <div className="panel px-4 py-3"><p className="eyebrow">{label}</p><p className={cn('text-2xl font-black tabular', tone)}>{value}</p></div>
}

function MatrixRow({ r, institutions, gapCodes, sel, onPick }: { r: Row; institutions: Institution[]; gapCodes: string[]; sel: { action: string; inst: string } | null; onPick: (inst: string) => void }) {
  const { t } = useTranslation()
  const st = ROW_STYLE[r.state]
  const RowIcon = st.icon
  return (
    <tr className={cn('border-t border-line', r.state === 'orphan' && 'bg-dangersoft/30')}>
      <th scope="row" className={cn('sticky left-0 z-10 border-l-4 bg-surface px-4 py-3 text-left align-middle', st.border)}>
        <span className="block font-semibold text-ink">{r.action.label}</span>
        <span className="block font-mono text-xs font-normal text-muted">{r.action.code}{r.action.reference_note ? ` · ${r.action.reference_note}` : ''}</span>
      </th>
      {institutions.map((i) => {
        const c = r.cells[i.id]
        const on = sel?.action === r.action.code && sel.inst === i.id
        return (
          <td key={i.id} className="px-2 py-2 text-center align-middle">
            <button type="button" onClick={() => onPick(i.id)} aria-pressed={on}
              aria-label={`${r.action.label} — ${i.code} : ${t(`gaps.matrix.cell.${c.state}`)}`} title={t(`gaps.matrix.cell.${c.state}`)}
              className={cn('mx-auto grid h-11 w-11 place-items-center rounded-lg border-2 transition hover:scale-110', CELL_STYLE[c.state],
                r.state === 'orphan' && c.state === 'none' && 'border-danger/40', on && 'ring-2 ring-brand ring-offset-2 ring-offset-[var(--surface)]')}>
              <CellIcon state={c.state} />
            </button>
          </td>
        )
      })}
      <td className="px-4 py-2 align-middle">
        <span className={cn('inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-bold whitespace-nowrap', st.bg, st.text)} title={t(`gaps.matrix.rowHint.${r.state}`)}>
          <RowIcon className="h-3.5 w-3.5" aria-hidden />{t(`gaps.matrix.row.${r.state}`)}
        </span>
        {gapCodes.length > 0 && <Link to="/gaps" className="mt-1 block font-mono text-xs font-bold whitespace-nowrap text-danger" title={t('gaps.matrix.openGaps')}>{gapCodes.join(' · ')}</Link>}
      </td>
    </tr>
  )
}

function Legend() {
  const { t } = useTranslation()
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-2 border-t border-line px-4 py-3 text-xs text-muted" aria-label={t('gaps.matrix.legend')}>
      {(['lead', 'responsible', 'proposed', 'involved', 'none'] as const).map((s) => (
        <li key={s} className="flex items-center gap-2">
          <span className={cn('grid h-6 w-6 place-items-center rounded-md border-2', CELL_STYLE[s], s === 'none' && 'text-muted')}><CellIcon state={s} /></span>{t(`gaps.matrix.cell.${s}`)}
        </li>
      ))}
    </ul>
  )
}

function Detail({ row, inst }: { row: Row | undefined; inst: Institution | undefined }) {
  const { t } = useTranslation()
  if (!row || !inst) {
    return <aside className="panel flex items-center gap-3 p-5 text-sm text-muted"><BookMarked className="h-5 w-5 shrink-0 text-brand" aria-hidden />{t('gaps.matrix.pick')}</aside>
  }
  const cell = row.cells[inst.id]
  const st = ROW_STYLE[row.state]
  return (
    <aside aria-label={t('gaps.matrix.detail')} className={cn('panel border-l-4 p-5', st.border)}>
      <p className="eyebrow mb-1">{t('gaps.matrix.detail')}</p>
      <h2 className="text-lg font-bold">{row.action.label}</h2>
      <p className="mb-3 text-sm"><span className="font-mono font-bold">{inst.code}</span> <span className="text-muted">— {inst.name}</span></p>
      <p className={cn('mb-4 rounded-lg px-3 py-2 text-sm', st.bg, st.text)}><strong>{t(`gaps.matrix.row.${row.state}`)}.</strong> {t(`gaps.matrix.rowHint.${row.state}`)}</p>
      {cell.mandates.length === 0 ? (
        <div className="flex flex-col gap-3 text-sm">
          <p className="text-muted">{t('gaps.matrix.noneHere', { inst: inst.code })} <Link to="/studio/countries">{t('gaps.matrix.addMandate')}</Link></p>
          {row.state !== 'covered' && (
            <Link to={`/what-if?inst=${inst.id}&action=${encodeURIComponent(row.action.code)}`}
              className="inline-flex items-center gap-2 self-start rounded-lg border border-brand/50 bg-brandsoft px-3 py-2 font-semibold text-brand no-underline hover:border-brand">
              <FlaskConical className="h-4 w-4" aria-hidden />{t('gaps.whatif.fromMatrix', { inst: inst.code })}
            </Link>
          )}
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {cell.mandates.map((m) => (
            <li key={m.id} className="rounded-lg border border-line bg-surface2/60 p-3 text-sm">
              <p className="flex flex-wrap items-center gap-2 font-semibold">
                {t(`gaps.matrix.kinds.${m.kind}`, m.kind)}
                <span className={cn('rounded px-1.5 text-xs', m.active ? 'bg-oksoft text-ok' : 'bg-warnsoft text-warn')}>{t(`common.enums.${m.validation}`, m.validation)}</span>
                {m.has_deadline && <span className="rounded bg-infosoft px-1.5 text-xs text-info">{t('gaps.matrix.deadline')}</span>}
              </p>
              {m.description && <p className="mt-1 text-muted">{m.description}</p>}
              {m.procedure_status && <p className="mt-1 text-xs text-muted">{t('gaps.matrix.procedure')} : {t(`gaps.matrix.proc.${m.procedure_status}`, m.procedure_status)}</p>}
              <div className="mt-2">
                <p className="eyebrow mb-1 flex items-center gap-1"><BookMarked className="h-3 w-3" aria-hidden />{t('gaps.matrix.source')}</p>
                {(m.sources ?? []).length === 0 ? <p className="text-xs text-muted">{t('gaps.matrix.noSource')}</p> : (
                  <ul className="flex flex-col gap-1">{(m.sources ?? []).map((s, k) => (
                    <li key={k} className="text-xs"><span className="font-semibold text-ok">{s.article ?? '—'}</span>{s.page ? ` · p.${s.page}` : ''}{s.quote && <span className="mt-0.5 block text-muted italic">« {s.quote} »</span>}</li>
                  ))}</ul>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </aside>
  )
}
