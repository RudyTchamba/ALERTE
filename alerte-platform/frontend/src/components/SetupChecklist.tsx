import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowRight, CheckCircle2, Circle, CircleDot, Lock } from 'lucide-react'
import { cn } from '@/lib/cn'
import { useSetup } from '@/app/useSetup'
import type { SetupStatus } from '@/app/setup'

const TONE: Record<SetupStatus, string> = {
  done: 'border-ok bg-oksoft text-ok', partial: 'border-warn bg-warnsoft text-warn', todo: 'border-brand text-brand', locked: 'border-line text-muted',
}
const ICON = { done: CheckCircle2, partial: CircleDot, todo: Circle, locked: Lock } as const

/** Les 10 étapes de préparation avec leur état RÉEL, ce qui manque et le bouton pour continuer. */
export function SetupChecklist() {
  const { t } = useTranslation()
  const { steps, next, pending, unavailable } = useSetup()
  return (
    <section aria-labelledby="setup-title" className="panel p-5">
      <p className="eyebrow">{t('home.setup')}</p>
      <h2 id="setup-title" className="text-lg font-bold">{t('journey.setup.title')}</h2>
      <p className="mb-4 text-sm text-muted">{t('journey.setup.lead')}</p>
      {unavailable && <p role="status" className="mb-3 rounded-md border border-warn bg-warnsoft px-3 py-2 text-sm">{t('journey.setup.unavailable')}</p>}
      {!unavailable && <ol className="grid gap-2 lg:grid-cols-2">
        {steps.map((s, i) => {
          const Icon = ICON[s.status]
          const isNext = next?.id === s.id
          const detail = t(`journey.setup.steps.${s.id}.${s.detailKey}`, s.detail)
          return (
            <li key={s.id} aria-current={isNext ? 'step' : undefined}
              className={cn('rounded-lg border px-3 py-2.5', isNext ? 'border-brand bg-brandsoft/60' : 'border-line', s.status === 'locked' && 'opacity-70')}>
              <div className="flex items-center gap-3">
                <span className={cn('grid h-7 w-7 shrink-0 place-items-center rounded-full border text-xs font-bold tabular', TONE[s.status])}>
                  <Icon className="h-4 w-4" aria-hidden /><span className="sr-only">{i + 1} — {s.status === 'locked' ? t('journey.setup.status.lockedShort') : t(`journey.setup.status.${s.status}`)}</span>
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold">{i + 1}. {t(`journey.setup.steps.${s.id}.title`)}</p>
                  {!pending && <p className="text-xs text-muted">{s.status === 'locked'
                    ? t('journey.setup.status.locked', { needs: s.needs.map((n) => t(`journey.setup.steps.${n}.title`)).join(', ') })
                    : detail}</p>}
                </div>
                {s.status !== 'locked' ? (
                  <Link to={s.to} className={cn('inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold no-underline', isNext ? 'bg-brand text-brandfg' : 'text-brand hover:underline')}>
                    {s.status === 'done' ? t('journey.setup.open') : t(`journey.setup.steps.${s.id}.action`)}<ArrowRight className="h-3.5 w-3.5" aria-hidden />
                  </Link>
                ) : null}
              </div>
              {isNext && <p className="mt-2 pl-10 text-xs text-muted">{t(`journey.setup.steps.${s.id}.why`)}</p>}
            </li>
          )
        })}
      </ol>}
    </section>
  )
}
