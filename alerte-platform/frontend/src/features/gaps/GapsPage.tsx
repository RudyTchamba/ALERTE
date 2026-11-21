import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { Gap, GapDetail, GapEvidence, Institution, IntlReference } from '@/api/types'
import type { Exercise, GapCompare, RefSuggestion } from '@/api/loose'
import { Badge, Button, Card, EmptyState, Field, Input, PageHeader, QueryState, Section, Select, StatusBadge, Table, TBody, Td, Textarea, Th, THead, Tr, useToast, useEnumLabel, Mono } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { fmtDateTime, fmtPct } from '@/lib/format'
import { natureTags } from './nature'

const SEV: Record<number, 'danger' | 'warn' | 'info'> = { 3: 'danger', 2: 'warn', 1: 'info' }

export function NatureBadges({ g }: { g: Pick<Gap, 'origin' | 'evidence_basis' | 'validation_status'> }) {
  const { t } = useTranslation()
  return <span className="inline-flex flex-wrap gap-1">{natureTags(g).map((n) => <Badge key={n.key} tone={n.tone}>{t(`gaps.nature.${n.key}`)}</Badge>)}</span>
}
export const SeverityBadge = ({ s }: { s: number }) => {
  const { t } = useTranslation()
  return <Badge tone={SEV[s] ?? 'neutral'}>{t(`gaps.severity.${s}`, String(s))}</Badge>
}

export function GapsPage() {
  const { gapId } = useParams()
  const { t } = useTranslation()
  const enumLabel = useEnumLabel()
  const [f, setF] = useState({ exercise: '', institution: '', code: '', severity: '', status: '', basis: '', origin: '', category: '', include_stale: false })
  const [tab, setTab] = useState<'list' | 'compare'>('list')
  const exs = useApiQuery<Exercise[]>(keys.exercises(), '/exercises')
  const insts = useApiQuery<Institution[]>(keys.institutions(undefined, true), '/institutions', { query: { include_archived: true } })
  const q = useApiQuery<Gap[]>(keys.gaps(f), '/gaps', { query: { ...f, include_stale: f.include_stale || undefined } })
  const set = (k: keyof typeof f, v: string | boolean) => setF({ ...f, [k]: v })
  const iname = (id: string) => insts.data?.find((i) => i.id === id)?.code ?? id.slice(-6)

  return (
    <>
      <PageHeader title={t('gaps.title')} description={t('gaps.description')} actions={<Button onClick={() => setTab(tab === 'list' ? 'compare' : 'list')}>{tab === 'list' ? t('gaps.compare') : t('gaps.backToList')}</Button>} />
      {tab === 'compare' ? <Compare exercises={exs.data ?? []} /> : (
        <div className={gapId ? 'grid grid-cols-1 gap-4 [&>*]:min-w-0 xl:grid-cols-[minmax(0,1fr)_minmax(0,38rem)]' : ''}>
          <div>
            <Card className="mb-3">
              <h2 className="sr-only">{t('common.filter')}</h2>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <Field label={t('gaps.exercise')}><Select value={f.exercise} onChange={(e) => set('exercise', e.target.value)}><option value="">{t('common.all')}</option>{exs.data?.map((x) => <option key={x.id} value={x.id}>{x.code}</option>)}</Select></Field>
                <Field label={t('geo.institution')}><Select value={f.institution} onChange={(e) => set('institution', e.target.value)}><option value="">{t('common.all')}</option>{insts.data?.map((x) => <option key={x.id} value={x.id}>{x.code}</option>)}</Select></Field>
                <Field label={t('gaps.code')}><Input value={f.code} placeholder="G1" onChange={(e) => set('code', e.target.value)} /></Field>
                <Field label={t('gaps.categoryF')}><Input value={f.category} onChange={(e) => set('category', e.target.value)} /></Field>
                <Field label={t('gaps.severityF')}><Select value={f.severity} onChange={(e) => set('severity', e.target.value)}><option value="">{t('common.all')}</option>{[3, 2, 1].map((s) => <option key={s} value={s}>{t(`gaps.severity.${s}`)}</option>)}</Select></Field>
                <Field label={t('gaps.statusF')}><Select value={f.status} onChange={(e) => set('status', e.target.value)}><option value="">{t('common.all')}</option>{['proposed', 'confirmed', 'disputed', 'rejected'].map((s) => <option key={s} value={s}>{s}</option>)}</Select></Field>
                <Field label={t('gaps.basisF')}><Select value={f.basis} onChange={(e) => set('basis', e.target.value)}><option value="">{t('common.all')}</option>{['documented', 'observed', 'inferred', 'hypothesis'].map((s) => <option key={s} value={s}>{s}</option>)}</Select></Field>
                <Field label={t('gaps.originF')}><Select value={f.origin} onChange={(e) => set('origin', e.target.value)}><option value="">{t('common.all')}</option>{['rule', 'coordinator_signal', 'agent_hypothesis', 'imported'].map((s) => <option key={s} value={s}>{s}</option>)}</Select></Field>
              </div>
              <label className="mt-2 inline-flex items-center gap-2 text-sm"><input type="checkbox" className="h-4 w-4" checked={f.include_stale} onChange={(e) => set('include_stale', e.target.checked)} />{t('gaps.includeStale')}</label>
            </Card>
            <QueryState q={q} what="(/gaps)">
              {(rows) => rows.length === 0 ? <EmptyState title={t('gaps.empty')} hint={t('gaps.emptyHint')} /> : (
                <Table caption={t('gaps.title')}>
                  <THead><Tr><Th>{t('gaps.code')}</Th><Th>{t('gaps.gapTitle')}</Th><Th>{t('gaps.severityF')}</Th><Th>{t('gaps.nature.label')}</Th><Th>{t('geo.institutions')}</Th><Th>{t('gaps.confidence')}</Th></Tr></THead>
                  <TBody>{rows.map((g) => (
                    <Tr key={g.id} className={g.id === gapId ? 'bg-brandsoft' : ''}>
                      <Td className="font-mono">{g.code}</Td>
                      <Td><Link to={`/gaps/${g.id}`} aria-current={g.id === gapId ? 'true' : undefined} className="font-medium">{g.title}</Link>{!g.is_current && <> <Badge tone="neutral">{t('gaps.stale')}</Badge></>}</Td>
                      <Td><SeverityBadge s={g.severity} /></Td><Td><NatureBadges g={g} /></Td>
                      <Td className="text-xs">{(g.institution_ids as string[]).map(iname).join(', ') || '—'}</Td><Td>{enumLabel(g.confidence)}</Td>
                    </Tr>
                  ))}</TBody>
                </Table>
              )}
            </QueryState>
          </div>
          {gapId && <GapPanel gapId={gapId} institutions={insts.data ?? []} />}
        </div>
      )}
    </>
  )
}

function Compare({ exercises }: { exercises: Exercise[] }) {
  const { t } = useTranslation()
  const [a, setA] = useState('')
  const [b, setB] = useState('')
  const q = useApiQuery<GapCompare>(keys.gapCompare(a, b), a && b ? '/gaps/compare' : null, { query: { a, b } })
  const list = (title: string, rows: { id: string; code: string; title: string; severity: number }[]) => (
    <Section title={`${title} (${rows.length})`}>{rows.length === 0 ? <p className="text-sm text-muted">—</p> : <ul className="flex flex-col gap-1 text-sm">{rows.map((g) => <li key={g.id}><Mono>{g.code}</Mono> <Link to={`/gaps/${g.id}`}>{g.title}</Link> <SeverityBadge s={g.severity} /></li>)}</ul>}</Section>
  )
  return (
    <div>
      <p className="mb-3 text-sm text-muted">{t('gaps.compareHint')}</p>
      <div className="mb-4 flex flex-wrap gap-3">
        <Field label={t('gaps.exerciseA')}><Select value={a} onChange={(e) => setA(e.target.value)}><option value="">—</option>{exercises.map((x) => <option key={x.id} value={x.id}>{x.code}</option>)}</Select></Field>
        <Field label={t('gaps.exerciseB')}><Select value={b} onChange={(e) => setB(e.target.value)}><option value="">—</option>{exercises.map((x) => <option key={x.id} value={x.id}>{x.code}</option>)}</Select></Field>
      </div>
      {a && b && <QueryState q={q} what="(/gaps/compare)">{(c) => (
        <div className="grid gap-4 md:grid-cols-3">
          {list(t('gaps.newGaps'), c.new)}
          <Section title={`${t('gaps.persistent')} (${c.persistent.length})`}>{c.persistent.length === 0 ? <p className="text-sm text-muted">—</p> : <ul className="text-sm">{c.persistent.map((p) => <li key={p.b.id}><Link to={`/gaps/${p.b.id}`}>{p.b.title}</Link> {p.severity_changed && <Badge tone="warn">{t('gaps.severityChanged')}</Badge>} {p.status_changed && <Badge tone="warn">{t('gaps.statusChanged')}</Badge>}</li>)}</ul>}</Section>
          {list(t('gaps.resolved'), c.resolved)}
        </div>
      )}</QueryState>}
    </div>
  )
}

function refLabel(e: GapEvidence): string {
  const r = e.ref as Record<string, unknown>
  if (e.kind === 'chunk') return [r.doc_code, r.article, r.page ? `p.${String(r.page)}` : null].filter(Boolean).join(' · ')
  if (e.kind === 'event') return String(r.inject_ref ?? '')
  if (e.kind === 'message') return r.msg_id ? String(r.msg_id).slice(-6) : `#${String(r.seq ?? '')}`
  return ''
}

const CHAIN_ORDER = ['mandate', 'chunk', 'event', 'message', 'decision', 'coordinator_signal', 'negative_search'] as const

function EvidenceChain({ g }: { g: GapDetail }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState<string | null>(null)
  const ev = g.evidence ?? []
  const groups = CHAIN_ORDER.map((k) => ({ k, items: ev.filter((e) => e.kind === k) })).filter((x) => x.items.length)
  const link = (e: GapEvidence): { to: string; label: string } | null => {
    const r = e.ref as Record<string, unknown>
    if (e.kind === 'decision' && r.decision_id) return { to: `/audit/${g.exercise_id}?decision=${String(r.decision_id)}`, label: t('gaps.openTrace') }
    if ((e.kind === 'event' || e.kind === 'message') && r.seq) return { to: `/audit/${g.exercise_id}?seq=${String(r.seq)}`, label: t('gaps.openInLedger') }
    if (e.kind === 'mandate') return { to: '/studio/countries', label: t('gaps.openRegistry') }
    return null
  }
  if (!ev.length) return <p className="text-sm text-muted">{t('gaps.noEvidence')}</p>
  return (
    <ol className="flex flex-col gap-1">
      {groups.map(({ k, items }, gi) => (
        <li key={k}>
          <p className="text-xs font-bold tracking-wide text-muted uppercase">{gi + 1}. {t(`gaps.chain.${k}`)}</p>
          <ul className="mb-2 flex flex-col gap-1">
            {items.map((e) => {
              const l = link(e)
              const exp = open === e.id
              return (
                <li key={e.id} className="rounded border border-line bg-surface p-2 text-sm">
                  <button type="button" aria-expanded={exp} onClick={() => setOpen(exp ? null : e.id)} className="flex w-full flex-wrap items-center gap-2 text-left">
                    <Badge tone={e.role === 'counter' ? 'danger' : e.role === 'supports' ? 'ok' : 'neutral'}>{t(`gaps.role.${e.role}`, e.role)}</Badge>
                    {e.is_agent && <Badge tone="neutral">{t('gaps.agentOrigin')}</Badge>}
                    <span className="flex-1">{refLabel(e) && <strong>{refLabel(e)} </strong>}{e.excerpt ? (e.excerpt.length > 140 ? `${e.excerpt.slice(0, 140)}…` : e.excerpt) : t(`gaps.chain.${e.kind}`)}</span>
                  </button>
                  {exp && (
                    <div className="mt-2 border-t border-line pt-2">
                      {e.excerpt && <p className="mb-1 whitespace-pre-wrap">{e.excerpt}</p>}
                      <pre className="overflow-x-auto rounded bg-surface2 p-2 text-xs">{JSON.stringify(e.ref, null, 2)}</pre>
                      {l && <Link to={l.to}>{l.label}</Link>}
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        </li>
      ))}
    </ol>
  )
}

function GapPanel({ gapId, institutions }: { gapId: string; institutions: Institution[] }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const q = useApiQuery<GapDetail>(keys.gap(gapId), `/gaps/${gapId}`)
  return (
    <aside aria-label={t('gaps.detail')} className="min-w-0">
      <div className="mb-2 flex justify-end"><Button size="sm" onClick={() => navigate('/gaps')}>{t('common.close')}</Button></div>
      <QueryState q={q} what="(/gaps)">{(g) => <GapView g={g} institutions={institutions} />}</QueryState>
    </aside>
  )
}

function GapView({ g, institutions }: { g: GapDetail; institutions: Institution[] }) {
  const { t } = useTranslation()
  const enumLabel = useEnumLabel()
  const toast = useToast()
  const iname = (id: string) => institutions.find((i) => i.id === id)?.code ?? id.slice(-6)
  const [action, setAction] = useState('confirm')
  const [comment, setComment] = useState('')
  const [reality, setReality] = useState('')
  const needsReason = action === 'dispute' || action === 'reject'
  const review = useApiMutation(() => api.post('/gaps/' + g.id + '/reviews', { action, comment: comment || null, reality_label: reality || null }), {
    invalidate: [keys.gap(g.id), ['gaps']], onSuccess: () => { setComment(''); toast.push(t('gaps.reviewSaved')) }, onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const refStatus = g.reference_status as { status?: string; message?: string | null; count?: number } | undefined
  const refs = useApiMutation((v: { id: string; status: string }) => api.patch(`/gap-references/${v.id}`, { status: v.status }), { invalidate: [keys.gap(g.id)], onError: (e) => toast.push(errorMessage(e, t), 'danger') })
  const suggestions = useApiQuery<RefSuggestion[]>(['gap-suggestions', g.id], `/gaps/${g.id}/reference-suggestions`)
  const assoc = useApiMutation((rid: string) => api.post(`/gaps/${g.id}/references`, { reference_id: rid }), { invalidate: [keys.gap(g.id), ['gap-suggestions', g.id]], onError: (e) => toast.push(errorMessage(e, t), 'danger') })
  const lib = useApiQuery<IntlReference[]>(keys.intlRefs, '/international-references')
  void lib

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <p className="mb-1 flex flex-wrap items-center gap-2"><Mono>{g.code}</Mono><SeverityBadge s={g.severity} /><StatusBadge status={g.validation_status} /></p>
        <h2 className="text-lg font-bold">{g.title}</h2>
        <p className="my-2 flex flex-wrap items-center gap-2 text-sm"><NatureBadges g={g} /><Badge tone="neutral">{t('gaps.confidence')}: {enumLabel(g.confidence)}</Badge><Badge tone="neutral">{t('gaps.cause')}: {enumLabel(g.cause)}</Badge>{g.registry_state && <Badge tone={g.registry_state === 'reviewed_complete' ? 'ok' : 'warn'}>{t('gaps.registry')}: {enumLabel(g.registry_state)}</Badge>}</p>
        <p className="whitespace-pre-wrap text-sm">{g.description}</p>
        {g.consequence && <p className="mt-2 text-sm"><strong>{t('gaps.consequence')}:</strong> {g.consequence}</p>}
        <p className="mt-2 text-xs text-muted">{t('geo.institutions')}: {(g.institution_ids as string[]).map(iname).join(', ') || '—'} · {t('gaps.action')}: {g.action_code ?? '—'} {g.demand_derivation && <>· {t('geo.derivation')}: {g.demand_derivation}</>}</p>
        <p className="mt-1 text-xs text-muted"><Link to={`/audit/${g.exercise_id}`}>{t('gaps.openAudit')}</Link></p>
      </Card>

      <Section title={t('gaps.evidenceChain')}><EvidenceChain g={g} /></Section>

      <Section title={t('gaps.negativeSearch')}>
        {(g.negative_searches ?? []).length === 0 ? <p className="text-sm text-muted">{t('gaps.noNegative')}</p> : (g.negative_searches ?? []).map((n) => (
          <Card key={n.id} className="mb-2 text-sm">
            <p className="font-medium">{n.statement}</p>
            <p className="mt-1 flex flex-wrap gap-2"><Badge tone={n.verdict === 'confirmed_absent' ? 'warn' : 'info'}>{n.verdict}</Badge><Badge tone={n.corpus_coverage === null ? 'warn' : n.corpus_coverage >= 1 ? 'ok' : 'warn'}>{t('gaps.corpusCoverage')}: {n.corpus_coverage === null ? t('kb.noExpected') : fmtPct(n.corpus_coverage)}</Badge></p>
            <p className="mt-1 text-xs text-muted">{t('gaps.queries')}: {(n.queries as string[]).join(' · ')} · {t('kb.languages')}: {(n.languages as string[]).join(', ')}</p>
            {(n.coverage_missing as string[]).length > 0 && <p className="text-xs text-warn">{t('gaps.missingDocs')}: {(n.coverage_missing as string[]).join(', ')}</p>}
          </Card>
        ))}
        {g.corpus_coverage !== null && <p className="text-xs text-muted">{t('gaps.corpusCoverage')}: {fmtPct(g.corpus_coverage)}</p>}
      </Section>

      <Section title={t('gaps.references')}>
        {refStatus?.status === 'insufficient_sources' && <p role="status" className="mb-2 rounded border border-warn bg-warnsoft p-2 text-sm">{refStatus.message}</p>}
        {(g.references ?? []).length === 0 ? <p className="text-sm text-muted">{t('gaps.noRefs')}</p> : <ul className="flex flex-col gap-2">{(g.references ?? []).map((r) => {
          const ref = (r.reference ?? {}) as Record<string, unknown>
          return (<li key={r.id} className="rounded border border-line bg-surface p-2 text-sm">
            <p><strong>{String(ref.jurisdiction ?? '')}</strong> — {String(ref.instrument ?? '')} {ref.article ? `Art. ${String(ref.article)}` : ''} <StatusBadge status={r.status} /></p>
            <p className="text-xs text-muted">{String(ref.summary ?? '')}</p>
            <div className="mt-1 flex gap-1"><Button size="sm" onClick={() => refs.mutate({ id: r.id, status: 'accepted' })}>{t('gaps.accept')}</Button><Button size="sm" onClick={() => refs.mutate({ id: r.id, status: 'rejected' })}>{t('gaps.rejectRef')}</Button></div>
          </li>)
        })}</ul>}
        {(suggestions.data ?? []).length > 0 && (
          <div className="mt-2"><p className="text-sm font-medium">{t('gaps.suggestions')}</p>
            <ul className="text-sm">{suggestions.data!.map((s) => <li key={s.reference_id} className="flex items-center gap-2">{s.jurisdiction} — {s.instrument} <Badge tone="neutral">{s.fit_score.toFixed(2)}</Badge><Button size="sm" onClick={() => assoc.mutate(s.reference_id)}>{t('gaps.associate')}</Button></li>)}</ul></div>
        )}
      </Section>

      <ImprovementActions g={g} institutions={institutions} />

      <Section title={t('gaps.review')}>
        <Card>
          <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); review.mutate(undefined) }}>
            <Field label={t('gaps.reviewAction')}><Select value={action} onChange={(e) => setAction(e.target.value)}>{['confirm', 'dispute', 'reject', 'comment', 'reopen'].map((a) => <option key={a} value={a}>{t(`gaps.actions.${a}`)}</option>)}</Select></Field>
            <Field label={t('gaps.reality')} hint={t('gaps.realityHint')}><Select value={reality} onChange={(e) => setReality(e.target.value)}><option value="">—</option>{['real', 'partially_real', 'not_real'].map((a) => <option key={a} value={a}>{t(`gaps.realityLabels.${a}`)}</option>)}</Select></Field>
            <Field label={t('gaps.reason')} required={needsReason} hint={needsReason ? t('gaps.reasonRequired') : undefined}><Textarea value={comment} onChange={(e) => setComment(e.target.value)} /></Field>
            <div><Button type="submit" variant="primary" disabled={needsReason && !comment.trim()} loading={review.isPending}>{t('gaps.submitReview')}</Button></div>
          </form>
        </Card>
        <h3 className="mt-3 mb-1 font-semibold">{t('gaps.history')}</h3>
        {(g.reviews ?? []).length === 0 ? <p className="text-sm text-muted">{t('gaps.noReviews')}</p> : <ol className="flex flex-col gap-1 text-sm">{(g.reviews ?? []).map((r) => (
          <li key={r.id} className="rounded border border-line bg-surface p-2"><p><Badge tone="info">{r.action}</Badge> {r.from_status} → {r.to_status} {r.reality_label && <Badge tone="neutral">{r.reality_label}</Badge>}</p><p className="text-xs text-muted">{r.reviewer} · {fmtDateTime(r.created_at)}</p>{r.comment && <p>{r.comment}</p>}</li>
        ))}</ol>}
      </Section>
    </div>
  )
}

function ImprovementActions({ g, institutions }: { g: GapDetail; institutions: Institution[] }) {
  const { t } = useTranslation()
  const toast = useToast()
  const [d, setD] = useState({ description: '', owner: '', due: '', kpi: '' })
  const add = useApiMutation(() => api.post(`/gaps/${g.id}/improvement-actions`, { description: d.description, owner_institution_id: d.owner || null, due_date: d.due || null, kpi: d.kpi || null }), {
    invalidate: [keys.gap(g.id)], onSuccess: () => setD({ description: '', owner: '', due: '', kpi: '' }), onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const upd = useApiMutation((v: { id: string; status: string }) => api.patch(`/improvement-actions/${v.id}`, { status: v.status }), { invalidate: [keys.gap(g.id)] })
  const acts = (g.improvement_actions ?? []) as { id: string; description: string; status: string; due_date: string | null; kpi: string | null; owner_institution_id: string | null }[]
  return (
    <Section title={t('gaps.improvement')}>
      <p className="mb-2 text-xs text-muted">{t('gaps.improvementHint')}</p>
      <ul className="mb-2 flex flex-col gap-1 text-sm">{acts.map((a) => (
        <li key={a.id} className="rounded border border-line bg-surface p-2">{a.description} <StatusBadge status={a.status} /> <span className="text-xs text-muted">{institutions.find((i) => i.id === a.owner_institution_id)?.code} {a.due_date} {a.kpi}</span>
          <Select aria-label={t('common.status')} className="!mt-1 !w-auto" value={a.status} onChange={(e) => upd.mutate({ id: a.id, status: e.target.value })}>{['planned', 'in_progress', 'done', 'dropped'].map((s) => <option key={s}>{s}</option>)}</Select></li>
      ))}</ul>
      <form className="grid gap-2 sm:grid-cols-2" onSubmit={(e) => { e.preventDefault(); if (d.description.trim()) add.mutate(undefined) }}>
        <Field label={t('common.description')} className="sm:col-span-2"><Input value={d.description} onChange={(e) => setD({ ...d, description: e.target.value })} /></Field>
        <Field label={t('gaps.owner')}><Select value={d.owner} onChange={(e) => setD({ ...d, owner: e.target.value })}><option value="">—</option>{institutions.map((i) => <option key={i.id} value={i.id}>{i.code}</option>)}</Select></Field>
        <Field label={t('gaps.due')}><Input type="date" value={d.due} onChange={(e) => setD({ ...d, due: e.target.value })} /></Field>
        <Field label="KPI" className="sm:col-span-2"><Input value={d.kpi} onChange={(e) => setD({ ...d, kpi: e.target.value })} /></Field>
        <div><Button type="submit" loading={add.isPending}>{t('gaps.addAction')}</Button></div>
      </form>
    </Section>
  )
}
