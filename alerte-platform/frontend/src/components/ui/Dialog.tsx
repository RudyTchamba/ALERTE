import { useEffect, useRef, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { X } from 'lucide-react'
import { Button } from './Button'

const FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'

/** Modal dialog: focus trap, Escape to close, focus restored to the opener, aria-modal. */
export function Dialog({ open, onClose, title, children, footer, wide }: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  footer?: ReactNode
  wide?: boolean
}) {
  const { t } = useTranslation()
  const ref = useRef<HTMLDivElement>(null)
  const opener = useRef<Element | null>(null)
  useEffect(() => {
    if (!open) return
    opener.current = document.activeElement
    const el = ref.current
    const first = el?.querySelector<HTMLElement>('[data-autofocus]') ?? el?.querySelector<HTMLElement>(FOCUSABLE)
    first?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose()
      } else if (e.key === 'Tab' && el) {
        const items = Array.from(el.querySelectorAll<HTMLElement>(FOCUSABLE))
        if (!items.length) return
        const a = items[0]
        const z = items[items.length - 1]
        if (e.shiftKey && document.activeElement === a) {
          e.preventDefault()
          z.focus()
        } else if (!e.shiftKey && document.activeElement === z) {
          e.preventDefault()
          a.focus()
        }
      }
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      ;(opener.current as HTMLElement | null)?.focus?.()
    }
  }, [open, onClose])
  if (!open) return null
  return (
    <div role="presentation" className="fade-in fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-3 backdrop-blur-sm" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={ref} role="dialog" aria-modal="true" aria-label={title}
        className={`dialog-in max-h-[92vh] w-full overflow-y-auto rounded-2xl border border-line bg-surface p-6 shadow-[var(--shadow-lg)] ${wide ? 'max-w-4xl' : 'max-w-lg'}`}>
        <div className="-mx-6 -mt-6 mb-5 flex items-start justify-between gap-3 border-b border-line px-6 py-4">
          <h2 className="text-lg font-bold">{title}</h2>
          <Button variant="ghost" size="sm" aria-label={t('common.close')} onClick={onClose}><X className="h-4 w-4" aria-hidden /></Button>
        </div>
        <div>{children}</div>
        {footer && <div className="-mx-6 -mb-6 mt-6 flex flex-wrap justify-end gap-2 border-t border-line bg-surface2/40 px-6 py-4">{footer}</div>}
      </div>
    </div>
  )
}

export function ConfirmDialog({ open, onClose, onConfirm, title, message, confirmLabel, danger, loading }: {
  open: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  message: ReactNode
  confirmLabel?: string
  danger?: boolean
  loading?: boolean
}) {
  const { t } = useTranslation()
  return (
    <Dialog open={open} onClose={onClose} title={title}
      footer={<>
        <Button onClick={onClose}>{t('common.cancel')}</Button>
        <Button variant={danger ? 'danger' : 'primary'} loading={loading} onClick={onConfirm} data-autofocus>{confirmLabel ?? t('common.confirm')}</Button>
      </>}>
      <div className="text-sm">{message}</div>
    </Dialog>
  )
}
