import { useEffect, useState } from 'react'
import { safeGet, safeSet } from '@/lib/storage'

/**
 * Seat/observer links carry the token in the URL FRAGMENT (`/play#t=…`): it never reaches the server or a Referer header.
 * We read it once, strip it from the address bar immediately, and keep it in sessionStorage (this tab only) so that a
 * refresh keeps working. It is never put in a query string or path, and never logged.
 */
export function readFragmentToken(hash: string): string | null {
  const m = /(?:^#|&)t=([^&]+)/.exec(hash)
  return m ? decodeURIComponent(m[1]) : null
}

export function useSeatToken(storageKey: string): string | null {
  const [token] = useState<string | null>(() => {
    const frag = readFragmentToken(window.location.hash)
    if (frag) {
      safeSet(storageKey, frag)
      return frag
    }
    return safeGet(storageKey)
  })
  useEffect(() => {
    if (window.location.hash) window.history.replaceState(null, '', window.location.pathname + window.location.search)
  }, [])
  return token
}
