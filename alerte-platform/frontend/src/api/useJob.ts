import { useEffect, useRef, useState } from 'react'
import { streamJob, type JobProgress } from './sse'

export interface JobState {
  status: 'idle' | 'running' | 'done' | 'failed'
  pct: number
  message?: string | null
  result?: unknown
  error?: string
}

/** Tracks a background job through its SSE stream (progress / done / failed). */
export function useJob(jobId: string | null | undefined, onFinished?: (s: JobState) => void): JobState {
  const [state, setState] = useState<JobState>({ status: 'idle', pct: 0 })
  const cb = useRef(onFinished)
  useEffect(() => {
    cb.current = onFinished
  })
  useEffect(() => {
    if (!jobId) return
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState({ status: 'running', pct: 0 })
    return streamJob(jobId, {
      onProgress: (p: JobProgress) => setState((s) => ({ ...s, status: 'running', pct: p.pct, message: p.message })),
      onDone: (result) => {
        const s: JobState = { status: 'done', pct: 100, result }
        setState(s)
        cb.current?.(s)
      },
      onFailed: (error) => {
        const s: JobState = { status: 'failed', pct: 0, error }
        setState(s)
        cb.current?.(s)
      },
    })
  }, [jobId])
  return state
}
