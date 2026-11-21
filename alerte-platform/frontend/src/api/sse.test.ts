import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ExerciseStream, parseSseFrames, streamJob, type StreamEvent } from './sse'
import { FakeEventSource, mockFetch } from '@/test/utils'

describe('ExerciseStream', () => {
  beforeEach(() => { vi.useFakeTimers(); FakeEventSource.reset() })
  afterEach(() => vi.useRealTimers())

  const make = (events: StreamEvent[], statuses: string[] = []) => {
    const tokens = ['tok-1', 'tok-2', 'tok-3']
    const fetchStreamToken = vi.fn(async () => tokens.shift()!)
    const s = new ExerciseStream({
      exerciseId: 'EX1', fetchStreamToken, retryMs: 100, EventSourceImpl: FakeEventSource as unknown as new (u: string) => EventSource,
      onEvent: (e) => events.push(e), onStatus: (st) => statuses.push(st),
    })
    return { s, fetchStreamToken }
  }

  it('opens the stream with a one-time stream token and after=0', async () => {
    const { s } = make([])
    s.start()
    await vi.advanceTimersByTimeAsync(0)
    expect(FakeEventSource.instances[0].url).toBe('/api/v1/exercises/EX1/stream?stream_token=tok-1&after=0')
    s.stop()
  })

  it('de-duplicates by seq and resumes with a NEW token and after=<last seq> after a drop', async () => {
    const events: StreamEvent[] = []
    const statuses: string[] = []
    const { s, fetchStreamToken } = make(events, statuses)
    s.start()
    await vi.advanceTimersByTimeAsync(0)
    const a = FakeEventSource.instances[0]
    a.open()
    a.emit(1, 'INJECT', { title: 'x' })
    a.emit(2, 'DECISION')
    a.emit(2, 'DECISION') // duplicate
    a.emit(1, 'INJECT') // replayed
    expect(events.map((e) => e.seq)).toEqual([1, 2])
    a.fail()
    expect(a.closed).toBe(true)
    expect(statuses).toContain('reconnecting')
    await vi.advanceTimersByTimeAsync(150)
    const b = FakeEventSource.instances[1]
    expect(fetchStreamToken).toHaveBeenCalledTimes(2)
    expect(b.url).toContain('stream_token=tok-2')
    expect(b.url).toContain('after=2')
    b.open()
    b.emit(2, 'DECISION') // server replays the boundary: ignored
    b.emit(3, 'BOARD')
    expect(events.map((e) => e.seq)).toEqual([1, 2, 3])
    s.stop()
  })

  it('stops (no reconnection) once the exercise has completed', async () => {
    const statuses: string[] = []
    const { s } = make([], statuses)
    s.start()
    await vi.advanceTimersByTimeAsync(0)
    const a = FakeEventSource.instances[0]
    a.emit(5, 'STATE', { from: 'running', to: 'completed' })
    expect(statuses).toContain('ended')
    expect(a.closed).toBe(true)
    a.fail()
    await vi.advanceTimersByTimeAsync(10_000)
    expect(FakeEventSource.instances).toHaveLength(1)
  })

  it('does not retry when the stream token request is refused (401/403)', async () => {
    const statuses: string[] = []
    const s = new ExerciseStream({
      exerciseId: 'EX1', fetchStreamToken: async () => { throw Object.assign(new Error('forbidden'), { status: 403 }) },
      EventSourceImpl: FakeEventSource as unknown as new (u: string) => EventSource, onEvent: () => undefined, onStatus: (x) => statuses.push(x),
    })
    s.start()
    await vi.advanceTimersByTimeAsync(10_000)
    expect(statuses.at(-1)).toBe('error')
    expect(FakeEventSource.instances).toHaveLength(0)
  })
})

describe('SSE parsing and job stream', () => {
  it('parses frames split across chunks and ignores comments', () => {
    const { frames, rest } = parseSseFrames(': hb\n\nid: 3\nevent: progress\ndata: {"pct":10}\n\nid: 4\nevent: pro')
    expect(frames).toEqual([{ id: '3', event: 'progress', data: '{"pct":10}' }])
    expect(rest).toBe('id: 4\nevent: pro')
  })

  it('follows job progress then completion, sending the Bearer header (not a URL token)', async () => {
    const enc = new TextEncoder()
    const body = new ReadableStream({ start(c) {
      c.enqueue(enc.encode('id: 100\nevent: progress\ndata: {"pct":10,"step":"kb_ingest","message":"extract"}\n\nid: 1001\nev'))
      c.enqueue(enc.encode('ent: done\ndata: {"result_ref":{"ok":1}}\n\n'))
      c.close()
    } })
    const fn = vi.fn(async () => new Response(body, { headers: { 'content-type': 'text/event-stream' } }))
    vi.stubGlobal('fetch', fn)
    const progress = vi.fn(); const done = vi.fn()
    streamJob('J1', { onProgress: progress, onDone: done, onFailed: vi.fn() }, { token: 'tok' })
    await vi.waitFor(() => expect(done).toHaveBeenCalledWith({ ok: 1 }))
    expect(progress).toHaveBeenCalledWith({ pct: 10, step: 'kb_ingest', message: 'extract' })
    const [url, init] = fn.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).not.toContain('tok')
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer tok')
  })

  it('reports a failed job', async () => {
    mockFetch({ 'GET /jobs/J2/stream': { text: 'id: 1001\nevent: failed\ndata: {"error":"corrupt pdf"}\n\n' } })
    const failed = vi.fn()
    streamJob('J2', { onProgress: vi.fn(), onDone: vi.fn(), onFailed: failed }, { token: 't' })
    await vi.waitFor(() => expect(failed).toHaveBeenCalledWith('corrupt pdf'))
  })
})
