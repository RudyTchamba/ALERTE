import { useQuery } from '@tanstack/react-query'
import { API_BASE } from './client'
import { keys } from './keys'

/** Reads the live OpenAPI document once to know which backend modules are delivered. */
export function useOpenApiPaths() {
  return useQuery<Set<string>>({
    queryKey: keys.openapi,
    staleTime: 60_000,
    retry: false,
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/openapi.json`)
      if (!res.ok) throw new Error('openapi unavailable')
      const j = (await res.json()) as { paths?: Record<string, unknown> }
      return new Set(Object.keys(j.paths ?? {}).map((p) => p.replace(/^\/api\/v1/, '')))
    },
  })
}

/** `undefined` while loading/unknown; otherwise whether the backend serves a route starting with `prefix`. */
export function useHasRoute(prefix: string): boolean | undefined {
  const { data } = useOpenApiPaths()
  if (!data) return undefined
  for (const p of data) if (p.startsWith(prefix)) return true
  return false
}
