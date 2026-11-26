import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, XCircle } from 'lucide-react'
import { api } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { CoherenceReport, JobRef, Kb, KbStatus } from '@/api/loose'
import { Badge, Button, ConfirmDialog, KeyValue, Mono, QueryState, Section, StatusBadge, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { fmtDateTime } from '@/lib/format'
import { JobProgress } from './JobProgress'

type Step = 'process' | 'embed' | 'index'
interface Action { id: string; steps: Step[]; reembed?: boolean; danger?: boolean }

/** The scope of every action here is THIS base. There is deliberately no "build everything" button. */
const ACTIONS: Action[] = [
  { id: 'process', steps: ['process'] },
  { id: 'embed', steps: ['embed'] },
  { id: 'index', steps: ['index'] },
  { id: 'all', steps: ['process', 'embed', 'index'] },
  { id: 'reembed', steps: ['process', 'embed', 'index'], reembed: true, danger: true },
]

export function BuildTab({ kb, archived }: { kb: Kb; archived: boolean }) {
  const { t } = useTranslation()
  const toast = useToast()
  const qc = useQueryClient()
  const kbId = kb.id
  const st = useApiQuery<KbStatus>(['kb-status', kbId], `/knowledge-bases/${kbId}/status`, { refetchInterval: 5000 })
  const [check, setCheck] = useState<CoherenceReport | null>(null)
  const [confirm, setConfirm] = useState<Action | null>(null)
  const [jobs, setJobs] = useState<{ id: string; label: string }[]>([])
  const [note, setNote] = useState('')
  const refresh = () => {
    for (const k of [['kb-status', kbId], keys.kbDocs(kbId), keys.kb(kbId), keys.kbQuality(kbId), keys.kbVersions(kbId)]) void qc.invalidateQueries({ queryKey: k })
  }
  const build = useApiMutation((a: Action) => api.post<{ job: JobRef }>(`/knowledge-bases/${kbId}/build`, { steps: a.steps, reembed: !!a.reembed }).then((r) => ({ r, a })), {
    onSuccess: ({ r, a }) => { setJobs((j) => [...j, { id: r.job.id, label: t(`kb.build.${a.id}`) }]); setConfirm(null) },
    onError: (e) => { setConfirm(null); toast.push(errorMessage(e, t), 'danger') },
  })
  const verify = useApiMutation(() => api.get<CoherenceReport>(`/knowledge-bases/${kbId}/check`), { onSuccess: setCheck, onError: (e) => toast.push(errorMessage(e, t), 'danger') })
  const vectorsIncomplete = !!st.data && st.data.chunks > 0 && !st.data.embeddings.complete
  const publish = useApiMutation(() => api.post(`/knowledge-bases/${kbId}/publish`, { note: note || null }), {
    invalidate: [keys.kbVersions(kbId), keys.kb(kbId), ['kbs'], ['kb-status', kbId]], onSuccess: () => { setNote(''); toast.push(t('kb.publishedToast')) },
    onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })

  return (
    <div>
      <p className="mb-3 rounded border border-line p-2 text-sm" data-testid="build-scope">{t('kb.build.scope', { code: kb.code, name: kb.name })} — <Mono>{kb.scope_path ?? kb.code}</Mono>. {t('kb.build.noGlobal')}</p>
      <QueryState q={st} what="(/status)">
        {(s) => (
          <>
            <Section title={t('kb.build.state')}>
              {s.chunks > 0 && !s.embeddings.complete && (
                <p role="alert" data-testid="vectors-incomplete" className="mb-3 rounded border border-danger p-2 text-sm text-danger">
                  {t('kb.build.vectorsIncomplete', { embedded: s.embeddings.embedded, chunks: s.embeddings.chunks })} {t('kb.build.vectorsBlocked')} {t('kb.build.vectorsRetry')}
                </p>
              )}
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <StatusBadge status={s.general_status} />
                {Object.entries(s.documents_by_state).map(([k, n]) => <span key={k} className="inline-flex items-center gap-1 text-sm"><StatusBadge status={k} /> ×{n}</span>)}
              </div>
              <KeyValue items={[
                [t('kb.docs'), `${s.documents} (${t('kb.build.ready')}: ${s.documents_ready}, ${t('kb.build.waiting')}: ${s.documents_waiting}, ${t('kb.build.failed')}: ${s.documents_failed})`],
                [t('kb.chunks'), s.chunks],
                [t('kb.embedded'), `${s.embeddings.embedded}/${s.embeddings.chunks}${s.embeddings.complete ? '' : ' ⚠'}`],
                [t('kb.embedder'), s.embeddings.embedder_key ?? <Badge tone="warn">{t('kb.noEmbedder')}</Badge>],
                [t('kb.build.lexical'), `${s.lexical_index.rows}/${s.lexical_index.chunks}`],
                [t('kb.build.vector'), <StatusBadge key="v" status={s.vector_index.status} />],
                [t('kb.build.activeVersion'), s.active_version ? `v${s.active_version} (${fmtDateTime(s.last_build_at)})` : <Badge key="u" tone="warn">{t('kb.unpublished')}</Badge>],
              ]} />
            </Section>
            <Section title={t('kb.build.actions')} className="mt-4">
              <p className="mb-2 text-sm text-muted">{t('kb.build.incremental')}</p>
              <div className="flex flex-wrap gap-2">
                {ACTIONS.map((a) => (
                  <Button key={a.id} variant={a.id === 'all' ? 'primary' : a.danger ? 'danger' : 'secondary'} disabled={archived || build.isPending} onClick={() => setConfirm(a)}>
                    {t(`kb.build.${a.id}`)} ({kb.code})
                  </Button>
                ))}
                <Button loading={verify.isPending} onClick={() => verify.mutate(undefined)}>{t('kb.build.check')} ({kb.code})</Button>
              </div>
              <ul className="mt-3 flex flex-col gap-2" aria-live="polite">{jobs.map((j) => <li key={j.id}><JobProgress jobId={j.id} label={j.label} onFinished={refresh} /></li>)}</ul>
            </Section>
          </>
        )}
      </QueryState>
      {check && (
        <Section title={t('kb.build.checkResult')} className="mt-4">
          <p className="mb-2" role="status">{check.ok ? <Badge tone="ok">{t('kb.build.coherent')}</Badge> : <Badge tone="danger">{t('kb.build.incoherent')}</Badge>}</p>
          <ul className="flex flex-col gap-1 text-sm">{check.checks.map((c) => (
            <li key={c.id} className="flex items-start gap-2">
              {c.ok ? <CheckCircle2 className="mt-0.5 h-4 w-4 text-ok" aria-label={t('common.enums.ok', { defaultValue: 'ok' })} /> : <XCircle className="mt-0.5 h-4 w-4 text-danger" aria-label="ko" />}
              <span><Mono>{c.id}</Mono> — {c.detail}</span>
            </li>
          ))}</ul>
        </Section>
      )}
      <Section title={t('kb.build.publishTitle')} className="mt-4">
        <p className="mb-2 text-sm text-muted">{t('kb.build.publishHint', { code: kb.code })}</p>
        {vectorsIncomplete && <p className="mb-2 text-sm text-danger" data-testid="publish-blocked">{t('kb.build.vectorsBlocked')}</p>}
        <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => { e.preventDefault(); publish.mutate(undefined) }}>
          <label className="flex min-w-64 flex-col text-sm font-medium">{t('kb.versionNote')}
            <input className="mt-1 rounded border border-line bg-surface px-2 py-1 font-normal" value={note} onChange={(e) => setNote(e.target.value)} /></label>
          <Button type="submit" variant="primary" disabled={archived || vectorsIncomplete} loading={publish.isPending}>{t('kb.build.publish', { code: kb.code })}</Button>
        </form>
      </Section>
      <ConfirmDialog open={!!confirm} onClose={() => setConfirm(null)} danger={!!confirm?.danger} loading={build.isPending}
        title={confirm ? t(`kb.build.${confirm.id}`) : ''} message={confirm ? t(`kb.build.confirm.${confirm.id}`, { code: kb.code }) : ''}
        confirmLabel={t('kb.build.run', { code: kb.code })} onConfirm={() => confirm && build.mutate(confirm)} />
    </div>
  )
}
