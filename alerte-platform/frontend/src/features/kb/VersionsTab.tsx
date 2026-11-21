import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { JobRef, KbOverview, KbVersion } from '@/api/loose'
import { Badge, Button, EmptyState, Field, Input, KeyValue, Mono, QueryState, Section, Table, TBody, Td, Th, THead, Tr, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { fmtDateTime } from '@/lib/format'
import { JobProgress } from './JobProgress'

export function VersionsTab({ kbId, overview, archived }: { kbId: string; overview: KbOverview | undefined; archived: boolean }) {
  const { t } = useTranslation()
  const toast = useToast()
  const q = useApiQuery<KbVersion[]>(keys.kbVersions(kbId), `/knowledge-bases/${kbId}/versions`)
  const [note, setNote] = useState('')
  const [jobs, setJobs] = useState<{ id: string; label: string }[]>([])
  const publish = useApiMutation(() => api.post(`/knowledge-bases/${kbId}/publish`, { note: note || null }), {
    invalidate: [keys.kbVersions(kbId), keys.kb(kbId), ['kbs']], onSuccess: () => { setNote(''); toast.push(t('kb.publishedToast')) }, onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const job = (path: string, label: string) => api.post<{ job: JobRef }>(`/knowledge-bases/${kbId}/${path}`, {}).then((r) => { setJobs((j) => [...j, { id: r.job.id, label }]); return r })
  const reindex = useApiMutation(() => job('reindex', t('kb.reindex')), { onError: (e) => toast.push(errorMessage(e, t), 'danger') })
  const embed = useApiMutation(() => job('embed', t('kb.embed')), { onError: (e) => toast.push(errorMessage(e, t), 'danger') })
  return (
    <div>
      <Section title={t('kb.publishTitle')}>
        <p className="mb-2 text-sm text-muted">{t('kb.publishHint')}</p>
        <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => { e.preventDefault(); publish.mutate(undefined) }}>
          <Field label={t('kb.versionNote')} className="min-w-64"><Input value={note} onChange={(e) => setNote(e.target.value)} /></Field>
          <Button type="submit" variant="primary" disabled={archived} loading={publish.isPending}>{t('kb.publish')}</Button>
        </form>
      </Section>
      <Section title={t('kb.versions')}>
        <QueryState q={q} what="(/versions)">
          {(rows) => rows.length === 0 ? <EmptyState title={t('kb.noVersions')} hint={t('kb.noVersionsHint')} /> : (
            <Table caption={t('kb.versions')}>
              <THead><Tr><Th>#</Th><Th>{t('common.createdAt')}</Th><Th>{t('kb.versionNote')}</Th><Th>{t('kb.manifest')}</Th></Tr></THead>
              <TBody>{rows.map((v) => <Tr key={v.id}><Td>v{v.version_no}</Td><Td>{fmtDateTime(v.created_at)}</Td><Td>{v.note ?? '—'}</Td><Td><Mono>{v.manifest_sha256.slice(0, 16)}…</Mono></Td></Tr>)}</TBody>
            </Table>
          )}
        </QueryState>
      </Section>
      <Section title={t('kb.indexTitle')}>
        {overview && <KeyValue items={[
          [t('kb.chunks'), overview.chunks], [t('kb.embedded'), `${overview.embedded_chunks}/${overview.chunks}`],
          [t('kb.embedder'), overview.embedder_key ?? <Badge tone="warn">{t('kb.noEmbedder')}</Badge>],
        ]} />}
        <div className="mt-3 flex flex-wrap gap-2">
          <Button loading={reindex.isPending} disabled={archived} onClick={() => reindex.mutate(undefined)}>{t('kb.reindex')}</Button>
          <Button loading={embed.isPending} disabled={archived} onClick={() => embed.mutate(undefined)}>{t('kb.embed')}</Button>
        </div>
        <ul className="mt-3 flex flex-col gap-2" aria-live="polite">{jobs.map((j) => <li key={j.id}><JobProgress jobId={j.id} label={j.label} onFinished={() => void 0} /></li>)}</ul>
      </Section>
    </div>
  )
}
