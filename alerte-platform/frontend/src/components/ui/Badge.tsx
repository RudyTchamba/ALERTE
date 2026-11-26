import type { ReactNode } from 'react'
import { AlertTriangle, CheckCircle2, Circle, Info, XCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/cn'

export type Tone = 'ok' | 'warn' | 'danger' | 'info' | 'neutral'

const toneClass: Record<Tone, string> = {
  ok: 'bg-oksoft text-ok border-[color-mix(in_srgb,var(--ok)_45%,transparent)]',
  warn: 'bg-warnsoft text-warn border-[color-mix(in_srgb,var(--warn)_45%,transparent)]',
  danger: 'bg-dangersoft text-danger border-[color-mix(in_srgb,var(--danger)_45%,transparent)]',
  info: 'bg-infosoft text-info border-[color-mix(in_srgb,var(--info)_45%,transparent)]',
  neutral: 'bg-neutralsoft text-neutral border-line',
}
const ToneIcon = { ok: CheckCircle2, warn: AlertTriangle, danger: XCircle, info: Info, neutral: Circle }

/** Status badge: colour is ALWAYS paired with an icon shape and the text label (WCAG 1.4.1). */
export function Badge({ tone = 'neutral', children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  const Icon = ToneIcon[tone]
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold whitespace-nowrap', toneClass[tone], className)}>
      <Icon className="h-3.5 w-3.5" aria-hidden />
      {children}
    </span>
  )
}

/** Maps well-known backend status strings to a tone; unknown values stay neutral (never hidden). */
const STATUS_TONE: Record<string, Tone> = {
  // exercise
  draft: 'neutral', ready: 'info', running: 'ok', paused: 'warn', interrupted: 'danger', completed: 'ok', stopped: 'neutral', archived: 'neutral',
  // jobs / documents / versions
  uploaded: 'neutral', validating: 'info', extracting: 'info', ocr_processing: 'info', structuring: 'info', chunking: 'info', embedding: 'info', indexing: 'info',
  empty: 'neutral', errors: 'danger', pending: 'warn', lexical_only: 'warn', vectors_incomplete: 'warn',
  queued: 'neutral', needs_review: 'warn', done: 'ok', failed: 'danger', published: 'ok', retired: 'neutral', indexed: 'ok', ingested: 'ok', ingesting: 'info',
  // decisions
  recorded: 'ok', not_verified: 'danger', not_recorded: 'danger',
  // gap validation
  proposed: 'info', confirmed: 'ok', disputed: 'warn', rejected: 'neutral',
  // mandates
  validated: 'ok',
  // validity / rights
  in_force: 'ok', replaced: 'warn', unknown: 'neutral', allowed: 'ok', restricted: 'danger',
  // registry
  unreviewed: 'warn', partial: 'info', reviewed_complete: 'ok',
  // misc
  present: 'ok', missing: 'danger', active: 'ok', revoked: 'danger',
}
/** Libellé traduit d'une valeur énumérée du backend (statut, gravité, cause…) ; valeur inconnue : texte brut lisible. */
export function useEnumLabel() {
  const { t } = useTranslation()
  return (v: string | null | undefined) => (v ? t(`common.enums.${v}`, { defaultValue: v.replaceAll('_', ' ') }) : '—')
}
export function StatusBadge({ status, label }: { status: string | null | undefined; label?: string }) {
  const s = status ?? 'unknown'
  const enumLabel = useEnumLabel()
  return <Badge tone={STATUS_TONE[s] ?? 'neutral'}>{label ?? enumLabel(s)}</Badge>
}
