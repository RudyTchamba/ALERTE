import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { BellOff, BellRing, Hourglass, Loader2, Megaphone, QrCode, Timer, TriangleAlert, X } from 'lucide-react'
import { api } from '@/api/client'
import { useApiQuery } from '@/api/hooks'
import type { Exercise, PublicAlerts } from '@/api/loose'
import { errorMessage } from '@/lib/errors'
import { cn } from '@/lib/cn'
import { safeGet, safeSet } from '@/lib/storage'
import { QrSvg } from '@/features/present/AudienceQR'
import { humanDelay } from './siren'

type TokenCreated = { token: string }

/** Lien public d'un exercice : jeton observateur limité à l'exercice (12 h), gardé pour l'onglet afin de ne pas en recréer. */
async function publicLink(exId: string, label: string): Promise<string> {
  const key = `alerte.public_link.${exId}`
  const cached = safeGet(key)
  if (cached) return cached
  const r = await api.post<TokenCreated>('/tokens', { role: 'observer', label, exercise_id: exId, expires_in_hours: 12 })
  const url = `${window.location.origin}/alerte?x=${encodeURIComponent(exId)}#t=${encodeURIComponent(r.token)}`
  safeSet(key, url)
  return url
}

/**
 * « Que reçoivent les habitants ? » : QR code vers le téléphone d'un habitant, et chronomètre de l'alerte
 * (début de la crise → première alerte diffusée), ou le silence si personne n'alerte.
 */
export function PublicAlertPanel({ ex, onClose, fixed }: { ex: Exercise; onClose: () => void; fixed?: boolean }) {
  const { t } = useTranslation()
  const [link, setLink] = useState<string | null>(() => safeGet(`alerte.public_link.${ex.id}`))
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const q = useApiQuery<PublicAlerts>(['public-alerts', ex.id], `/exercises/${ex.id}/public-alerts`, { refetchInterval: 2500 })
  const d = q.data
  const first = d?.first_alert ?? null
  const blocked = d?.alerts.filter((a) => a.status === 'blocked').length ?? 0

  const create = async () => {
    setBusy(true); setErr(null)
    try { setLink(await publicLink(ex.id, t('citizen.panelEyebrow'))) } catch (e) { setErr(errorMessage(e, t)) } finally { setBusy(false) }
  }

  const tone = d?.verdict === 'alerted' ? 'border-ok text-ok' : d?.verdict === 'silent' ? 'border-danger text-danger' : 'border-warn text-warn'
  const VerdictIcon = d?.verdict === 'alerted' ? BellRing : d?.verdict === 'silent' ? BellOff : Hourglass

  return (
    <div role="dialog" aria-modal="true" aria-label={t('citizen.panelTitle')}
      className={cn(fixed ? 'fixed z-50' : 'absolute z-20', 'inset-0 grid place-items-center overflow-y-auto bg-[color-mix(in_srgb,var(--bg)_85%,transparent)] p-6 backdrop-blur')}>
      <div className="panel relative w-full max-w-4xl p-8">
        <button type="button" onClick={onClose} aria-label={t('common.close', 'Close')} className="absolute top-4 right-4 grid h-9 w-9 place-items-center rounded-lg border border-line hover:border-muted"><X className="h-5 w-5" aria-hidden /></button>
        <p className="eyebrow mb-1 flex items-center gap-2 text-brand"><Megaphone className="h-4 w-4" aria-hidden />{t('citizen.panelEyebrow')}</p>
        <h2 className="mb-6 text-3xl font-black tracking-tight">{t('citizen.panelTitle')}</h2>

        <div className="grid items-start gap-8 md:grid-cols-[minmax(0,18rem)_1fr]">
          <div>
            {link ? (
              <>
                <QrSvg value={link} title={t('citizen.panelScan')} className="w-full rounded-xl" />
                <p className="mt-3 text-lg font-semibold">{t('citizen.panelScan')}</p>
                <p className="mt-1 text-xs text-muted">{t('citizen.panelScope')}</p>
                {['localhost', '127.0.0.1'].includes(window.location.hostname) && <p className="mt-3 flex gap-2 rounded-lg border border-warn bg-warnsoft p-2 text-xs text-warn"><TriangleAlert className="h-4 w-4 shrink-0" aria-hidden />{t('room.present.audience.localhost')}</p>}
              </>
            ) : (
              <button type="button" disabled={busy} onClick={() => void create()}
                className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-lg bg-brand px-6 text-base font-semibold text-brandfg disabled:opacity-50">
                {busy ? <Loader2 className="spin h-5 w-5" aria-hidden /> : <QrCode className="h-5 w-5" aria-hidden />}
                {busy ? t('citizen.panelWorking') : t('citizen.panelLink')}
              </button>
            )}
            {err && <p role="alert" className="mt-3 rounded-lg border border-danger bg-dangersoft p-3 text-sm text-danger">{err}</p>}
          </div>

          <div aria-live="polite">
            {d && (
              <>
                <p className={cn('mb-6 flex items-center gap-3 rounded-xl border-2 px-4 py-3 text-xl font-black', tone)}>
                  <VerdictIcon className="h-7 w-7 shrink-0" aria-hidden />
                  {t(`citizen.verdict.${d.verdict}`, { who: first?.institution ?? '' })}
                </p>
                <dl className="grid grid-cols-3 gap-3 text-center">
                  <Stat label={t('citizen.hazardAt')} value={d.hazard?.sim_time ?? '—'} sub={d.hazard?.title ?? undefined} />
                  <Stat label={t('citizen.firstAlert')} value={first?.sim_time ?? t('citizen.none')} sub={first?.seat ?? undefined} />
                  <Stat label={t('citizen.delayLabel')} icon={<Timer className="h-4 w-4" aria-hidden />}
                    value={first?.delay_minutes != null ? humanDelay(first.delay_minutes, t) : d.verdict === 'silent' ? '∞' : '…'}
                    tone={first ? (first.delay_minutes ?? 0) > 0 ? 'text-warn' : 'text-ok' : d.verdict === 'silent' ? 'text-danger' : undefined} />
                </dl>
                {blocked > 0 && <p className="mt-4 flex items-center gap-2 text-sm text-warn"><TriangleAlert className="h-4 w-4 shrink-0" aria-hidden />{t('citizen.blocked', { n: blocked })}</p>}
                {d.alerts.length > 0 && (
                  <ul className="mt-4 flex flex-col gap-1.5 text-sm">
                    {d.alerts.map((a) => (
                      <li key={a.seq} className="flex flex-wrap items-baseline gap-2">
                        <span className="font-mono text-muted tabular">{a.sim_time}</span>
                        <span className="font-mono font-bold">{a.seat}</span>
                        <span className="min-w-0 flex-1 truncate">{a.action}</span>
                        <span className={cn('rounded px-1.5 text-xs font-bold', a.status === 'issued' ? 'bg-oksoft text-ok' : 'bg-warnsoft text-warn')}>{a.status === 'issued' ? t('citizen.issued') : t('citizen.blockedTag')}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function Stat({ label, value, sub, tone, icon }: { label: string; value: string; sub?: string; tone?: string; icon?: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-line bg-surface2 px-3 py-4">
      <dt className="eyebrow flex items-center justify-center gap-1">{icon}{label}</dt>
      <dd className={cn('mt-1 font-mono text-2xl font-black tabular', tone)}>{value}</dd>
      {sub && <dd className="mt-1 truncate text-xs text-muted">{sub}</dd>}
    </div>
  )
}
