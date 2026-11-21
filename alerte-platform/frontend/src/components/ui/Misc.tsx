import { useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, Copy } from 'lucide-react'
import { cn } from '@/lib/cn'
import { Button } from './Button'

export function ProgressBar({ pct, label }: { pct: number; label: string }) {
  const v = Math.max(0, Math.min(100, Math.round(pct)))
  return (
    <div className="w-full">
      <div className="mb-1 flex justify-between text-xs text-muted"><span>{label}</span><span>{v} %</span></div>
      <div role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={v} className="h-2 w-full overflow-hidden rounded bg-surface2">
        <div className="h-full bg-brand transition-all" style={{ width: `${v}%` }} />
      </div>
    </div>
  )
}

export function CopyButton({ value, label }: { value: string; label?: string }) {
  const { t } = useTranslation()
  const [done, setDone] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setDone(true)
      setTimeout(() => setDone(false), 2000)
    } catch {
      /* clipboard unavailable: the value stays selectable */
    }
  }
  return (
    <Button size="sm" onClick={() => void copy()} icon={done ? <Check className="h-4 w-4" aria-hidden /> : <Copy className="h-4 w-4" aria-hidden />}>
      {done ? t('common.copied') : (label ?? t('common.copy'))}
    </Button>
  )
}

/** Wizard step indicator (ordered list, current step marked with aria-current). */
export function Stepper({ steps, current }: { steps: string[]; current: number }) {
  return (
    <ol className="mb-4 flex flex-wrap gap-2" aria-label="Steps">
      {steps.map((s, i) => (
        <li key={s} aria-current={i === current ? 'step' : undefined}
          className={cn('rounded-full border px-3 py-1 text-xs font-semibold', i === current ? 'border-brand bg-brandsoft text-brand' : i < current ? 'border-ok text-ok' : 'border-line text-muted')}>
          {i + 1}. {s}{i < current ? ' ✓' : ''}
        </li>
      ))}
    </ol>
  )
}

export function KeyValue({ items }: { items: [ReactNode, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
      {items.map(([k, v], i) => (
        <div key={i} className="contents"><dt className="font-medium text-muted">{k}</dt><dd className="break-words">{v}</dd></div>
      ))}
    </dl>
  )
}

export function Mono({ children }: { children: ReactNode }) {
  return <code className="rounded bg-surface2 px-1 py-0.5 font-mono text-xs break-all">{children}</code>
}
