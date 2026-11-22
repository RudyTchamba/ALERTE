/**
 * Traduit les événements bruts du ledger en « étapes » visuelles et racontées pour la vue Flux.
 * Fonction pure : aucune logique métier, seulement de la mise en récit de ce que le backend a consigné.
 */
import type { StreamEvent } from '@/api/sse'
import { seatOf } from '../state'

/** Nœuds du schéma : sièges (code), `kb:<code>` (documents du siège), et les acteurs fixes. */
export const SCENARIO = 'scenario'
export const BOARD = 'board'
export const LEGAL = 'legal'
export const GAPS = 'gaps'
export const kbOf = (seat: string) => `kb:${seat}`

export type StepKind = 'inject' | 'search' | 'legal' | 'message' | 'citation' | 'decision' | 'gap' | 'error' | 'state' | 'human'
export type StepTone = 'brand' | 'ok' | 'danger' | 'warn' | 'info' | 'neutral'

export interface FlowStep {
  seq: number
  kind: StepKind
  /** Trajets animés (de → vers). Un trajet aller-retour s'écrit [a, b, a]. */
  paths: string[][]
  /** Nœud mis en avant (acteur principal de l'étape). */
  focus: string | null
  tone: StepTone
  /** Clé i18n `room.flow.say.*` et paramètres. */
  say: string
  params: Record<string, string | number>
  simTime: string | null
  /** Effet sur l'état affiché d'un siège (pour colorer le nœud). */
  seatStatus?: { seat: string; status: 'thinking' | 'verified' | 'refused' | 'unrecorded' | 'waiting' }
}

const s = (v: unknown, max = 140): string => {
  const t = typeof v === 'string' ? v : v == null ? '' : String(v)
  return t.length > max ? `${t.slice(0, max - 1)}…` : t
}
const list = (v: unknown): unknown[] => (Array.isArray(v) ? v : [])

export function toSteps(events: StreamEvent[]): FlowStep[] {
  const out: FlowStep[] = []
  for (const e of events) {
    const p = e.payload ?? {}
    const seat = seatOf(e)
    const base = { seq: e.seq, simTime: e.sim_time }
    switch (e.type) {
      case 'INJECT': {
        const to = list(p.recipients).map(String)
        out.push({ ...base, kind: 'inject', paths: to.map((r) => [SCENARIO, r]), focus: SCENARIO, tone: 'brand', say: 'inject',
          params: { title: s(p.title, 80), to: to.join(', ') || '—', body: s(p.body, 160) } })
        break
      }
      case 'LLM_CALL':
        // Trop fréquent pour être raconté : l'activité du siège se voit déjà dans les recherches et décisions.
        break
      case 'RETRIEVAL':
        if (seat) out.push({ ...base, kind: 'search', paths: [[seat, kbOf(seat), seat]], focus: kbOf(seat), tone: 'info', say: 'search',
          params: { seat, query: s(p.query, 90), n: list(p.results).length }, seatStatus: { seat, status: 'thinking' } })
        break
      case 'TOOL_CALL': {
        const args = (p.args ?? {}) as Record<string, unknown>
        if (seat && p.tool === 'ask_legal') out.push({ ...base, kind: 'legal', paths: [[seat, LEGAL, seat]], focus: LEGAL, tone: 'info', say: 'legal', params: { seat, question: s(args.question, 100) }, seatStatus: { seat, status: 'thinking' } })
        break
      }
      case 'BOARD': {
        const from = s(p.from, 20), to = s(p.to, 20)
        out.push({ ...base, kind: 'message', paths: [[from, BOARD, to]], focus: BOARD, tone: p.msg_type === 'OBJECTION' ? 'warn' : p.msg_type === 'GAP_FLAG' ? 'danger' : 'neutral',
          say: 'message', params: { from, to, type: s(p.msg_type, 20), body: s(p.body, 160) } })
        break
      }
      case 'CITATION_CHECK': {
        const cites = list(p.citations) as { pass?: boolean }[]
        if (!seat || cites.length === 0) break
        const ok = cites.filter((c) => c.pass === true).length
        out.push({ ...base, kind: 'citation', paths: [[seat, kbOf(seat), seat]], focus: seat, tone: ok === cites.length ? 'ok' : 'danger',
          say: ok === cites.length ? 'citationOk' : 'citationKo', params: { seat, ok, n: cites.length } })
        break
      }
      case 'DECISION': {
        const who = s(p.seat_code, 20) || seat || '?'
        const status = s(p.status, 20)
        const basis = list(p.legal_basis) as { article?: string | null }[]
        const article = basis.map((b) => b.article).filter(Boolean)[0] ?? ''
        const verified = status === 'recorded' && p.author !== 'fallback'
        const say = verified ? 'decisionOk' : status === 'not_recorded' ? 'decisionNone' : 'decisionKo'
        out.push({ ...base, kind: 'decision', paths: [[who, BOARD]], focus: who, tone: verified ? 'ok' : 'danger', say,
          params: { seat: who, action: s(p.action, 120), article: String(article) },
          seatStatus: { seat: who, status: verified ? 'verified' : status === 'not_recorded' ? 'unrecorded' : 'refused' } })
        break
      }
      case 'GAP':
        out.push({ ...base, kind: 'gap', paths: [[BOARD, GAPS]], focus: GAPS, tone: 'danger', say: 'gap', params: { signal: s(p.signal, 40) } })
        break
      case 'ERROR':
        if (seat) out.push({ ...base, kind: 'error', paths: [], focus: seat, tone: 'warn', say: String(p.next_action ?? '').startsWith('retry') ? 'errorRetry' : 'errorFinal', params: { seat } })
        break
      case 'HUMAN':
        if (p.kind === 'task_opened') {
          const c = s(p.seat, 20) || seat || '?'
          out.push({ ...base, kind: 'human', paths: [], focus: c, tone: 'warn', say: 'human', params: { seat: c }, seatStatus: { seat: c, status: 'waiting' } })
        }
        break
      case 'STATE':
        if (p.to === 'running' || p.to === 'completed' || p.to === 'stopped') out.push({ ...base, kind: 'state', paths: [], focus: null, tone: p.to === 'running' ? 'ok' : 'brand', say: `state_${String(p.to)}`, params: {} })
        break
      default:
        break
    }
  }
  return out
}

export type SeatVisual = 'idle' | 'thinking' | 'verified' | 'refused' | 'unrecorded' | 'waiting'

/** État visuel de chaque siège après les étapes 0..idx (la dernière information l'emporte ; « réfléchit » ne dure qu'une étape). */
export function seatVisuals(steps: FlowStep[], idx: number): Record<string, SeatVisual> {
  const out: Record<string, SeatVisual> = {}
  for (let i = 0; i <= idx && i < steps.length; i++) {
    const st = steps[i].seatStatus
    if (!st) continue
    if (st.status === 'thinking') { if (i === idx) out[st.seat] = 'thinking'; continue }
    out[st.seat] = st.status
  }
  return out
}
