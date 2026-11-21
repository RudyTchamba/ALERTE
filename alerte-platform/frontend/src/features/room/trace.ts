/** Decision trace assembled from the ledger events of the deciding seat (no model "chain of thought": verifiable acts only). */
import type { StreamEvent } from '@/api/sse'
import { seatOf } from './state'

export interface Trace {
  decision: StreamEvent
  retrievals: StreamEvent[]
  toolCalls: StreamEvent[]
  llmCalls: StreamEvent[]
  citationChecks: StreamEvent[]
  errors: StreamEvent[]
  board: StreamEvent[]
}

export function buildTrace(events: Pick<StreamEvent, 'seq' | 'type' | 'actor' | 'seat' | 'payload' | 'sim_time' | 'real_time' | 'visibility'>[], decisionId: string): Trace | null {
  const decision = events.find((e) => e.type === 'DECISION' && e.payload.decision_id === decisionId) as StreamEvent | undefined
  if (!decision) return null
  const seat = (decision.payload.seat_code as string | undefined) ?? seatOf(decision)
  const before = events
    .filter((e) => e.type === 'DECISION' && e.seq < decision.seq && ((e.payload.seat_code as string | undefined) ?? seatOf(e as StreamEvent)) === seat)
    .reduce((m, e) => Math.max(m, e.seq), 0)
  const mine = (events as StreamEvent[]).filter((e) => e.seq > before && e.seq <= decision.seq && seatOf(e) === seat)
  const of = (t: string) => mine.filter((e) => e.type === t)
  return {
    decision,
    retrievals: of('RETRIEVAL'),
    toolCalls: of('TOOL_CALL'),
    llmCalls: of('LLM_CALL'),
    citationChecks: (events as StreamEvent[]).filter((e) => e.type === 'CITATION_CHECK' && e.payload.decision_id === decisionId),
    errors: of('ERROR'),
    board: of('BOARD'),
  }
}
