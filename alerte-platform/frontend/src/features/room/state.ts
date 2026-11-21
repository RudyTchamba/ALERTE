/**
 * Pure reducer deriving the Simulation Room state from stream events (doc 12 §12.4: the client DERIVES its state,
 * it does not duplicate business logic). Payload shapes: backend/CONTRACTS.md "Charges utiles d'événements".
 */
import type { StreamEvent } from '@/api/sse'

export interface InjectItem {
  ref: string
  seq: number
  title: string
  body: string
  simTime: string | null
  recipients: string[]
  tags: string[]
  faultMode: string | null
  surprise: boolean
  eventSeq: number
}
export interface DecisionItem {
  decisionId: string
  seq: number
  seat: string
  injectRef: string | null
  round: number | null
  action: string
  actionCode: string | null
  outcome: string | null
  confidence: string | null
  status: string
  author: string | null
  rationale: string | null
  evidenceTag: string | null
  legalBasis: { chunk_id: string; article: string | null; quote?: string; check?: string; pass?: boolean; reason?: string | null }[]
  gapFlags: { hint?: string | null; text: string }[]
  simTime: string | null
}
export interface BoardItem {
  seq: number
  msgId: string
  from: string
  to: string
  type: string
  body: string
  inReplyTo: string | null
  replyStatus: string | null
  injectRef: string | null
  round: number | null
}
export interface SignalItem {
  seq: number
  signal: string
  originKind: string
  injectRef: string | null
  actionCode: string | null
  institutions: string[]
  gapId: string | null
  scripted: boolean
  visibility: string
}
export interface SeatLive {
  code: string
  controller: string | null
  humanName: string | null
  awaitingHuman: boolean
  lastSeq: number | null
}
export interface RoomState {
  lastSeq: number
  exerciseState: string | null
  simTime: string | null
  injects: InjectItem[]
  currentInject: string | null
  seats: Record<string, SeatLive>
  decisions: DecisionItem[]
  board: BoardItem[]
  signals: SignalItem[]
  llmCalls: number
  errors: { seq: number; component: string; message: string }[]
  announcements: string[]
  events: StreamEvent[]
}

export const initialRoomState: RoomState = {
  lastSeq: 0, exerciseState: null, simTime: null, injects: [], currentInject: null, seats: {}, decisions: [], board: [], signals: [],
  llmCalls: 0, errors: [], announcements: [], events: [],
}

const str = (v: unknown): string | null => (typeof v === 'string' ? v : null)
const arr = <T,>(v: unknown): T[] => (Array.isArray(v) ? (v as T[]) : [])
const MAX_EVENTS = 5000

export function seatOf(e: Pick<StreamEvent, 'seat' | 'actor'>): string | null {
  if (e.seat) return e.seat
  return e.actor?.startsWith('seat:') ? e.actor.slice(5) : null
}

function seatRef(state: RoomState, code: string): SeatLive {
  return state.seats[code] ?? { code, controller: null, humanName: null, awaitingHuman: false, lastSeq: null }
}

export type RoomAction =
  | { type: 'events'; events: StreamEvent[] }
  | { type: 'seed-seats'; seats: { code: string; controller: string; human_name: string | null }[] }
  | { type: 'reset' }

function apply(s: RoomState, e: StreamEvent): RoomState {
  if (e.seq <= s.lastSeq) return s // de-duplication (idempotent)
  const p = e.payload ?? {}
  const next: RoomState = { ...s, lastSeq: e.seq, simTime: e.sim_time ?? s.simTime, events: s.events.length >= MAX_EVENTS ? [...s.events.slice(1), e] : [...s.events, e] }
  const code = seatOf(e)
  if (code && !['coord', 'facilitator', 'system'].includes(code)) next.seats = { ...next.seats, [code]: { ...seatRef(next, code), lastSeq: e.seq } }
  switch (e.type) {
    case 'STATE':
      next.exerciseState = str(p.to) ?? s.exerciseState
      if (next.exerciseState === 'completed' || next.exerciseState === 'stopped') {
        next.seats = Object.fromEntries(Object.entries(next.seats).map(([k, v]) => [k, { ...v, awaitingHuman: false }]))
      }
      next.announcements = [...s.announcements, `State: ${String(p.from)} → ${String(p.to)}`].slice(-20)
      break
    case 'INJECT': {
      const ref = str(p.inject_ref) ?? `seq-${e.seq}`
      const item: InjectItem = {
        ref, seq: typeof p.seq === 'number' ? p.seq : s.injects.length + 1, title: str(p.title) ?? ref, body: str(p.body) ?? '', simTime: e.sim_time,
        recipients: arr<string>(p.recipients), tags: arr<string>(p.tags), faultMode: str(p.fault_mode), surprise: p.surprise === true, eventSeq: e.seq,
      }
      next.injects = [...s.injects.filter((i) => i.ref !== ref), item]
      next.currentInject = ref
      next.announcements = [...s.announcements, `Inject: ${item.title}`].slice(-20)
      break
    }
    case 'DECISION': {
      const lb = arr<DecisionItem['legalBasis'][number]>(p.legal_basis)
      const d: DecisionItem = {
        decisionId: str(p.decision_id) ?? `d-${e.seq}`, seq: e.seq, seat: str(p.seat_code) ?? code ?? '?', injectRef: str(p.inject_ref), round: typeof p.round === 'number' ? p.round : null,
        action: str(p.action) ?? '', actionCode: str(p.action_code), outcome: str(p.outcome), confidence: str(p.confidence), status: str(p.status) ?? 'recorded', author: str(p.author),
        rationale: str(p.rationale), evidenceTag: str(p.evidence_tag), legalBasis: lb, gapFlags: arr(p.gap_flags), simTime: e.sim_time,
      }
      next.decisions = [...s.decisions.filter((x) => x.decisionId !== d.decisionId), d]
      next.announcements = [...s.announcements, `Decision by ${d.seat}: ${d.outcome ?? d.status}`].slice(-20)
      break
    }
    case 'BOARD': {
      const b: BoardItem = {
        seq: e.seq, msgId: str(p.msg_id) ?? `m-${e.seq}`, from: str(p.from) ?? '?', to: str(p.to) ?? '?', type: str(p.msg_type) ?? 'INFO', body: str(p.body) ?? '',
        inReplyTo: str(p.in_reply_to), replyStatus: str(p.reply_status), injectRef: str(p.inject_ref), round: typeof p.round === 'number' ? p.round : null,
      }
      next.board = [...s.board, b]
      next.announcements = [...s.announcements, `Board ${b.type}: ${b.from} → ${b.to}`].slice(-20)
      break
    }
    case 'GAP':
      next.signals = [...s.signals, {
        seq: e.seq, signal: str(p.signal) ?? 'GAP', originKind: str(p.origin_kind) ?? 'rule', injectRef: str(p.inject_ref), actionCode: str(p.action_code),
        institutions: arr<string>(p.institutions), gapId: str(p.gap_id), scripted: p.scripted === true, visibility: e.visibility,
      }]
      break
    case 'LLM_CALL':
      next.llmCalls = s.llmCalls + 1
      break
    case 'HUMAN': {
      const c = str(p.seat) ?? code
      if (c) {
        const kind = str(p.kind)
        next.seats = { ...next.seats, [c]: { ...seatRef(next, c), awaitingHuman: kind === 'task_opened' ? true : kind === 'submitted' || kind === 'expired' ? false : seatRef(next, c).awaitingHuman, lastSeq: e.seq } }
      }
      break
    }
    case 'SEAT': {
      const c = str(p.seat)
      if (c) next.seats = { ...next.seats, [c]: { ...seatRef(next, c), controller: str(p.to), humanName: str(p.human_name), lastSeq: e.seq } }
      break
    }
    case 'ERROR':
      next.errors = [...s.errors, { seq: e.seq, component: str(p.component) ?? 'system', message: str(p.message) ?? '' }].slice(-50)
      next.announcements = [...s.announcements, `Error in ${str(p.component) ?? 'system'}`].slice(-20)
      break
    default:
      break
  }
  return next
}

export function roomReducer(state: RoomState, action: RoomAction): RoomState {
  if (action.type === 'reset') return initialRoomState
  if (action.type === 'seed-seats') {
    const seats = { ...state.seats }
    for (const s of action.seats) seats[s.code] = { ...(seats[s.code] ?? { code: s.code, awaitingHuman: false, lastSeq: null }), controller: seats[s.code]?.controller ?? s.controller, humanName: seats[s.code]?.humanName ?? s.human_name }
    return { ...state, seats }
  }
  return action.events.reduce(apply, state)
}
