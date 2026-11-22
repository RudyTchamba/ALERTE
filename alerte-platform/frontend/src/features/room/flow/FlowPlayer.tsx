import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronLeft, ChevronRight, Pause, Play, RotateCcw, SkipForward } from 'lucide-react'
import type { StreamEvent } from '@/api/sse'
import { Button, Select } from '@/components/ui'
import { cn } from '@/lib/cn'
import { FlowDiagram } from './FlowDiagram'
import { seatVisuals, toSteps } from './narrate'
import { StepIcon, TONE_BORDER, TONE_TEXT, useCallout, useSay } from './present'

const SPEEDS = [0.5, 1, 2, 4]

export function FlowPlayer({ events, seats, live, title, autoplay = false, loop = false, heading, badge }: {
  events: StreamEvent[]; seats: string[]; live: boolean; title: string
  /** Démarre la lecture dès l'affichage ; `loop` recommence à la fin (démonstration de l'accueil). */
  autoplay?: boolean; loop?: boolean; heading?: string; badge?: string
}) {
  const { t } = useTranslation()
  const say = useSay()
  const callout = useCallout()
  const steps = useMemo(() => toSteps(events), [events])
  // `cursor === null` : suivre la dernière étape (direct). Sinon : rejeu à la position choisie.
  const [cursor, setCursor] = useState<number | null>(autoplay ? 0 : null)
  const [playing, setPlaying] = useState(autoplay)
  const [speed, setSpeed] = useState(1)
  const last = steps.length - 1
  const idx = cursor === null ? last : Math.min(cursor, last)
  const step = idx >= 0 ? steps[idx] : null
  const visuals = useMemo(() => seatVisuals(steps, idx), [steps, idx])
  const listRef = useRef<HTMLOListElement>(null)

  useEffect(() => {
    if (!playing || cursor === null) return
    const id = window.setTimeout(() => {
      if (cursor < last) setCursor(cursor + 1)
      else if (loop) setCursor(0)
      else setPlaying(false)
    }, (cursor >= last && loop ? 4000 : 2200) / speed)
    return () => window.clearTimeout(id)
  }, [playing, cursor, last, speed, loop])

  // Garde l'étape courante visible dans le fil, sans faire défiler la page.
  useEffect(() => {
    const ol = listRef.current
    const li = ol?.querySelector<HTMLElement>('[aria-current="step"]')
    if (ol && li) ol.scrollTop = li.offsetTop - ol.clientHeight / 2 + li.clientHeight / 2
  }, [idx])

  const go = (i: number) => { setPlaying(false); setCursor(Math.max(0, Math.min(last, i))) }
  const replay = () => { setCursor(0); setPlaying(true) }
  const togglePlay = () => {
    if (playing) { setPlaying(false); return }
    if (cursor === null || cursor >= last) setCursor(0)
    setPlaying(true)
  }
  const atEnd = cursor === null

  return (
    <section aria-label={heading ?? t('room.flow.title')} className="panel mb-4 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-2.5">
        <h2 className="flex items-center gap-2 text-sm font-bold tracking-wide uppercase">
          <span className={cn('live-dot', (live && atEnd) || playing ? 'is-live text-ok' : 'text-brand')} aria-hidden />{heading ?? t('room.flow.title')}
          {badge && <span className="rounded-md border border-warn px-1.5 py-0.5 text-[0.65rem] font-semibold tracking-normal text-warn normal-case">{badge}</span>}
        </h2>
        <p className="text-xs text-muted">{live && atEnd ? t('room.flow.liveHint') : t('room.flow.replayHint')}</p>
      </div>

      <div className="grid gap-0 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <div className="relative border-b border-line p-3 xl:border-r xl:border-b-0">
          <FlowDiagram seats={seats} step={step} visuals={visuals} title={title} callout={callout(step)} />
          {!live && atEnd && !playing && steps.length > 0 && (
            <div className="absolute inset-0 grid place-items-center bg-[color-mix(in_srgb,var(--bg)_55%,transparent)] backdrop-blur-[2px]">
              <div className="flex flex-col items-center gap-3 text-center">
                <Button variant="primary" className="!min-h-12 !px-6 !text-base" onClick={replay} icon={<Play className="h-5 w-5" aria-hidden />}>{t('room.flow.replay')}</Button>
                <p className="max-w-sm text-sm text-muted">{t('room.flow.replayLead', { n: steps.length })}</p>
              </div>
            </div>
          )}
          <ul className="mt-2 flex flex-wrap justify-center gap-x-4 gap-y-1 text-xs text-muted" aria-label={t('room.flow.legend')}>
            <li className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-info" aria-hidden />{t('room.flow.seat.thinking')}</li>
            <li className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-ok" aria-hidden />{t('room.flow.seat.verified')}</li>
            <li className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-danger" aria-hidden />{t('room.flow.seat.refused')}</li>
            <li className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-warn" aria-hidden />{t('room.flow.seat.waiting')}</li>
          </ul>
        </div>

        <div className="flex min-h-0 flex-col">
          {/* Ce qui se passe maintenant */}
          <div className={cn('border-b border-l-4 border-line p-4', step ? TONE_BORDER[step.tone] : 'border-l-line')} aria-live="polite">
            <p className="eyebrow mb-1">{t('room.flow.now')}{step?.simTime ? ` · ${step.simTime}` : ''}{steps.length ? ` · ${idx + 1}/${steps.length}` : ''}</p>
            {step ? (
              <p className="flex gap-3 text-base leading-snug font-semibold">
                <StepIcon st={step} className={cn('mt-0.5 h-5 w-5 shrink-0', TONE_TEXT[step.tone])} />
                <span>{say(step)}</span>
              </p>
            ) : <p className="text-sm text-muted">{t('room.flow.empty')}</p>}
          </div>

          {/* Commandes de rejeu */}
          <div className="flex flex-wrap items-center gap-1.5 border-b border-line px-3 py-2" role="group" aria-label={t('room.flow.controls')}>
            <Button size="sm" variant="ghost" aria-label={t('room.flow.restart')} title={t('room.flow.restart')} disabled={!steps.length} onClick={replay}><RotateCcw className="h-4 w-4" aria-hidden /></Button>
            <Button size="sm" variant="ghost" aria-label={t('room.flow.prev')} title={t('room.flow.prev')} disabled={idx <= 0} onClick={() => go(idx - 1)}><ChevronLeft className="h-4 w-4" aria-hidden /></Button>
            <Button size="sm" variant="primary" aria-label={playing ? t('room.flow.pause') : t('room.flow.play')} disabled={!steps.length} onClick={togglePlay}>
              {playing ? <Pause className="h-4 w-4" aria-hidden /> : <Play className="h-4 w-4" aria-hidden />}
            </Button>
            <Button size="sm" variant="ghost" aria-label={t('room.flow.next')} title={t('room.flow.next')} disabled={idx >= last} onClick={() => go(idx + 1)}><ChevronRight className="h-4 w-4" aria-hidden /></Button>
            <Button size="sm" variant="ghost" aria-label={t('room.flow.toEnd')} title={t('room.flow.toEnd')} disabled={atEnd} onClick={() => { setPlaying(false); setCursor(null) }}><SkipForward className="h-4 w-4" aria-hidden /></Button>
            <label className="sr-only" htmlFor="flow-speed">{t('room.flow.speed')}</label>
            <Select id="flow-speed" className="!ml-auto !w-auto !min-h-8 !py-0.5 text-xs" value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
              {SPEEDS.map((v) => <option key={v} value={v}>×{v}</option>)}
            </Select>
            <label className="sr-only" htmlFor="flow-scrub">{t('room.flow.position')}</label>
            <input id="flow-scrub" type="range" min={0} max={Math.max(0, last)} value={Math.max(0, idx)} disabled={steps.length < 2}
              onChange={(e) => go(Number(e.target.value))} className="mt-1 w-full accent-[var(--brand)]" />
          </div>

          {/* Le fil de l'histoire */}
          <ol ref={listRef} className="relative h-72 overflow-y-auto p-2 xl:h-[19rem]" aria-label={t('room.flow.story')}>
            {steps.map((st, i) => {
              return (
                <li key={st.seq} aria-current={i === idx ? 'step' : undefined}>
                  <button type="button" onClick={() => go(i)}
                    className={cn('flex w-full gap-2 rounded-md px-2 py-1.5 text-left text-xs transition-colors',
                      i === idx ? 'bg-brandsoft text-ink' : i > idx ? 'text-muted opacity-60 hover:opacity-100' : 'text-ink hover:bg-surface2')}>
                    <StepIcon st={st} className={cn('mt-0.5 h-3.5 w-3.5 shrink-0', TONE_TEXT[st.tone])} />
                    <span className="line-clamp-2">{say(st)}</span>
                  </button>
                </li>
              )
            })}
          </ol>
        </div>
      </div>
    </section>
  )
}
