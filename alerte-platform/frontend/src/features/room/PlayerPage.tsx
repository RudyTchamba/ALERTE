import { useEffect, useState } from 'react'
import { Quote } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { BoardMessage, LegalAnswer, SeatCard, SeatSearch, SeatTask } from '@/api/loose'
import { FictionalBanner, NoAiBanner } from '@/app/AppShell'
import { Badge, Button, Card, ErrorState, Field, Input, KeyValue, LoadingState, Mono, Section, Select, Textarea, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { fmtDateTime } from '@/lib/format'
import { useSeatToken } from './seatSession'
import { useExerciseStream } from './useExerciseStream'

type Citation = { chunk_id: string; article: string; quote: string }
type Hit = SeatSearch['hits'][number]

/**
 * Passage à citer : la première phrase de l'extrait (≥ 20 caractères, ≤ 240), recopiée telle quelle.
 * Le contrôle normalise la casse, la ponctuation et les espaces : tout fragment contigu du texte réel est accepté.
 */
export function quoteFrom(text: string): string {
  const flat = text.replace(/\s+/g, ' ').trim()
  const body = flat.replace(/^(article|art\.?)\s+[\w-]+(er)?\s*[.:–—-]?\s*/i, '') || flat
  const sentence = body.match(/^.{20,}?[.;:](?=\s|$)/)?.[0] ?? body
  if (sentence.length <= 240) return sentence
  const cut = sentence.slice(0, 240)
  return cut.slice(0, cut.lastIndexOf(' ') > 40 ? cut.lastIndexOf(' ') : 240)
}

export function PlayerPage() {
  const { t } = useTranslation()
  const token = useSeatToken('alerte.seat_token')
  const card = useApiQuery<SeatCard>([...keys.seatMe, token], token ? '/seats/me' : null, { token })
  return (
    <div className="min-h-screen">
      <FictionalBanner />
      <main id="main" className="mx-auto max-w-3xl p-3 lg:p-6">
        {!token ? <p role="alert">{t('room.invalidLink')}</p> : card.isPending ? <LoadingState /> : card.isError ? <ErrorState error={card.error} /> : <Seat card={card.data} token={token} />}
      </main>
    </div>
  )
}

function Seat({ card, token }: { card: SeatCard; token: string }) {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const task = useApiQuery<SeatTask>([...keys.seatTask, token], '/seats/me/task', { token, refetchInterval: 6000 })
  const { state, status } = useExerciseStream(card.exercise.id, { authToken: token })
  useEffect(() => { if (state.lastSeq) void qc.invalidateQueries({ queryKey: [...keys.seatTask, token] }) }, [state.lastSeq, qc, token])
  const tk = task.data?.task
  const toast = useToast()
  // Citations de la décision en cours : remises à zéro à chaque nouvelle tâche ; remplies par « Citer cet extrait ».
  const [cites, setCites] = useState<{ task: string | null; items: Citation[] }>({ task: null, items: [] })
  const current = cites.task === (tk?.id ?? null) ? cites.items : []
  const setCurrent = (items: Citation[]) => setCites({ task: tk?.id ?? null, items })
  const cite = (h: Hit) => {
    const text = String(h.text ?? h.excerpt ?? h.snippet ?? '')
    if (current.some((c) => c.chunk_id === h.chunk_id)) return
    setCurrent([...current, { chunk_id: h.chunk_id, article: h.article ?? '', quote: quoteFrom(text) }])
    toast.push(t('room.citationAdded'))
    document.getElementById('decision-form')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  return (
    <>
      <NoAiBanner aiMode={card.exercise.ai_mode} />
      <header className="mb-4">
        <h1 className="text-2xl font-bold">{card.institution.name ?? card.seat.code}</h1>
        <p className="flex flex-wrap items-center gap-2 text-sm text-muted">{card.exercise.title} · <Badge tone="info">{t('room.seatLabel', { seat: card.seat.code })}</Badge> {card.seat.human_name} <Badge tone={status === 'open' ? 'ok' : 'warn'}>{t(`room.stream.${status}`)}</Badge></p>
      </header>
      <div role="status" aria-live="polite" className="mb-4">
        {tk ? <p className="rounded border-2 border-warn bg-warnsoft p-3 font-semibold text-warn">{t('room.yourTurn', { inject: tk.inject.title, round: tk.round })}</p>
          : <p className="rounded border border-line bg-surface p-3 text-sm">{t('room.nothingToDo', { state: task.data?.exercise_state ?? card.exercise.state })}</p>}
      </div>
      <RoleCard card={card} />
      {tk && (
        <>
          <Section title={t('room.currentInject')}><Card><p className="font-semibold">{tk.inject.sim_time} — {tk.inject.title}</p><p className="mt-1 whitespace-pre-wrap">{tk.inject.body}</p><p className="mt-1 text-xs text-muted">{t('scenarios.from')}: {tk.inject.from_actor} · {tk.inject.tags.join(', ')}</p>
            <p className="mt-2 text-xs text-muted">{t('room.deadline')}: {fmtDateTime(tk.deadline_at)} ({tk.fallback})</p></Card></Section>
          <Section title={t('room.inbox')}>{tk.inbox.length === 0 ? <p className="text-sm text-muted">{t('room.emptyInbox')}</p> : <ul className="flex flex-col gap-2">{tk.inbox.map((i, k) => <li key={k} className="rounded border border-line bg-surface p-2 text-sm">{String(i.title ?? '')} {String(i.body ?? i.text ?? JSON.stringify(i))}</li>)}</ul>}</Section>
          <Section title={t('room.board')}>{tk.board.length === 0 ? <p className="text-sm text-muted">{t('room.noMessages')}</p> : <ul className="flex flex-col gap-2">{(tk.board as BoardMessage[]).map((b) => <li key={b.msg_id} className="rounded border border-line bg-surface p-2 text-sm"><Badge tone="neutral">{b.msg_type}</Badge> <strong>{b.from}</strong> → {b.to}: {b.body}</li>)}</ul>}</Section>
          <SearchAndAdvice token={token} onCite={(h) => cite(h)} />
          <PostForm card={card} taskId={tk.id} token={token} />
          <DecisionForm key={tk.id} card={card} taskId={tk.id} token={token} cites={current} setCites={setCurrent} />
        </>
      )}
    </>
  )
}

function RoleCard({ card }: { card: SeatCard }) {
  const { t } = useTranslation()
  return (
    <Section title={t('room.roleCard')}>
      <Card>
        <KeyValue items={[
          [t('agents.mission'), card.role.mission || '—'], [t('agents.instructions'), card.role.instructions || '—'], [t('agents.tools'), card.role.tools?.join(', ') ?? '—'],
          [t('room.kbs'), card.knowledge_bases.map((k) => k.name).join(', ') || '—'], [t('room.otherSeats'), card.seat_codes.join(', ') || '—'],
        ]} />
        <details className="mt-3"><summary className="cursor-pointer text-sm font-medium">{t('room.mandates', { n: card.mandates.length })}</summary>
          <ul className="mt-2 flex flex-col gap-1 text-sm">{card.mandates.map((m, i) => <li key={i}><Badge tone="info">{String(m.kind)}</Badge> <code>{String(m.action_code)}</code> {m.description} {m.sources?.map((s, k) => <span key={k} className="text-xs text-muted"> (Art. {s.article ?? '?'})</span>)}</li>)}</ul>
        </details>
      </Card>
    </Section>
  )
}

function Generic({ v }: { v: unknown }) {
  if (v === null || v === undefined) return <span className="text-muted">—</span>
  if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') return <span className="whitespace-pre-wrap">{String(v)}</span>
  if (Array.isArray(v)) return <ul className="list-disc pl-5">{v.map((x, i) => <li key={i}><Generic v={x} /></li>)}</ul>
  return <dl className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1">{Object.entries(v as Record<string, unknown>).map(([k, x]) => <div key={k} className="contents"><dt className="font-medium text-muted">{k}</dt><dd><Generic v={x} /></dd></div>)}</dl>
}

function SearchAndAdvice({ token, onCite }: { token: string; onCite: (h: Hit) => void }) {
  const { t } = useTranslation()
  const [q, setQ] = useState('')
  const [question, setQuestion] = useState('')
  const search = useApiMutation((query: string) => api.post<SeatSearch>('/seats/me/search', { query }, { token }))
  const legal = useApiMutation((question: string) => api.post<LegalAnswer>('/seats/me/ask-legal', { question }, { token }))
  return (
    <Section title={t('room.research')}>
      <p className="mb-2 text-sm text-muted">{t('room.researchHint')}</p>
      <form className="mb-3 flex flex-wrap items-end gap-2" onSubmit={(e) => { e.preventDefault(); if (q.trim()) search.mutate(q) }}>
        <Field label={t('room.searchKb')} className="min-w-52 flex-1"><Input value={q} onChange={(e) => setQ(e.target.value)} /></Field>
        <Button type="submit" loading={search.isPending}>{t('common.search')}</Button>
      </form>
      {search.error && <p role="alert" className="text-sm text-danger">{errorMessage(search.error, t)}</p>}
      {search.data?.warning && <p className="text-sm text-warn">{search.data.warning}</p>}
      <ul className="mb-4 flex flex-col gap-2" aria-live="polite">{search.data?.hits.map((h) => <li key={h.chunk_id} className="rounded border border-line bg-surface p-2 text-sm"><p className="font-medium">{h.title ?? h.doc_code ?? h.doc_title} {h.article ? `· ${h.article}` : ''} {h.page ? `· p.${h.page}` : ''}{typeof h.score === 'number' ? ` · ${t('kb.score')} ${h.score.toFixed(3)}` : ''}</p><p>{h.excerpt ?? h.snippet ?? h.text}</p><p className="text-xs text-muted">chunk <Mono>{h.chunk_id}</Mono></p><Button size="sm" variant="primary" className="mt-2" onClick={() => onCite(h)} icon={<Quote className="h-4 w-4" aria-hidden />}>{t('room.citeThis')}</Button></li>)}</ul>
      <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => { e.preventDefault(); if (question.trim()) legal.mutate(question) }}>
        <Field label={t('room.askAdviser')} className="min-w-52 flex-1" hint={t('room.adviserHint')}><Input value={question} onChange={(e) => setQuestion(e.target.value)} /></Field>
        <Button type="submit" loading={legal.isPending}>{t('room.ask')}</Button>
      </form>
      {legal.error && <p role="alert" className="mt-1 text-sm text-danger">{errorMessage(legal.error, t)}</p>}
      {legal.data && <Card className="mt-2 text-sm" role="status">{legal.data.ok ? <pre className="font-sans whitespace-pre-wrap">{legal.data.answer.replace(/<\/?legal_adviser_answer[^>]*>/g, '').trim()}</pre> : <p className="text-warn">{legal.data.reason ?? t('errors.generic')}</p>}{legal.data.structured && <details className="mt-2"><summary className="cursor-pointer">{t('common.showDetails')}</summary><Generic v={legal.data.structured} /></details>}</Card>}
    </Section>
  )
}

function ErrorList({ err }: { err: unknown }) {
  const { t } = useTranslation()
  if (!err) return null
  const e = err as ApiError
  const failures = (e.details?.failures as { chunk_id: string; reason: string }[] | undefined) ?? []
  const errors = (e.details?.errors as { field?: string; reason?: string; msg?: string; loc?: unknown[] }[] | undefined) ?? []
  return (
    <div role="alert" className="mt-2 rounded border border-danger bg-dangersoft p-2 text-sm text-danger">
      <p className="font-semibold">{errorMessage(err, t)}</p>
      <ul className="list-disc pl-5">
        {failures.map((f, i) => <li key={i}><Mono>{f.chunk_id}</Mono>: {t(`room.citationReasons.${f.reason}`, f.reason)}</li>)}
        {errors.map((x, i) => <li key={i}>{x.field ?? (x.loc ? x.loc.join('.') : '')}: {x.reason ?? x.msg}</li>)}
      </ul>
    </div>
  )
}

function PostForm({ card, taskId, token }: { card: SeatCard; taskId: string; token: string }) {
  const { t } = useTranslation()
  const toast = useToast()
  const [v, setV] = useState({ to: '', msg_type: 'INFO', body: '', final: false })
  const post = useApiMutation(() => api.post('/seats/me/post', { to: v.to, msg_type: v.msg_type, body: v.body, final: v.final }, { token }), {
    onSuccess: () => { toast.push(t('room.postStaged')); setV({ ...v, body: '' }) },
  })
  return (
    <Section title={t('room.postTitle')}>
      <p className="mb-2 text-sm text-muted">{t('room.postHint')}</p>
      <form key={taskId} className="grid gap-3 sm:grid-cols-2" onSubmit={(e) => { e.preventDefault(); post.mutate(undefined) }}>
        <Field label={t('room.to')} required><Select value={v.to} onChange={(e) => setV({ ...v, to: e.target.value })}><option value="">—</option>{card.seat_codes.map((c) => <option key={c}>{c}</option>)}</Select></Field>
        <Field label={t('room.msgType')}><Select value={v.msg_type} onChange={(e) => setV({ ...v, msg_type: e.target.value })}>{['INFO', 'REQUEST', 'DECISION', 'OBJECTION', 'GAP_FLAG'].map((m) => <option key={m}>{m}</option>)}</Select></Field>
        <Field label={t('room.message')} required className="sm:col-span-2"><Textarea maxLength={1500} value={v.body} onChange={(e) => setV({ ...v, body: e.target.value })} /></Field>
        <div className="sm:col-span-2"><Button type="submit" disabled={!v.to || !v.body.trim()} loading={post.isPending}>{t('room.stagePost')}</Button></div>
      </form>
      <ErrorList err={post.error} />
    </Section>
  )
}

function DecisionForm({ card, taskId, token, cites, setCites }: { card: SeatCard; taskId: string; token: string; cites: Citation[]; setCites: (c: Citation[]) => void }) {
  const { t } = useTranslation()
  const toast = useToast()
  const qc = useQueryClient()
  const [v, setV] = useState({ action: '', action_code: '', outcome: 'act', confidence: 'medium', evidence_tag: 'documented', rationale: '', options: '' })
  const decide = useApiMutation(() => api.post('/seats/me/decision', {
    action: v.action, action_code: v.action_code || null, outcome: v.outcome, confidence: v.confidence, evidence_tag: v.evidence_tag, rationale: v.rationale,
    options_considered: v.options.split('\n').map((x) => x.trim()).filter(Boolean), legal_basis: v.outcome === 'no_legal_basis_found' ? [] : cites.map((c) => ({ chunk_id: c.chunk_id, article: c.article || null, quote: c.quote })), gap_flags: [],
  }, { token }), {
    onSuccess: () => { toast.push(t('room.decisionRecorded')); void qc.invalidateQueries({ queryKey: [...keys.seatTask, token] }) },
  })
  const kb = card.knowledge_bases.length
  // Même règle que le serveur : une base légale est obligatoire, sauf issue « aucune base légale trouvée ».
  const complete = cites.filter((c) => c.chunk_id.trim() && c.quote.trim())
  const needsBasis = v.outcome !== 'no_legal_basis_found' && complete.length === 0
  return (
    <Section title={t('room.decisionTitle')}>
      <span id="decision-form" className="block scroll-mt-4" />
      <p className="mb-2 text-sm text-muted">{t('room.decisionHint')}</p>
      <form key={taskId} className="grid gap-3 sm:grid-cols-2" onSubmit={(e) => { e.preventDefault(); decide.mutate(undefined) }}>
        <Field label={t('room.action')} required className="sm:col-span-2"><Input maxLength={500} value={v.action} onChange={(e) => setV({ ...v, action: e.target.value })} /></Field>
        <Field label={t('room.actionCode')}><Input value={v.action_code} onChange={(e) => setV({ ...v, action_code: e.target.value })} /></Field>
        <Field label={t('room.outcome')}><Select value={v.outcome} onChange={(e) => setV({ ...v, outcome: e.target.value })}>{['act', 'decline', 'refer', 'no_legal_basis_found'].map((o) => <option key={o} value={o}>{t(`room.outcomes.${o}`)}</option>)}</Select></Field>
        <Field label={t('room.confidence')}><Select value={v.confidence} onChange={(e) => setV({ ...v, confidence: e.target.value })}>{['low', 'medium', 'high'].map((o) => <option key={o}>{o}</option>)}</Select></Field>
        <Field label={t('room.evidenceTag')}><Select value={v.evidence_tag} onChange={(e) => setV({ ...v, evidence_tag: e.target.value })}>{['documented', 'inferred', 'assumed'].map((o) => <option key={o}>{o}</option>)}</Select></Field>
        <Field label={t('room.rationale')} required hint={t('room.rationaleHint', { n: v.rationale.length })} className="sm:col-span-2"><Textarea rows={2} maxLength={280} value={v.rationale} onChange={(e) => setV({ ...v, rationale: e.target.value })} /></Field>
        <Field label={t('room.options')} className="sm:col-span-2"><Textarea rows={2} value={v.options} onChange={(e) => setV({ ...v, options: e.target.value })} /></Field>
        {v.outcome !== 'no_legal_basis_found' && (
          <fieldset className="rounded border border-line p-3 sm:col-span-2"><legend className="px-1 text-sm font-semibold">{t('room.legalBasis')}</legend>
            <p className="mb-2 text-xs text-muted">{t('room.legalBasisHint', { kb })}</p>
            {cites.length === 0 && <p className="mb-2 rounded bg-brandsoft p-2 text-xs font-semibold text-brand">{t('room.citeHint')}</p>}
            {cites.map((c, i) => (
              <div key={i} className="mb-2 grid gap-2 sm:grid-cols-[1fr_6rem_auto]">
                <Input aria-label="chunk_id" placeholder="chunk_id" value={c.chunk_id} onChange={(e) => setCites(cites.map((x, j) => j === i ? { ...x, chunk_id: e.target.value } : x))} />
                <Input aria-label={t('kb.article')} placeholder={t('kb.article')} value={c.article} onChange={(e) => setCites(cites.map((x, j) => j === i ? { ...x, article: e.target.value } : x))} />
                <Button size="sm" onClick={() => setCites(cites.filter((_, j) => j !== i))}>{t('common.delete')}</Button>
                <Textarea className="sm:col-span-3" rows={2} aria-label={t('room.quote')} placeholder={t('room.quote')} value={c.quote} onChange={(e) => setCites(cites.map((x, j) => j === i ? { ...x, quote: e.target.value } : x))} />
              </div>
            ))}
            <Button size="sm" onClick={() => setCites([...cites, { chunk_id: '', article: '', quote: '' }])}>{t('room.addCitation')}</Button>
          </fieldset>
        )}
        <div className="flex flex-col gap-2 sm:col-span-2">
          {needsBasis && <p role="status" className="rounded border border-warn bg-warnsoft p-2 text-sm text-warn">{t('room.needBasis')}</p>}
          <Button type="submit" variant="primary" className="self-start" disabled={!v.action.trim() || !v.rationale.trim() || needsBasis} loading={decide.isPending}>{t('room.submitDecision')}</Button>
        </div>
      </form>
      <ErrorList err={decide.error} />
    </Section>
  )
}
