import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, Inbox, Loader2, ServerOff } from 'lucide-react'
import { ApiError } from '@/api/client'
import { errorMessage } from '@/lib/errors'
import { cn } from '@/lib/cn'
import { Button } from './Button'

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn('spin h-5 w-5', className)} aria-hidden />
}

export function LoadingState({ label }: { label?: string }) {
  const { t } = useTranslation()
  return (
    <div role="status" className="flex items-center gap-2 p-6 text-muted">
      <Spinner />
      <span>{label ?? t('common.loading')}</span>
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useTranslation()
  const e = error instanceof ApiError ? error : null
  return (
    <div role="alert" className="flex flex-col gap-2 rounded-xl border border-danger bg-dangersoft p-4 text-danger">
      <p className="flex items-center gap-2 font-semibold"><AlertTriangle className="h-4 w-4" aria-hidden />{t('common.error')}</p>
      <p className="text-sm text-ink">{errorMessage(error, t)}</p>
      {e?.requestId && <p className="text-xs text-muted">{t('common.requestId')}: <code>{e.requestId}</code></p>}
      {onRetry && <div><Button size="sm" onClick={onRetry}>{t('common.retry')}</Button></div>}
    </div>
  )
}

export function EmptyState({ title, hint, action }: { title: ReactNode; hint?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-line bg-surface/40 p-10 text-center text-muted">
      <span aria-hidden className="mb-1 grid h-12 w-12 place-items-center rounded-full bg-surface2 text-muted"><Inbox className="h-6 w-6" /></span>
      <p className="text-base font-semibold text-ink">{title}</p>
      {hint && <p className="max-w-prose text-sm">{hint}</p>}
      {action}
    </div>
  )
}

/** Shown when the backend module serving an endpoint is not delivered yet. Never replaced by invented data. */
export function BackendUnavailable({ what }: { what?: string }) {
  const { t } = useTranslation()
  return (
    <div role="status" className="flex flex-col gap-1 rounded-xl border border-warn bg-warnsoft p-4 text-ink">
      <p className="flex items-center gap-2 font-semibold text-warn"><ServerOff className="h-4 w-4" aria-hidden />{t('common.backendUnavailable')}</p>
      <p className="text-sm">{t('common.backendUnavailableHint', { what: what ?? '' })}</p>
    </div>
  )
}
