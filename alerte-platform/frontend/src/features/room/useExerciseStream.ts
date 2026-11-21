import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import { ExerciseStream, type StreamStatus, type ExerciseStreamOptions, type StreamEvent } from '@/api/sse'
import { initialRoomState, roomReducer, type RoomState } from './state'

export interface UseExerciseStream {
  state: RoomState
  status: StreamStatus
  error: string | null
  seed: (seats: { code: string; controller: string; human_name: string | null }[]) => void
}

/**
 * Opens the exercise SSE stream (one-time stream token + EventSource, reconnection with `after=<last seq>`),
 * buffers events (the first connection replays the whole ledger visible to the role) and reduces them into state.
 */
export function useExerciseStream(exerciseId: string | undefined, opts: {
  authToken?: string | null
  types?: string[]
  enabled?: boolean
  impl?: Partial<Pick<ExerciseStreamOptions, 'EventSourceImpl' | 'fetchStreamToken' | 'retryMs'>>
} = {}): UseExerciseStream {
  const [state, dispatch] = useReducer(roomReducer, initialRoomState)
  const [status, setStatus] = useState<StreamStatus>('connecting')
  const [error, setError] = useState<string | null>(null)
  const buf = useRef<StreamEvent[]>([])
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const { authToken, enabled = true } = opts
  const typesKey = opts.types?.join(',')
  const implRef = useRef(opts.impl)
  useEffect(() => { implRef.current = opts.impl })

  useEffect(() => {
    if (!exerciseId || !enabled) return
    dispatch({ type: 'reset' })
    const flush = () => {
      timer.current = null
      const events = buf.current
      buf.current = []
      if (events.length) dispatch({ type: 'events', events })
    }
    const stream = new ExerciseStream({
      exerciseId, authToken, types: typesKey ? typesKey.split(',') : undefined, ...implRef.current,
      onEvent: (e) => {
        buf.current.push(e)
        if (!timer.current) timer.current = setTimeout(flush, 80)
      },
      onStatus: (s, info) => { setStatus(s); setError(info?.error ?? null) },
    })
    stream.start()
    return () => {
      stream.stop()
      if (timer.current) clearTimeout(timer.current)
      buf.current = []
    }
  }, [exerciseId, authToken, typesKey, enabled])

  const seed = useCallback((seats: { code: string; controller: string; human_name: string | null }[]) => dispatch({ type: 'seed-seats', seats }), [])
  return { state, status, error, seed }
}
