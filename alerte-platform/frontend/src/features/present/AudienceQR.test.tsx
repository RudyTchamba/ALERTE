import { describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockFetch, renderPage } from '@/test/utils'
import type { Exercise } from '@/api/loose'
import { AudienceQR } from './AudienceQR'

const ID = (n: string) => n.padEnd(26, '0')
const ws = { id: ID('W'), name: 'Demo', slug: 'demo', created_at: '2026-01-01T00:00:00Z' }
const ex = {
  id: ID('E1'), code: 'EX-1', title: 'Flood', state: 'ready', ai_mode: 'ai', settings: {},
  seats: [{ code: 'MET', institution_id: ID('I1'), agent_id: ID('A1'), controller: 'agent', human_name: null },
          { code: 'DPC', institution_id: ID('I2'), agent_id: ID('A2'), controller: 'agent', human_name: null }],
} as unknown as Exercise

describe('AudienceQR', () => {
  it('hands a seat to a human before launch, gets the personal link and shows it as a QR code', async () => {
    const user = userEvent.setup()
    const { calls } = mockFetch({
      'GET /workspaces/current': ws, 'GET /tokens': [],
      'PUT /exercises/:id/seats': { status: 200, body: null },
      'POST /exercises/:id/ready': { ok: true },
      [`POST /exercises/${ID('E1')}/seats/DPC/invite`]: { status: 201, body: { token: 'tok', link: '/play#t=tok', seat: 'DPC', human_name: 'Public', expires_at: null, token_id: 't1' } },
    })
    const onClose = vi.fn()
    renderPage(<AudienceQR ex={ex} onClose={onClose} />)
    await user.click(screen.getByText('DPC'))
    await user.click(screen.getByRole('button', { name: /generate the qr code/i }))
    expect(await screen.findByRole('img', { name: /QR code for seat DPC/i })).toBeInTheDocument()
    expect(screen.getByText('Scan to play DPC')).toBeInTheDocument()
    const put = calls.find((c) => c.method === 'PUT')?.body as { seats: { code: string; controller: string; human_name: string | null }[] }
    expect(put.seats.find((s) => s.code === 'DPC')).toMatchObject({ controller: 'human', human_name: 'Audience' })
    expect(put.seats.find((s) => s.code === 'MET')).toMatchObject({ controller: 'agent' })
    expect(calls.some((c) => c.method === 'POST' && c.path.endsWith('/ready'))).toBe(true) // était « prêt » : on le refige
    expect(screen.queryByText(/#t=tok/)).toBeNull() // le jeton n'est jamais affiché en clair
  })
})
