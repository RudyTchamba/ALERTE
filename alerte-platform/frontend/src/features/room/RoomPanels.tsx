import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Hourglass } from 'lucide-react'
import { Badge, Button, EmptyState, Select } from '@/components/ui'
import { cn } from '@/lib/cn'
import { BOARD_TYPES, OutcomeBadge, SIGNAL_TONE, VerifiedBadge } from './parts'
import type { BoardItem, DecisionItem, InjectItem, SeatLive, SignalItem } from './state'

export function Timeline({ injects, current }: { injects: InjectItem[]; current: string | null }) {
  const { t } = useTranslation()
  return (
    <section aria-label={t('room.timeline')}>
      <h2 className="mb-2 text-base font-semibold">{t('room.timeline')}</h2>
      {injects.length === 0 ? <p className="text-sm text-muted">{t('room.noInjects')}</p> : (
        <ol className="flex flex-col gap-2">
          {injects.map((i) => (
            <li key={i.ref} aria-current={i.ref === current ? 'step' : undefined} className={cn('rounded-md border p-2 text-sm', i.ref === current ? 'border-brand bg-brandsoft' : 'border-line bg-surface')}>
              <p className="font-semibold">{i.ref === current && <Badge tone="info">{t('room.current')}</Badge>} {i.simTime} — {i.title}</p>
              <p className="text-xs text-muted">→ {i.recipients.join(', ') || '—'}</p>
              {i.surprise && <Badge tone="warn">{t('room.surprise')}</Badge>}
              {i.faultMode && i.faultMode !== 'none' && <Badge tone="warn">{t('scenarios.fault')}: {i.faultMode}</Badge>}
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

export function SeatCards({ seats, decisions, onSeat, onDecision }: { seats: SeatLive[]; decisions: DecisionItem[]; onSeat: (code: string) => void; onDecision: (d: DecisionItem) => void }) {
  const { t } = useTranslation()
  return (
    <section aria-label={t('room.seats')}>
      <h2 className="mb-2 text-base font-semibold">{t('room.seats')}</h2>
      {seats.length === 0 ? <EmptyState title={t('room.noSeats')} /> : (
        <ul className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">
          {seats.map((s) => {
            const last = [...decisions].reverse().find((d) => d.seat === s.code)
            return (
              <li key={s.code} className="flex flex-col gap-2 rounded-lg border border-line bg-surface p-3">
                <div className="flex items-center justify-between gap-2">
                  <button type="button" className="text-left font-bold underline" onClick={() => onSeat(s.code)} aria-label={t('room.openSeat', { seat: s.code })}>{s.code}</button>
                  <Badge tone={s.controller === 'human' ? 'info' : s.controller === 'scripted' ? 'warn' : 'neutral'}>{s.controller === 'human' ? `${t('exercises.ctrl.human')}${s.humanName ? ` · ${s.humanName}` : ''}` : s.controller ? t(`exercises.ctrl.${s.controller}`, s.controller) : '—'}</Badge>
                </div>
                {s.awaitingHuman && <p className="flex items-center gap-1 text-sm font-semibold text-warn"><Hourglass className="h-4 w-4" aria-hidden />{t('room.awaitingHuman')}</p>}
                {last ? (
                  <div className="text-sm">
                    <p className="mb-1 flex flex-wrap items-center gap-1"><VerifiedBadge d={last} /><OutcomeBadge outcome={last.outcome} /></p>
                    <p className="line-clamp-3">{last.action}</p>
                    <Button size="sm" className="mt-1" onClick={() => onDecision(last)}>{t('room.showTrace')}</Button>
                  </div>
                ) : <p className="text-sm text-muted">{t('room.noDecisionYet')}</p>}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

export function BoardPanel({ board }: { board: BoardItem[] }) {
  const { t } = useTranslation()
  const [types, setTypes] = useState<Set<string>>(new Set(BOARD_TYPES))
  const [round, setRound] = useState('')
  const rounds = [...new Set(board.map((b) => b.round).filter((r): r is number => r !== null))].sort()
  const shown = board.filter((b) => types.has(b.type) && (!round || String(b.round) === round))
  return (
    <section aria-label={t('room.board')}>
      <h2 className="mb-2 text-base font-semibold">{t('room.board')}</h2>
      <div className="mb-2 flex flex-wrap items-end gap-2">
        <fieldset className="flex flex-wrap gap-2 text-xs"><legend className="sr-only">{t('room.filterTypes')}</legend>
          {BOARD_TYPES.map((ty) => <label key={ty} className="inline-flex items-center gap-1"><input type="checkbox" className="h-4 w-4" checked={types.has(ty)} onChange={(e) => { const n = new Set(types); if (e.target.checked) n.add(ty); else n.delete(ty); setTypes(n) }} />{ty}</label>)}
        </fieldset>
        <label className="text-xs">{t('room.round')} <Select className="!inline-block !w-auto !min-h-7 !py-0" value={round} onChange={(e) => setRound(e.target.value)}><option value="">{t('common.all')}</option>{rounds.map((r) => <option key={r} value={r}>{r}</option>)}</Select></label>
      </div>
      {shown.length === 0 ? <p className="text-sm text-muted">{t('room.noMessages')}</p> : (
        <ul className="flex max-h-96 flex-col gap-2 overflow-y-auto">
          {shown.map((b) => (
            <li key={b.msgId} className="rounded border border-line bg-surface p-2 text-sm">
              <p className="flex flex-wrap items-center gap-1"><Badge tone={b.type === 'OBJECTION' ? 'warn' : b.type === 'GAP_FLAG' ? 'danger' : b.type === 'REQUEST' ? 'info' : 'neutral'}>{b.type}</Badge><strong>{b.from}</strong> → {b.to}{b.round !== null && <span className="text-xs text-muted"> · {t('room.round')} {b.round}</span>}{b.replyStatus && <Badge tone="neutral">{b.replyStatus}</Badge>}</p>
              <p className="mt-1">{b.body}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export function SignalsPanel({ signals, canSeeAudit }: { signals: SignalItem[]; canSeeAudit: boolean }) {
  const { t } = useTranslation()
  return (
    <section aria-label={t('room.signals')}>
      <h2 className="mb-1 text-base font-semibold">{t('room.signals')}</h2>
      <p className="mb-2 text-xs text-muted">{t('room.signalsHint')}</p>
      {signals.length === 0 ? <p className="text-sm text-muted">{canSeeAudit ? t('room.noSignals') : t('room.signalsHidden')}</p> : (
        <ul className="flex flex-col gap-1">
          {signals.map((s) => (
            <li key={s.seq} className="rounded border border-line bg-surface p-2 text-sm">
              <Badge tone={SIGNAL_TONE[s.signal] ?? 'neutral'}>{t(`room.signalNames.${s.signal}`, s.signal)}</Badge>{' '}
              {s.scripted && <Badge tone="warn">{t('common.noAiShort')}</Badge>}{' '}
              {s.actionCode && <code className="text-xs">{s.actionCode}</code>} {s.injectRef && <span className="text-xs text-muted">({s.injectRef})</span>}
              {s.gapId && <> <Link to={`/gaps/${s.gapId}`}>{t('room.openGap')}</Link></>}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
