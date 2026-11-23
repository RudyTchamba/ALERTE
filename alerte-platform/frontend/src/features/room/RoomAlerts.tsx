import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Bot, Hourglass, Play, QrCode, RotateCcw } from 'lucide-react'
import type { StreamEvent } from '@/api/sse'
import type { Exercise } from '@/api/loose'
import { Button } from '@/components/ui'
import type { SeatLive } from './state'

/** Échéance d'une tâche humaine : heure d'ouverture (dernier HUMAN task_opened du siège) + `human_deadline_s`. */
export function humanDeadline(events: StreamEvent[], seat: string, deadlineS: number): { at: number | null; fallback: string } {
  const ev = [...events].reverse().find((e) => e.type === 'HUMAN' && e.payload?.kind === 'task_opened' && (e.payload.seat === seat || e.seat === seat))
  if (!ev) return { at: null, fallback: 'agent_takeover' }
  const opened = Date.parse(ev.real_time)
  return { at: Number.isFinite(opened) ? opened + deadlineS * 1000 : null, fallback: String(ev.payload.fallback ?? 'agent_takeover') }
}

function useNow(active: boolean) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!active) return
    const id = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [active])
  return now
}

const mmss = (ms: number) => {
  const s = Math.max(0, Math.round(ms / 1000))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

/**
 * Ce qu'il faut faire quand l'exercice attend : un siège humain doit décider (QR / rendre à l'IA, compte à rebours),
 * ou l'exercice a été interrompu (reprendre).
 */
export function RoomAlerts({ ex, exState, seats, events, canControl, onShowQr, onGiveToAgent, onResume }: {
  ex: Exercise; exState: string; seats: SeatLive[]; events: StreamEvent[]; canControl: boolean
  onShowQr: (seat: string) => void; onGiveToAgent: (seat: string) => void; onResume: () => void
}) {
  const { t } = useTranslation()
  const waiting = ['running', 'paused'].includes(exState) ? seats.filter((s) => s.awaitingHuman) : []
  const now = useNow(waiting.length > 0)
  const deadlineS = Number(ex.settings.human_deadline_s ?? 900)

  return (
    <>
      {exState === 'interrupted' && (
        <div role="status" className="mb-3 flex flex-wrap items-center gap-3 rounded-xl border-2 border-warn bg-warnsoft px-4 py-3">
          <RotateCcw className="h-6 w-6 shrink-0 text-warn" aria-hidden />
          <div className="min-w-0 flex-1">
            <p className="font-bold text-warn">{t('room.alerts.interruptedTitle')}</p>
            <p className="text-sm">{t('room.alerts.interruptedText')}</p>
          </div>
          {canControl && <Button variant="primary" onClick={onResume} icon={<Play className="h-4 w-4" aria-hidden />}>{t('room.cmd.resume')}</Button>}
        </div>
      )}
      {waiting.map((s) => {
        const d = humanDeadline(events, s.code, deadlineS)
        const left = d.at ? d.at - now : null
        return (
          <div key={s.code} role="status" className="mb-3 flex flex-wrap items-center gap-3 rounded-xl border-2 border-warn bg-warnsoft px-4 py-3">
            <Hourglass className="h-6 w-6 shrink-0 text-warn" aria-hidden />
            <div className="min-w-0 flex-1">
              <p className="font-bold text-warn">{t('room.alerts.waitingTitle', { seat: s.code, name: s.humanName ?? '—' })}</p>
              <p className="text-sm">
                {t('room.alerts.waitingText')}{' '}
                {left !== null && <strong className="tabular">{t(d.fallback === 'skip' ? 'room.alerts.deadlineSkip' : 'room.alerts.deadlineAgent', { time: mmss(left) })}</strong>}
              </p>
            </div>
            {canControl && (
              <div className="flex flex-wrap gap-2">
                <Button variant="primary" onClick={() => onShowQr(s.code)} icon={<QrCode className="h-4 w-4" aria-hidden />}>{t('room.alerts.showQr')}</Button>
                <Button onClick={() => onGiveToAgent(s.code)} icon={<Bot className="h-4 w-4" aria-hidden />}>{t('room.giveToAgent')}</Button>
              </div>
            )}
          </div>
        )
      })}
    </>
  )
}
