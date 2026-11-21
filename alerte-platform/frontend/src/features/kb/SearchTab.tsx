import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '@/api/client'
import { useApiMutation } from '@/api/hooks'
import type { SearchHit, SearchResult } from '@/api/loose'
import { Badge, Button, EmptyState, Field, Input, Mono } from '@/components/ui'
import { errorMessage } from '@/lib/errors'

function Signal({ label, v }: { label: string; v: unknown }) {
  if (v === undefined || v === null) return null
  const text = typeof v === 'object' ? JSON.stringify(v) : String(v)
  return <span className="mr-2 text-xs"><span className="text-muted">{label}</span> <Mono>{text}</Mono></span>
}

export function SearchTab({ kbId }: { kbId: string }) {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [article, setArticle] = useState('')
  const search = useApiMutation((v: { q: string; a: string }) => api.post<SearchResult>(`/knowledge-bases/${kbId}/search`, { query: v.q, k: 8, article: v.a || null }))
  const r = search.data
  return (
    <div>
      <p className="mb-3 text-sm text-muted">{t('kb.searchHint')}</p>
      <form className="mb-4 flex flex-wrap items-end gap-2" onSubmit={(e) => { e.preventDefault(); if (query.trim()) search.mutate({ q: query, a: article }) }}>
        <Field label={t('kb.query')} className="min-w-64 flex-1"><Input value={query} onChange={(e) => setQuery(e.target.value)} /></Field>
        <Field label={t('kb.articleFilter')} className="w-32"><Input value={article} onChange={(e) => setArticle(e.target.value)} /></Field>
        <Button type="submit" variant="primary" loading={search.isPending}>{t('common.search')}</Button>
      </form>
      {search.error && <p role="alert" className="text-sm text-danger">{errorMessage(search.error, t)}</p>}
      {r && (
        <div aria-live="polite">
          <p className="mb-2 flex flex-wrap items-center gap-2 text-sm">
            <Badge tone={r.degraded ? 'warn' : 'ok'}>{r.degraded ? t('kb.degraded') : t('kb.hybrid')}</Badge>
            <span className="text-muted">{r.label}</span>
          </p>
          {r.hits.length === 0 ? <EmptyState title={t('kb.noHits')} /> : (
            <ol className="flex flex-col gap-3">
              {r.hits.map((h: SearchHit, i) => (
                <li key={h.chunk_id} className="rounded-md border border-line bg-surface p-3">
                  <p className="font-semibold">#{i + 1} {h.doc_code ?? h.doc_title} {h.article ? `· Art. ${h.article}` : ''} {h.page ? `· p.${h.page}` : ''}</p>
                  <p className="my-1 text-sm">{h.snippet}</p>
                  <p><span className="mr-2 text-xs"><span className="text-muted">{t('kb.score')}</span> <Mono>{h.score.toFixed(4)}</Mono></span>
                    <Signal label={t('kb.lexical')} v={h.signals.lexical} /><Signal label={t('kb.vector')} v={h.signals.dense} />
                    {h.signals.degraded && <Badge tone="warn">{t('kb.lexicalOnly')}</Badge>}</p>
                  <p className="mt-1 text-xs text-muted">chunk <Mono>{h.chunk_id}</Mono></p>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  )
}
