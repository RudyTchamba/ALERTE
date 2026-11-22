import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowRight, BookMarked, CheckCircle2, Hourglass, XCircle } from 'lucide-react'
import { Badge, Button, EmptyState, Select } from '@/components/ui'
import { cn } from '@/lib/cn'
import { BOARD_TYPES, OutcomeBadge, SIGNAL_TONE, VerifiedBadge } from './parts'
import type { BoardItem, DecisionItem, InjectItem, SeatLive, SignalItem } from './state'

function PanelTitle({ children, count }: { children: ReactNode; count?: number }) {
  return (
    <h2 className="mb-3 flex items-center gap-2 text-sm font-bold tracking-wide uppercase">
      {children}
      {count !== undefined && <span className="rounded bg-surface2 px-1.5 text-xs font-semibold text-muted tabular">{count}</span>}
    </h2>
  )
}

/** Fil chronologique des événements (injects) : ligne verticale, point lumineux pour l'événement en cours. */
export function Timeline({ injects, current }: { injects: InjectItem[]; current: string | null }) {
  const { t } = useTranslation()
  return (
    <section aria-label={t('room.timeline')} className="panel p-4">
      <PanelTitle count={injects.length}>{t('room.timeline')}</PanelTitle>
      {injects.length === 0 ? <p className="text-sm text-muted">{t('room.noInjects')}</p> : (
        <ol className="relative flex flex-col gap-3 pl-5">
          <span aria-hidden className="absolute top-2 bottom-2 left-[0.3rem] w-px bg-line" />
          {injects.map((i) => {
            const isCur = i.ref === current
            return (
              <li key={i.ref} aria-current={isCur ? 'step' : undefined} className="relative">
                <span aria-hidden className={cn('absolute top-1.5 -left-5 h-3 w-3 rounded-full border-2',
                  isCur ? 'live-dot is-live border-brand bg-brand text-brand' : 'border-muted bg-surface')} />
                <div className={cn('rounded-lg border p-2.5 text-sm', isCur ? 'border-brand bg-brandsoft/50' : 'border-line bg-surface2/50')}>
                  <p className="font-semibold">{isCur && <Badge tone="info">{t('room.current')}</Badge>} {i.simTime} — {i.title}</p>
                  {i.body && <p className="mt-1 line-clamp-3 text-xs text-muted">{i.body}</p>}
                  <p className="mt-1.5 flex flex-wrap items-center gap-1 text-xs text-muted">
                    <ArrowRight className="h-3 w-3" aria-hidden />
                    {i.recipients.length ? i.recipients.map((r) => <span key={r} className="rounded bg-surface px-1 font-mono font-semibold text-ink">{r}</span>) : '—'}
                  </p>
                  {(i.surprise || (i.faultMode && i.faultMode !== 'none')) && (
                    <p className="mt-1.5 flex flex-wrap gap-1">
                      {i.surprise && <Badge tone="warn">{t('room.surprise')}</Badge>}
                      {i.faultMode && i.faultMode !== 'none' && <Badge tone="warn">{t('scenarios.fault')}: {i.faultMode}</Badge>}
                    </p>
                  )}
                </div>
              </li>
            )
          })}
        </ol>
      )}
    </section>
  )
}

function decisionTone(d: DecisionItem | undefined): 'ok' | 'danger' | 'warn' | 'none' {
  if (!d) return 'none'
  if (d.author === 'fallback') return 'warn'
  return d.status === 'recorded' ? 'ok' : 'danger'
}
const STRIPE = { ok: 'bg-ok', danger: 'bg-danger', warn: 'bg-warn', none: 'bg-line' }

/** Une carte par institution : qui la tient, sa dernière décision et la base légale citée (vérifiée ou refusée). */
export function SeatCards({ seats, decisions, onSeat, onDecision }: { seats: SeatLive[]; decisions: DecisionItem[]; onSeat: (code: string) => void; onDecision: (d: DecisionItem) => void }) {
  const { t } = useTranslation()
  return (
    <section aria-label={t('room.seats')}>
      <PanelTitle count={seats.length}>{t('room.seats')}</PanelTitle>
      {seats.length === 0 ? <EmptyState title={t('room.noSeats')} /> : (
        <ul className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">
          {seats.map((s) => {
            const last = [...decisions].reverse().find((d) => d.seat === s.code)
            const tone = s.awaitingHuman ? 'warn' : decisionTone(last)
            return (
              <li key={s.code} className="panel relative flex flex-col gap-3 overflow-hidden p-4">
                <span aria-hidden className={cn('absolute inset-y-0 left-0 w-1', STRIPE[tone])} />
                <div className="flex items-center justify-between gap-2">
                  <button type="button" className="font-mono text-lg font-black tracking-wide text-ink hover:text-brand hover:underline" onClick={() => onSeat(s.code)} aria-label={t('room.openSeat', { seat: s.code })}>{s.code}</button>
                  <Badge tone={s.controller === 'human' ? 'info' : s.controller === 'scripted' ? 'warn' : 'neutral'}>{s.controller === 'human' ? `${t('exercises.ctrl.human')}${s.humanName ? ` · ${s.humanName}` : ''}` : s.controller ? t(`exercises.ctrl.${s.controller}`, s.controller) : '—'}</Badge>
                </div>
                {s.awaitingHuman && <p className="flex items-center gap-1 text-sm font-semibold text-warn"><Hourglass className="h-4 w-4" aria-hidden />{t('room.awaitingHuman')}</p>}
                {last ? (
                  <div className="flex flex-1 flex-col gap-2 text-sm">
                    <p className="flex flex-wrap items-center gap-1"><VerifiedBadge d={last} /><OutcomeBadge outcome={last.outcome} /></p>
                    <p className="line-clamp-3 text-base font-semibold">{last.action}</p>
                    <div className="rounded-lg border border-line bg-surface2/60 p-2">
                      <p className="eyebrow mb-1 flex items-center gap-1"><BookMarked className="h-3 w-3" aria-hidden />{t('room.citations')}</p>
                      {last.legalBasis.length === 0 ? <p className="text-xs text-muted">{t('room.noCitation')}</p> : (
                        <ul className="flex flex-col gap-1">
                          {last.legalBasis.slice(0, 2).map((b, k) => {
                            const ok = b.check === 'pass' || b.pass === true
                            return (
                              <li key={`${b.chunk_id}-${k}`} className="text-xs">
                                <span className={cn('inline-flex items-center gap-1 font-semibold', ok ? 'text-ok' : 'text-danger')}>
                                  {ok ? <CheckCircle2 className="h-3.5 w-3.5" aria-hidden /> : <XCircle className="h-3.5 w-3.5" aria-hidden />}
                                  {b.article || b.chunk_id.slice(-8)}
                                </span>
                                {b.quote && <span className="mt-0.5 line-clamp-2 block text-muted italic">« {b.quote} »</span>}
                              </li>
                            )
                          })}
                        </ul>
                      )}
                    </div>
                    <Button size="sm" className="mt-auto self-start" onClick={() => onDecision(last)}>{t('room.showTrace')}</Button>
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

const BOARD_TONE: Record<string, 'warn' | 'danger' | 'info' | 'ok' | 'neutral'> = { OBJECTION: 'warn', GAP_FLAG: 'danger', REQUEST: 'info', DECISION: 'ok', INFO: 'neutral' }

/** Tableau de coordination : fil de messages entre institutions, filtrable par type et par tour. */
export function BoardPanel({ board }: { board: BoardItem[] }) {
  const { t } = useTranslation()
  const [types, setTypes] = useState<Set<string>>(new Set(BOARD_TYPES))
  const [round, setRound] = useState('')
  const rounds = [...new Set(board.map((b) => b.round).filter((r): r is number => r !== null))].sort()
  const shown = board.filter((b) => types.has(b.type) && (!round || String(b.round) === round))
  return (
    <section aria-label={t('room.board')} className="panel p-4">
      <PanelTitle count={board.length}>{t('room.board')}</PanelTitle>
      <div className="mb-3 flex flex-wrap items-end gap-2">
        <fieldset className="flex flex-wrap gap-1.5 text-xs"><legend className="sr-only">{t('room.filterTypes')}</legend>
          {BOARD_TYPES.map((ty) => (
            <label key={ty} className={cn('inline-flex cursor-pointer items-center gap-1 rounded-md border px-1.5 py-0.5 font-semibold', types.has(ty) ? 'border-line bg-surface2 text-ink' : 'border-transparent text-muted line-through')}>
              <input type="checkbox" className="h-3.5 w-3.5 accent-[var(--brand)]" checked={types.has(ty)} onChange={(e) => { const n = new Set(types); if (e.target.checked) n.add(ty); else n.delete(ty); setTypes(n) }} />{ty}
            </label>
          ))}
        </fieldset>
        <label className="text-xs text-muted">{t('room.round')} <Select className="!inline-block !w-auto !min-h-7 !py-0" value={round} onChange={(e) => setRound(e.target.value)}><option value="">{t('common.all')}</option>{rounds.map((r) => <option key={r} value={r}>{r}</option>)}</Select></label>
      </div>
      {shown.length === 0 ? <p className="text-sm text-muted">{t('room.noMessages')}</p> : (
        <ul className="flex max-h-[28rem] flex-col gap-2 overflow-y-auto pr-1">
          {shown.map((b) => (
            <li key={b.msgId} className="rounded-lg border border-line bg-surface2/60 p-2.5 text-sm">
              <p className="flex flex-wrap items-center gap-1.5 text-xs">
                <Badge tone={BOARD_TONE[b.type] ?? 'neutral'}>{b.type}</Badge>
                <span className="font-mono font-bold text-ink">{b.from}</span><ArrowRight className="h-3 w-3 text-muted" aria-label={t('room.to')} /><span className="font-mono font-bold text-ink">{b.to}</span>
                {b.round !== null && <span className="text-muted">· {t('room.round')} {b.round}</span>}
                {b.replyStatus && <Badge tone="neutral">{b.replyStatus}</Badge>}
              </p>
              <p className="mt-1.5">{b.body}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

/** Signaux du moteur de coordination : indices de lacunes, pas encore des constats. */
export function SignalsPanel({ signals, canSeeAudit }: { signals: SignalItem[]; canSeeAudit: boolean }) {
  const { t } = useTranslation()
  return (
    <section aria-label={t('room.signals')} className={cn('panel p-4', signals.length > 0 && 'border-danger/50')}>
      <PanelTitle count={signals.length}>{t('room.signals')}</PanelTitle>
      <p className="-mt-2 mb-3 text-xs text-muted">{t('room.signalsHint')}</p>
      {signals.length === 0 ? <p className="text-sm text-muted">{canSeeAudit ? t('room.noSignals') : t('room.signalsHidden')}</p> : (
        <ul className="flex flex-col gap-1.5">
          {signals.map((s) => (
            <li key={s.seq} className="flex flex-wrap items-center gap-1.5 rounded-lg border border-line bg-surface2/60 p-2 text-sm">
              <Badge tone={SIGNAL_TONE[s.signal] ?? 'neutral'}>{t(`room.signalNames.${s.signal}`, s.signal)}</Badge>
              {s.scripted && <Badge tone="warn">{t('common.noAiShort')}</Badge>}
              {s.actionCode && <code className="text-xs">{s.actionCode}</code>} {s.injectRef && <span className="text-xs text-muted">({s.injectRef})</span>}
              {s.gapId && <Link to={`/gaps/${s.gapId}`} className="ml-auto text-xs">{t('room.openGap')}</Link>}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
