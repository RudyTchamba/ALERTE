import { cloneElement, isValidElement, useId, type InputHTMLAttributes, type ReactElement, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

interface FieldProps {
  label: ReactNode
  error?: string | null
  hint?: ReactNode
  required?: boolean
  children: ReactElement<Record<string, unknown>>
  className?: string
}

/** Label + control + hint + error, with ids and aria wiring done once. */
export function Field({ label, error, hint, required, children, className }: FieldProps) {
  const id = useId()
  const hintId = hint ? `${id}-hint` : undefined
  const errId = error ? `${id}-err` : undefined
  const control = isValidElement(children)
    ? cloneElement(children, {
        id,
        'aria-invalid': error ? true : undefined,
        'aria-describedby': [hintId, errId].filter(Boolean).join(' ') || undefined,
        'aria-required': required || undefined,
      })
    : children
  return (
    <div className={cn('flex flex-col gap-1', className)}>
      <label htmlFor={id} className="text-sm font-medium">
        {label}
        {required && <span aria-hidden className="text-danger"> *</span>}
      </label>
      {control}
      {hint && <p id={hintId} className="text-xs text-muted">{hint}</p>}
      {error && <p id={errId} role="alert" className="text-xs font-medium text-danger">{error}</p>}
    </div>
  )
}

const base = 'w-full rounded-lg border border-line bg-surface2 px-3 py-2 text-sm text-ink shadow-[inset_0_1px_2px_rgba(0,0,0,0.12)] placeholder:text-muted transition hover:border-muted focus:border-brand focus:shadow-[0_0_0_3px_var(--ring)] focus:outline-none disabled:opacity-60 aria-[invalid=true]:border-danger'

export function Input({ className, ...p }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(base, 'min-h-10', className)} {...p} />
}
export function Textarea({ className, rows = 4, ...p }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea rows={rows} className={cn(base, className)} {...p} />
}
export function Select({ className, children, ...p }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn(base, 'min-h-10', className)} {...p}>{children}</select>
}

export function Checkbox({ label, className, ...p }: InputHTMLAttributes<HTMLInputElement> & { label: ReactNode }) {
  return (
    <label className={cn('inline-flex items-center gap-2 text-sm', className)}>
      <input type="checkbox" className="h-4 w-4 accent-[var(--brand)]" {...p} />
      {label}
    </label>
  )
}
