import type { HTMLAttributes, ReactNode, TdHTMLAttributes, ThHTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

/** Scrollable, captioned table. `caption` is announced to screen readers; headers use scope. */
export function Table({ caption, children, className }: { caption: string; children: ReactNode; className?: string }) {
  return (
    <div className={cn('panel relative overflow-x-auto', className)} tabIndex={0} role="region" aria-label={caption}>
      <table className="w-full border-collapse text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  )
}
export const THead = (p: HTMLAttributes<HTMLTableSectionElement>) => <thead className="bg-surface2 text-xs tracking-wide text-muted uppercase" {...p} />
export const TBody = (p: HTMLAttributes<HTMLTableSectionElement>) => <tbody {...p} />
export const Tr = ({ className, ...p }: HTMLAttributes<HTMLTableRowElement>) => <tr className={cn('border-t border-line transition-colors hover:bg-surface2/60', className)} {...p} />
export const Th = ({ className, ...p }: ThHTMLAttributes<HTMLTableCellElement>) => <th scope="col" className={cn('px-3 py-2 font-semibold whitespace-nowrap', className)} {...p} />
export const Td = ({ className, ...p }: TdHTMLAttributes<HTMLTableCellElement>) => <td className={cn('px-3 py-2 align-top', className)} {...p} />
