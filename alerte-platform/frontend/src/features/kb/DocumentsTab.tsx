import { useRef, useState, type DragEvent } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import { UploadCloud } from 'lucide-react'
import { api } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiQuery } from '@/api/hooks'
import type { DocList, JobRef, Doc } from '@/api/loose'
import { Badge, Button, EmptyState, Field, Input, QueryState, Select, StatusBadge, Table, TBody, Td, Th, THead, Tr, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { fmtPct } from '@/lib/format'
import { cn } from '@/lib/cn'
import { JobProgress } from './JobProgress'

interface Upload { key: string; name: string; jobId?: string; error?: string }

export function DocumentsTab({ kbId, archived }: { kbId: string; archived: boolean }) {
  const { t } = useTranslation()
  const toast = useToast()
  const qc = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)
  const [uploads, setUploads] = useState<Upload[]>([])
  const [meta, setMeta] = useState({ jurisdiction: '', language: '', doc_type: '', redistribution: 'unknown', license_spdx: '' })
  const q = useApiQuery<DocList>(keys.kbDocs(kbId), `/knowledge-bases/${kbId}/documents`, { query: { limit: 200 } })

  const send = async (files: FileList | File[]) => {
    for (const f of Array.from(files)) {
      const key = `${f.name}-${Date.now()}-${Math.random()}`
      setUploads((u) => [...u, { key, name: f.name }])
      const fd = new FormData()
      fd.append('file', f)
      for (const [k, v] of Object.entries(meta)) if (v) fd.append(k, v)
      try {
        const r = await api.upload<{ job: JobRef; document: Doc }>(`/knowledge-bases/${kbId}/documents`, fd)
        setUploads((u) => u.map((x) => (x.key === key ? { ...x, jobId: r.job.id } : x)))
        void qc.invalidateQueries({ queryKey: keys.kbDocs(kbId) })
      } catch (e) {
        setUploads((u) => u.map((x) => (x.key === key ? { ...x, error: errorMessage(e, t) } : x)))
        toast.push(errorMessage(e, t), 'danger')
      }
    }
  }
  const onDrop = (e: DragEvent) => { e.preventDefault(); setOver(false); if (e.dataTransfer.files.length) void send(e.dataTransfer.files) }
  const refresh = () => { void qc.invalidateQueries({ queryKey: keys.kbDocs(kbId) }); void qc.invalidateQueries({ queryKey: keys.kb(kbId) }); void qc.invalidateQueries({ queryKey: keys.kbQuality(kbId) }) }

  return (
    <div>
      {!archived && (
        <div className="mb-4">
          <div onDragOver={(e) => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)} onDrop={onDrop}
            className={cn('flex flex-col items-center gap-2 rounded-lg border-2 border-dashed p-6 text-center', over ? 'border-brand bg-brandsoft' : 'border-line')}>
            <UploadCloud className="h-6 w-6" aria-hidden />
            <p className="text-sm">{t('kb.dropHint')}</p>
            <input ref={input} type="file" multiple className="sr-only" id="kb-upload" aria-label={t('kb.chooseFiles')} onChange={(e) => { if (e.target.files) void send(e.target.files); e.target.value = '' }} />
            <Button variant="primary" onClick={() => input.current?.click()}>{t('kb.chooseFiles')}</Button>
          </div>
          <details className="mt-2 text-sm">
            <summary className="cursor-pointer">{t('kb.uploadMeta')}</summary>
            <div className="mt-2 grid gap-3 md:grid-cols-5">
              <Field label={t('kb.jurisdiction')}><Input value={meta.jurisdiction} onChange={(e) => setMeta({ ...meta, jurisdiction: e.target.value })} /></Field>
              <Field label={t('kb.language')}><Input value={meta.language} onChange={(e) => setMeta({ ...meta, language: e.target.value })} /></Field>
              <Field label={t('kb.docType')}><Input value={meta.doc_type} onChange={(e) => setMeta({ ...meta, doc_type: e.target.value })} /></Field>
              <Field label={t('kb.redistribution')}><Select value={meta.redistribution} onChange={(e) => setMeta({ ...meta, redistribution: e.target.value })}>{['unknown', 'allowed', 'restricted'].map((r) => <option key={r} value={r}>{r}</option>)}</Select></Field>
              <Field label={t('kb.license')}><Input value={meta.license_spdx} onChange={(e) => setMeta({ ...meta, license_spdx: e.target.value })} /></Field>
            </div>
          </details>
          <ul className="mt-3 flex flex-col gap-2" aria-live="polite">
            {uploads.map((u) => (
              <li key={u.key} className="rounded border border-line p-2 text-sm">
                {u.error ? <p role="alert" className="text-danger">{u.name}: {u.error}</p>
                  : u.jobId ? <JobProgress jobId={u.jobId} label={u.name} onFinished={refresh} />
                    : <p>{u.name}: {t('kb.uploading')}</p>}
              </li>
            ))}
          </ul>
        </div>
      )}
      <QueryState q={q} what="(/documents)">
        {(d) => d.items.length === 0 ? <EmptyState title={t('kb.noDocs')} hint={t('kb.noDocsHint')} /> : (
          <Table caption={t('kb.documentsTab')}>
            <THead><Tr><Th>{t('common.code')}</Th><Th>{t('kb.docTitle')}</Th><Th>{t('kb.jurisdiction')}</Th><Th>{t('kb.validity')}</Th><Th>{t('kb.redistribution')}</Th><Th>{t('kb.quality')}</Th><Th>{t('kb.toReview')}</Th><Th>{t('common.status')}</Th></Tr></THead>
            <TBody>{d.items.map((x) => (
              <Tr key={x.id}>
                <Td className="font-mono">{x.code}</Td>
                <Td><Link to={`/studio/knowledge/${kbId}/documents/${x.id}`}>{x.title}</Link></Td>
                <Td>{x.jurisdiction ?? '—'}</Td>
                <Td><StatusBadge status={x.validity} /></Td>
                <Td><StatusBadge status={x.redistribution} />{x.license_spdx && <div className="text-xs text-muted">{x.license_spdx}</div>}</Td>
                <Td>{x.version?.extraction_quality == null ? '—' : fmtPct(x.version.extraction_quality)}</Td>
                <Td>{x.version?.pages_to_review?.length ? <Badge tone="warn">{t('kb.nPages', { n: x.version.pages_to_review.length })}</Badge> : '—'}</Td>
                <Td><StatusBadge status={x.version?.status} /></Td>
              </Tr>
            ))}</TBody>
          </Table>
        )}
      </QueryState>
    </div>
  )
}
