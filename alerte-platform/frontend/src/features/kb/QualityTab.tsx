import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { ExpectedList, KbQuality } from '@/api/loose'
import { Badge, Button, EmptyState, Field, Input, QueryState, Section, StatusBadge, Table, TBody, Td, Th, THead, Tr, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { fmtPct } from '@/lib/format'

export function QualityTab({ kbId }: { kbId: string }) {
  const { t } = useTranslation()
  const q = useApiQuery<KbQuality>(keys.kbQuality(kbId), `/knowledge-bases/${kbId}/quality`)
  return (
    <div>
      <QueryState q={q} what="(/quality)">
        {(r) => (
          <>
            <Section title={t('kb.qualitySummary')}>
              <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {[
                  [t('kb.documents'), r.documents],
                  [t('kb.avgQuality'), r.avg_extraction_quality === null ? t('common.notComputed') : fmtPct(r.avg_extraction_quality)],
                  [t('kb.pctArticles'), r.pct_documents_with_articles === null ? '—' : `${r.pct_documents_with_articles} %`],
                  [t('kb.toReview'), r.totals.pages_to_review ?? 0],
                  [t('kb.ocrPages'), r.totals.ocr_pages ?? 0],
                  [t('kb.injectionFlags'), r.totals.injection_flags ?? 0],
                ].map(([k, v]) => <li key={String(k)} className="rounded-md border border-line bg-surface p-3"><p className="text-xs text-muted">{k}</p><p className="text-xl font-bold">{v}</p></li>)}
              </ul>
              {r.alerts.length > 0 && <ul className="mt-3 list-disc pl-5 text-sm text-warn" role="status">{r.alerts.map((a) => <li key={a}>{a}</li>)}</ul>}
            </Section>
            <Section title={t('kb.perDocument')}>
              {r.items.length === 0 ? <EmptyState title={t('kb.noDocs')} /> : (
                <Table caption={t('kb.perDocument')}>
                  <THead><Tr><Th>{t('common.code')}</Th><Th>{t('kb.quality')}</Th><Th>{t('kb.pages')}</Th><Th>OCR</Th><Th>{t('kb.articles')}</Th><Th>{t('kb.toReview')}</Th><Th>{t('kb.warnings')}</Th></Tr></THead>
                  <TBody>{r.items.map((i) => (
                    <Tr key={i.document_id}>
                      <Td className="font-mono">{i.code}</Td><Td>{i.extraction_quality === null ? '—' : fmtPct(i.extraction_quality)}</Td><Td>{i.pages ?? '—'}</Td>
                      <Td>{i.ocr_pct ?? '—'}</Td><Td>{i.articles_detected ?? '—'}</Td>
                      <Td>{i.pages_to_review.length ? i.pages_to_review.join(', ') : '—'}</Td>
                      <Td className="text-xs">{[...i.warnings, ...i.missing_metadata.map((m) => `${t('kb.missingMeta')}: ${m}`), ...(i.injection_flags.length ? [t('kb.injectionSuspected')] : [])].join(' · ') || '—'}</Td>
                    </Tr>
                  ))}</TBody>
                </Table>
              )}
            </Section>
          </>
        )}
      </QueryState>
      <Coverage kbId={kbId} />
    </div>
  )
}

function Coverage({ kbId }: { kbId: string }) {
  const { t } = useTranslation()
  const toast = useToast()
  const q = useApiQuery<ExpectedList>(keys.kbExpected(kbId), `/knowledge-bases/${kbId}/expected`)
  const [title, setTitle] = useState('')
  const [juris, setJuris] = useState('')
  const add = useApiMutation(() => api.post(`/knowledge-bases/${kbId}/expected`, { title, jurisdiction: juris || null }), {
    invalidate: [keys.kbExpected(kbId), keys.kb(kbId), keys.kbQuality(kbId)], onSuccess: () => { setTitle(''); setJuris('') }, onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const upd = useApiMutation((v: { id: string; status: string }) => api.patch(`/knowledge-bases/${kbId}/expected/${v.id}`, { status: v.status }), { invalidate: [keys.kbExpected(kbId), keys.kb(kbId)] })
  const del = useApiMutation((id: string) => api.delete(`/knowledge-bases/${kbId}/expected/${id}`), { invalidate: [keys.kbExpected(kbId), keys.kb(kbId)] })
  return (
    <Section title={t('kb.coverageTitle')}>
      <p className="mb-2 text-sm text-muted">{t('kb.coverageHint')}</p>
      <QueryState q={q} what="(/expected)">
        {(d) => (
          <>
            <p className="mb-2 text-sm" role="status">{d.coverage.ratio === null ? <Badge tone="warn">{t('kb.noExpected')}</Badge> : <Badge tone={d.coverage.ratio >= 1 ? 'ok' : 'warn'}>{t('kb.coverageRatio', { pct: fmtPct(d.coverage.ratio), present: d.coverage.present, expected: d.coverage.expected })}</Badge>}</p>
            {d.items.length > 0 && (
              <Table caption={t('kb.coverageTitle')} className="mb-3">
                <THead><Tr><Th>{t('kb.docTitle')}</Th><Th>{t('kb.jurisdiction')}</Th><Th>{t('common.status')}</Th><Th><span className="sr-only">{t('common.actions')}</span></Th></Tr></THead>
                <TBody>{d.items.map((e) => (
                  <Tr key={e.id}><Td>{e.title}</Td><Td>{e.jurisdiction ?? '—'}</Td><Td><StatusBadge status={e.status} /></Td>
                    <Td><div className="flex gap-1">
                      {e.status !== 'present' && <Button size="sm" onClick={() => upd.mutate({ id: e.id, status: 'present' })}>{t('kb.markPresent')}</Button>}
                      {e.status !== 'missing' && <Button size="sm" onClick={() => upd.mutate({ id: e.id, status: 'missing' })}>{t('kb.markMissing')}</Button>}
                      <Button size="sm" variant="danger" onClick={() => del.mutate(e.id)}>{t('common.delete')}</Button></div></Td></Tr>
                ))}</TBody>
              </Table>
            )}
          </>
        )}
      </QueryState>
      <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => { e.preventDefault(); if (title) add.mutate(undefined) }}>
        <Field label={t('kb.expectedTitle')}><Input value={title} onChange={(e) => setTitle(e.target.value)} /></Field>
        <Field label={t('kb.jurisdiction')}><Input value={juris} onChange={(e) => setJuris(e.target.value)} /></Field>
        <Button type="submit" disabled={!title} loading={add.isPending}>{t('kb.addExpected')}</Button>
      </form>
    </Section>
  )
}
