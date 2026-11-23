import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ChevronLeft, ChevronRight, Keyboard, Maximize, Megaphone, Minimize, Pause, Play, QrCode, X } from 'lucide-react'
import type { StreamEvent } from '@/api/sse'
import { keys } from '@/api/keys'
import { useApiQuery } from '@/api/hooks'
import type { Exercise } from '@/api/loose'
import { LogoMark, QueryState } from '@/components/ui'
import { cn } from '@/lib/cn'
import { DEMO_SEATS, useDemoEvents } from '@/features/home/FlowDemo'
import { FlowDiagram } from '@/features/room/flow/FlowDiagram'
import { seatVisuals, toSteps, type FlowStep } from '@/features/room/flow/narrate'
import { StepIcon, TONE_BORDER, TONE_TEXT, useCallout, useSay } from '@/features/room/flow/present'
import { useExerciseStream } from '@/features/room/useExerciseStream'
import { AudienceQR } from './AudienceQR'
import { PublicAlertPanel } from '@/features/citizen/PublicAlertPanel'

/** Mode présentation : `/present` (démonstration fictive) ou `/present/:exerciseId` (exercice réel, en direct ou en rejeu). */
export function PresentPage() {
  const { exerciseId } = useParams()
  return exerciseId ? <PresentExercise id={exerciseId} /> : <PresentDemo />
}

function PresentDemo() {
  const { t } = useTranslation()
  const events = useDemoEvents()
  return <Stage events={events} seats={DEMO_SEATS} title={t('home.demo.title')} badge={t('home.demo.badge')} exitTo="/" />
}

function PresentExercise({ id }: { id: string }) {
  const q = useApiQuery<Exercise>(keys.exercise(id), `/exercises/${id}`, { refetchInterval: 5000 })
  return <div className="min-h-screen bg-bg"><QueryState q={q} what="(/exercises)">{(ex) => <PresentStream ex={ex} />}</QueryState></div>
}

function PresentStream({ ex }: { ex: Exercise }) {
  const { t } = useTranslation()
  const { state } = useExerciseStream(ex.id)
  const seats = useMemo(() => {
    const codes = new Set([...(ex.seats ?? []).map((s) => s.code), ...Object.keys(state.seats)])
    return [...codes].sort()
  }, [ex.seats, state.seats])
  const badge = ex.ai_mode === 'ai' ? undefined : ex.ai_mode === 'cassette' ? t('common.replayShort', 'REPLAY') : t('common.noAiShort')
  return <Stage events={state.events} seats={seats} title={ex.title} code={ex.code} badge={badge} exitTo={`/room/${ex.id}`} audience={ex} />
}

function useFullscreen(): [boolean, () => void] {
  const [on, setOn] = useState(() => typeof document !== 'undefined' && !!document.fullscreenElement)
  useEffect(() => {
    const h = () => setOn(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', h)
    return () => document.removeEventListener('fullscreenchange', h)
  }, [])
  const toggle = useCallback(() => {
    if (document.fullscreenElement) void document.exitFullscreen?.()
    else void document.documentElement.requestFullscreen?.().catch(() => { /* refusé par le navigateur : on reste en fenêtre */ })
  }, [])
  return [on, toggle]
}

function summary(steps: FlowStep[]) {
  const decisions = steps.filter((s) => s.kind === 'decision')
  return {
    injects: steps.filter((s) => s.kind === 'inject').length,
    verified: decisions.filter((s) => s.tone === 'ok').length,
    refused: decisions.filter((s) => s.tone !== 'ok').length,
    messages: steps.filter((s) => s.kind === 'message').length,
    gaps: steps.filter((s) => s.kind === 'gap').length,
  }
}

const AUTO_MS = 3400

function Stage({ events, seats, title, code, badge, exitTo, audience }: { events: StreamEvent[]; seats: string[]; title: string; code?: string; badge?: string; exitTo: string; audience?: Exercise }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const say = useSay()
  const callout = useCallout()
  const steps = useMemo(() => toSteps(events), [events])
  const n = steps.length
  // -1 : écran-titre ; 0..n-1 : étapes ; n : bilan.
  const [pos, setPos] = useState(-1)
  const [playing, setPlaying] = useState(false)
  const [help, setHelp] = useState(false)
  const [qr, setQr] = useState(false)
  const [warn, setWarn] = useState(false)
  const [fullscreen, toggleFullscreen] = useFullscreen()
  const cur = Math.min(pos, n)
  const step = cur >= 0 && cur < n ? steps[cur] : null
  const visuals = useMemo(() => seatVisuals(steps, Math.min(cur, n - 1)), [steps, cur, n])

  const next = useCallback(() => setPos((p) => Math.min(p + 1, n)), [n])
  const prev = useCallback(() => setPos((p) => Math.max(p - 1, -1)), [])

  useEffect(() => {
    if (!playing) return
    const id = window.setTimeout(() => {
      if (cur >= n) setPlaying(false)
      else setPos(cur + 1)
    }, cur < 0 ? 1200 : AUTO_MS)
    return () => window.clearTimeout(id)
  }, [playing, cur, n])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.altKey || e.ctrlKey || e.metaKey) return
      // Pas de raccourci pendant la saisie (prénom du joueur) ; Échap ferme le panneau QR.
      const tag = (e.target as HTMLElement | null)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      if (qr) { if (e.key === 'Escape' || e.key === 'q' || e.key === 'Q') setQr(false); return }
      if (warn) { if (e.key === 'Escape' || e.key === 'a' || e.key === 'A') setWarn(false); return }
      switch (e.key) {
        case ' ': case 'ArrowRight': case 'PageDown': case 'Enter': e.preventDefault(); setPlaying(false); next(); break
        case 'ArrowLeft': case 'PageUp': case 'Backspace': e.preventDefault(); setPlaying(false); prev(); break
        case 'Home': e.preventDefault(); setPlaying(false); setPos(-1); break
        case 'End': e.preventDefault(); setPlaying(false); setPos(n); break
        case 'p': case 'P': setPlaying((v) => !v); break
        case 'f': case 'F': toggleFullscreen(); break
        case 'h': case 'H': case '?': setHelp((v) => !v); break
        case 'q': case 'Q': if (audience) { setPlaying(false); setQr(true) } break
        case 'a': case 'A': if (audience) { setPlaying(false); setWarn(true) } break
        case 'Escape': if (!document.fullscreenElement) navigate(exitTo); break
        default: break
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [next, prev, n, toggleFullscreen, navigate, exitTo, qr, warn, audience])

  const sum = summary(steps)
  const pct = n ? Math.round((Math.max(cur, 0) / n) * 100) : 0

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-bg text-ink" data-testid="present-stage">
      <div aria-hidden className="h-1 w-full bg-surface2"><div className="h-full bg-brand transition-all duration-500" style={{ width: `${pct}%` }} /></div>
      <header className="flex items-center gap-4 px-8 py-4">
        <span className="grid h-10 w-10 place-items-center rounded-xl border border-line bg-surface2"><LogoMark className="h-6 w-6" /></span>
        <div className="min-w-0">
          <p className="eyebrow">{t('common.appName')}{code ? ` · ${code}` : ''}</p>
          <h1 className="truncate text-xl font-extrabold tracking-tight">{title}</h1>
        </div>
        {badge && <span className="rounded-md border border-warn px-2 py-0.5 text-xs font-bold text-warn">{badge}</span>}
        <div className="ml-auto flex items-center gap-6 text-right">
          {step?.simTime && <p><span className="eyebrow block">{t('room.clock')}</span><span className="font-mono text-2xl font-bold text-brand tabular">{step.simTime}</span></p>}
          {cur >= 0 && cur < n && <p><span className="eyebrow block">{t('room.present.step')}</span><span className="font-mono text-2xl font-bold tabular">{cur + 1}<span className="text-muted">/{n}</span></span></p>}
        </div>
      </header>

      {/* Scène : un clic n'importe où avance d'une étape (bouton transparent couvrant la scène). */}
      <main className="relative min-h-0 flex-1 px-6">
        <FlowDiagram seats={seats} step={step} visuals={visuals} title={title} callout={callout(step)} className="pointer-events-none mx-auto h-full w-full max-w-[1500px]" />
        <button type="button" aria-label={t('room.flow.next')} className="absolute inset-0 cursor-pointer focus-visible:outline-none" onClick={() => { setPlaying(false); next() }} />

        {cur < 0 && (
          <div className="pointer-events-none absolute inset-0 grid place-items-center bg-[color-mix(in_srgb,var(--bg)_70%,transparent)] backdrop-blur-sm">
            <div className="max-w-3xl px-6 text-center">
              <p className="eyebrow mb-4 flex items-center justify-center gap-2 text-brand"><span className="live-dot is-live text-brand" aria-hidden />{t('room.present.titleEyebrow')}</p>
              <p className="text-5xl leading-tight font-black tracking-tight">{title}</p>
              <p className="mt-6 text-xl text-muted">{t('room.present.titleLead', { seats: seats.join(' · ') })}</p>
              <p className="mt-10 inline-flex items-center gap-2 rounded-full border border-line bg-surface px-5 py-2 text-lg"><Keyboard className="h-5 w-5 text-brand" aria-hidden />{t('room.present.pressSpace')}</p>
            </div>
          </div>
        )}

        {cur >= n && n > 0 && (
          <div className="pointer-events-none absolute inset-0 grid place-items-center bg-[color-mix(in_srgb,var(--bg)_80%,transparent)] backdrop-blur-sm">
            <div className="w-full max-w-5xl px-6 text-center">
              <p className="eyebrow mb-3 text-brand">{t('room.present.endEyebrow')}</p>
              <p className="mb-10 text-5xl font-black tracking-tight">{t('room.present.endTitle')}</p>
              <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <EndStat label={t('room.summary.injects')} value={sum.injects} />
                <EndStat label={t('room.present.verified')} value={sum.verified} tone="text-ok" />
                <EndStat label={t('room.present.refused')} value={sum.refused} tone={sum.refused ? 'text-danger' : undefined} />
                <EndStat label={t('room.summary.signals')} value={sum.gaps} tone={sum.gaps ? 'text-danger' : undefined} />
              </dl>
              <p className="mt-10 text-xl text-muted">{sum.gaps ? t('room.present.endLeadGaps', { n: sum.gaps }) : t('room.present.endLeadClean')}</p>
            </div>
          </div>
        )}
      </main>

      {/* Sous-titres : ce qui se passe, en grand. */}
      <footer className="px-8 pt-3 pb-5">
        <div className={cn('flex min-h-24 items-center gap-5 rounded-2xl border border-l-8 border-line bg-surface px-6 py-4', step ? TONE_BORDER[step.tone] : 'border-l-brand')} aria-live="polite">
          {step ? (
            <>
              <StepIcon st={step} className={cn('h-9 w-9 shrink-0', TONE_TEXT[step.tone])} />
              <p className="text-2xl leading-snug font-semibold lg:text-3xl">{say(step)}</p>
            </>
          ) : <p className="text-2xl text-muted">{cur < 0 ? t('room.present.subtitleStart') : t('room.present.subtitleEnd')}</p>}
        </div>
        <div className="mt-3 flex items-center gap-2 text-sm text-muted">
          <p className="hidden md:block">{t('room.present.keys')}</p>
          <div className="ml-auto flex items-center gap-1" role="group" aria-label={t('room.flow.controls')}>
            <CtlButton label={t('room.flow.prev')} onClick={() => { setPlaying(false); prev() }}><ChevronLeft className="h-5 w-5" /></CtlButton>
            <CtlButton label={playing ? t('room.flow.pause') : t('room.present.auto')} onClick={() => setPlaying((v) => !v)} active={playing}>{playing ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}</CtlButton>
            <CtlButton label={t('room.flow.next')} onClick={() => { setPlaying(false); next() }}><ChevronRight className="h-5 w-5" /></CtlButton>
            {audience && <CtlButton label={t('room.present.audience.title')} onClick={() => { setPlaying(false); setQr(true) }} active={qr}><QrCode className="h-5 w-5" /></CtlButton>}
            {audience && <CtlButton label={t('citizen.panelTitle')} onClick={() => { setPlaying(false); setWarn(true) }} active={warn}><Megaphone className="h-5 w-5" /></CtlButton>}
            <CtlButton label={t('room.present.fullscreen')} onClick={toggleFullscreen}>{fullscreen ? <Minimize className="h-5 w-5" /> : <Maximize className="h-5 w-5" />}</CtlButton>
            <CtlButton label={t('room.present.help')} onClick={() => setHelp((v) => !v)}><Keyboard className="h-5 w-5" /></CtlButton>
            <CtlButton label={t('room.present.exit')} onClick={() => navigate(exitTo)}><X className="h-5 w-5" /></CtlButton>
          </div>
        </div>
      </footer>

      {qr && audience && <AudienceQR ex={audience} onClose={() => setQr(false)} />}
      {warn && audience && <PublicAlertPanel ex={audience} onClose={() => setWarn(false)} />}
      {help && (
        <div role="dialog" aria-label={t('room.present.help')} className="absolute right-8 bottom-32 w-80 rounded-xl border border-line bg-surface p-4 text-sm shadow-2xl">
          <p className="mb-2 font-bold">{t('room.present.help')}</p>
          <dl className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1.5">
            {(['next', 'prev', 'auto', 'home', 'fs', 'qr', 'alert', 'exit'] as const).filter((k) => (k !== 'qr' && k !== 'alert') || audience).map((k) => (
              <div key={k} className="contents"><dt><kbd className="rounded border border-line bg-surface2 px-1.5 font-mono text-xs">{t(`room.present.kbd.${k}`)}</kbd></dt><dd className="text-muted">{t(`room.present.kbdDesc.${k}`)}</dd></div>
            ))}
          </dl>
        </div>
      )}
    </div>
  )
}

function EndStat({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <div className="panel px-5 py-6">
      <dt className="eyebrow">{label}</dt>
      <dd className={cn('mt-2 text-6xl font-black tabular', tone)}>{value}</dd>
    </div>
  )
}

function CtlButton({ label, onClick, children, active }: { label: string; onClick: () => void; children: ReactNode; active?: boolean }) {
  return (
    <button type="button" aria-label={label} title={label} onClick={onClick}
      className={cn('grid h-10 w-10 place-items-center rounded-lg border transition-colors', active ? 'border-brand bg-brand text-brandfg' : 'border-line bg-surface text-ink hover:border-muted')}>
      {children}
    </button>
  )
}
