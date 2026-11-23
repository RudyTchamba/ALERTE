import { describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockFetch, renderPage } from '@/test/utils'
import { PresentPage } from './PresentPage'

const ws = { id: '01J0000000000000000000000W', name: 'Demo', slug: 'demo', created_at: '2026-01-01T00:00:00Z' }

describe('Presentation mode (demo)', () => {
  it('starts on a title screen, advances with the keyboard and ends on a debrief', async () => {
    const user = userEvent.setup()
    mockFetch({ 'GET /workspaces/current': ws, 'GET /tokens': [] })
    renderPage(<PresentPage />, { route: '/present', path: '/present' })
    expect(await screen.findByText('Press Space to start')).toBeInTheDocument()
    await user.keyboard(' ')
    expect(screen.getByText('The exercise begins.')).toBeInTheDocument()
    await user.keyboard('{ArrowRight}')
    expect(screen.getByText(/New event “Flash flood on the river”, sent to MET, DPC\./)).toBeInTheDocument()
    await user.keyboard('{ArrowLeft}')
    expect(screen.getByText('The exercise begins.')).toBeInTheDocument()
    await user.keyboard('{End}')
    expect(screen.getByText('What the exercise revealed')).toBeInTheDocument()
    expect(screen.getByText(/2 gap signal\(s\) for humans to review/)).toBeInTheDocument()
  })
})
