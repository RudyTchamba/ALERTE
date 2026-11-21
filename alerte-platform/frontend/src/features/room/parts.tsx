import { useTranslation } from 'react-i18next'
import { Badge } from '@/components/ui'
import type { DecisionItem } from './state'

/** Verified / not verified is ALWAYS a word + icon + colour. */
export function VerifiedBadge({ d }: { d: Pick<DecisionItem, 'status' | 'author'> }) {
  const { t } = useTranslation()
  if (d.author === 'fallback') return <Badge tone="warn">{t('room.fallback')}</Badge>
  if (d.status === 'recorded') return <Badge tone="ok">{t('room.verified')}</Badge>
  if (d.status === 'not_verified') return <Badge tone="danger">{t('room.notVerified')}</Badge>
  return <Badge tone="danger">{t('room.notRecorded')}</Badge>
}

export function OutcomeBadge({ outcome }: { outcome: string | null }) {
  const { t } = useTranslation()
  if (!outcome) return null
  const tone = outcome === 'act' ? 'ok' : outcome === 'no_legal_basis_found' ? 'warn' : 'info'
  return <Badge tone={tone}>{t(`room.outcomes.${outcome}`, outcome)}</Badge>
}

export const BOARD_TYPES = ['INFO', 'REQUEST', 'DECISION', 'OBJECTION', 'GAP_FLAG'] as const
export const SIGNAL_TONE: Record<string, 'danger' | 'warn' | 'info' | 'neutral'> = {
  ORPHAN_REQUEST: 'danger', NO_OWNER: 'danger', CLAIM_OVERLAP: 'warn', CONFLICTING_DECISIONS: 'warn', MISSING_BASIS: 'danger', NO_RESPONSE: 'info', AGENT_HYPOTHESIS: 'neutral', UNSUPPORTED_DECISION: 'warn',
}
