import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import type { StreamEvent } from '@/api/sse'
import { FlowPlayer } from '@/features/room/flow/FlowPlayer'

export const DEMO_SEATS = ['MET', 'DPC', 'TEL']

/**
 * Démonstration animée (données FICTIVES, étiquetées comme telles) : le même lecteur que la Salle de simulation,
 * alimenté par une courte séquence d'événements illustrative, pour montrer le flux sans avoir à ouvrir un exercice.
 */
/** Séquence d'événements FICTIVE de la démonstration (accueil et mode présentation sans exercice). */
export function useDemoEvents(): StreamEvent[] {
  const { t } = useTranslation()
  return useMemo<StreamEvent[]>(() => {
    const d = (k: string) => t(`home.demo.${k}`)
    const raw: [string, Record<string, unknown>, string | null][] = [
      ['STATE', { from: 'ready', to: 'running' }, null],
      ['INJECT', { title: d('inject'), body: d('injectBody'), recipients: ['MET', 'DPC'] }, null],
      ['RETRIEVAL', { query: d('q1'), results: [1, 2, 3] }, 'MET'],
      ['CITATION_CHECK', { citations: [{ pass: true }] }, 'MET'],
      ['DECISION', { seat_code: 'MET', action: d('a1'), status: 'recorded', legal_basis: [{ article: 'Article 12' }] }, 'MET'],
      ['BOARD', { from: 'MET', to: 'DPC', msg_type: 'REQUEST', body: d('m1') }, 'MET'],
      ['RETRIEVAL', { query: d('q2'), results: [1, 2] }, 'DPC'],
      ['BOARD', { from: 'DPC', to: 'TEL', msg_type: 'REQUEST', body: d('m2') }, 'DPC'],
      ['RETRIEVAL', { query: d('q3'), results: [1] }, 'TEL'],
      ['CITATION_CHECK', { citations: [{ pass: false }] }, 'TEL'],
      ['DECISION', { seat_code: 'TEL', action: d('a2'), status: 'not_verified', legal_basis: [] }, 'TEL'],
      ['GAP', { signal: 'UNSUPPORTED_DECISION' }, null],
      ['GAP', { signal: 'NO_OWNER' }, null],
      ['STATE', { from: 'running', to: 'completed' }, null],
    ]
    return raw.map(([type, payload, seat], i) => ({
      seq: i + 1, type, actor: seat ? `seat:${seat}` : 'coord', seat, sim_time: 'J1 06:00', real_time: '', visibility: 'public', payload,
    }))
  }, [t])
}

export function FlowDemo() {
  const { t } = useTranslation()
  const events = useDemoEvents()
  return <FlowPlayer events={events} seats={DEMO_SEATS} live={false} title={t('home.demo.title')} heading={t('home.demo.title')} badge={t('home.demo.badge')} autoplay loop />
}
