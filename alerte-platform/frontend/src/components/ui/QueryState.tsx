import type { ReactNode } from 'react'
import type { UseQueryResult } from '@tanstack/react-query'
import { ApiError } from '@/api/client'
import { BackendUnavailable, ErrorState, LoadingState } from './Feedback'

/** Renders loading / error / "backend module missing" and only then the children with the data. */
export function QueryState<T>({ q, what, children, loading }: {
  q: UseQueryResult<T, ApiError>
  what?: string
  loading?: string
  children: (data: T) => ReactNode
}) {
  if (q.isPending) return <LoadingState label={loading} />
  if (q.isError) {
    return q.error instanceof ApiError && q.error.isRouteMissing
      ? <BackendUnavailable what={what} />
      : <ErrorState error={q.error} onRetry={() => void q.refetch()} />
  }
  return <>{children(q.data)}</>
}
