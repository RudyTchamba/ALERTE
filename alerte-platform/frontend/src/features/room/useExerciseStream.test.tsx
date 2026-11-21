import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { FakeEventSource } from '@/test/utils'
import { useExerciseStream } from './useExerciseStream'

describe('useExerciseStream', () => {
  beforeEach(() => FakeEventSource.reset())

  const setup = () => {
    let n = 0
    const fetchStreamToken = vi.fn(async () => `tok-${++n}`)
    const hook = renderHook(() => useExerciseStream('EX1', { impl: { EventSourceImpl: FakeEventSource as unknown as new (u: string) => EventSource, fetchStreamToken, retryMs: 10 } }))
    return { ...hook, fetchStreamToken }
  }

  it('derives state from events, de-duplicates, and resumes after a drop without losing or repeating events', async () => {
    const { result, fetchStreamToken } = setup()
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1))
    const a = FakeEventSource.instances[0]
    act(() => { a.open(); a.emit(1, 'INJECT', { inject_ref: 'i1', title: 'First' }); a.emit(2, 'BOARD', { msg_id: 'm', from: 'A', to: 'B', msg_type: 'INFO', body: 'x' }); a.emit(2, 'BOARD', { msg_id: 'm', from: 'A', to: 'B', msg_type: 'INFO', body: 'x' }) })
    await waitFor(() => expect(result.current.state.board).toHaveLength(1))
    expect(result.current.status).toBe('open')
    act(() => a.fail())
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(2))
    expect(fetchStreamToken).toHaveBeenCalledTimes(2)
    const b = FakeEventSource.instances[1]
    expect(b.url).toContain('after=2')
    act(() => { b.open(); b.emit(2, 'BOARD', { msg_id: 'm', from: 'A', to: 'B', msg_type: 'INFO', body: 'x' }); b.emit(3, 'DECISION', { decision_id: 'd', seat_code: 'A', status: 'recorded' }) })
    await waitFor(() => expect(result.current.state.decisions).toHaveLength(1))
    expect(result.current.state.board).toHaveLength(1) // the replayed boundary event did not duplicate
    expect(result.current.state.injects.map((i) => i.title)).toEqual(['First'])
    expect(result.current.state.lastSeq).toBe(3)
  })

  it('closes the stream on unmount', async () => {
    const { unmount } = setup()
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1))
    unmount()
    expect(FakeEventSource.instances[0].closed).toBe(true)
  })
})
