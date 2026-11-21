import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { KeyRound } from 'lucide-react'
import { CopyButton, Mono } from './Misc'

/** A secret that is shown ONCE (token, seat link): explicit warning, selectable text, copy button. */
export function OneTimeSecret({ value, title, children }: { value: string; title: string; children?: ReactNode }) {
  const { t } = useTranslation()
  return (
    <div role="alert" className="rounded-md border-2 border-warn bg-warnsoft p-4">
      <p className="mb-1 flex items-center gap-2 font-bold text-warn"><KeyRound className="h-4 w-4" aria-hidden />{title}</p>
      <p className="mb-2 text-sm text-ink">{t('access.shownOnce')}</p>
      <p className="mb-2"><Mono>{value}</Mono></p>
      <div className="flex flex-wrap items-center gap-2"><CopyButton value={value} />{children}</div>
    </div>
  )
}
