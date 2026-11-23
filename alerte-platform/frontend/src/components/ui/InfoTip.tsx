import { useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CircleHelp } from 'lucide-react'
import { Link } from 'react-router-dom'

/** Bouton « ? » qui explique une notion technique (définition du glossaire). Accessible au clavier, jamais bloquant. */
export function InfoTip({ term }: { term: string }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const id = useId()
  return (
    <span className="relative inline-block align-middle">
      <button type="button" aria-expanded={open} aria-controls={id} onClick={() => setOpen((o) => !o)}
        aria-label={t('glossary.about', { term: t(`glossary.terms.${term}.name`) })}
        className="ml-1 inline-flex h-6 w-6 items-center justify-center rounded-full text-muted hover:bg-surface2 hover:text-brand">
        <CircleHelp className="h-4 w-4" aria-hidden />
      </button>
      {open && (
        <span id={id} role="note" className="absolute left-0 z-20 mt-1 block w-72 rounded-md border border-line bg-surface p-3 text-left text-sm font-normal shadow-lg">
          <strong className="block">{t(`glossary.terms.${term}.name`)}</strong>
          <span className="block text-muted">{t(`glossary.terms.${term}.def`)}</span>
          <Link to="/help/glossary" className="mt-1 inline-block text-xs" onClick={() => setOpen(false)}>{t('glossary.seeAll')}</Link>
        </span>
      )}
    </span>
  )
}
