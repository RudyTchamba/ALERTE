import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { PageHeader, Tabs } from '@/components/ui'
import { CountriesTab } from './CountriesTab'
import { InstitutionsTab } from './InstitutionsTab'
import { MandatesTab } from './MandatesTab'

export function CountriesPage() {
  const { t } = useTranslation()
  const [tab, setTab] = useState('countries')
  return (
    <>
      <PageHeader title={t('geo.title')} description={t('geo.description')} />
      <Tabs label={t('geo.title')} value={tab} onChange={setTab} tabs={[
        { id: 'countries', label: t('geo.countries'), content: <CountriesTab /> },
        { id: 'institutions', label: t('geo.institutions'), content: <InstitutionsTab /> },
        { id: 'mandates', label: t('geo.mandatesTab'), content: <MandatesTab /> },
      ]} />
    </>
  )
}
