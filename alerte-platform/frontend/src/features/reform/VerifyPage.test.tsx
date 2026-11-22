import { afterEach, describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import '@/i18n'
import type { ReformVerification } from '@/api/loose'
import { mockFetch, renderPage } from '@/test/utils'
import { VerifyPage } from './VerifyPage'

const SHA = 'a'.repeat(64)
const doc: ReformVerification = {
  found: true, ok: true, content_ok: true, ledger_ok: true, anchor_ok: true, ledger_checked: 128, verified_citations: true,
  sha256: SHA, created_at: '2026-11-22T21:00:00+00:00', model: 'openai_compat:qwen2.5:7b-instruct',
  content: {
    title: "Émission de l'avis de crue", article_label: 'Article 1er (projet)', article_text: "La DPC émet l'avis de crue dans les 30 minutes.",
    explanation: "L'exercice a montré que personne n'émettait l'avis.", rejected_citations: 1, language: 'fr', action_label: 'Émettre un avis de crue', prompt_version: 'v2',
    citations: [{ chunk_id: 'C1', document_version_id: 'D1', doc_code: 'DOC-0005', article: 'Article 1er', quote: 'La Protection Civile consiste à assurer', check: 'pass', reason: 'ok' }],
  },
  anchors: { exercise_code: 'EX-019', snapshot_sha256: 'b'.repeat(64), ledger_head_seq: 128, ledger_head_hash: 'c'.repeat(64), ledger_ok_at_drafting: true, gap_fingerprint: 'f', gap_code: 'G1', gap_title: 'Responsabilité orpheline : Émettre un avis de crue' },
}

describe('VerifyPage', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows the document, its basis and the three integrity checks without any token', async () => {
    const { calls } = mockFetch({ [`GET /verify/reform/${SHA}`]: doc })
    renderPage(<VerifyPage />, { route: `/verify/${SHA}`, path: '/verify/:sha', token: null })
    expect(await screen.findByText('Authentic and intact document')).toBeInTheDocument()
    expect(screen.getByText(/The exercise ledger is intact \(128 events checked\)/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: "Émission de l'avis de crue" })).toBeInTheDocument()
    expect(screen.getByText(/La Protection Civile consiste à assurer/)).toBeInTheDocument()
    expect(screen.getByText(/1 citation\(s\) removed/)).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /verify this document/i })).toBeInTheDocument()
    expect(calls[0].headers.get('authorization')).toBeNull()
  })

  it('warns loudly when the document no longer matches', async () => {
    mockFetch({ [`GET /verify/reform/${SHA}`]: { ...doc, ok: false, content_ok: false } })
    renderPage(<VerifyPage />, { route: `/verify/${SHA}`, path: '/verify/:sha', token: null })
    expect(await screen.findByText('Warning: this document no longer matches the ledger')).toBeInTheDocument()
  })

  it('says when no document has this fingerprint', async () => {
    mockFetch({ [`GET /verify/reform/${SHA}`]: { found: false } })
    renderPage(<VerifyPage />, { route: `/verify/${SHA}`, path: '/verify/:sha', token: null })
    expect(await screen.findByText('No document matches this fingerprint.')).toBeInTheDocument()
  })
})
