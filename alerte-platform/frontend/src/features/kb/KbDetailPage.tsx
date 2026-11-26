import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { keys } from '@/api/keys'
import { useApiQuery } from '@/api/hooks'
import type { Kb } from '@/api/loose'
import { Badge, Card, PageHeader, QueryState, StatusBadge, Tabs } from '@/components/ui'
import { BuildTab } from './BuildTab'
import { DocumentsTab } from './DocumentsTab'
import { ExportTab } from './ExportTab'
import { QualityTab } from './QualityTab'
import { SearchTab } from './SearchTab'
import { VersionsTab } from './VersionsTab'

export function KbDetailPage() {
  const { t } = useTranslation()
  const { kbId = '' } = useParams()
  const [params] = useSearchParams()
  const [tab, setTab] = useState('documents')
  const q = useApiQuery<Kb>(keys.kb(kbId), `/knowledge-bases/${kbId}`)
  return (
    <QueryState q={q} what="(/knowledge-bases)">
      {(kb) => (
        <>
          <p className="mb-1 text-sm"><Link to="/studio/knowledge">← {t('kb.title')}</Link></p>
          <PageHeader title={kb.name} description={`${kb.code} — ${kb.scope_path ?? kb.code}${kb.description ? ` — ${kb.description}` : ''}`}
            actions={<>
              <StatusBadge status={kb.archived_at ? 'archived' : kb.status} />
              {kb.overview?.published_version_no ? <Badge tone="ok">v{kb.overview.published_version_no}</Badge> : <Badge tone="warn">{t('kb.unpublished')}</Badge>}
            </>} />
          {params.get('welcome') && (
            <Card className="mb-4" role="status">
              <p className="font-semibold">{t('kb.welcome.title')}</p>
              <ol className="list-decimal pl-5 text-sm"><li>{t('kb.welcome.upload')}</li><li>{t('kb.welcome.review')}</li><li>{t('kb.welcome.publish')}</li></ol>
            </Card>
          )}
          <Tabs label={kb.name} value={tab} onChange={setTab} tabs={[
            { id: 'documents', label: t('kb.documentsTab'), content: <DocumentsTab kb={kb} archived={!!kb.archived_at} /> },
            { id: 'build', label: t('kb.buildTab'), content: <BuildTab kb={kb} archived={!!kb.archived_at} /> },
            { id: 'quality', label: t('kb.qualityTab'), content: <QualityTab kbId={kb.id} /> },
            { id: 'versions', label: t('kb.versionsTab'), content: <VersionsTab kbId={kb.id} overview={kb.overview} archived={!!kb.archived_at} /> },
            { id: 'search', label: t('kb.searchTab'), content: <SearchTab kbId={kb.id} /> },
            { id: 'export', label: t('kb.exportTab'), content: <ExportTab kbId={kb.id} /> },
          ]} />
        </>
      )}
    </QueryState>
  )
}
