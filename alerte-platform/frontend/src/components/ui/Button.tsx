import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/cn'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost'
export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: 'sm' | 'md'
  loading?: boolean
  icon?: ReactNode
}

const variants: Record<Variant, string> = {
  primary: 'bg-brand text-brandfg border-transparent font-semibold shadow-[0_1px_0_0_rgba(255,255,255,0.25)_inset,0_6px_20px_-8px_var(--brand)] hover:brightness-110 hover:shadow-[0_1px_0_0_rgba(255,255,255,0.25)_inset,0_10px_28px_-8px_var(--brand)]',
  secondary: 'bg-surface2 text-ink border-line shadow-sm hover:border-muted hover:bg-[color-mix(in_srgb,var(--surface-2)_70%,var(--border))]',
  danger: 'bg-danger text-[var(--danger-contrast)] border-transparent font-semibold shadow-[0_6px_20px_-10px_var(--danger)] hover:brightness-110',
  ghost: 'bg-transparent text-ink border-transparent hover:bg-surface2',
}

export function Button({ variant = 'secondary', size = 'md', loading, icon, children, className, disabled, type = 'button', ...rest }: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg border font-medium whitespace-nowrap transition-all duration-150 active:translate-y-px disabled:pointer-events-none disabled:opacity-50 disabled:shadow-none',
        size === 'sm' ? 'min-h-8 px-3 py-1 text-sm' : 'min-h-10 px-4 py-2 text-sm',
        variants[variant],
        className,
      )}
      {...rest}
    >
      {loading ? <Loader2 className="spin h-4 w-4" aria-hidden /> : icon}
      {children}
    </button>
  )
}
