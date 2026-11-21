import { describe, expect, it, vi } from 'vitest'
import { api, ApiError, buildUrl, fieldErrors } from './client'
import { session } from './session'
import { apiError, mockFetch } from '@/test/utils'

describe('api client', () => {
  it('sends the token as a Bearer header and never in the URL', async () => {
    session.setToken('s3cret-token')
    const { calls } = mockFetch({ 'GET /countries': [] })
    await api.get('/countries', { query: { include_archived: true } })
    expect(calls[0].headers.get('authorization')).toBe('Bearer s3cret-token')
    expect(calls[0].url).not.toContain('s3cret-token')
    expect(calls[0].url).toBe('http://localhost/api/v1/countries?include_archived=true')
  })

  it('does not log the token', async () => {
    session.setToken('s3cret-token')
    const spies = [vi.spyOn(console, 'log'), vi.spyOn(console, 'error'), vi.spyOn(console, 'warn')]
    mockFetch({ 'GET /x': apiError(500, 'internal_error', 'boom') })
    await api.get('/x').catch(() => undefined)
    for (const s of spies) expect(JSON.stringify(s.mock.calls)).not.toContain('s3cret-token')
  })

  it('stores the token in sessionStorage only', () => {
    session.setToken('abc', 'owner')
    expect(sessionStorage.getItem('alerte.token')).toBe('abc')
    expect(localStorage.length).toBe(0)
  })

  it('maps the standard error body to ApiError', async () => {
    mockFetch({ 'POST /knowledge-bases/x/exports': apiError(422, 'kb.export.restricted_documents', 'restricted', { documents: ['a'] }) })
    const err = await api.post('/knowledge-bases/x/exports', {}).catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err).toMatchObject({ status: 422, code: 'kb.export.restricted_documents', requestId: 'req-1', details: { documents: ['a'] } })
  })

  it('distinguishes a missing route from a missing object', async () => {
    mockFetch({ 'GET /obj': apiError(404, 'not_found', 'nope') })
    const missingRoute = (await api.get('/reports').catch((e) => e)) as ApiError
    const missingObject = (await api.get('/obj').catch((e) => e)) as ApiError
    expect(missingRoute.isRouteMissing).toBe(true)
    expect(missingObject.isRouteMissing).toBe(false)
  })

  it('reports an unreachable server', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('failed') }))
    await expect(api.get('/x')).rejects.toMatchObject({ code: 'network.unreachable', status: 0 })
  })

  it('triggers the session-expired handler on 401 (workspace token only)', async () => {
    const handler = vi.fn()
    session.onUnauthorized(handler)
    session.setToken('t')
    mockFetch({ 'GET /workspaces/current': apiError(401, 'auth.invalid_token', 'bad') })
    await api.get('/workspaces/current').catch(() => undefined)
    expect(handler).toHaveBeenCalledOnce()
    await api.get('/workspaces/current', { token: 'seat-token' }).catch(() => undefined)
    expect(handler).toHaveBeenCalledOnce()
    session.onUnauthorized(null)
  })

  it('extracts per-field errors from validation.failed', () => {
    const e = new ApiError(422, { code: 'validation.failed', message: 'x', details: { errors: [{ loc: ['body', 'name'], msg: 'too short' }] } })
    expect(fieldErrors(e)).toEqual({ name: 'too short' })
  })

  it('drops empty query values', () => {
    expect(buildUrl('/gaps', { a: '', b: undefined, c: 1, d: false })).toBe('/api/v1/gaps?c=1&d=false')
  })
})
