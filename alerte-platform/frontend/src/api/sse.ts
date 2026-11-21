/**
 * SSE clients.
 *  - ExerciseStream: `POST /exercises/{id}/stream-token` (one-time, 60 s token) then native `EventSource`
 *    with `?stream_token=`; on any connection loss the stream re-requests a token and reconnects with
 *    `?after=<last seq>` (a new EventSource has no Last-Event-ID). Events are de-duplicated by `seq`.
 *  - streamJob: fetch-based SSE for `GET /jobs/{id}/stream` (Bearer header, so no token in the URL),
 *    resuming with `after=<last id>`.
 */
import { api, buildUrl } from './client'
import { session } from './session'
import type { StreamToken } from './loose'

export interface StreamEvent {
  seq: number
  type: string
  actor: string
  seat: string | null
  sim_time: string | null
  real_time: string
  visibility: string
  payload: Record<string, unknown>
}

export type StreamStatus = 'connecting' | 'open' | 'reconnecting' | 'ended' | 'error'

export const EVENT_TYPES = [
  'INJECT', 'BOARD', 'DECISION', 'RETRIEVAL', 'TOOL_CALL', 'LLM_CALL', 'CITATION_CHECK', 'GAP', 'HUMAN', 'SEAT',
  'STATE', 'FACILITATOR', 'CORRECTION', 'ERROR', 'SNAPSHOT', 'LEDGER_ANCHOR',
] as const

type ESCtor = new (url: string) => EventSource

export interface ExerciseStreamOptions {
  exerciseId: string
  /** Token used to request the one-time stream token. Defaults to the workspace session token. */
  authToken?: string | null
  after?: number
  types?: string[]
  onEvent: (e: StreamEvent) => void
  onStatus?: (s: StreamStatus, info?: { attempt: number; error?: string }) => void
  /** Test seams. */
  EventSourceImpl?: ESCtor
  fetchStreamToken?: () => Promise<string>
  retryMs?: number
}

export class ExerciseStream {
  private es: EventSource | null = null
  private lastSeq: number
  private stopped = false
  private attempt = 0
  private timer: ReturnType<typeof setTimeout> | null = null
  private o: ExerciseStreamOptions
  constructor(o: ExerciseStreamOptions) {
    this.o = o
    this.lastSeq = o.after ?? 0
  }

  get lastSeen(): number {
    return this.lastSeq
  }

  start(): void {
    this.stopped = false
    void this.connect()
  }

  stop(): void {
    this.stopped = true
    if (this.timer) clearTimeout(this.timer)
    this.es?.close()
    this.es = null
  }

  private async token(): Promise<string> {
    if (this.o.fetchStreamToken) return this.o.fetchStreamToken()
    const r = await api.post<StreamToken>(`/exercises/${this.o.exerciseId}/stream-token`, undefined,
      { token: this.o.authToken === undefined ? session.getToken() : this.o.authToken })
    return r.stream_token
  }

  private status(s: StreamStatus, error?: string) {
    this.o.onStatus?.(s, { attempt: this.attempt, error })
  }

  private async connect(): Promise<void> {
    if (this.stopped) return
    this.status(this.attempt === 0 ? 'connecting' : 'reconnecting')
    let tok: string
    try {
      tok = await this.token()
    } catch (e) {
      if (this.stopped) return
      const status = (e as { status?: number }).status
      if (status === 401 || status === 403 || status === 404) {
        this.status('error', (e as Error).message)
        return
      }
      this.schedule((e as Error).message)
      return
    }
    if (this.stopped) return
    const url = buildUrl(`/exercises/${this.o.exerciseId}/stream`, {
      stream_token: tok,
      after: this.lastSeq,
      types: this.o.types?.join(','),
    })
    const Ctor: ESCtor = this.o.EventSourceImpl ?? (EventSource as unknown as ESCtor)
    const es = new Ctor(url)
    this.es = es
    es.onopen = () => {
      this.attempt = 0
      this.status('open')
    }
    const handle = (ev: MessageEvent) => {
      let data: StreamEvent
      try {
        data = JSON.parse(ev.data as string) as StreamEvent
      } catch {
        return
      }
      if (typeof data.seq !== 'number' || data.seq <= this.lastSeq) return // de-duplication
      this.lastSeq = data.seq
      this.o.onEvent(data)
      if (data.type === 'STATE') {
        const to = (data.payload as { to?: string }).to
        if (to === 'completed' || to === 'stopped') {
          this.status('ended')
          this.stop()
        }
      }
    }
    for (const t of EVENT_TYPES) es.addEventListener(t, handle as EventListener)
    es.addEventListener('heartbeat', () => this.status('open'))
    es.onerror = (ev: Event) => {
      // A server-sent `event: error` carries data; a transport failure does not.
      const msg = (ev as MessageEvent).data as string | undefined
      if (msg) {
        this.status('error', msg)
        this.stop()
        return
      }
      es.close()
      this.es = null
      this.schedule('connection lost')
    }
  }

  private schedule(error: string) {
    if (this.stopped) return
    this.attempt += 1
    this.status('reconnecting', error)
    const delay = Math.min((this.o.retryMs ?? 3000) * Math.min(this.attempt, 5), 15000)
    this.timer = setTimeout(() => void this.connect(), delay)
  }
}

/** Minimal SSE frame parser (id/event/data) over a text chunk stream. */
export function parseSseFrames(buffer: string): { frames: { id?: string; event: string; data: string }[]; rest: string } {
  const parts = buffer.split(/\r?\n\r?\n/)
  const rest = parts.pop() ?? ''
  const frames: { id?: string; event: string; data: string }[] = []
  for (const block of parts) {
    let id: string | undefined
    let event = 'message'
    const data: string[] = []
    for (const line of block.split(/\r?\n/)) {
      if (!line || line.startsWith(':')) continue
      const i = line.indexOf(':')
      const field = i === -1 ? line : line.slice(0, i)
      const value = i === -1 ? '' : line.slice(i + 1).replace(/^ /, '')
      if (field === 'id') id = value
      else if (field === 'event') event = value
      else if (field === 'data') data.push(value)
    }
    if (data.length || event !== 'message') frames.push({ id, event, data: data.join('\n') })
  }
  return { frames, rest }
}

export interface JobProgress {
  pct: number
  step?: string
  message?: string | null
}
export interface JobHandlers {
  onProgress: (p: JobProgress) => void
  onDone: (result: unknown) => void
  onFailed: (error: string) => void
}

/** Follows a job's SSE progress; resumes (after=<last id>) if the connection drops. Returns a cancel function. */
export function streamJob(jobId: string, h: JobHandlers, o: { token?: string | null; retryMs?: number } = {}): () => void {
  const ctrl = new AbortController()
  let lastId = 0
  let finished = false
  const run = async () => {
    for (let attempt = 0; attempt < 20 && !finished && !ctrl.signal.aborted; attempt++) {
      try {
        const token = o.token === undefined ? session.getToken() : o.token
        const res = await fetch(buildUrl(`/jobs/${jobId}/stream`, { after: lastId }), {
          headers: { Accept: 'text/event-stream', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
          signal: ctrl.signal,
          credentials: 'omit',
        })
        if (!res.ok || !res.body) throw new Error(`stream ${res.status}`)
        const reader = res.body.getReader()
        const dec = new TextDecoder()
        let buf = ''
        for (;;) {
          const { done, value } = await reader.read()
          if (done) break
          buf += dec.decode(value, { stream: true })
          const { frames, rest } = parseSseFrames(buf)
          buf = rest
          for (const f of frames) {
            if (f.id && /^\d+$/.test(f.id)) lastId = Number(f.id)
            if (f.event === 'progress') h.onProgress(JSON.parse(f.data) as JobProgress)
            else if (f.event === 'done') {
              finished = true
              h.onDone((JSON.parse(f.data) as { result_ref?: unknown }).result_ref)
            } else if (f.event === 'failed') {
              finished = true
              h.onFailed((JSON.parse(f.data) as { error?: string }).error ?? 'failed')
            }
          }
          if (finished) return
        }
      } catch (e) {
        if (ctrl.signal.aborted) return
        if (attempt >= 19) {
          h.onFailed((e as Error).message)
          return
        }
      }
      await new Promise((r) => setTimeout(r, o.retryMs ?? 1500))
    }
  }
  void run()
  return () => ctrl.abort()
}
