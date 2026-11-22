import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import i18n from '@/i18n'
import type { PublicAlerts } from '@/api/loose'
import { mockFetch, renderPage } from '@/test/utils'
import { CitizenPage } from './CitizenPage'
import { humanDelay } from './siren'

const EX = '01JALERTE0000000000000000X'
const base: PublicAlerts = {
  exercise_id: EX, code: 'EX-1', title: 'Crue', state: 'running', verdict: 'waiting', first_alert: null, alerts: [],
  hazard: { sim_time: 'J1 06:00', title: 'Crue du Logone', body: 'b', area: "Crue de l'Extrême-Nord" },
}
const issued = {
  seq: 45, seat: 'OPS', institution: 'Opérateurs de téléphonie mobile', action: 'Alerter les habitants', action_code: null,
  status: 'issued' as const, author: 'agent', sim_time: 'J1 10:00', inject_title: 'Villages inondés', delay_minutes: 240,
  real_time: null, cap_xml: '<alert><status>Exercise</status></alert>',
}

describe('CitizenPage', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', `/alerte?x=${EX}#t=obs_secret`)
    vi.stubGlobal('navigator', { ...navigator, vibrate: vi.fn(() => true) })
  })
  afterEach(() => { vi.unstubAllGlobals(); sessionStorage.clear() })

  it('uses the fragment token, strips it from the address bar, and waits once armed', async () => {
    const { calls } = mockFetch({ [`GET /exercises/${EX}/public-alerts`]: base })
    renderPage(<CitizenPage />, { token: null })
    await userEvent.setup().click(await screen.findByRole('button', { name: /enable alerts/i }))
    expect(screen.getByText('No alert received')).toBeInTheDocument()
    expect(window.location.hash).toBe('')
    expect(calls[0].headers.get('authorization')).toBe('Bearer obs_secret')
  })

  it('rings with a full-screen alert, then shows the CAP message after acknowledgement', async () => {
    mockFetch({ [`GET /exercises/${EX}/public-alerts`]: { ...base, verdict: 'alerted', first_alert: issued, alerts: [issued] } })
    renderPage(<CitizenPage />, { token: null })
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: /enable alerts/i }))
    expect(screen.getByRole('alertdialog')).toHaveTextContent('Alerter les habitants')
    expect(screen.getByRole('alertdialog')).toHaveTextContent('4 h after the crisis began')
    expect(navigator.vibrate).toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Got it' }))
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /CAP message/ }))
    expect(screen.getByText(/<status>Exercise<\/status>/)).toBeInTheDocument()
  })

  it('explains the silence when the exercise ends without any verified alert', async () => {
    const blocked = { ...issued, status: 'blocked' as const, cap_xml: undefined }
    mockFetch({ [`GET /exercises/${EX}/public-alerts`]: { ...base, state: 'completed', verdict: 'silent', alerts: [blocked] } })
    renderPage(<CitizenPage />, { token: null })
    await userEvent.setup().click(await screen.findByRole('button', { name: /enable alerts/i }))
    expect(screen.getByText('Your phone never rang')).toBeInTheDocument()
    expect(screen.getByText(/1 alert\(s\) blocked/)).toBeInTheDocument()
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
  })

  it('formats delays', () => {
    const t = i18n.getFixedT('en')
    expect(humanDelay(45, t)).toBe('45 min')
    expect(humanDelay(240, t)).toBe('4 h')
    expect(humanDelay(90, t)).toBe('1 h 30')
    expect(humanDelay(1440 + 360, t)).toBe('1 d 6 h')
  })
})
