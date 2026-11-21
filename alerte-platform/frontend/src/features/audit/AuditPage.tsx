import { useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { LedgerEvent, VerifyResult } from '@/api/types'
import type { Exercise } from '@/api/loose'
import type { StreamEvent } from '@/api/sse'
import { NoAiBanner } from '@/app/AppShell'
import { Badge, Button, Card, EmptyState, Field, Input, Mono, PageHeader, QueryState, Section, Select, Table, TBody, Td, Th, THead, Tr, useToast } from '@/components/ui'
import { DecisionTraceDialog } from '@/features/room/DecisionTrace'
import { BoardPanel, SeatCards, Timeline } from '@/features/room/RoomPanels'
import { roomReducer, initialRoomState, seatOf, type DecisionItem } from '@/features/room/state'
import { errorMessage } from '@/lib/errors'

/** Ledger rows as stream events (seat code derived from the actor, which is `seat:<CODE>` for seat acts). */
export function toStreamEvent(e: LedgerEvent): StreamEvent {
  const seat = e.actor.startsWith('seat:') ? e.actor.slice(5) : (e.payload.seat as string | undefined) ?? null
  return { seq: e.seq, type: e.type, actor: e.actor, seat, sim_time: e.sim_time, real_time: e.real_time, visibility: e.visibility, payload: e.payload }
}

export function AuditPage() {
  const { exerciseId = '' } = useParams()
  const ex = useApiQuery<Exercise>(keys.exercise(exerciseId), `/exercises/${exerciseId}`)
  return <QueryState q={ex} what="(/exercises)">{(e) => <AuditView ex={e} />}</QueryState>
}

function AuditView({ ex }: { ex: Exercise }) {
  const { t } = useTranslation()
  const toast = useToast()
  const [params, setParams] = useSearchParams()
  const q = useApiQuery<LedgerEvent[]>(keys.ledger(ex.id), `/exercises/${ex.id}/ledger`, { query: { limit: 5000 } })
  const anchors = useApiQuery<{ seq: number; hash: string; kind: string; created_at: string }[]>(keys.anchors(ex.id), `/exercises/${ex.id}/anchors`)
  const digest = useApiQuery<{ replay_digest: string; events: number }>(keys.replayDigest(ex.id), `/exercises/${ex.id}/replay-digest`)
  const [type, setType] = useState('')
  const [seat, setSeat] = useState('')
  const [text, setText] = useState('')
  const [cursor, setCursor] = useState<number | null>(null)
  const verify = useApiMutation(() => api.get<VerifyResult>(`/exercises/${ex.id}/ledger/verify`), { onError: (e) => toast.push(errorMessage(e, t), 'danger') })
  const events = useMemo(() => (q.data ?? []).map(toStreamEvent), [q.data])
  const types = [...new Set(events.map((e) => e.type))].sort()
  const seats = [...new Set(events.map((e) => seatOf(e)).filter((s): s is string => !!s))].sort()
  const shown = events.filter((e) => (!type || e.type === type) && (!seat || seatOf(e) === seat) && (!text || JSON.stringify(e.payload).toLowerCase().includes(text.toLowerCase())))
  const highlight = Number(params.get('seq') ?? 0)
  const traceId = params.get('decision')
  const replay = useMemo(() => roomReducer(initialRoomState, { type: 'events', events: cursor === null ? [] : events.filter((e) => e.seq <= cursor) }), [events, cursor])
  const traceDecision: DecisionItem | null = useMemo(() => {
    if (!traceId) return null
    const all = roomReducer(initialRoomState, { type: 'events', events })
    return all.decisions.find((d) => d.decisionId === traceId) ?? null
  }, [traceId, events])
  const v = verify.data
  const maxSeq = events.length ? events[events.length - 1].seq : 0
  const replaySeats = Object.values(replay.seats).sort((a, b) => a.code.localeCompare(b.code))

  return (
    <>
      <p className="mb-1 text-sm"><Link to="/audit">← {t('nav.audit')}</Link> · <Link to={`/room/${ex.id}`}>{t('nav.room_live')}</Link></p>
      <NoAiBanner aiMode={ex.ai_mode} />
      <PageHeader title={`${t('nav.audit')} — ${ex.title}`} description={t('audit.description')}
        actions={<Button onClick={() => void api.download(`/exercises/${ex.id}/ledger/export`, `ledger-${ex.code}.jsonl`).catch((e) => toast.push(errorMessage(e, t), 'danger'))}>{t('audit.exportJsonl')}</Button>} />

      <Section title={t('audit.integrity')}>
        <Card>
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="primary" loading={verify.isPending} onClick={() => verify.mutate(undefined)}>{t('audit.verify')}</Button>
            <div role="status" aria-live="polite">
              {v && (v.ok ? <Badge tone="ok">{t('audit.intact', { n: v.checked })}</Badge> : <Badge tone="danger">{v.first_bad_seq !== null ? t('audit.firstAltered', { n: v.first_bad_seq }) : t('audit.notIntact')}</Badge>)}
              {v?.anchor_mismatch && <> <Badge tone="danger">{t('audit.anchorMismatch')}</Badge></>}
              {v?.truncated_after_anchor && <> <Badge tone="danger">{t('audit.truncated')}</Badge></>}
              {v && !v.ok && v.reason && <p className="text-sm text-danger">{v.reason}</p>}
            </div>
          </div>
          {v && <p className="mt-2 text-xs text-muted">{t('audit.head')}: #{v.head_seq ?? '—'} <Mono>{(v.head_hash ?? '').slice(0, 24)}</Mono></p>}
          <p className="mt-3 text-xs text-muted">{t('audit.honest')}</p>
          <dl className="mt-2 grid grid-cols-[max-content_1fr] gap-x-3 text-xs">
            <dt className="text-muted">{t('audit.replayDigest')}</dt><dd><Mono>{digest.data?.replay_digest ?? '—'}</Mono> ({digest.data?.events ?? 0} {t('audit.events')})</dd>
            <dt className="text-muted">{t('audit.anchors')}</dt><dd>{anchors.data?.length ? anchors.data.map((a) => `#${a.seq}`).join(', ') : '—'}</dd>
          </dl>
        </Card>
      </Section>

      <Section title={t('audit.timeline')}>
        <div className="mb-3 grid gap-3 sm:grid-cols-3">
          <Field label={t('audit.type')}><Select value={type} onChange={(e) => setType(e.target.value)}><option value="">{t('common.all')}</option>{types.map((x) => <option key={x}>{x}</option>)}</Select></Field>
          <Field label={t('audit.seat')}><Select value={seat} onChange={(e) => setSeat(e.target.value)}><option value="">{t('common.all')}</option>{seats.map((x) => <option key={x}>{x}</option>)}</Select></Field>
          <Field label={t('audit.contains')}><Input value={text} onChange={(e) => setText(e.target.value)} /></Field>
        </div>
        <QueryState q={q} what="(/ledger)">
          {() => shown.length === 0 ? <EmptyState title={t('audit.noEvents')} /> : (
            <Table caption={t('audit.timeline')}>
              <THead><Tr><Th>#</Th><Th>{t('audit.type')}</Th><Th>{t('audit.actor')}</Th><Th>{t('room.clock')}</Th><Th>{t('audit.visibility')}</Th><Th>{t('audit.summary')}</Th></Tr></THead>
              <TBody>{shown.map((e) => (
                <Tr key={e.seq} className={e.seq === highlight ? 'bg-brandsoft' : ''} aria-current={e.seq === highlight ? 'true' : undefined}>
                  <Td className="font-mono">{e.seq}</Td><Td><Badge tone={e.type === 'ERROR' ? 'danger' : e.type === 'DECISION' ? 'ok' : 'neutral'}>{e.type}</Badge></Td><Td>{e.actor}</Td><Td>{e.sim_time ?? '—'}</Td><Td>{e.visibility}</Td>
                  <Td className="max-w-lg text-xs">{e.type === 'DECISION' ? <Link to={`?decision=${String(e.payload.decision_id)}`}>{String(e.payload.action ?? e.payload.outcome)} — {t('room.showTrace')}</Link> : <details><summary className="cursor-pointer">{summary(e)}</summary><pre className="mt-1 overflow-x-auto rounded bg-surface2 p-1 whitespace-pre-wrap">{JSON.stringify(e.payload, null, 2)}</pre></details>}</Td>
                </Tr>
              ))}</TBody>
            </Table>
          )}
        </QueryState>
      </Section>

      <Section title={t('audit.replay')}>
        <p className="mb-2 text-sm text-muted">{t('audit.replayHint')}</p>
        {maxSeq === 0 ? <p className="text-sm text-muted">{t('audit.noEvents')}</p> : (
          <>
            <label className="mb-2 block text-sm font-medium" htmlFor="cursor">{t('audit.cursor', { seq: cursor ?? 0, max: maxSeq })}</label>
            <input id="cursor" type="range" min={0} max={maxSeq} value={cursor ?? 0} onChange={(e) => setCursor(Number(e.target.value))} className="mb-1 w-full" />
            <p className="mb-3 text-sm">{t('room.clock')}: <strong>{replay.simTime ?? '—'}</strong> · {t('audit.stateAt')}: <strong>{replay.exerciseState ?? '—'}</strong></p>
            {cursor !== null && (
              <div className="grid gap-4 lg:grid-cols-[17rem_1fr]">
                <Timeline injects={replay.injects} current={replay.currentInject} />
                <div className="flex flex-col gap-4"><SeatCards seats={replaySeats} decisions={replay.decisions} onSeat={() => undefined} onDecision={(d) => setParams({ decision: d.decisionId })} /><BoardPanel board={replay.board} /></div>
              </div>
            )}
          </>
        )}
      </Section>
      <DecisionTraceDialog decision={traceDecision} events={events} onClose={() => setParams({})} />
    </>
  )
}

function summary(e: StreamEvent): string {
  const p = e.payload
  const pick = (p.title ?? p.query ?? p.tool ?? p.body ?? p.message ?? p.signal ?? p.to ?? p.command ?? p.kind) as string | undefined
  return pick ? String(pick).slice(0, 100) : '…'
}
