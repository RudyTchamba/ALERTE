import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { ImportInfo, JobRef } from '@/api/loose'
import type { Kb } from '@/api/loose'
import { Badge, Button, Card, Field, Select, Input, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { JobProgress } from './JobProgress'

/** Archive import: upload -> validation job (dry run) -> report -> confirmation -> import job. */
export function ImportArchive({ kbId }: { kbId?: string }) {
  const { t } = useTranslation()
  const toast = useToast()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const file = useRef<HTMLInputElement>(null)
  const [imp, setImp] = useState<{ id: string; jobId: string } | null>(null)
  const [validated, setValidated] = useState(false)
  const [mode, setMode] = useState<'new_kb' | 'new_version'>('new_kb')
  const [target, setTarget] = useState(kbId ?? '')
  const [code, setCode] = useState('')
  const [confirmJob, setConfirmJob] = useState<string | null>(null)
  const kbs = useApiQuery<Kb[]>(keys.kbs(false), '/knowledge-bases')
  const info = useApiQuery<ImportInfo>(keys.import(imp?.id ?? ''), imp && validated ? `/imports/${imp.id}` : null)

  const start = useApiMutation((f: File) => { const fd = new FormData(); fd.append('file', f); return api.upload<{ job: JobRef; import: { id: string } }>('/knowledge-bases/import', fd) }, {
    onSuccess: (r) => { setImp({ id: r.import.id, jobId: r.job.id }); setValidated(false); setConfirmJob(null) },
    onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const confirm = useApiMutation(() => api.post<{ job: JobRef }>(`/imports/${imp!.id}/confirm`, { mode, target_kb_id: mode === 'new_version' ? target : undefined, code: code || undefined }), {
    onSuccess: (r) => setConfirmJob(r.job.id), onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const report = info.data?.report
  const errs = (report?.errors as unknown[] | undefined) ?? []
  const warns = (report?.warnings as unknown[] | undefined) ?? []
  const ok = info.data?.status === 'validated' && errs.length === 0
  const summary = report?.summary as { signature?: { valid: boolean; key_id: string | null } | null; signed_by_this_instance?: boolean } | undefined
  const msg = (e: unknown) => typeof e === 'string' ? e : ((e as { message?: string }).message ?? JSON.stringify(e))

  return (
    <Card>
      <h3 className="mb-1 font-semibold">{t('kb.importTitle')}</h3>
      <p className="mb-3 text-sm text-muted">{t('kb.importHint')}</p>
      <div className="flex flex-wrap items-center gap-2">
        <input ref={file} type="file" accept=".zip,application/zip" aria-label={t('kb.archiveFile')} />
        <Button loading={start.isPending} onClick={() => { const f = file.current?.files?.[0]; if (f) start.mutate(f) }}>{t('kb.validateArchive')}</Button>
      </div>
      {imp && <div className="mt-3"><JobProgress jobId={imp.jobId} label={t('kb.validating')} onFinished={(s) => { if (s.status === 'done') setValidated(true) }} /></div>}
      {info.data && (
        <div className="mt-3 text-sm" role="status">
          <p className="flex flex-wrap items-center gap-2 font-semibold">{ok ? t('kb.importValid') : t('kb.importInvalid')}
            {ok && (summary?.signature?.valid
              ? <Badge tone="ok">{summary.signed_by_this_instance ? t('kb.signedHere') : t('kb.signedOther', { key: summary.signature.key_id })}</Badge>
              : <Badge tone="warn">{t('kb.unsigned')}</Badge>)}</p>
          {errs.length > 0 && <ul className="list-disc pl-5 text-danger">{errs.map((e, i) => <li key={i}>{msg(e)}</li>)}</ul>}
          {warns.length > 0 && <ul className="list-disc pl-5 text-warn">{warns.map((e, i) => <li key={i}>{msg(e)}</li>)}</ul>}
          {ok && (
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              <Field label={t('kb.importMode')}>
                <Select value={mode} onChange={(e) => setMode(e.target.value as 'new_kb' | 'new_version')}>
                  <option value="new_kb">{t('kb.newKb')}</option><option value="new_version">{t('kb.newVersion')}</option>
                </Select>
              </Field>
              {mode === 'new_version'
                ? <Field label={t('kb.targetKb')}><Select value={target} onChange={(e) => setTarget(e.target.value)}><option value="">—</option>{kbs.data?.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}</Select></Field>
                : <Field label={t('kb.newCode')}><Input value={code} onChange={(e) => setCode(e.target.value)} /></Field>}
              <div className="flex items-end"><Button variant="primary" loading={confirm.isPending} disabled={mode === 'new_version' && !target} onClick={() => confirm.mutate(undefined)}>{t('kb.confirmImport')}</Button></div>
            </div>
          )}
        </div>
      )}
      {confirmJob && <div className="mt-3"><JobProgress jobId={confirmJob} label={t('kb.importing')} onFinished={(s) => {
        if (s.status === 'done') { void qc.invalidateQueries({ queryKey: ['kbs'] }); toast.push(t('kb.imported')); const r = s.result as { kb_id?: string } | undefined; if (r?.kb_id && !kbId) navigate(`/studio/knowledge/${r.kb_id}`) }
      }} /></div>}
    </Card>
  )
}
