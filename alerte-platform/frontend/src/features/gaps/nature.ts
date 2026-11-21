import type { Tone } from '@/components/ui'

export interface NatureTag { key: string; tone: Tone }

/**
 * Distinguishes what a gap IS (doc 09 §9.9 #14): agent hypothesis / observed signal / deduced from a rule /
 * supported by documents, and independently its human validation status. Keys map to `gaps.nature.*`.
 */
export function natureTags(g: { origin: string; evidence_basis: string; validation_status: string }): NatureTag[] {
  const out: NatureTag[] = []
  if (g.origin === 'agent_hypothesis' || g.evidence_basis === 'hypothesis') out.push({ key: 'hypothesis', tone: 'neutral' })
  if (g.origin === 'coordinator_signal' || g.evidence_basis === 'observed') out.push({ key: 'observed', tone: 'info' })
  if (g.origin === 'rule') out.push({ key: 'rule', tone: 'info' })
  if (g.origin === 'imported') out.push({ key: 'imported', tone: 'warn' })
  if (g.evidence_basis === 'documented') out.push({ key: 'documented', tone: 'ok' })
  if (g.evidence_basis === 'inferred') out.push({ key: 'inferred', tone: 'warn' })
  if (g.validation_status === 'confirmed') out.push({ key: 'validated', tone: 'ok' })
  else if (g.validation_status === 'disputed') out.push({ key: 'disputed', tone: 'warn' })
  else if (g.validation_status === 'rejected') out.push({ key: 'rejected', tone: 'danger' })
  else out.push({ key: 'toReview', tone: 'neutral' })
  return out
}
