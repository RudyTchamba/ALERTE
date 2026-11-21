import { useMutation, useQuery, useQueryClient, type QueryKey } from '@tanstack/react-query'
import { api, ApiError, type Query } from './client'

interface QueryOpts {
  query?: Query
  enabled?: boolean
  refetchInterval?: number | false
  token?: string | null
}

/** GET + cache. `path === null` disables the query. */
export function useApiQuery<T>(key: QueryKey, path: string | null, opts: QueryOpts = {}) {
  return useQuery<T, ApiError>({
    queryKey: key,
    queryFn: ({ signal }) => api.get<T>(path as string, { query: opts.query, signal, token: opts.token }),
    enabled: path !== null && (opts.enabled ?? true),
    refetchInterval: opts.refetchInterval,
  })
}

interface MutOpts<R, V> {
  invalidate?: readonly QueryKey[]
  onSuccess?: (data: R, vars: V) => void
  onError?: (e: ApiError) => void
}

export function useApiMutation<V, R = unknown>(fn: (vars: V) => Promise<R>, opts: MutOpts<R, V> = {}) {
  const qc = useQueryClient()
  return useMutation<R, ApiError, V>({
    mutationFn: fn,
    onSuccess: (data, vars) => {
      for (const k of opts.invalidate ?? []) void qc.invalidateQueries({ queryKey: k })
      opts.onSuccess?.(data, vars)
    },
    onError: (e) => opts.onError?.(e),
  })
}
