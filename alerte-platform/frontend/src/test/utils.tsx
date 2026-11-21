import type { ReactElement } from 'react'
import { render } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'
import axe from 'axe-core'
import { AuthProvider } from '@/app/auth'
import { Providers, makeQueryClient } from '@/app/providers'
import { session } from '@/api/session'

export type Handler = (req: { url: URL; method: string; body: unknown; headers: Headers }) => { status?: number; body?: unknown; text?: string; headers?: Record<string, string> } | Promise<{ status?: number; body?: unknown; text?: string }>

export interface Call { method: string; path: string; query: string; body: unknown; headers: Headers; url: string }

/** `fetch` mock FOR TESTS ONLY: routes are matched on "METHOD /path" (path without the /api/v1 prefix). */
export function mockFetch(routes: Record<string, Handler | unknown>) {
  const calls: Call[] = []
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(typeof input === 'string' ? input : input.toString(), 'http://localhost')
    const method = (init?.method ?? 'GET').toUpperCase()
    const path = url.pathname.replace(/^\/api\/v1/, '')
    let body: unknown = init?.body
    if (typeof body === 'string') { try { body = JSON.parse(body) } catch { /* raw text */ } }
    const headers = new Headers(init?.headers as HeadersInit)
    calls.push({ method, path, query: url.search, body, headers, url: url.toString() })
    const h = routes[`${method} ${path}`] ?? routes[`${method} ${path.replace(/\/[0-9A-Z]{26}(?=\/|$)/g, '/:id')}`]
    if (h === undefined) return new Response(JSON.stringify({ error: { code: 'http.404', message: 'Not Found', details: null, request_id: 'r1' } }), { status: 404, headers: { 'content-type': 'application/json' } })
    const isResp = typeof h === 'object' && h !== null && !Array.isArray(h) && (Object.keys(h).length > 0 && Object.keys(h).every((k) => ['status', 'body', 'text'].includes(k)))
    const r = typeof h === 'function' ? await (h as Handler)({ url, method, body, headers }) : isResp ? h : { body: h }
    const status = (r as { status?: number }).status ?? 200
    const rb = (r as { body?: unknown; text?: string })
    if (status === 204) return new Response(null, { status })
    return new Response(rb.text ?? JSON.stringify(rb.body ?? null), { status, headers: { 'content-type': rb.text !== undefined ? 'text/plain' : 'application/json' } })
  })
  vi.stubGlobal('fetch', fn)
  return { fn, calls }
}

export const apiError = (status: number, code: string, message: string, details: Record<string, unknown> = {}) => ({ status, body: { error: { code, message, details, request_id: 'req-1' } } })

export function renderPage(ui: ReactElement, opts: { route?: string; path?: string; token?: string | null; role?: string } = {}) {
  const { route = '/', path = '/', token = 'test-token', role = 'owner' } = opts
  if (token) session.setToken(token, role)
  return render(
    <Providers client={makeQueryClient()}>
      <MemoryRouter initialEntries={[route]}>
        <AuthProvider>
          <Routes><Route path={path} element={ui} /><Route path="*" element={<p>other route</p>} /></Routes>
        </AuthProvider>
      </MemoryRouter>
    </Providers>,
  )
}

export async function axeViolations(container: Element): Promise<string[]> {
  const res = await axe.run(container, { rules: { 'color-contrast': { enabled: false }, region: { enabled: false } } })
  return res.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.html).join(' | ')}`)
}

export class FakeEventSource {
  static instances: FakeEventSource[] = []
  url: string
  readyState = 0
  onopen: (() => void) | null = null
  onerror: ((e: Event) => void) | null = null
  listeners = new Map<string, ((e: MessageEvent) => void)[]>()
  closed = false
  constructor(url: string) { this.url = url; FakeEventSource.instances.push(this) }
  addEventListener(t: string, fn: (e: MessageEvent) => void) { this.listeners.set(t, [...(this.listeners.get(t) ?? []), fn]) }
  close() { this.closed = true }
  open() { this.readyState = 1; this.onopen?.() }
  emit(seq: number, type: string, payload: Record<string, unknown> = {}, extra: Record<string, unknown> = {}) {
    const data = JSON.stringify({ seq, type, actor: 'coord', seat: null, sim_time: 'D1 06:00', real_time: '2026-01-01T00:00:00Z', visibility: 'public', payload, ...extra })
    for (const fn of this.listeners.get(type) ?? []) fn({ data, lastEventId: String(seq) } as MessageEvent)
  }
  fail() { this.onerror?.(new Event('error')) }
  static reset() { FakeEventSource.instances = [] }
}
