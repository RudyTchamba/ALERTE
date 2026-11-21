import { useTranslation } from 'react-i18next'
import { ExercisePicker } from '@/features/room/RoomPickerPage'

export function AuditPickerPage() {
  const { t } = useTranslation()
  return <ExercisePicker base="/audit" title={t('nav.audit')} />
}
