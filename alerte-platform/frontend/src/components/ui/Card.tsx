import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/lib/cn'

export function Card({ className, ...p }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('panel p-5', className)} {...p} />
}

export function PageHeader({ title, description, actions, eyebrow }: { title: ReactNode; description?: ReactNode; actions?: ReactNode; eyebrow?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4 border-b border-line pb-5">
      <div className="min-w-0">
        {eyebrow && <p className="eyebrow mb-1 text-brand">{eyebrow}</p>}
        <h1 className="text-2xl font-black tracking-tight sm:text-3xl">{title}</h1>
        {description && <p className="mt-2 max-w-3xl text-base text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}

export function Section({ title, actions, children, className }: { title: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cn('mb-8', className)}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2.5 text-lg font-bold"><span aria-hidden className="h-5 w-1 rounded-full bg-brand" />{title}</h2>
        {actions}
      </div>
      {children}
    </section>
  )
}
