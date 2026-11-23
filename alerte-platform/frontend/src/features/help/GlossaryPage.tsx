import { useTranslation } from 'react-i18next'
import { PageHeader } from '@/components/ui'

const TERMS = ['workspace', 'knowledgeBase', 'chunk', 'mandate', 'registry', 'agent', 'accessMapping', 'scenario', 'inject', 'seat',
  'readiness', 'exercise', 'gap', 'ledger', 'replay', 'scripted']

export function GlossaryPage() {
  const { t } = useTranslation()
  return (
    <>
      <PageHeader title={t('glossary.title')} description={t('glossary.description')} />
      <dl className="grid max-w-3xl gap-4">
        {TERMS.map((k) => (
          <div key={k} id={k} className="rounded-md border border-line bg-surface p-3">
            <dt className="font-semibold">{t(`glossary.terms.${k}.name`)}</dt>
            <dd className="mt-1 text-sm text-muted">{t(`glossary.terms.${k}.def`)}</dd>
          </div>
        ))}
      </dl>
    </>
  )
}
