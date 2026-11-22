import { createElement, type ComponentType } from 'react'
import { useTranslation } from 'react-i18next'
import {
  AlertTriangle, CheckCircle2, CircleDot, Hourglass, MessagesSquare, Radio, Scale, Search, ShieldCheck, ShieldX, XCircle,
} from 'lucide-react'
import type { FlowStep, StepKind, StepTone } from './narrate'

/** Éléments de présentation partagés par le lecteur de flux et le mode présentation. */
const KIND_ICON: Record<StepKind, ComponentType<{ className?: string }>> = {
  inject: Radio, search: Search, legal: Scale, message: MessagesSquare, citation: ShieldCheck,
  decision: CheckCircle2, gap: AlertTriangle, error: XCircle, state: CircleDot, human: Hourglass,
}
export const TONE_TEXT: Record<StepTone, string> = { brand: 'text-brand', ok: 'text-ok', danger: 'text-danger', warn: 'text-warn', info: 'text-info', neutral: 'text-muted' }
export const TONE_BORDER: Record<StepTone, string> = { brand: 'border-l-brand', ok: 'border-l-ok', danger: 'border-l-danger', warn: 'border-l-warn', info: 'border-l-info', neutral: 'border-l-line' }

function stepIcon(st: FlowStep) {
  if (st.kind === 'citation') return st.tone === 'ok' ? ShieldCheck : ShieldX
  if (st.kind === 'decision' && st.tone !== 'ok') return XCircle
  return KIND_ICON[st.kind]
}
/** Icône d'une étape (createElement : l'icône dépend des données, pas de composant créé au rendu). */
export function StepIcon({ st, className }: { st: FlowStep | null; className?: string }) {
  return createElement(st ? stepIcon(st) : CircleDot, { className, 'aria-hidden': true } as { className?: string })
}

/** Phrase racontée d'une étape. Les noms de signaux sont traduits avant d'être insérés. */
export function useSay() {
  const { t } = useTranslation()
  return (st: FlowStep) => {
    const params = { ...st.params }
    if (st.kind === 'gap') params.signal = t(`room.signalNames.${String(st.params.signal)}`, String(st.params.signal))
    if (st.kind === 'decision' && st.params.article) params.article = String(st.params.article)
    const key = st.kind === 'decision' && st.say === 'decisionOk' && !st.params.article ? 'decisionOkNoArt' : st.say
    return t(`room.flow.say.${key}`, params)
  }
}

/** Texte court de la bulle affichée sur le schéma. */
export function useCallout() {
  const { t } = useTranslation()
  return (st: FlowStep | null): string | null => {
    if (!st) return null
    const q = (v: unknown) => `« ${String(v)} »`
    switch (st.kind) {
      case 'inject': return String(st.params.title)
      case 'search': return `${t('room.flow.callout.search')} ${q(st.params.query)}`
      case 'legal': return q(st.params.question)
      case 'message': return `${st.params.from} → ${st.params.to} : ${q(st.params.body)}`
      case 'decision': return st.tone === 'ok' ? `✓ ${String(st.params.action)}` : `✗ ${String(st.params.action) || t('room.flow.seat.unrecorded')}`
      case 'citation': return st.tone === 'ok' ? t('room.flow.callout.citationOk') : t('room.flow.callout.citationKo')
      case 'gap': return `⚠ ${t(`room.signalNames.${String(st.params.signal)}`, String(st.params.signal))}`
      case 'error': return t('room.flow.callout.error')
      case 'human': return t('room.flow.seat.waiting')
      default: return null
    }
  }
}

