import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { api } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { ChunkList, Doc, DocVersion, JobRef, Preview } from '@/api/loose'
import type { DocumentUpdate } from '@/api/types'
import { Badge, Button, Card, ConfirmDialog, EmptyState, Field, Input, KeyValue, PageHeader, QueryState, Section, Select, StatusBadge, Table, TBody, Td, Th, THead, Tr, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { fmtBytes, fmtDateTime, fmtPct } from '@/lib/format'
import { JobProgress } from './JobProgress'

type MetaForm = {
  title: string; doc_type: string; doc_number: string; doc_date: string; jurisdiction: string; language: string; source_url: string
  reliability: string; validity: string; license_spdx: string; redistribution: string; evidence_default: string
}

export function DocumentPage() {
  const { t } = useTranslation()
  const { kbId = '', docId = '' } = useParams()
  const q = useApiQuery<Doc>(keys.doc(docId), `/documents/${docId}`)
  return (
    <>
      <p className="mb-1 text-sm"><Link to={`/studio/knowledge/${kbId}`}>← {t('kb.backToKb')}</Link></p>
      <QueryState q={q} what="(/documents)">
        {(d) => <DocumentView doc={d} kbId={kbId} />}
      </QueryState>
    </>
  )
}

function DocumentView({ doc, kbId }: { doc: Doc; kbId: string }) {
  const { t } = useTranslation()
  const toast = useToast()
  const navigate = useNavigate()
  const [retire, setRetire] = useState(false)
  const [job, setJob] = useState<string | null>(null)
  const versions = useApiQuery<DocVersion[]>(keys.docVersions(doc.id), `/documents/${doc.id}/versions`)
  const cur = doc.version
  const { register, handleSubmit } = useForm<MetaForm>({
    defaultValues: {
      title: doc.title, doc_type: doc.doc_type ?? '', doc_number: doc.doc_number ?? '', doc_date: doc.doc_date ?? '', jurisdiction: doc.jurisdiction ?? '',
      language: doc.language ?? '', source_url: doc.source_url ?? '', reliability: doc.reliability ?? 'unofficial', validity: doc.validity ?? 'unknown',
      license_spdx: doc.license_spdx ?? '', redistribution: doc.redistribution ?? 'unknown', evidence_default: doc.evidence_default ?? 'documented',
    },
  })
  const save = useApiMutation((v: MetaForm) => {
    const body: Record<string, unknown> = {}
    for (const [k, val] of Object.entries(v)) body[k] = val === '' ? null : val
    return api.patch(`/documents/${doc.id}`, body as DocumentUpdate)
  }, { invalidate: [keys.doc(doc.id), keys.kbDocs(kbId)], onSuccess: () => toast.push(t('common.saved')), onError: (e) => toast.push(errorMessage(e, t), 'danger') })
  const del = useApiMutation(() => api.delete(`/documents/${doc.id}`), {
    invalidate: [keys.kbDocs(kbId), keys.kb(kbId)], onSuccess: () => navigate(`/studio/knowledge/${kbId}`), onError: (e) => { setRetire(false); toast.push(errorMessage(e, t), 'danger') },
  })
  const newVersion = useApiMutation((f: File) => { const fd = new FormData(); fd.append('file', f); return api.upload<{ job: JobRef }>(`/documents/${doc.id}/versions`, fd) }, {
    onSuccess: (r) => setJob(r.job.id), onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })

  return (
    <>
      <PageHeader title={doc.title} description={doc.code} actions={<><StatusBadge status={cur?.status} /><Button variant="danger" onClick={() => setRetire(true)}>{t('kb.retire')}</Button></>} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="mb-2 font-semibold">{t('kb.metadata')}</h2>
          <form className="grid gap-3 sm:grid-cols-2" onSubmit={handleSubmit((v) => save.mutate(v))}>
            <Field label={t('kb.docTitle')} className="sm:col-span-2"><Input {...register('title')} /></Field>
            <Field label={t('kb.docType')}><Input {...register('doc_type')} /></Field>
            <Field label={t('kb.docNumber')}><Input {...register('doc_number')} /></Field>
            <Field label={t('kb.docDate')}><Input type="date" {...register('doc_date')} /></Field>
            <Field label={t('kb.jurisdiction')}><Input {...register('jurisdiction')} /></Field>
            <Field label={t('kb.language')}><Input {...register('language')} /></Field>
            <Field label={t('kb.sourceUrl')}><Input type="url" {...register('source_url')} /></Field>
            <Field label={t('kb.reliability')}><Select {...register('reliability')}>{['official', 'summary', 'unofficial', 'unknown', 'not_found'].map((v) => <option key={v}>{v}</option>)}</Select></Field>
            <Field label={t('kb.validity')}><Select {...register('validity')}>{['in_force', 'replaced', 'unknown'].map((v) => <option key={v}>{v}</option>)}</Select></Field>
            <Field label={t('kb.license')}><Input {...register('license_spdx')} /></Field>
            <Field label={t('kb.redistribution')} hint={t('kb.redistributionHint')}><Select {...register('redistribution')}>{['allowed', 'restricted', 'unknown'].map((v) => <option key={v}>{v}</option>)}</Select></Field>
            <Field label={t('kb.evidenceDefault')}><Select {...register('evidence_default')}>{['documented', 'inferred', 'assumed'].map((v) => <option key={v}>{v}</option>)}</Select></Field>
            <div className="sm:col-span-2"><Button type="submit" variant="primary" loading={save.isPending}>{t('common.save')}</Button></div>
          </form>
        </Card>
        <Card>
          <h2 className="mb-2 font-semibold">{t('kb.currentVersion')}</h2>
          {cur ? <KeyValue items={[
            ['#', `v${cur.version_no}`], [t('kb.file'), cur.original_name ?? '—'], [t('kb.size'), fmtBytes(cur.bytes)],
            [t('kb.extraction'), cur.extraction_method ?? '—'], [t('kb.quality'), cur.extraction_quality == null ? '—' : fmtPct(cur.extraction_quality)],
            [t('kb.toReview'), cur.pages_to_review.length ? cur.pages_to_review.join(', ') : '—'], [t('common.createdAt'), fmtDateTime(cur.created_at)],
          ]} /> : <p className="text-sm text-muted">—</p>}
          <div className="mt-3">
            <label className="text-sm font-medium" htmlFor="newver">{t('kb.newVersion')}</label>
            <div className="flex flex-wrap items-center gap-2"><input id="newver" type="file" onChange={(e) => { const f = e.target.files?.[0]; if (f) newVersion.mutate(f) }} /></div>
            {job && <div className="mt-2"><JobProgress jobId={job} label={t('kb.ingesting')} onFinished={() => void 0} /></div>}
          </div>
        </Card>
      </div>
      {cur && (cur.pages_to_review.length > 0) && (
        <Section title={t('kb.pagesToReview')} className="mt-4">
          <p className="text-sm">{t('kb.pagesToReviewHint')}</p>
          <ul className="mt-1 flex flex-wrap gap-2">{cur.pages_to_review.map((p) => <li key={p}><Badge tone="warn">{t('kb.page')} {p}</Badge></li>)}</ul>
        </Section>
      )}
      <Section title={t('kb.versionHistory')} className="mt-4">
        <QueryState q={versions} what="(/versions)">
          {(rows) => (
            <Table caption={t('kb.versionHistory')}>
              <THead><Tr><Th>#</Th><Th>{t('common.status')}</Th><Th>{t('kb.file')}</Th><Th>{t('common.createdAt')}</Th><Th>{t('kb.note')}</Th></Tr></THead>
              <TBody>{rows.map((v) => <Tr key={v.id}><Td>v{v.version_no}</Td><Td><StatusBadge status={v.status} /></Td><Td>{v.original_name}</Td><Td>{fmtDateTime(v.created_at)}</Td><Td>{v.note ?? '—'}</Td></Tr>)}</TBody>
            </Table>
          )}
        </QueryState>
      </Section>
      {cur && <ChunksAndPreview docId={doc.id} versionNo={cur.version_no} />}
      <ConfirmDialog open={retire} onClose={() => setRetire(false)} danger loading={del.isPending} title={t('kb.retire')} message={t('kb.retireConfirm', { title: doc.title })} confirmLabel={t('kb.retire')} onConfirm={() => del.mutate(undefined)} />
    </>
  )
}

function ChunksAndPreview({ docId, versionNo }: { docId: string; versionNo: number }) {
  const { t } = useTranslation()
  const [page, setPage] = useState(1)
  const chunks = useApiQuery<ChunkList>(keys.docChunks(docId, versionNo), `/documents/${docId}/versions/${versionNo}/chunks`, { query: { limit: 50 } })
  const preview = useApiQuery<Preview>(keys.docPreview(docId, versionNo, page), `/documents/${docId}/versions/${versionNo}/preview`, { query: { page, limit: 1 } })
  return (
    <>
      <Section title={t('kb.preview')} className="mt-4">
        <QueryState q={preview} what="(/preview)">
          {(p) => (
            <Card>
              <div className="mb-2 flex items-center gap-2 text-sm">
                <Button size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>{t('common.previous')}</Button>
                <span>{t('kb.pageOf', { page, total: p.total_pages })}</span>
                <Button size="sm" disabled={page >= p.total_pages} onClick={() => setPage(page + 1)}>{t('common.next')}</Button>
              </div>
              <pre className="max-h-80 overflow-auto text-sm whitespace-pre-wrap">{p.pages.map((x) => typeof x === 'string' ? x : JSON.stringify(x, null, 2)).join('\n\n')}</pre>
            </Card>
          )}
        </QueryState>
      </Section>
      <Section title={t('kb.chunks')} className="mt-4">
        <QueryState q={chunks} what="(/chunks)">
          {(c) => c.items.length === 0 ? <EmptyState title={t('kb.noChunks')} /> : (
            <Table caption={t('kb.chunks')}>
              <THead><Tr><Th>#</Th><Th>{t('kb.article')}</Th><Th>{t('kb.pages')}</Th><Th>{t('kb.text')}</Th></Tr></THead>
              <TBody>{c.items.map((x) => <Tr key={x.id}><Td>{x.ordinal}</Td><Td>{x.article ?? '—'}</Td><Td>{x.page_start ?? '—'}{x.page_end && x.page_end !== x.page_start ? `–${x.page_end}` : ''}</Td><Td className="max-w-2xl text-xs">{x.text.length > 400 ? `${x.text.slice(0, 400)}…` : x.text}</Td></Tr>)}</TBody>
            </Table>
          )}
        </QueryState>
      </Section>
    </>
  )
}
