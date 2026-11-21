/**
 * Central API client.
 *  - `Authorization: Bearer <token>` header only (the token is never put in a URL or logged);
 *  - standard error format `{error:{code,message,details,request_id}}` -> ApiError;
 *  - JSON, multipart upload and authenticated file download helpers.
 */
import { session } from './session'

export const API_BASE: string = (import.meta.env?.VITE_API_BASE as string | undefined) ?? '/api/v1'

export interface ApiErrorBody {
  code: string
  message: string
  details?: Record<string, unknown> | null
  request_id?: string | null
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: Record<string, unknown>
  readonly requestId: string | null
  constructor(status: number, body: ApiErrorBody) {
    super(body.message)
    this.name = 'ApiError'
    this.status = status
    this.code = body.code
    this.details = (body.details as Record<string, unknown>) ?? {}
    this.requestId = body.request_id ?? null
  }
  /** Route does not exist on this backend (module not delivered yet), as opposed to "object not found". */
  get isRouteMissing(): boolean {
    return this.status === 404 && this.code === 'http.404'
  }
}

export type Query = Record<string, string | number | boolean | null | undefined>

export interface RequestOptions {
  query?: Query
  body?: unknown
  form?: FormData
  rawBody?: string
  contentType?: string
  /** Explicit token (e.g. a seat token held in memory). Defaults to the workspace session token. */
  token?: string | null
  signal?: AbortSignal
  headers?: Record<string, string>
  /** Do not trigger the global "session expired" handler on 401. */
  noAuthRedirect?: boolean
}

export function buildUrl(path: string, query?: Query): string {
  const url = path.startsWith('http') ? path : `${API_BASE}${path.startsWith('/') ? '' : '/'}${path}`
  if (!query) return url
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined || v === null || v === '') continue
    qs.set(k, String(v))
  }
  const s = qs.toString()
  return s ? `${url}?${s}` : url
}

function authHeaders(token: string | null | undefined): Record<string, string> {
  const t = token === undefined ? session.getToken() : token
  return t ? { Authorization: `Bearer ${t}` } : {}
}

async function toError(res: Response): Promise<ApiError> {
  let body: ApiErrorBody | null = null
  try {
    const j = await res.json()
    if (j && typeof j === 'object' && 'error' in j && j.error && typeof j.error === 'object') body = j.error as ApiErrorBody
    else if (j && typeof j === 'object' && 'detail' in j) body = { code: `http.${res.status}`, message: String(j.detail) }
  } catch {
    /* not JSON */
  }
  return new ApiError(res.status, body ?? { code: `http.${res.status}`, message: res.statusText || `HTTP ${res.status}` })
}

async function send(method: string, path: string, o: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = { Accept: 'application/json', ...authHeaders(o.token), ...(o.headers ?? {}) }
  let body: BodyInit | undefined
  if (o.form) body = o.form
  else if (o.rawBody !== undefined) {
    body = o.rawBody
    headers['Content-Type'] = o.contentType ?? 'text/plain'
  } else if (o.body !== undefined) {
    body = JSON.stringify(o.body)
    headers['Content-Type'] = 'application/json'
  }
  let res: Response
  try {
    res = await fetch(buildUrl(path, o.query), { method, headers, body, signal: o.signal, credentials: 'omit' })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw e
    throw new ApiError(0, { code: 'network.unreachable', message: 'The server cannot be reached.' })
  }
  if (!res.ok) {
    const err = await toError(res)
    if (res.status === 401 && !o.noAuthRedirect && o.token === undefined) session.notifyUnauthorized()
    throw err
  }
  return res
}

async function json<T>(method: string, path: string, o: RequestOptions = {}): Promise<T> {
  const res = await send(method, path, o)
  if (res.status === 204) return undefined as T
  const text = await res.text()
  return (text ? JSON.parse(text) : undefined) as T
}

export const api = {
  get: <T>(path: string, o?: RequestOptions) => json<T>('GET', path, o),
  post: <T>(path: string, body?: unknown, o?: RequestOptions) => json<T>('POST', path, { ...o, body }),
  put: <T>(path: string, body?: unknown, o?: RequestOptions) => json<T>('PUT', path, { ...o, body }),
  patch: <T>(path: string, body?: unknown, o?: RequestOptions) => json<T>('PATCH', path, { ...o, body }),
  delete: <T = void>(path: string, o?: RequestOptions) => json<T>('DELETE', path, o),
  upload: <T>(path: string, form: FormData, o?: RequestOptions) => json<T>('POST', path, { ...o, form }),
  text: async (path: string, o?: RequestOptions): Promise<string> => (await send('GET', path, o ?? {})).text(),
  postText: <T>(path: string, text: string, contentType: string, o?: RequestOptions) =>
    json<T>('POST', path, { ...o, rawBody: text, contentType }),
  /** Authenticated download: fetches with the Bearer header, then saves the blob (token never in the URL). */
  async download(path: string, fallbackName: string, o: RequestOptions = {}): Promise<void> {
    const res = await send('GET', path, { ...o, headers: { ...(o.headers ?? {}), Accept: '*/*' } })
    const blob = await res.blob()
    const cd = res.headers.get('content-disposition') ?? ''
    const m = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(cd)
    const name = m ? decodeURIComponent(m[1]) : fallbackName
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = name
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  },
}

/** Field errors from a 422 `validation.failed` response: `{ fieldName: message }`. */
export function fieldErrors(err: unknown): Record<string, string> {
  const out: Record<string, string> = {}
  if (!(err instanceof ApiError)) return out
  const errors = err.details?.errors
  if (Array.isArray(errors)) {
    for (const e of errors as { loc?: unknown[]; msg?: string }[]) {
      const loc = (e.loc ?? []).filter((x) => x !== 'body')
      const key = String(loc[loc.length - 1] ?? '')
      if (key) out[key] = e.msg ?? 'invalid'
    }
  }
  return out
}
