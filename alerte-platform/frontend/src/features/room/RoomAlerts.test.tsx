import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@/i18n'
import type { Exercise } from '@/api/loose'
import type { StreamEvent } from '@/api/sse'
import { RoomAlerts, humanDeadline } from './RoomAlerts'

const opened = new Date(Date.now() - 60_000).toISOString()
const events = [{ seq: 1, type: 'HUMAN', actor: 'coord', seat: 'DPC', sim_time: 'D1', real_time: opened, visibility: 'seat', payload: { kind: 'task_opened', seat: 'DPC', fallback: 'agent_takeover' } }] as StreamEvent[]
const ex = { id: 'E', settings: { human_deadline_s: 900 } } as unknown as Exercise
const seat = { code: 'DPC', controller: 'human', humanName: 'Marie', awaitingHuman: true, lastSeq: 1 }

describe('RoomAlerts', () => {
  it('derives the deadline from the task opening time and the exercise setting', () => {
    const d = humanDeadline(events, 'DPC', 900)
    expect(d.fallback).toBe('agent_takeover')
    expect(d.at).toBe(Date.parse(opened) + 900_000)
    expect(humanDeadline(events, 'MET', 900).at).toBeNull()
  })

  it('explains what to do when a human seat is awaited, with a countdown and two actions', async () => {
    const user = userEvent.setup()
    const onShowQr = vi.fn(), onGiveToAgent = vi.fn()
    render(<RoomAlerts ex={ex} exState="running" seats={[seat]} events={events} canControl onShowQr={onShowQr} onGiveToAgent={onGiveToAgent} onResume={vi.fn()} />)
    expect(screen.getByText('DPC is waiting for a human decision (Marie)')).toBeInTheDocument()
    expect(screen.getByText(/The AI agent takes over automatically in 1[34]:\d\d\./)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /show the player's qr code/i }))
    await user.click(screen.getByRole('button', { name: /give to ai agent/i }))
    expect(onShowQr).toHaveBeenCalledWith('DPC')
    expect(onGiveToAgent).toHaveBeenCalledWith('DPC')
  })

  it('offers to resume an interrupted exercise', async () => {
    const onResume = vi.fn()
    render(<RoomAlerts ex={ex} exState="interrupted" seats={[]} events={[]} canControl onShowQr={vi.fn()} onGiveToAgent={vi.fn()} onResume={onResume} />)
    await userEvent.setup().click(screen.getByRole('button', { name: /^resume$/i }))
    expect(onResume).toHaveBeenCalled()
  })
})
