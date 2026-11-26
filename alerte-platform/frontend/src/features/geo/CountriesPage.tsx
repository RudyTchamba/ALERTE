import { useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { PageHeader, Tabs } from '@/components/ui'
import { CountriesTab } from './CountriesTab'
import { InstitutionsTab } from './InstitutionsTab'
import { MandatesTab } from './MandatesTab'

export function CountriesPage() {
  const { t } = useTranslation()
  const [params, setParams] = useSearchParams()
  const wanted = params.get('tab') ?? ''
  const tab = ['countries', 'institutions', 'mandates'].includes(wanted) ? wanted : 'countries'
  const setTab = (id: string) => setParams({ tab: id }, { replace: true })
  return (
    <>
      <PageHeader title={t('geo.title')} term="mandate" description={t('geo.description')} />
      <Tabs label={t('geo.title')} value={tab} onChange={setTab} tabs={[
        { id: 'countries', label: t('geo.countries'), content: <CountriesTab /> },
        { id: 'institutions', label: t('geo.institutions'), content: <InstitutionsTab /> },
        { id: 'mandates', label: t('geo.mandatesTab'), content: <MandatesTab /> },
      ]} />
    </>
  )
}
