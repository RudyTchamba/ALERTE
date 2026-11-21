/**
 * Bearer-token session. The token lives in sessionStorage only (never localStorage, never in a URL, never logged).
 * Player/observer seat tokens (from a `#t=` fragment) are kept in memory by their pages, not here.
 */
import { safeGet, safeSet } from '@/lib/storage'

const KEY = 'alerte.token'
const ROLE_KEY = 'alerte.role'
const listeners = new Set<() => void>()
let unauthorizedHandler: (() => void) | null = null

export const session = {
  getToken: (): string | null => safeGet(KEY),
  setToken(token: string | null, role?: string | null) {
    safeSet(KEY, token)
    safeSet(ROLE_KEY, token ? (role ?? null) : null)
    listeners.forEach((l) => l())
  },
  getRole: (): string | null => safeGet(ROLE_KEY),
  setRole(role: string | null) {
    safeSet(ROLE_KEY, role)
    listeners.forEach((l) => l())
  },
  clear() {
    safeSet(KEY, null)
    safeSet(ROLE_KEY, null)
    listeners.forEach((l) => l())
  },
  subscribe(l: () => void) {
    listeners.add(l)
    return () => listeners.delete(l)
  },
  onUnauthorized(fn: (() => void) | null) {
    unauthorizedHandler = fn
  },
  notifyUnauthorized() {
    unauthorizedHandler?.()
  },
}
