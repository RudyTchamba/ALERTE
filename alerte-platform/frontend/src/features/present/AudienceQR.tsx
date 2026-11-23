import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import qrcode from 'qrcode-generator'
import { Loader2, QrCode, Smartphone, TriangleAlert, X } from 'lucide-react'
import { api } from '@/api/client'
import { keys } from '@/api/keys'
import type { Exercise, InviteResult } from '@/api/loose'
import { errorMessage } from '@/lib/errors'
import { cn } from '@/lib/cn'

/** QR code en SVG (modules noirs sur fond blanc, marge de 4 modules : lisible par tous les téléphones). */
export function QrSvg({ value, title, className }: { value: string; title: string; className?: string }) {
  const { d, size } = useMemo(() => {
    const qr = qrcode(0, 'M')
    qr.addData(value)
    qr.make()
    const n = qr.getModuleCount()
    let path = ''
    for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) if (qr.isDark(r, c)) path += `M${c + 4} ${r + 4}h1v1h-1z`
    return { d: path, size: n + 8 }
  }, [value])
  return (
    <svg viewBox={`0 0 ${size} ${size}`} role="img" aria-label={title} className={className} shapeRendering="crispEdges">
      <rect width={size} height={size} fill="#ffffff" />
      <path d={d} fill="#000000" />
    </svg>
  )
}

type Step = { kind: 'pick' } | { kind: 'working' } | { kind: 'ready'; url: string; seat: string; name: string } | { kind: 'error'; msg: string }

const LIVE = ['running', 'paused']

/**
 * « Faire jouer le public » : confie un siège à un humain, puis affiche son lien personnel en QR code.
 * Exercice en cours : bascule `seat_switch` (appliquée entre deux activations). Exercice non lancé : configuration des sièges.
 */
export function AudienceQR({ ex, onClose, initialSeat, fixed }: { ex: Exercise; onClose: () => void; initialSeat?: string; fixed?: boolean }) {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const seats = ex.seats ?? []
  const [seat, setSeat] = useState(initialSeat ?? seats[0]?.code ?? '')
  const [name, setName] = useState(() => seats.find((s) => s.code === initialSeat)?.human_name ?? t('room.present.audience.defaultName'))
  const [step, setStep] = useState<Step>({ kind: 'pick' })
  const terminal = ['completed', 'stopped', 'archived', 'failed'].includes(ex.state)
  const local = typeof window !== 'undefined' && ['localhost', '127.0.0.1'].includes(window.location.hostname)

  const go = async () => {
    setStep({ kind: 'working' })
    try {
      const cur = seats.find((s) => s.code === seat)
      const who = name.trim() || t('room.present.audience.defaultName')
      if (cur && !(cur.controller === 'human' && cur.human_name === who)) {
        if (LIVE.includes(ex.state)) {
          await api.post(`/exercises/${ex.id}/commands`, { kind: 'seat_switch', args: { seat, controller: 'human', human_name: who, reason: 'audience' } })
          // La bascule s'applique entre deux activations : on attend qu'elle soit visible.
          for (let i = 0; i < 60; i++) {
            const e = await api.get<Exercise>(`/exercises/${ex.id}`)
            if (e.seats?.find((s) => s.code === seat)?.controller === 'human') break
            await new Promise((r) => setTimeout(r, 1000))
          }
        } else {
          const wasReady = ex.state === 'ready'
          await api.put(`/exercises/${ex.id}/seats`, { seats: seats.map((s) => (s.code === seat
            ? { code: s.code, institution_id: s.institution_id, agent_id: s.agent_id, controller: 'human', human_name: who }
            : { code: s.code, institution_id: s.institution_id, agent_id: s.agent_id, controller: s.controller, human_name: s.human_name })) })
          if (wasReady) await api.post(`/exercises/${ex.id}/ready`)
        }
        void qc.invalidateQueries({ queryKey: keys.exercise(ex.id) })
      }
      const inv = await api.post<InviteResult>(`/exercises/${ex.id}/seats/${encodeURIComponent(seat)}/invite`, { expires_in_hours: 12 })
      setStep({ kind: 'ready', url: `${window.location.origin}${inv.link}`, seat: inv.seat, name: inv.human_name })
    } catch (e) {
      setStep({ kind: 'error', msg: errorMessage(e, t) })
    }
  }

  return (
    <div role="dialog" aria-modal="true" aria-label={t('room.present.audience.title')}
      className={cn(fixed ? 'fixed z-50' : 'absolute z-20', 'inset-0 grid place-items-center bg-[color-mix(in_srgb,var(--bg)_85%,transparent)] p-6 backdrop-blur')}>
      <div className="panel relative w-full max-w-3xl p-8">
        <button type="button" onClick={onClose} aria-label={t('common.close', 'Close')} className="absolute top-4 right-4 grid h-9 w-9 place-items-center rounded-lg border border-line hover:border-muted"><X className="h-5 w-5" aria-hidden /></button>
        <p className="eyebrow mb-1 flex items-center gap-2 text-brand"><Smartphone className="h-4 w-4" aria-hidden />{t('room.present.audience.eyebrow')}</p>
        <h2 className="mb-6 text-3xl font-black tracking-tight">{t('room.present.audience.title')}</h2>

        {terminal ? <p className="text-lg text-muted">{t('room.present.audience.terminal')}</p> : step.kind === 'ready' ? (
          <div className="grid items-center gap-8 md:grid-cols-[minmax(0,22rem)_1fr]">
            <QrSvg value={step.url} title={t('room.present.audience.qrFor', { seat: step.seat })} className="w-full rounded-xl" />
            <div>
              <p className="text-4xl font-black text-brand">{step.seat}</p>
              <p className="mt-2 text-xl">{t('room.present.audience.scan', { seat: step.seat })}</p>
              <p className="mt-4 text-sm text-muted">{t('room.present.audience.heldBy', { name: step.name })}</p>
              <p className="mt-4 rounded-lg bg-surface2 p-2 font-mono text-xs break-all text-muted">{step.url.replace(/#t=.*/, '#t=…')}</p>
              {local && <p className="mt-3 flex gap-2 rounded-lg border border-warn bg-warnsoft p-2 text-xs text-warn"><TriangleAlert className="h-4 w-4 shrink-0" aria-hidden />{t('room.present.audience.localhost')}</p>}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-5">
            <p className="text-muted">{t('room.present.audience.lead')}</p>
            <fieldset>
              <legend className="mb-2 text-sm font-semibold">{t('room.present.audience.pickSeat')}</legend>
              <div className="flex flex-wrap gap-2">
                {seats.map((s) => (
                  <label key={s.code} className={cn('cursor-pointer rounded-lg border-2 px-4 py-2 font-mono text-lg font-black', seat === s.code ? 'border-brand bg-brandsoft text-brand' : 'border-line text-ink hover:border-muted')}>
                    <input type="radio" name="aud-seat" className="sr-only" checked={seat === s.code} onChange={() => setSeat(s.code)} />{s.code}
                  </label>
                ))}
              </div>
            </fieldset>
            <label className="flex max-w-sm flex-col gap-1 text-sm font-semibold">{t('room.present.audience.name')}
              <input value={name} onChange={(e) => setName(e.target.value)} maxLength={60} className="rounded-lg border border-line bg-surface2 px-3 py-2 text-base font-normal text-ink" />
            </label>
            {step.kind === 'error' && <p role="alert" className="rounded-lg border border-danger bg-dangersoft p-3 text-sm text-danger">{step.msg}</p>}
            <p className="text-xs text-muted">{LIVE.includes(ex.state) ? t('room.present.audience.liveHint') : t('room.present.audience.setupHint')}</p>
            <button type="button" disabled={!seat || step.kind === 'working'} onClick={() => void go()}
              className="inline-flex min-h-12 items-center justify-center gap-2 self-start rounded-lg bg-brand px-6 text-base font-semibold text-brandfg disabled:opacity-50">
              {step.kind === 'working' ? <Loader2 className="spin h-5 w-5" aria-hidden /> : <QrCode className="h-5 w-5" aria-hidden />}
              {step.kind === 'working' ? t('room.present.audience.working') : t('room.present.audience.generate')}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
