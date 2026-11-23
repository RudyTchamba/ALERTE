import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/lib/cn'
import { InfoTip } from './InfoTip'

export function Card({ className, ...p }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('panel p-5', className)} {...p} />
}

export function PageHeader({ title, description, actions, term }: { title: ReactNode; description?: ReactNode; actions?: ReactNode; term?: string }) {
  return (
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold">{title}{term && <InfoTip term={term} />}</h1>
        {description && <p className="mt-1 max-w-3xl text-sm text-muted">{description}</p>}
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
