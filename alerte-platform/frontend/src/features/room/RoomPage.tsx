import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Pause, Play, SkipForward, Square, Zap } from 'lucide-react'
import { api } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { CommandKind } from '@/api/types'
import type { CommandResult, Exercise, InboxItem } from '@/api/loose'
import { NoAiBanner } from '@/app/AppShell'
import { useAuth } from '@/app/auth'
import { Badge, Button, ConfirmDialog, Dialog, Field, Input, Mono, QueryState, Select, StatusBadge, Textarea, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { useQueryClient } from '@tanstack/react-query'
import { DecisionTraceDialog } from './DecisionTrace'
import { BoardPanel, SeatCards, SignalsPanel, Timeline } from './RoomPanels'
import { OutcomeBadge, VerifiedBadge } from './parts'
import type { DecisionItem } from './state'
import { useExerciseStream } from './useExerciseStream'

const ALLOWED: Record<string, string[]> = {
  pause: ['running'], resume: ['paused', 'interrupted'], step: ['running', 'paused'], stop: ['running', 'paused'], surprise: ['running', 'paused'], speed: ['running'],
}

export function RoomPage() {
  const { exerciseId = '' } = useParams()
  const q = useApiQuery<Exercise>(keys.exercise(exerciseId), `/exercises/${exerciseId}`, { refetchInterval: 5000 })
  return <QueryState q={q} what="(/exercises)">{(ex) => <RoomView ex={ex} />}</QueryState>
}

function RoomView({ ex }: { ex: Exercise }) {
  const { t } = useTranslation()
  const toast = useToast()
  const qc = useQueryClient()
  const { role } = useAuth()
  const { state, status, error, seed } = useExerciseStream(ex.id)
  const [trace, setTrace] = useState<DecisionItem | null>(null)
  const [seatOpen, setSeatOpen] = useState<string | null>(null)
  const [stopAsk, setStopAsk] = useState(false)
  const [surprise, setSurprise] = useState(false)
  const exState = state.exerciseState ?? ex.state
  const canControl = role === 'owner' || role === 'member'

  useEffect(() => { if (ex.seats) seed(ex.seats.map((s) => ({ code: s.code, controller: s.controller, human_name: s.human_name }))) }, [ex.seats, seed])
  useEffect(() => { if (state.exerciseState) void qc.invalidateQueries({ queryKey: keys.exercise(ex.id) }) }, [state.exerciseState, qc, ex.id])

  const cmd = useApiMutation((v: { kind: CommandKind; args?: Record<string, unknown> }) => api.post<CommandResult>(`/exercises/${ex.id}/commands`, v), {
    invalidate: [keys.exercise(ex.id)], onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const seats = useMemo(() => Object.values(state.seats).sort((a, b) => a.code.localeCompare(b.code)), [state.seats])
  const cap = Number(ex.settings.max_llm_calls ?? 0)
  const used = Math.max(ex.llm_calls_used, state.llmCalls)
  const ok = (k: string) => ALLOWED[k]?.includes(exState) && canControl
  const live = status === 'open' ? 'ok' : status === 'ended' ? 'neutral' : status === 'error' ? 'danger' : 'warn'
  const hasAudit = role === 'owner' || role === 'member'

  return (
    <>
      <NoAiBanner aiMode={ex.ai_mode} />
      <header className="mb-4 rounded-lg border border-line bg-surface p-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold">{ex.title}</h1>
            <p className="flex flex-wrap items-center gap-2 text-sm">
              <StatusBadge status={exState} />{ex.substate === 'waiting_human' && <Badge tone="warn">{t('room.waitingHuman')}</Badge>}
              <span><span className="text-muted">{t('room.clock')}:</span> <strong>{state.simTime ?? '—'}</strong></span>
              <span><span className="text-muted">{t('room.budget')}:</span> <strong>{used}{cap ? `/${cap}` : ''}</strong> {t('room.calls')}</span>
              <Badge tone={live}>{t(`room.stream.${status}`)}</Badge>
              <Link to={`/audit/${ex.id}`}>{t('nav.audit')}</Link>
            </p>
          </div>
          <div className="flex flex-wrap gap-2" role="group" aria-label={t('room.commands')}>
            <Button disabled={!ok('pause')} onClick={() => cmd.mutate({ kind: 'pause' })} icon={<Pause className="h-4 w-4" aria-hidden />}>{t('room.cmd.pause')}</Button>
            <Button disabled={!ok('resume')} onClick={() => cmd.mutate({ kind: 'resume' })} icon={<Play className="h-4 w-4" aria-hidden />}>{t('room.cmd.resume')}</Button>
            <Button disabled={!ok('step')} onClick={() => cmd.mutate({ kind: 'step' })} icon={<SkipForward className="h-4 w-4" aria-hidden />}>{t('room.cmd.step')}</Button>
            <label className="sr-only" htmlFor="pace">{t('exercises.pace')}</label>
            <Select id="pace" className="!w-auto" disabled={!ok('speed')} value={ex.pace} onChange={(e) => cmd.mutate({ kind: 'speed', args: { pace: e.target.value } })}>
              <option value="manual">{t('exercises.paces.manual')}</option><option value="auto">{t('exercises.paces.auto')}</option><option value="auto_delay">{t('exercises.paces.auto_delay')}</option>
            </Select>
            <Button disabled={!ok('surprise')} onClick={() => setSurprise(true)} icon={<Zap className="h-4 w-4" aria-hidden />}>{t('room.cmd.surprise')}</Button>
            <Button variant="danger" disabled={!ok('stop')} onClick={() => setStopAsk(true)} icon={<Square className="h-4 w-4" aria-hidden />}>{t('room.cmd.stop')}</Button>
          </div>
        </div>
        {error && status !== 'open' && <p role="status" className="mt-2 text-xs text-muted">{error}</p>}
      </header>
      {state.errors.length > 0 && <div role="alert" className="mb-3 rounded border border-danger bg-dangersoft p-2 text-sm">{state.errors.slice(-3).map((e) => <p key={e.seq}><Badge tone="danger">{e.component}</Badge> {e.message}</p>)}</div>}
      <div className="grid gap-4 lg:grid-cols-[17rem_1fr] xl:grid-cols-[17rem_1fr_22rem]">
        <Timeline injects={state.injects} current={state.currentInject} />
        <SeatCards seats={seats} decisions={state.decisions} onSeat={setSeatOpen} onDecision={setTrace} />
        <div className="flex flex-col gap-6 lg:col-span-2 xl:col-span-1">
          <BoardPanel board={state.board} />
          <SignalsPanel signals={state.signals} canSeeAudit={hasAudit} />
        </div>
      </div>
      <p className="sr-only-live" aria-live="polite" role="log">{state.announcements.slice(-1)[0] ?? ''}</p>
      <DecisionTraceDialog decision={trace} events={state.events} onClose={() => setTrace(null)} />
      {seatOpen && <SeatDialog ex={ex} code={seatOpen} state={state.decisions} onTrace={(d) => { setSeatOpen(null); setTrace(d) }} onClose={() => setSeatOpen(null)} canControl={canControl} running={['running', 'paused'].includes(exState)} />}
      {surprise && <SurpriseDialog exId={ex.id} seats={seats.map((s) => s.code)} onClose={() => setSurprise(false)} />}
      <ConfirmDialog open={stopAsk} onClose={() => setStopAsk(false)} danger title={t('room.cmd.stop')} message={t('room.stopConfirm')} confirmLabel={t('room.cmd.stop')} onConfirm={() => { cmd.mutate({ kind: 'stop' }); setStopAsk(false) }} />
    </>
  )
}

function SurpriseDialog({ exId, seats, onClose }: { exId: string; seats: string[]; onClose: () => void }) {
  const { t } = useTranslation()
  const toast = useToast()
  const [v, setV] = useState({ title: '', body: '', fault_mode: 'none' })
  const [rec, setRec] = useState<string[]>([])
  const send = useApiMutation(() => api.post(`/exercises/${exId}/commands`, { kind: 'surprise', args: { ...v, recipients: rec } }), {
    invalidate: [keys.exercise(exId)], onSuccess: () => { toast.push(t('room.surpriseSent')); onClose() }, onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  return (
    <Dialog open onClose={onClose} title={t('room.cmd.surprise')} footer={<><Button onClick={onClose}>{t('common.cancel')}</Button><Button variant="primary" disabled={!v.title || !v.body || !rec.length} loading={send.isPending} onClick={() => send.mutate(undefined)}>{t('room.sendSurprise')}</Button></>}>
      <div className="flex flex-col gap-3">
        <Field label={t('scenarios.title_')} required><Input data-autofocus value={v.title} onChange={(e) => setV({ ...v, title: e.target.value })} /></Field>
        <Field label={t('scenarios.body')} required><Textarea value={v.body} onChange={(e) => setV({ ...v, body: e.target.value })} /></Field>
        <fieldset><legend className="mb-1 text-sm font-medium">{t('scenarios.recipients')}</legend>
          <div className="flex flex-wrap gap-3">{seats.map((s) => <label key={s} className="inline-flex items-center gap-1 text-sm"><input type="checkbox" className="h-4 w-4" checked={rec.includes(s)} onChange={(e) => setRec(e.target.checked ? [...rec, s] : rec.filter((x) => x !== s))} />{s}</label>)}</div>
        </fieldset>
        <p className="text-xs text-muted">{t('room.surpriseHint')}</p>
      </div>
    </Dialog>
  )
}

function SeatDialog({ ex, code, state, onTrace, onClose, canControl, running }: { ex: Exercise; code: string; state: DecisionItem[]; onTrace: (d: DecisionItem) => void; onClose: () => void; canControl: boolean; running: boolean }) {
  const { t } = useTranslation()
  const toast = useToast()
  const inbox = useApiQuery<InboxItem[]>(keys.ledger(ex.id, { inbox: code }), `/exercises/${ex.id}/inbox`, { query: { seat: code }, enabled: canControl })
  const [name, setName] = useState('')
  const switchCtl = useApiMutation((v: { controller: string; human_name?: string }) => api.post(`/exercises/${ex.id}/commands`, { kind: 'seat_switch', args: { seat: code, ...v } }), {
    invalidate: [keys.exercise(ex.id)], onSuccess: () => { toast.push(t('room.seatSwitched')); onClose() }, onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const mine = state.filter((d) => d.seat === code)
  return (
    <Dialog open wide onClose={onClose} title={t('room.seatTitle', { seat: code })}>
      <section className="mb-4"><h3 className="mb-1 font-semibold">{t('room.decisions')}</h3>
        {mine.length === 0 ? <p className="text-sm text-muted">{t('room.noDecisionYet')}</p> : <ul className="flex flex-col gap-2">{mine.map((d) => (
          <li key={d.decisionId} className="rounded border border-line p-2 text-sm"><p className="flex flex-wrap items-center gap-1"><VerifiedBadge d={d} /><OutcomeBadge outcome={d.outcome} /><span className="text-xs text-muted">{d.simTime} · {t('room.round')} {d.round}</span></p><p>{d.action}</p><Button size="sm" onClick={() => onTrace(d)}>{t('room.showTrace')}</Button></li>
        ))}</ul>}
      </section>
      {canControl && <section className="mb-4"><h3 className="mb-1 font-semibold">{t('room.inbox')}</h3>
        <QueryState q={inbox} what="(/inbox)">{(items) => items.length === 0 ? <p className="text-sm text-muted">{t('room.emptyInbox')}</p> : <ul className="flex flex-col gap-1 text-sm">{items.map((i) => <li key={i.item_id} className="rounded border border-line p-2"><Badge tone="neutral">{i.source}</Badge> <strong>{String(i.title ?? '')}</strong> {String(i.body ?? i.text ?? '')}</li>)}</ul>}</QueryState>
      </section>}
      {canControl && running && (
        <section><h3 className="mb-1 font-semibold">{t('room.takeControl')}</h3>
          <p className="mb-2 text-xs text-muted">{t('room.takeControlHint')} <Mono>seat_switch</Mono></p>
          <div className="flex flex-wrap items-end gap-2">
            <Button onClick={() => switchCtl.mutate({ controller: 'agent' })}>{t('room.giveToAgent')}</Button>
            <Field label={t('exercises.humanName')} className="w-48"><Input value={name} onChange={(e) => setName(e.target.value)} /></Field>
            <Button variant="primary" disabled={!name.trim()} onClick={() => switchCtl.mutate({ controller: 'human', human_name: name })}>{t('room.giveToHuman')}</Button>
          </div>
        </section>
      )}
    </Dialog>
  )
}
