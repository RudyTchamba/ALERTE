import { Prereq } from '@/components/Prereq'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { keys } from '@/api/keys'
import { useApiQuery } from '@/api/hooks'
import type { Exercise } from '@/api/loose'
import { EmptyState, PageHeader, QueryState, StatusBadge, Table, TBody, Td, Th, THead, Tr } from '@/components/ui'

/** Exercise picker shared by Room and Audit entry routes. */
export function ExercisePicker({ base, title }: { base: string; title: string }) {
  const { t } = useTranslation()
  const q = useApiQuery<Exercise[]>(keys.exercises(), '/exercises')
  return (
    <>
      <PageHeader title={title} description={t('room.pick')} />
      <Prereq page="room" />
      <QueryState q={q} what="(/exercises)">
        {(rows) => {
          const started = rows.filter((e) => e.state !== 'draft' && e.state !== 'ready')
          return started.length === 0 ? <EmptyState title={t('room.noStarted')} hint={t('room.noStartedHint')} action={<Link to="/studio/exercises">{t('journey.steps.exercises.title')}</Link>} /> : (
            <Table caption={title}>
              <THead><Tr><Th>{t('common.code')}</Th><Th>{t('home.exTitle')}</Th><Th>{t('common.status')}</Th></Tr></THead>
              <TBody>{started.map((e) => <Tr key={e.id}><Td className="font-mono">{e.code}</Td><Td><Link to={`${base}/${e.id}`}>{e.title}</Link></Td><Td><StatusBadge status={e.state} /></Td></Tr>)}</TBody>
            </Table>
          )
        }}
      </QueryState>
    </>
  )
}

export function RoomPickerPage() {
  const { t } = useTranslation()
  return <ExercisePicker base="/room" title={t('nav.room_live')} />
}
