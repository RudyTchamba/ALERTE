import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowRight } from 'lucide-react'
import { cn } from '@/lib/cn'
import { PHASES, STEPS, stepFor, stepsOf } from '@/app/journey'

/** Bandeau « où suis-je ? » : phase (Préparer / Conduire / Analyser), numéro d'étape, ce qu'on y fait et l'étape suivante. */
export function JourneyBar() {
  const { t } = useTranslation()
  const { pathname } = useLocation()
  const cur = stepFor(pathname)
  if (!cur) return null
  const { step, index } = cur
  const inPhase = stepsOf(step.phase)
  const next = STEPS[index + 1]
  return (
    <nav aria-label={t('journey.label')} className="mb-4 rounded-md border border-line bg-surface p-3 text-sm">
      <ol className="mb-2 flex flex-wrap gap-2">
        {PHASES.map((p, i) => (
          <li key={p} aria-current={p === step.phase ? 'step' : undefined}
            className={cn('rounded-full border px-3 py-0.5 text-xs font-semibold', p === step.phase ? 'border-brand bg-brandsoft text-brand' : 'border-line text-muted')}>
            {t(`journey.phases.${p}.short`, { n: 'ABC'[i] })}
          </li>
        ))}
      </ol>
      <p>
        <strong>{t('journey.stepOf', { n: inPhase.findIndex((s) => s.id === step.id) + 1, total: inPhase.length })}</strong>
        {' — '}{t(`journey.steps.${step.id}.title`)}. <span className="text-muted">{t(`journey.steps.${step.id}.what`)}</span>
      </p>
      {next && (
        <p className="mt-1">
          {t('journey.next')} <Link to={next.to} className="inline-flex items-center gap-1 font-semibold">{t(`journey.steps.${next.id}.title`)}<ArrowRight className="h-4 w-4" aria-hidden /></Link>
          <span className="text-muted"> — {t(`journey.steps.${step.id}.next`)}</span>
        </p>
      )}
    </nav>
  )
}
