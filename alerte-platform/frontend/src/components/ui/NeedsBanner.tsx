import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { CheckCircle2, CircleAlert } from 'lucide-react'

export interface Need { ok: boolean | undefined; label: ReactNode; to: string }

/** Prérequis d'une page : ce qui doit exister avant d'agir, avec un lien vers l'endroit où le créer. Silencieux si tout est prêt. */
export function NeedsBanner({ needs }: { needs: Need[] }) {
  const { t } = useTranslation()
  const missing = needs.filter((n) => n.ok === false)
  if (missing.length === 0) return null
  return (
    <section aria-label={t('journey.prereq.title')} className="mb-4 rounded-md border border-warn bg-warnsoft p-3 text-sm">
      <p className="mb-1 font-semibold text-warn">{t('journey.prereq.title')}</p>
      <ul className="flex flex-col gap-1">
        {needs.map((n, i) => (
          <li key={i} className="flex items-center gap-2">
            {n.ok === false ? <CircleAlert className="h-4 w-4 shrink-0 text-warn" aria-hidden /> : <CheckCircle2 className="h-4 w-4 shrink-0 text-ok" aria-hidden />}
            <span>{n.label}</span>
            {n.ok === false && <Link to={n.to}>{t('journey.prereq.fix')}</Link>}
          </li>
        ))}
      </ul>
    </section>
  )
}
