import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { FileSignature, ShieldCheck, TriangleAlert } from 'lucide-react'
import { api } from '@/api/client'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { ReformDraft } from '@/api/loose'
import { Badge, Button, Card, Section, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'

/** Dans le détail d'une lacune : faire rédiger un projet d'article par l'IA, puis ouvrir le document vérifiable. */
export function ReformSection({ gapId }: { gapId: string }) {
  const { t } = useTranslation()
  const toast = useToast()
  const key = ['reform-drafts', gapId]
  const list = useApiQuery<ReformDraft[]>(key, `/gaps/${gapId}/reform-drafts`)
  const gen = useApiMutation(() => api.post<ReformDraft>(`/gaps/${gapId}/reform-drafts`), {
    invalidate: [key], onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const drafts = list.data ?? []

  return (
    <Section title={t('reform.section')}>
      <p className="mb-2 text-xs text-muted">{t('reform.hint')}</p>
      <Button variant="primary" onClick={() => gen.mutate(undefined)} loading={gen.isPending} icon={<FileSignature className="h-4 w-4" aria-hidden />}>
        {gen.isPending ? t('reform.working') : t('reform.generate')}
      </Button>
      {drafts.length === 0 && !gen.isPending && <p className="mt-2 text-sm text-muted">{t('reform.none')}</p>}
      <div className="mt-3 flex flex-col gap-3">
        {drafts.map((d) => <DraftCard key={d.id} d={d} />)}
      </div>
    </Section>
  )
}

export function DraftStatus({ d }: { d: Pick<ReformDraft, 'verified' | 'content'> }) {
  const { t } = useTranslation()
  if (d.verified) return <Badge tone="ok"><ShieldCheck className="mr-1 inline h-3.5 w-3.5" aria-hidden />{t('reform.verified')}</Badge>
  if (d.content.citations.length === 0) return <Badge tone="danger"><TriangleAlert className="mr-1 inline h-3.5 w-3.5" aria-hidden />{t('reform.unsupported')}</Badge>
  return <Badge tone="warn">{t('reform.partial', { n: d.content.rejected_citations })}</Badge>
}

function DraftCard({ d }: { d: ReformDraft }) {
  const { t } = useTranslation()
  const c = d.content
  return (
    <Card className="text-sm">
      <p className="mb-1 flex flex-wrap items-center gap-2"><strong className="text-base">{c.title}</strong><DraftStatus d={d} /></p>
      <p className="mt-2"><strong>{c.article_label}</strong> — {c.article_text}</p>
      <p className="mt-2 text-muted"><strong>{t('reform.motives')} :</strong> {c.explanation}</p>
      {c.citations.length > 0 && (
        <ul className="mt-2 flex flex-col gap-1 text-xs">
          {c.citations.map((x) => <li key={x.chunk_id} className="rounded border border-line bg-surface2 p-1.5"><strong>{x.doc_code}{x.article ? ` · ${x.article}` : ''}</strong> — « {x.quote} »</li>)}
        </ul>
      )}
      <p className="mt-3 flex flex-wrap items-center gap-3">
        <Link to={`/verify/${d.sha256}`} className="font-semibold">{t('reform.open')}</Link>
        <Link to={`/verify/${d.sha256}?print=1`}>{t('reform.print')}</Link>
        <span className="font-mono text-xs text-muted">{d.sha256.slice(0, 16)}…</span>
      </p>
    </Card>
  )
}
