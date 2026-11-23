import { Prereq } from '@/components/Prereq'
import { useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { Exercise, JobRef, Report, ReportCompare, ReportVersion } from '@/api/loose'
import { Badge, Button, Card, EmptyState, Field, Input, Mono, PageHeader, QueryState, Section, Select, StatusBadge, Table, TBody, Td, Textarea, Th, THead, Tr, useToast } from '@/components/ui'
import { JobProgress } from '@/features/kb/JobProgress'
import { errorMessage } from '@/lib/errors'
import { fmtBytes, fmtDateTime } from '@/lib/format'

const FORMATS = ['pdf', 'md', 'json', 'csv', 'xlsx'] as const

export function ReportsPage() {
  const { reportId } = useParams()
  return reportId ? <ReportDetail id={reportId} /> : <ReportList />
}

export function OriginBanner({ r }: { r: Pick<Report, 'kind'> }) {
  const { t } = useTranslation()
  return r.kind === 'imported' ? <Badge tone="warn">{t('reports.priorAnalysis')}</Badge> : <Badge tone="info">{t('reports.generated')}</Badge>
}

function ReportList() {
  const { t } = useTranslation()
  const toast = useToast()
  const navigate = useNavigate()
  const q = useApiQuery<Report[]>(keys.reports, '/reports')
  const exs = useApiQuery<Exercise[]>(keys.exercises(), '/exercises')
  const [ex, setEx] = useState('')
  const [job, setJob] = useState<string | null>(null)
  const [importOpen, setImportOpen] = useState(false)
  const [title, setTitle] = useState('')
  const file = useRef<HTMLInputElement>(null)
  const gen = useApiMutation(() => api.post<{ job: JobRef }>(`/exercises/${ex}/reports`, {}, { headers: { 'Idempotency-Key': `${ex}-${Date.now()}` } }), { onSuccess: (r) => setJob(r.job.id), onError: (e) => toast.push(errorMessage(e, t), 'danger') })
  const imp = useApiMutation((f: File) => { const fd = new FormData(); fd.append('file', f); fd.append('title', title || f.name); return api.upload<Report>('/reports/import', fd) }, {
    invalidate: [keys.reports], onSuccess: (r) => navigate(`/reports/${r.id}`), onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  return (
    <>
      <PageHeader title={t('reports.title')} description={t('reports.description')} actions={<Button onClick={() => setImportOpen((v) => !v)}>{t('reports.importPrior')}</Button>} />
      <Prereq page="reports" />
      {importOpen && (
        <Card className="mb-4">
          <h2 className="mb-2 font-semibold">{t('reports.importPrior')}</h2>
          <p className="mb-2 text-sm text-muted">{t('reports.importHint')}</p>
          <div className="flex flex-wrap items-end gap-2">
            <Field label={t('reports.reportTitle')} className="w-72"><Input value={title} onChange={(e) => setTitle(e.target.value)} /></Field>
            <input ref={file} type="file" accept=".pdf,.docx,.md" aria-label={t('reports.chooseFile')} />
            <Button variant="primary" loading={imp.isPending} onClick={() => { const f = file.current?.files?.[0]; if (f) imp.mutate(f) }}>{t('reports.import')}</Button>
          </div>
        </Card>
      )}
      <Card className="mb-4">
        <h2 className="mb-2 font-semibold">{t('reports.generate')}</h2>
        <div className="flex flex-wrap items-end gap-2">
          <Field label={t('gaps.exercise')} className="w-72"><Select value={ex} onChange={(e) => setEx(e.target.value)}><option value="">—</option>{exs.data?.filter((x) => !['draft', 'ready'].includes(x.state)).map((x) => <option key={x.id} value={x.id}>{x.code} — {x.title}</option>)}</Select></Field>
          <Button variant="primary" disabled={!ex} loading={gen.isPending} onClick={() => gen.mutate(undefined)}>{t('reports.generateBtn')}</Button>
        </div>
        {job && <div className="mt-3"><JobProgress jobId={job} label={t('reports.generating')} onFinished={(s) => { if (s.status === 'done') { toast.push(t('reports.generatedToast')); void q.refetch() } }} /></div>}
      </Card>
      <QueryState q={q} what="(/reports)">
        {(rows) => rows.length === 0 ? <EmptyState title={t('reports.empty')} hint={t('reports.emptyHint')} action={<Link to="/studio/exercises">{t('journey.steps.exercises.title')}</Link>} /> : (
          <Table caption={t('reports.title')}>
            <THead><Tr><Th>{t('reports.reportTitle')}</Th><Th>{t('reports.origin')}</Th><Th>{t('reports.versions')}</Th><Th>{t('common.createdAt')}</Th></Tr></THead>
            <TBody>{rows.map((r) => <Tr key={r.id}><Td><Link to={`/reports/${r.id}`} className="font-medium">{r.title}</Link></Td><Td><OriginBanner r={r} /></Td><Td>{r.versions}</Td><Td>{fmtDateTime(r.created_at)}</Td></Tr>)}</TBody>
          </Table>
        )}
      </QueryState>
    </>
  )
}

function ReportDetail({ id }: { id: string }) {
  const { t } = useTranslation()
  const toast = useToast()
  const q = useApiQuery<Report>(keys.report(id), `/reports/${id}`)
  const [ver, setVer] = useState('')
  const [cmpA, setCmpA] = useState('')
  const [cmpB, setCmpB] = useState('')
  const versions = q.data?.version_list ?? []
  const cur = ver || versions[0]?.id || ''
  const v = useApiQuery<ReportVersion>(keys.reportVersion(cur), cur ? `/report-versions/${cur}` : null)
  const cmp = useApiQuery<ReportCompare>(['report-compare', id, cmpA, cmpB], cmpA && cmpB ? `/reports/${id}/compare` : null, { query: { a: cmpA, b: cmpB } })
  const publish = useApiMutation(() => api.post(`/report-versions/${cur}/publish`), { invalidate: [keys.report(id), keys.reportVersion(cur)], onSuccess: () => toast.push(t('reports.published')), onError: (e) => toast.push(errorMessage(e, t), 'danger') })
  const [f, setF] = useState({ title: '', body: '', code_hint: '', source_page: '' })
  const addFinding = useApiMutation(() => api.post(`/reports/${id}/findings`, { title: f.title, body: f.body, code_hint: f.code_hint || null, source_page: f.source_page ? Number(f.source_page) : null }), {
    invalidate: [keys.report(id)], onSuccess: () => setF({ title: '', body: '', code_hint: '', source_page: '' }), onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  return (
    <QueryState q={q} what="(/reports)">
      {(r) => (
        <>
          <p className="mb-1 text-sm"><Link to="/reports">← {t('reports.title')}</Link></p>
          <PageHeader title={r.title} actions={<OriginBanner r={r} />} description={`${t('reports.confidentiality')}: ${r.confidentiality}`} />
          {r.kind === 'imported' && <p role="note" className="mb-3 rounded border-2 border-warn bg-warnsoft p-2 text-sm font-semibold text-warn">{t('reports.priorBanner')}</p>}
          {r.document && (
            <p className="mb-3 text-sm">{r.document.filename} ({fmtBytes(r.document.bytes)}) <Mono>{(r.document.sha256 ?? '').slice(0, 16)}</Mono>{' '}
              <Button size="sm" onClick={() => void api.download(`/reports/${r.id}/document`, r.document?.filename ?? 'report').catch((e) => toast.push(errorMessage(e, t), 'danger'))}>{t('reports.downloadOriginal')}</Button></p>
          )}
          {r.kind === 'imported' ? (
            <Section title={t('reports.findings')}>
              <p className="mb-2 text-sm text-muted">{t('reports.findingsHint')}</p>
              {(r.findings ?? []).length === 0 ? <p className="mb-2 text-sm text-muted">{t('reports.noFindings')}</p> : (
                <Table caption={t('reports.findings')} className="mb-3">
                  <THead><Tr><Th>{t('reports.findingTitle')}</Th><Th>{t('gaps.code')}</Th><Th>{t('kb.page')}</Th><Th>{t('common.status')}</Th></Tr></THead>
                  <TBody>{r.findings!.map((x) => <Tr key={x.id}><Td><strong>{x.title}</strong><div className="text-xs text-muted">{x.body}</div></Td><Td>{x.code_hint ?? '—'}</Td><Td>{x.source_page ?? '—'}</Td><Td><StatusBadge status={x.status} /></Td></Tr>)}</TBody>
                </Table>
              )}
              <form className="grid gap-2 sm:grid-cols-2" onSubmit={(e) => { e.preventDefault(); if (f.title.trim()) addFinding.mutate(undefined) }}>
                <Field label={t('reports.findingTitle')} className="sm:col-span-2"><Input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></Field>
                <Field label={t('reports.findingText')} className="sm:col-span-2"><Textarea rows={2} value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })} /></Field>
                <Field label={t('gaps.code')}><Input value={f.code_hint} onChange={(e) => setF({ ...f, code_hint: e.target.value })} /></Field>
                <Field label={t('kb.page')}><Input type="number" min={1} value={f.source_page} onChange={(e) => setF({ ...f, source_page: e.target.value })} /></Field>
                <div><Button type="submit" loading={addFinding.isPending}>{t('reports.addFinding')}</Button></div>
              </form>
            </Section>
          ) : (
            <>
              <Section title={t('reports.versions')}>
                {versions.length === 0 ? <p className="text-sm text-muted">{t('reports.noVersions')}</p> : (
                  <Table caption={t('reports.versions')}>
                    <THead><Tr><Th>#</Th><Th>{t('common.status')}</Th><Th>{t('common.createdAt')}</Th><Th>{t('reports.ledgerHead')}</Th><Th><span className="sr-only">{t('common.actions')}</span></Th></Tr></THead>
                    <TBody>{versions.map((x) => <Tr key={x.id} className={x.id === cur ? 'bg-brandsoft' : ''}><Td>v{x.version_no}</Td><Td><StatusBadge status={x.status} /></Td><Td>{fmtDateTime(x.created_at)}</Td><Td className="text-xs">{x.ledger_head_seq !== null ? `#${x.ledger_head_seq}` : '—'}</Td><Td><Button size="sm" aria-pressed={x.id === cur} onClick={() => setVer(x.id)}>{t('reports.open')}</Button></Td></Tr>)}</TBody>
                  </Table>
                )}
              </Section>
              {cur && (
                <Section title={t('reports.selected')}>
                  <QueryState q={v} what="(/report-versions)">
                    {(rv) => (
                      <Card>
                        <div className="mb-3 flex flex-wrap items-center gap-2">
                          <StatusBadge status={rv.status} />
                          {rv.status !== 'published' && <Button variant="primary" loading={publish.isPending} onClick={() => publish.mutate(undefined)}>{t('reports.publish')}</Button>}
                          {FORMATS.map((fm) => <Button key={fm} onClick={() => void api.download(`/report-versions/${rv.id}/artifacts/${fm}`, `report-v${rv.version_no}.${fm}`).catch((e) => toast.push(errorMessage(e, t), 'danger'))}>{t('reports.download', { fmt: fm.toUpperCase() })}</Button>)}
                        </div>
                        <p className="mb-2 text-xs text-muted">{t('reports.ledgerHead')}: #{rv.ledger_head_seq ?? '—'} <Mono>{(rv.ledger_head_hash ?? '').slice(0, 16)}</Mono> · {t('reports.contentHash')}: <Mono>{rv.content_sha256.slice(0, 16)}</Mono> · {rv.artifacts.map((a) => `${a.format} ${fmtBytes(a.bytes)}`).join(', ')}</p>
                        <details open><summary className="cursor-pointer text-sm font-medium">{t('reports.content')}</summary><pre className="mt-2 max-h-96 overflow-auto rounded bg-surface2 p-2 text-xs whitespace-pre-wrap">{JSON.stringify(rv.content ?? {}, null, 2)}</pre></details>
                      </Card>
                    )}
                  </QueryState>
                </Section>
              )}
              {versions.length > 1 && (
                <Section title={t('reports.compare')}>
                  <div className="mb-2 flex flex-wrap gap-3">
                    <Field label={t('gaps.exerciseA')}><Select value={cmpA} onChange={(e) => setCmpA(e.target.value)}><option value="">—</option>{versions.map((x) => <option key={x.id} value={x.id}>v{x.version_no}</option>)}</Select></Field>
                    <Field label={t('gaps.exerciseB')}><Select value={cmpB} onChange={(e) => setCmpB(e.target.value)}><option value="">—</option>{versions.map((x) => <option key={x.id} value={x.id}>v{x.version_no}</option>)}</Select></Field>
                  </div>
                  {cmpA && cmpB && <QueryState q={cmp} what="(/compare)">{(c) => <pre className="max-h-96 overflow-auto rounded bg-surface2 p-2 text-xs whitespace-pre-wrap">{JSON.stringify(c.diff, null, 2)}</pre>}</QueryState>}
                </Section>
              )}
            </>
          )}
        </>
      )}
    </QueryState>
  )
}
