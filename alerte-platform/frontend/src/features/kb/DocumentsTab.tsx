import { useEffect, useRef, useState, type DragEvent } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import { UploadCloud, X } from 'lucide-react'
import { api } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import { IN_FLIGHT_STATES, PROCESSING_STATES, type AdoptResult, type Doc, type DocList, type JobRef, type Kb, type UnregisteredFiles } from '@/api/loose'
import { Badge, Button, EmptyState, Field, Input, Mono, QueryState, Section, Select, StatusBadge, Table, TBody, Td, Th, THead, Tr, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { fmtBytes, fmtPct } from '@/lib/format'
import { cn } from '@/lib/cn'
import { JobProgress } from './JobProgress'

/** A file chosen by the user, NOT yet sent: the user checks it and gives its metadata one by one. */
interface Staged {
  key: string
  file: File
  sha256?: string
  title: string
  doc_type: string
  language: string
  jurisdiction: string
  redistribution: string
  license_spdx: string
}
interface Upload { key: string; name: string; jobId?: string; error?: string }

const WAITING = ['uploaded', 'queued']

async function sha256Hex(f: File): Promise<string | undefined> {
  try {
    if (!globalThis.crypto?.subtle) return undefined
    const buf = await f.arrayBuffer()
    const h = new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', buf))
    return Array.from(h, (b) => b.toString(16).padStart(2, '0')).join('')
  } catch {
    return undefined // very large file / insecure context: the server computes and checks the hash anyway
  }
}

export function DocumentsTab({ kb, archived }: { kb: Kb; archived: boolean }) {
  const kbId = kb.id
  const { t } = useTranslation()
  const toast = useToast()
  const qc = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)
  const [staged, setStaged] = useState<Staged[]>([])
  const [uploads, setUploads] = useState<Upload[]>([])
  const [filter, setFilter] = useState('')
  const q = useApiQuery<DocList>([...keys.kbDocs(kbId), filter], `/knowledge-bases/${kbId}/documents`, {
    query: { limit: 200, ...(filter ? { state: filter } : {}) }, refetchInterval: 5000,
  })
  const unreg = useApiQuery<UnregisteredFiles>(['kb-unregistered', kbId], `/knowledge-bases/${kbId}/unregistered`)
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: keys.kbDocs(kbId) }); void qc.invalidateQueries({ queryKey: keys.kb(kbId) })
    void qc.invalidateQueries({ queryKey: keys.kbQuality(kbId) }); void qc.invalidateQueries({ queryKey: ['kb-status', kbId] })
    void qc.invalidateQueries({ queryKey: ['kb-unregistered', kbId] })
  }

  const stage = (files: FileList | File[]) => {
    const rows: Staged[] = Array.from(files).map((f) => ({
      key: `${f.name}-${f.size}-${Math.random()}`, file: f, title: f.name.replace(/\.[^.]+$/, ''), doc_type: '', language: '',
      jurisdiction: '', redistribution: 'unknown', license_spdx: '',
    }))
    setStaged((s) => [...s, ...rows])
    for (const r of rows) void sha256Hex(r.file).then((h) => setStaged((s) => s.map((x) => (x.key === r.key ? { ...x, sha256: h } : x))))
  }
  const patch = (key: string, p: Partial<Staged>) => setStaged((s) => s.map((x) => (x.key === key ? { ...x, ...p } : x)))
  const dupInBatch = (s: Staged) => !!s.sha256 && staged.some((o) => o.key !== s.key && o.sha256 === s.sha256)

  const sendAll = async () => {
    const batch = staged
    setStaged([])
    for (const s of batch) {
      setUploads((u) => [...u, { key: s.key, name: s.file.name }])
      const fd = new FormData()
      fd.append('file', s.file)
      for (const k of ['title', 'doc_type', 'language', 'jurisdiction', 'redistribution', 'license_spdx'] as const) if (s[k]) fd.append(k, s[k])
      try { // one file = one independent document: a refusal does not stop the others
        const r = await api.upload<{ job: JobRef; document: Doc }>(`/knowledge-bases/${kbId}/documents`, fd)
        setUploads((u) => u.map((x) => (x.key === s.key ? { ...x, jobId: r.job.id } : x)))
        refresh()
      } catch (e) {
        setUploads((u) => u.map((x) => (x.key === s.key ? { ...x, error: errorMessage(e, t) } : x)))
        toast.push(`${s.file.name}: ${errorMessage(e, t)}`, 'danger')
      }
    }
  }
  const adopt = useApiMutation((files: string[]) => api.post<AdoptResult>(`/knowledge-bases/${kbId}/adopt`, { files, meta: {} }), {
    onSuccess: (r) => { toast.push(t('kb.adoptedToast', { n: r.documents.filter((d) => d.document_id).length })); refresh() },
    onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const retry = useApiMutation((x: Doc) => api.post<{ job: JobRef }>(`/documents/${x.id}/versions/${x.version?.version_no ?? 1}/reprocess`, {}), {
    onSuccess: () => { toast.push(t('kb.retryQueued')); refresh() }, onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const onDrop = (e: DragEvent) => { e.preventDefault(); setOver(false); if (e.dataTransfer.files.length) stage(e.dataTransfer.files) }
  useEffect(() => { if (!staged.length && input.current) input.current.value = '' }, [staged.length])

  return (
    <div>
      <p className="mb-3 rounded border border-line p-2 text-sm" data-testid="kb-scope">
        {t('kb.scopeLine', { code: kb.code })} <Mono>blobs/knowledge_sources/{kb.scope_path ?? kb.code}</Mono>
      </p>
      {!archived && (
        <div className="mb-4">
          <div onDragOver={(e) => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)} onDrop={onDrop}
            className={cn('flex flex-col items-center gap-2 rounded-lg border-2 border-dashed p-6 text-center', over ? 'border-brand bg-brandsoft' : 'border-line')}>
            <UploadCloud className="h-6 w-6" aria-hidden />
            <p className="text-sm">{t('kb.dropHint')}</p>
            <input ref={input} type="file" multiple accept=".pdf,.docx,.txt,.md,.html,.htm,application/pdf" className="sr-only" id="kb-upload" aria-label={t('kb.chooseFiles')}
              onChange={(e) => { if (e.target.files) stage(e.target.files); e.target.value = '' }} />
            <Button variant="primary" onClick={() => input.current?.click()}>{t('kb.chooseFiles')}</Button>
          </div>

          {staged.length > 0 && (
            <Section title={t('kb.stagedTitle', { n: staged.length, code: kb.code })} className="mt-3">
              <p className="mb-2 text-sm text-muted">{t('kb.stagedHint')}</p>
              <Table caption={t('kb.stagedTitle', { n: staged.length, code: kb.code })}>
                <THead><Tr><Th>{t('kb.file')}</Th><Th>SHA-256</Th><Th>{t('kb.docTitle')}</Th><Th>{t('kb.docType')}</Th><Th>{t('kb.language')}</Th><Th>{t('kb.jurisdiction')}</Th><Th>{t('kb.redistribution')}</Th><Th><span className="sr-only">{t('common.remove')}</span></Th></Tr></THead>
                <TBody>{staged.map((s) => (
                  <Tr key={s.key}>
                    <Td><div className="font-mono text-xs">{s.file.name}</div><div className="text-xs text-muted">{fmtBytes(s.file.size)}</div>
                      {dupInBatch(s) && <Badge tone="warn">{t('kb.dupInBatch')}</Badge>}</Td>
                    <Td><Mono>{s.sha256 ? `${s.sha256.slice(0, 12)}…` : '…'}</Mono></Td>
                    <Td><Input aria-label={`${t('kb.docTitle')} ${s.file.name}`} value={s.title} onChange={(e) => patch(s.key, { title: e.target.value })} /></Td>
                    <Td><Input aria-label={`${t('kb.docType')} ${s.file.name}`} value={s.doc_type} onChange={(e) => patch(s.key, { doc_type: e.target.value })} /></Td>
                    <Td><Input aria-label={`${t('kb.language')} ${s.file.name}`} className="w-16" value={s.language} onChange={(e) => patch(s.key, { language: e.target.value })} /></Td>
                    <Td><Input aria-label={`${t('kb.jurisdiction')} ${s.file.name}`} className="w-20" value={s.jurisdiction} onChange={(e) => patch(s.key, { jurisdiction: e.target.value })} /></Td>
                    <Td><Select aria-label={`${t('kb.redistribution')} ${s.file.name}`} value={s.redistribution} onChange={(e) => patch(s.key, { redistribution: e.target.value })}>
                      {['unknown', 'allowed', 'restricted'].map((r) => <option key={r} value={r}>{r}</option>)}</Select></Td>
                    <Td><Button size="sm" aria-label={t('common.remove')} onClick={() => setStaged((x) => x.filter((o) => o.key !== s.key))}><X className="h-4 w-4" aria-hidden /></Button></Td>
                  </Tr>
                ))}</TBody>
              </Table>
              <div className="mt-2 flex gap-2">
                <Button variant="primary" onClick={() => void sendAll()}>{t('kb.importN', { n: staged.length, code: kb.code })}</Button>
                <Button onClick={() => setStaged([])}>{t('common.cancel')}</Button>
              </div>
            </Section>
          )}

          <ul className="mt-3 flex flex-col gap-2" aria-live="polite">
            {uploads.map((u) => (
              <li key={u.key} className="rounded border border-line p-2 text-sm">
                {u.error ? <p role="alert" className="text-danger">{u.name}: {u.error}</p>
                  : u.jobId ? <JobProgress jobId={u.jobId} label={u.name} onFinished={refresh} />
                    : <p>{u.name}: {t('kb.uploading')}</p>}
              </li>
            ))}
          </ul>

          {(unreg.data?.files.length ?? 0) > 0 && (
            <Section title={t('kb.unregisteredTitle', { n: unreg.data?.files.length })} className="mt-3">
              <p className="mb-2 text-sm text-muted">{t('kb.unregisteredHint', { path: unreg.data?.scope_path })}</p>
              <Button loading={adopt.isPending} onClick={() => adopt.mutate(unreg.data!.files.map((f) => f.path))}>{t('kb.adoptAll', { code: kb.code })}</Button>
            </Section>
          )}
        </div>
      )}

      <div className="mb-2 flex flex-wrap items-end gap-3">
        <Field label={t('kb.filterState')}>
          <Select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">{t('kb.allStates')}</option>
            {PROCESSING_STATES.map((st) => <option key={st} value={st}>{t(`common.enums.${st}`, { defaultValue: st })}</option>)}
          </Select>
        </Field>
      </div>
      <QueryState q={q} what="(/documents)">
        {(d) => d.items.length === 0 ? <EmptyState title={t('kb.noDocs')} hint={t('kb.noDocsHint')} /> : (
          <Table caption={t('kb.documentsTab')}>
            <THead><Tr><Th>{t('common.code')}</Th><Th>{t('kb.docTitle')}</Th><Th>{t('kb.file')}</Th><Th>{t('kb.jurisdiction')}</Th><Th>{t('kb.redistribution')}</Th><Th>{t('kb.quality')}</Th><Th>{t('kb.toReview')}</Th><Th>{t('common.status')}</Th><Th><span className="sr-only">{t('common.actions')}</span></Th></Tr></THead>
            <TBody>{d.items.map((x) => {
              const st = x.version?.processing_state ?? x.version?.status
              const inFlight = !!st && (IN_FLIGHT_STATES as readonly string[]).includes(st) && !WAITING.includes(st)
              return (
                <Tr key={x.id}>
                  <Td className="font-mono">{x.code}</Td>
                  <Td><Link to={`/studio/knowledge/${kbId}/documents/${x.id}`}>{x.title}</Link></Td>
                  <Td className="max-w-48 truncate font-mono text-xs" title={x.version?.storage_path ?? undefined}>{x.version?.original_name ?? '—'}</Td>
                  <Td>{x.jurisdiction ?? '—'}</Td>
                  <Td><StatusBadge status={x.redistribution} />{x.license_spdx && <div className="text-xs text-muted">{x.license_spdx}</div>}</Td>
                  <Td>{x.version?.extraction_quality == null ? '—' : fmtPct(x.version.extraction_quality)}</Td>
                  <Td>{x.version?.pages_to_review?.length ? <Badge tone="warn">{t('kb.nPages', { n: x.version.pages_to_review.length })}</Badge> : '—'}</Td>
                  <Td><StatusBadge status={st} />{x.version?.processing_error && <div role="alert" className="max-w-56 text-xs text-danger">{x.version.processing_error}</div>}</Td>
                  <Td>{!archived && !inFlight && st !== 'retired' && (st === 'failed' || WAITING.includes(st ?? '')) &&
                    <Button size="sm" loading={retry.isPending && retry.variables?.id === x.id} onClick={() => retry.mutate(x)}>{st === 'failed' ? t('kb.retry') : t('kb.process')}</Button>}</Td>
                </Tr>
              )
            })}</TBody>
          </Table>
        )}
      </QueryState>
    </div>
  )
}
