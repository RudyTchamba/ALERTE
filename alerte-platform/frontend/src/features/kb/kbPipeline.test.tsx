import { describe, expect, it } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockFetch, renderPage } from '@/test/utils'
import type { Kb, KbStatus } from '@/api/loose'
import { BuildTab } from './BuildTab'
import { DocumentsTab } from './DocumentsTab'

const ID = (n: string) => n.padEnd(26, '0').toUpperCase()
const kb: Kb = {
  id: ID('K1'), code: 'CM', name: 'Cameroun', description: null, country_id: null, domain: null, kind: 'national', scope_kind: 'country', scope_path: 'CM',
  languages: ['fr'], embedder_key: null, embedder_fingerprint: null, chunking_params: null, status: 'active', archived_at: null,
}
const ver = (state: string, extra: Record<string, unknown> = {}) => ({
  id: ID('V1'), version_no: 1, status: 'processing', processing_state: state, bytes: 10, blob_sha256: 'a'.repeat(64), original_name: 'x.pdf', storage_path: 'CM/x.pdf',
  pages_to_review: [], extraction_quality: null, supersedes_id: null, note: null, created_at: '2026-01-01T00:00:00Z', ...extra,
})
const doc = (id: string, code: string, v: unknown) => ({ id, kb_id: kb.id, code, title: `Doc ${code}`, jurisdiction: null, redistribution: 'unknown', license_spdx: null, version: v })
const status: KbStatus = {
  kb_id: kb.id, code: 'CM', name: 'Cameroun', scope_kind: 'country', scope_path: 'CM', documents: 3, documents_by_state: { ready: 1, uploaded: 1, failed: 1 },
  documents_ready: 1, documents_waiting: 1, documents_running: 0, documents_failed: 1, documents_needing_review: 0, chunks: 12,
  embeddings: { embedded: 4, chunks: 12, embedder_key: 'k', complete: false }, lexical_index: { rows: 12, chunks: 12, complete: true },
  vector_index: { status: 'incomplete' }, active_version: null, last_build_at: null, general_status: 'errors',
}

describe('Documents tab (pipeline)', () => {
  it('shows the explicit scope, the detailed state and error of each document, and retries ONE failed document', async () => {
    const user = userEvent.setup()
    const { calls } = mockFetch({
      [`GET /knowledge-bases/${kb.id}/documents`]: { items: [doc(ID('D1'), 'DOC-1', ver('failed', { processing_error: 'OCR indisponible' })), doc(ID('D2'), 'DOC-2', ver('ready', { status: 'ready' }))], next_cursor: null },
      [`GET /knowledge-bases/${kb.id}/unregistered`]: { scope_path: 'CM', files: [] },
      [`POST /documents/${ID('D1')}/versions/1/reprocess`]: { status: 202, body: { job: { id: ID('J1'), status: 'queued' } } },
    })
    renderPage(<DocumentsTab kb={kb} archived={false} />)
    expect(screen.getByTestId('kb-scope')).toHaveTextContent('blobs/knowledge_sources/CM')
    expect(await screen.findByText('OCR indisponible')).toBeInTheDocument()
    const btns = screen.getAllByRole('button', { name: /^retry$/i })
    expect(btns).toHaveLength(1) // only the failed document offers a retry
    await user.click(btns[0])
    await waitFor(() => expect(calls.some((c) => c.method === 'POST' && c.path === `/documents/${ID('D1')}/versions/1/reprocess`)).toBe(true))
    expect(calls.filter((c) => c.method === 'POST')).toHaveLength(1) // the other document is untouched
  })

  it('previews several files with per-file metadata and imports each one independently into THIS base', async () => {
    const user = userEvent.setup()
    const { calls } = mockFetch({
      [`GET /knowledge-bases/${kb.id}/documents`]: { items: [], next_cursor: null },
      [`GET /knowledge-bases/${kb.id}/unregistered`]: { scope_path: 'CM', files: [] },
      [`POST /knowledge-bases/${kb.id}/documents`]: ({ body }: { body: unknown }) => ({ status: 202, body: { job: { id: ID('J' + String((body as FormData).get('title'))), status: 'queued' }, document: {} } }),
    })
    renderPage(<DocumentsTab kb={kb} archived={false} />)
    const files = [new File(['%PDF-1.4 a'], 'AE-01_ITU_x.pdf', { type: 'application/pdf' }), new File(['%PDF-1.4 b'], 'b.pdf', { type: 'application/pdf' })]
    await user.upload(screen.getByLabelText(/choose files/i), files)
    const table = await screen.findByRole('table', { name: /2 file\(s\) to import into base CM/i })
    expect(within(table).getByText('AE-01_ITU_x.pdf')).toBeInTheDocument() // the name is only displayed
    const lang = within(table).getByLabelText('Language b.pdf')
    await user.type(lang, 'fr')
    await user.clear(within(table).getByLabelText('Title b.pdf'))
    await user.type(within(table).getByLabelText('Title b.pdf'), 'Décret B')
    expect(calls.filter((c) => c.method === 'POST')).toHaveLength(0) // nothing is sent before confirmation
    await user.click(screen.getByRole('button', { name: /import 2 file\(s\) into CM/i }))
    await waitFor(() => expect(calls.filter((c) => c.method === 'POST' && c.path === `/knowledge-bases/${kb.id}/documents`)).toHaveLength(2))
    const sent = calls.filter((c) => c.method === 'POST').map((c) => c.body as FormData)
    expect(sent[1].get('title')).toBe('Décret B')
    expect(sent[1].get('language')).toBe('fr')
    expect(sent[0].get('jurisdiction')).toBeNull() // no country/institution is invented from the file name
    expect(sent[0].get('doc_type')).toBeNull()
  })
})

describe('Build tab (per-base scope)', () => {
  it('states the scope, offers no global build, asks confirmation naming the base, and builds only this base', async () => {
    const user = userEvent.setup()
    const { calls } = mockFetch({
      [`GET /knowledge-bases/${kb.id}/status`]: status,
      [`POST /knowledge-bases/${kb.id}/build`]: { status: 202, body: { job: { id: ID('J2'), status: 'queued' } } },
      [`GET /knowledge-bases/${kb.id}/check`]: { kb_id: kb.id, ok: false, status, checks: [{ id: 'embeddings_complete', ok: false, detail: 'vecteurs 4/12' }, { id: 'documents_have_chunks', ok: true, detail: 'ok' }] },
    })
    renderPage(<BuildTab kb={kb} archived={false} />)
    expect(await screen.findByTestId('build-scope')).toHaveTextContent(/base CM.*no global build/i)
    expect(screen.queryByRole('button', { name: /build all|everything|all bases/i })).toBeNull()
    expect(await screen.findByText('4/12 ⚠')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /process waiting documents \(CM\)/i }))
    expect(await screen.findByText(/only the waiting documents of base CM/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /run on CM/i }))
    await waitFor(() => expect(calls.some((c) => c.method === 'POST' && c.path.endsWith('/build'))).toBe(true))
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({ steps: ['process'], reembed: false })
    await user.click(screen.getByRole('button', { name: /check consistency \(CM\)/i }))
    expect(await screen.findByText('inconsistent')).toBeInTheDocument()
    expect(screen.getByText(/vecteurs 4\/12/)).toBeInTheDocument()
  })

  it('makes an incomplete vectorization visible and blocks publication until every chunk has a vector', async () => {
    mockFetch({ [`GET /knowledge-bases/${kb.id}/status`]: status })
    renderPage(<BuildTab kb={kb} archived={false} />)
    expect(await screen.findByTestId('vectors-incomplete')).toHaveTextContent(/4\/12 chunks have a vector/i)
    expect(screen.getByTestId('publish-blocked')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /publish CM/i })).toBeDisabled()
  })

  it('allows publication once the vectors are complete', async () => {
    mockFetch({ [`GET /knowledge-bases/${kb.id}/status`]: { ...status, embeddings: { embedded: 12, chunks: 12, embedder_key: 'k', complete: true } } })
    renderPage(<BuildTab kb={kb} archived={false} />)
    await screen.findByTestId('build-scope')
    await screen.findAllByText('12/12') // vecteurs ET index lexical
    expect(screen.queryByTestId('vectors-incomplete')).toBeNull()
    expect(screen.getByRole('button', { name: /publish CM/i })).toBeEnabled()
  })
})
