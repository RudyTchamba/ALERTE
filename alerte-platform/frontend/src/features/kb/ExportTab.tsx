import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { DocList, ExportInfo, ExportStart } from '@/api/loose'
import { Badge, Button, Card, Checkbox, Field, Select, Stepper, StatusBadge, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { JobProgress } from './JobProgress'
import { ImportArchive } from './ImportArchive'

type Mode = 'full_reimportable' | 'processed_only' | 'documents_only' | 'selection' | 'open_publication'
const MODES: Mode[] = ['full_reimportable', 'processed_only', 'documents_only', 'selection', 'open_publication']

/** Export wizard: mode -> selection -> rights check -> progress -> download. */
export function ExportTab({ kbId }: { kbId: string }) {
  const { t } = useTranslation()
  const toast = useToast()
  const [step, setStep] = useState(0)
  const [mode, setMode] = useState<Mode>('full_reimportable')
  const [sel, setSel] = useState<Set<string>>(new Set())
  const [inc, setInc] = useState({ originals: true, embeddings: false, mandates: true, references: true })
  const [purpose, setPurpose] = useState<'private' | 'open_publication'>('private')
  const [restricted, setRestricted] = useState<string | null>(null)
  const [started, setStarted] = useState<ExportStart | null>(null)
  const [finished, setFinished] = useState(false)
  const docs = useApiQuery<DocList>(keys.kbDocs(kbId), `/knowledge-bases/${kbId}/documents`, { query: { limit: 200 } })
  const info = useApiQuery<ExportInfo>(keys.export(started?.export.id ?? ''), started && finished ? `/exports/${started.export.id}` : null)

  const start = useApiMutation(() => api.post<ExportStart>(`/knowledge-bases/${kbId}/exports`, {
    mode, purpose: mode === 'open_publication' ? 'open_publication' : purpose,
    document_ids: mode === 'selection' ? [...sel] : null, include: inc,
  }), {
    onSuccess: (r) => { setStarted(r); setFinished(false); setRestricted(null); setStep(3) },
    onError: (e) => {
      if (e instanceof ApiError && e.code === 'kb.export.restricted_documents') { setRestricted(JSON.stringify(e.details)); setStep(2) }
      toast.push(errorMessage(e, t), 'danger')
    },
  })
  const steps = [t('kb.export.mode'), t('kb.export.select'), t('kb.export.rights'), t('kb.export.progress')]
  const items = docs.data?.items ?? []
  const rights = (['allowed', 'restricted', 'unknown'] as const).map((r) => ({ r, n: items.filter((d) => (d.redistribution ?? 'unknown') === r).length }))

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <h3 className="mb-2 font-semibold">{t('kb.export.title')}</h3>
        <Stepper steps={steps} current={step} />
        {step === 0 && (
          <div className="flex flex-col gap-3">
            <Field label={t('kb.export.mode')} hint={t(`kb.export.modes.${mode}`)}>
              <Select value={mode} onChange={(e) => setMode(e.target.value as Mode)}>{MODES.map((m) => <option key={m} value={m}>{t(`kb.export.modeNames.${m}`)}</option>)}</Select>
            </Field>
            <fieldset className="flex flex-wrap gap-4"><legend className="mb-1 text-sm font-medium">{t('kb.export.include')}</legend>
              {(['originals', 'embeddings', 'mandates', 'references'] as const).map((k) => <Checkbox key={k} label={t(`kb.export.inc.${k}`)} checked={inc[k]} onChange={(e) => setInc({ ...inc, [k]: e.target.checked })} />)}
            </fieldset>
            <div><Button variant="primary" onClick={() => setStep(1)}>{t('common.next')}</Button></div>
          </div>
        )}
        {step === 1 && (
          <div>
            {mode === 'selection' ? (
              <fieldset><legend className="mb-1 text-sm font-medium">{t('kb.export.pickDocs')}</legend>
                <ul className="mb-3 max-h-60 overflow-y-auto">{items.map((d) => (
                  <li key={d.id}><Checkbox label={`${d.code} — ${d.title}`} checked={sel.has(d.id)} onChange={(e) => { const n = new Set(sel); if (e.target.checked) n.add(d.id); else n.delete(d.id); setSel(n) }} /></li>
                ))}</ul>
              </fieldset>
            ) : <p className="mb-3 text-sm">{t('kb.export.allDocs', { n: items.length })}</p>}
            <div className="flex gap-2"><Button onClick={() => setStep(0)}>{t('common.back')}</Button><Button variant="primary" disabled={mode === 'selection' && sel.size === 0} onClick={() => setStep(2)}>{t('common.next')}</Button></div>
          </div>
        )}
        {step === 2 && (
          <div>
            <p className="mb-2 text-sm">{t('kb.export.rightsHint')}</p>
            <ul className="mb-3 flex flex-wrap gap-2">{rights.map(({ r, n }) => <li key={r}><Badge tone={r === 'allowed' ? 'ok' : r === 'restricted' ? 'danger' : 'warn'}>{r}: {n}</Badge></li>)}</ul>
            {mode !== 'open_publication' && (
              <Field label={t('kb.export.purpose')}><Select value={purpose} onChange={(e) => setPurpose(e.target.value as 'private' | 'open_publication')}><option value="private">{t('kb.export.private')}</option><option value="open_publication">{t('kb.export.open')}</option></Select></Field>
            )}
            {restricted && <p role="alert" className="mt-2 rounded border border-danger bg-dangersoft p-2 text-sm text-danger">{t('errors.kb.export.restricted_documents')} <code className="text-xs">{restricted}</code></p>}
            <div className="mt-3 flex gap-2"><Button onClick={() => setStep(1)}>{t('common.back')}</Button><Button variant="primary" loading={start.isPending} onClick={() => start.mutate(undefined)}>{t('kb.export.start')}</Button></div>
          </div>
        )}
        {step === 3 && started && (
          <div className="flex flex-col gap-3">
            {started.warnings.length > 0 && <ul className="list-disc pl-5 text-sm text-warn">{started.warnings.map((w, i) => <li key={i}>{typeof w === 'string' ? w : JSON.stringify(w)}</li>)}</ul>}
            <JobProgress jobId={started.job.id} label={t('kb.export.running')} onFinished={(s) => setFinished(s.status === 'done')} />
            {info.data && (
              <div className="flex flex-wrap items-center gap-3">
                <StatusBadge status={info.data.status} />
                {info.data.status === 'done' || info.data.filename
                  ? <Button variant="primary" onClick={() => void api.download(`/exports/${info.data!.id}/download`, info.data!.filename ?? 'kb-export.zip').catch((e) => toast.push(errorMessage(e, t), 'danger'))}>{t('common.download')} {info.data.filename}</Button>
                  : null}
              </div>
            )}
            <div><Button onClick={() => { setStep(0); setStarted(null) }}>{t('kb.export.again')}</Button></div>
          </div>
        )}
      </Card>
      <ImportArchive kbId={kbId} />
    </div>
  )
}
