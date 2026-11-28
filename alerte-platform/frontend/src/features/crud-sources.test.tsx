import { describe, expect, it } from 'vitest'
import { useState } from 'react'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { apiError, mockFetch, renderPage } from '@/test/utils'
import { ModelProfiles } from './agents/AgentsPage'
import { SourcePicker } from './geo/MandatesTab'
import type { SourceIn } from '@/api/loose'

const ID = (n: string) => n.padEnd(26, '0').toUpperCase()
const profile = { id: ID('P1'), name: 'test-faux', provider: 'openai_compat', endpoint_ref: null, model: 'modele-inexistant', temperature: 0, max_tokens: 1024, timeout_s: 120, extra: null }

describe('Model profiles: edit and delete', () => {
  it('edits a profile (PATCH, empty model sent as null) and refreshes the list', async () => {
    const user = userEvent.setup()
    const { calls } = mockFetch({ 'GET /model-profiles': [profile], 'PATCH /model-profiles/:id': { ...profile, name: 'corrige', model: null } })
    renderPage(<ModelProfiles />)
    await user.click(await screen.findByRole('button', { name: /^edit test-faux$/i }))
    const dialog = await screen.findByRole('dialog')
    const name = within(dialog).getByLabelText(/^name/i)
    expect(name).toHaveValue('test-faux') // the form is pre-filled with the existing profile
    await user.clear(name)
    await user.type(name, 'corrige')
    await user.clear(within(dialog).getByLabelText(/^model$/i))
    await user.click(within(dialog).getByRole('button', { name: /^save$/i }))
    await waitFor(() => expect(calls.some((c) => c.method === 'PATCH')).toBe(true))
    const patch = calls.find((c) => c.method === 'PATCH')!
    expect(patch.path).toBe(`/model-profiles/${profile.id}`)
    expect(patch.body).toMatchObject({ name: 'corrige', model: null, provider: 'openai_compat' })
  })

  it('asks for confirmation, then deletes', async () => {
    const user = userEvent.setup()
    const { calls } = mockFetch({ 'GET /model-profiles': [profile], 'DELETE /model-profiles/:id': { status: 204, body: null } })
    renderPage(<ModelProfiles />)
    await user.click(await screen.findByRole('button', { name: /^delete test-faux$/i }))
    expect(calls.some((c) => c.method === 'DELETE')).toBe(false) // nothing is deleted before the confirmation
    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveTextContent(/test-faux/)
    await user.click(within(dialog).getByRole('button', { name: /^delete$/i }))
    await waitFor(() => expect(calls.some((c) => c.method === 'DELETE' && c.path === `/model-profiles/${profile.id}`)).toBe(true))
  })

  it('shows the server reason when an agent still uses the profile', async () => {
    const user = userEvent.setup()
    mockFetch({ 'GET /model-profiles': [profile], 'DELETE /model-profiles/:id': apiError(409, 'model_profile.in_use', 'profil utilisé par des agents : DPC') })
    renderPage(<ModelProfiles />)
    await user.click(await screen.findByRole('button', { name: /^delete test-faux$/i }))
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: /^delete$/i }))
    expect(await screen.findByText(/DPC/)).toBeInTheDocument()
  })
})

const hit = (n: string) => ({ chunk_id: ID(n), document_version_id: ID('V'), doc_code: 'CM-04', article: `Article ${n}`, page: 3, snippet: `extrait ${n}`, text: `texte complet ${n}`, score: 1 })

function Harness({ existing = [] as string[] }) {
  const [src, setSrc] = useState<SourceIn[]>([])
  return <SourcePicker sources={src} onChange={setSrc} existingChunkIds={existing} />
}

describe('Source picker: a passage cannot be added twice', () => {
  const routes = {
    'GET /knowledge-bases': [{ id: ID('K1'), code: 'CM', name: 'Cameroon' }],
    'POST /knowledge-bases/:id/search': { query: 'x', hits: [hit('A'), hit('B')] },
  }
  async function search(user: ReturnType<typeof userEvent.setup>) {
    await screen.findByRole('option', { name: 'Cameroon' }) // the list of bases arrives asynchronously
    await user.selectOptions(screen.getByRole('combobox'), 'Cameroon')
    await user.type(screen.getByRole('textbox'), 'fléaux')
    await user.click(screen.getByRole('button', { name: /^search$/i }))
  }

  it('removes a passage from the results as soon as it is chosen', async () => {
    const user = userEvent.setup()
    mockFetch(routes)
    renderPage(<Harness />)
    await search(user)
    expect(await screen.findAllByRole('button', { name: /use as source/i })).toHaveLength(2)
    await user.click(screen.getAllByRole('button', { name: /use as source/i })[0])
    expect(screen.getAllByRole('button', { name: /use as source/i })).toHaveLength(1)
    expect(screen.queryByText('extrait A')).not.toBeInTheDocument()
    expect(screen.getByText(/1 passage already added, hidden/i)).toBeInTheDocument()
  })

  it('does not offer a passage that is already saved on the mandate', async () => {
    const user = userEvent.setup()
    mockFetch(routes)
    renderPage(<Harness existing={[ID('B')]} />)
    await search(user)
    expect(await screen.findAllByRole('button', { name: /use as source/i })).toHaveLength(1)
    expect(screen.getByText('extrait A')).toBeInTheDocument()
    expect(screen.queryByText('extrait B')).not.toBeInTheDocument()
  })
})
