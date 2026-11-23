import { afterEach, describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import '@/i18n'
import type { Exercise } from '@/api/loose'
import { mockFetch, renderPage } from '@/test/utils'
import { LastExercise } from './HomePage'

const ex = { id: 'EX1', code: 'EX-019', title: 'Crue du Wouri', state: 'completed', ai_mode: 'ai' } as Exercise
const gap = (id: string, severity: number, title: string) => ({ id, exercise_id: 'EX1', code: 'G1', severity, title, validation_status: 'confirmed' })

describe('LastExercise', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows how late residents were warned and the worst gaps first', async () => {
    mockFetch({
      'GET /exercises/EX1/public-alerts': { verdict: 'alerted', first_alert: { institution: 'OPS', delay_minutes: 240 }, alerts: [{ status: 'blocked' }, { status: 'issued' }] },
      'GET /gaps': [gap('a', 1, 'Low gap'), gap('b', 3, 'Orphan duty: flood warning'), { ...gap('c', 2, 'Other exercise'), exercise_id: 'EX2' }],
    })
    renderPage(<LastExercise ex={ex} />)
    expect(await screen.findByText('4 h')).toBeInTheDocument()
    expect(screen.getByText(/issued by OPS/)).toBeInTheDocument()
    expect(screen.getByText(/1 attempt\(s\) blocked/)).toBeInTheDocument()
    expect(await screen.findByText('Gaps revealed (2)')).toBeInTheDocument()
    const items = screen.getAllByRole('listitem').map((li) => li.textContent)
    expect(items[0]).toContain('Orphan duty')
    expect(screen.queryByText('Other exercise')).toBeNull()
  })

  it('says loudly when residents were never warned', async () => {
    mockFetch({ 'GET /exercises/EX1/public-alerts': { verdict: 'silent', first_alert: null, alerts: [] }, 'GET /gaps': [] })
    renderPage(<LastExercise ex={ex} />)
    expect(await screen.findByText('No alert')).toBeInTheDocument()
    expect(screen.getByText(/never warned/)).toBeInTheDocument()
  })
})
