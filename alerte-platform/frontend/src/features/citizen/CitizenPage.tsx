import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { BellOff, BellRing, Code2, Radio, Smartphone, TriangleAlert } from 'lucide-react'
import { useApiQuery } from '@/api/hooks'
import type { PublicAlert, PublicAlerts } from '@/api/loose'
import { ErrorState, LoadingState } from '@/components/ui'
import { useSeatToken } from '@/features/room/seatSession'
import { humanDelay, startSiren, unlockAudio } from './siren'

/**
 * Le téléphone d'un habitant : `/alerte?x=<exercice>#t=<jeton observateur limité à l'exercice>`.
 * Il sonne (853 + 960 Hz, vibration) dès qu'une institution diffuse une alerte avec une base légale vérifiée,
 * et reste muet sinon : à la fin, le silence est expliqué.
 */
export function CitizenPage() {
  const { t } = useTranslation()
  const token = useSeatToken('alerte.citizen_token')
  const [exId] = useState(() => new URLSearchParams(window.location.search).get('x'))
  const q = useApiQuery<PublicAlerts>(['public-alerts', exId, token], token && exId ? `/exercises/${exId}/public-alerts` : null,
    { token: token ?? undefined, refetchInterval: 2500 })

  return (
    <div className="min-h-screen bg-bg text-ink">
      <p className="hazard py-1 text-center text-xs font-black tracking-widest text-black uppercase">{t('citizen.exercise')}</p>
      <main id="main" className="mx-auto flex min-h-[calc(100vh-1.5rem)] max-w-md flex-col p-5">
        {!token || !exId ? <p role="alert" className="mt-10 text-center text-lg">{t('citizen.invalid')}</p>
          : q.isPending ? <LoadingState />
          : q.isError ? <ErrorState error={q.error} />
          : <Phone data={q.data} />}
      </main>
    </div>
  )
}

function Phone({ data }: { data: PublicAlerts }) {
  const { t } = useTranslation()
  const audio = useRef<AudioContext | null>(null)
  const [armed, setArmed] = useState(false)
  const [ack, setAck] = useState<number | null>(null)
  const issued = data.alerts.filter((a) => a.status === 'issued')
  const latest = issued.at(-1) ?? null
  const ringing = armed && latest !== null && ack !== latest.seq

  // Une nouvelle alerte diffusée fait sonner le téléphone (une fois par alerte).
  useEffect(() => {
    if (!ringing) return
    return startSiren(audio.current, 12)
  }, [ringing, latest?.seq])

  if (!armed) {
    return (
      <div className="my-auto text-center">
        <Smartphone className="mx-auto mb-4 h-16 w-16 text-brand" aria-hidden />
        <p className="eyebrow mb-2 text-brand">{t('citizen.introEyebrow')}</p>
        <h1 className="mb-4 text-3xl font-black tracking-tight">{t('citizen.introTitle')}</h1>
        <p className="mb-8 text-lg text-muted">{t('citizen.introLead', { area: data.hazard?.area ?? data.title })}</p>
        <button type="button" onClick={() => { audio.current = unlockAudio(); setArmed(true) }}
          className="inline-flex min-h-14 w-full items-center justify-center gap-2 rounded-xl bg-brand px-6 text-lg font-bold text-brandfg">
          <BellRing className="h-6 w-6" aria-hidden />{t('citizen.introButton')}
        </button>
        <p className="mt-3 text-sm text-muted">{t('citizen.introHint')}</p>
      </div>
    )
  }

  if (ringing && latest) return <AlertScreen alert={latest} data={data} onAck={() => setAck(latest.seq)} />

  if (latest) {
    return (
      <div className="my-auto flex flex-col gap-4">
        {issued.slice().reverse().map((a) => <AlertCard key={a.seq} alert={a} />)}
      </div>
    )
  }

  if (data.verdict === 'silent') {
    const blocked = data.alerts.filter((a) => a.status === 'blocked').length
    return (
      <div className="my-auto text-center">
        <BellOff className="mx-auto mb-4 h-16 w-16 text-danger" aria-hidden />
        <h1 className="mb-4 text-3xl font-black tracking-tight">{t('citizen.silentTitle')}</h1>
        <p className="mb-3 text-lg">{t('citizen.silentLead', { time: data.hazard?.sim_time ?? '—', hazard: data.hazard?.title ?? '' })}</p>
        <p className="font-semibold text-danger">{t('citizen.silentWhy')}</p>
        {blocked > 0 && <p className="mt-4 text-sm text-muted">{t('citizen.blocked', { n: blocked })}</p>}
      </div>
    )
  }

  return (
    <div className="my-auto text-center">
      <span className="relative mx-auto mb-6 grid h-24 w-24 place-items-center rounded-full border-2 border-line">
        <Radio className="h-10 w-10 text-muted" aria-hidden />
        <span className="live-dot is-live absolute top-2 right-2 text-ok" aria-hidden />
      </span>
      <h1 className="mb-2 text-2xl font-black">{t('citizen.waitingTitle')}</h1>
      <p className="text-muted">{data.verdict === 'not_started' ? t('citizen.notStarted') : t('citizen.waitingLead')}</p>
    </div>
  )
}

function When({ alert }: { alert: PublicAlert }) {
  const { t } = useTranslation()
  return (
    <p className="text-sm">
      {alert.sim_time && t('citizen.at', { time: alert.sim_time })}
      {alert.delay_minutes !== null && <> · <strong>{alert.delay_minutes > 0 ? t('citizen.delay', { delay: humanDelay(alert.delay_minutes, t) }) : t('citizen.delayZero')}</strong></>}
    </p>
  )
}

function AlertScreen({ alert, data, onAck }: { alert: PublicAlert; data: PublicAlerts; onAck: () => void }) {
  const { t } = useTranslation()
  return (
    <div role="alertdialog" aria-modal="true" aria-label={t('citizen.alertKind')} className="alert-flash fixed inset-0 z-50 flex flex-col overflow-y-auto p-6 text-white">
      <p className="mb-6 flex items-center gap-2 text-sm font-black tracking-widest uppercase"><TriangleAlert className="h-6 w-6" aria-hidden />{t('citizen.alertKind')}</p>
      <p className="text-xs font-bold tracking-widest uppercase">{t('citizen.exercise')}</p>
      <h1 className="mt-2 text-3xl leading-tight font-black">{alert.action}</h1>
      <p className="mt-4 text-lg">{data.hazard?.area}</p>
      {alert.inject_title && <p className="mt-1 text-lg font-bold">{alert.inject_title}</p>}
      <p className="mt-6 font-semibold">{t('citizen.from', { who: alert.institution })}</p>
      <When alert={alert} />
      <button type="button" onClick={onAck} className="mt-auto min-h-14 rounded-xl bg-white text-lg font-black text-black">{t('citizen.ack')}</button>
    </div>
  )
}

function AlertCard({ alert }: { alert: PublicAlert }) {
  const { t } = useTranslation()
  const [cap, setCap] = useState(false)
  return (
    <article className="rounded-2xl border-2 border-danger bg-dangersoft p-4">
      <p className="mb-1 flex items-center gap-2 text-xs font-black tracking-widest text-danger uppercase"><TriangleAlert className="h-4 w-4" aria-hidden />{t('citizen.alertKind')}</p>
      <h2 className="text-xl font-black">{alert.action}</h2>
      <p className="mt-2 text-sm font-semibold">{t('citizen.from', { who: alert.institution })}</p>
      <When alert={alert} />
      {alert.cap_xml && (
        <div className="mt-3">
          <button type="button" onClick={() => setCap((v) => !v)} className="inline-flex items-center gap-1 text-sm font-semibold text-brand underline">
            <Code2 className="h-4 w-4" aria-hidden />{cap ? t('citizen.hideCap') : t('citizen.showCap')}
          </button>
          {cap && (
            <>
              <p className="mt-2 text-xs text-muted">{t('citizen.capNote')}</p>
              <pre className="mt-2 max-h-72 overflow-auto rounded-lg bg-surface2 p-2 font-mono text-xs leading-snug">{alert.cap_xml}</pre>
            </>
          )}
        </div>
      )}
    </article>
  )
}
