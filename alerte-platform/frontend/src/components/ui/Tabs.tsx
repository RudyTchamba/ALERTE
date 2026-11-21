import { useId, useRef, type KeyboardEvent, type ReactNode } from 'react'
import { cn } from '@/lib/cn'

export interface TabDef {
  id: string
  label: ReactNode
  content: ReactNode
}

/** Accessible tabs: roving tabindex, arrow/Home/End keys, tabpanel wiring. Controlled by `value`. */
export function Tabs({ tabs, value, onChange, label }: { tabs: TabDef[]; value: string; onChange: (id: string) => void; label: string }) {
  const uid = useId()
  const refs = useRef<Record<string, HTMLButtonElement | null>>({})
  const idx = Math.max(0, tabs.findIndex((t) => t.id === value))
  const onKey = (e: KeyboardEvent) => {
    let n = idx
    if (e.key === 'ArrowRight') n = (idx + 1) % tabs.length
    else if (e.key === 'ArrowLeft') n = (idx - 1 + tabs.length) % tabs.length
    else if (e.key === 'Home') n = 0
    else if (e.key === 'End') n = tabs.length - 1
    else return
    e.preventDefault()
    onChange(tabs[n].id)
    refs.current[tabs[n].id]?.focus()
  }
  return (
    <div>
      <div role="tablist" aria-label={label} onKeyDown={onKey} className="flex flex-wrap gap-1 border-b border-line">
        {tabs.map((t) => (
          <button key={t.id} ref={(el) => { refs.current[t.id] = el }} role="tab" type="button" id={`${uid}-tab-${t.id}`}
            aria-selected={t.id === value} aria-controls={`${uid}-panel-${t.id}`} tabIndex={t.id === value ? 0 : -1}
            onClick={() => onChange(t.id)}
            className={cn('-mb-px border-b-2 px-3 py-2 text-sm font-medium', t.id === value ? 'border-brand text-brand' : 'border-transparent text-muted hover:text-ink')}>
            {t.label}
          </button>
        ))}
      </div>
      {tabs.map((t) => t.id === value && (
        <div key={t.id} role="tabpanel" id={`${uid}-panel-${t.id}`} aria-labelledby={`${uid}-tab-${t.id}`} tabIndex={0} className="pt-4">
          {t.content}
        </div>
      ))}
    </div>
  )
}
