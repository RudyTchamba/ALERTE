import { useTranslation } from 'react-i18next'
import { useJob, type JobState } from '@/api/useJob'
import { ProgressBar } from '@/components/ui'

/** Progress of a background job, fed by its SSE stream. Announces completion/failure politely. */
export function JobProgress({ jobId, label, onFinished }: { jobId: string; label: string; onFinished?: (s: JobState) => void }) {
  const { t } = useTranslation()
  const s = useJob(jobId, onFinished)
  return (
    <div className="w-full">
      {s.status === 'failed' ? (
        <p role="alert" className="text-sm text-danger">{label}: {t('kb.jobFailed')} — {s.error}</p>
      ) : s.status === 'done' ? (
        <p role="status" className="text-sm text-ok">{label}: {t('kb.jobDone')}</p>
      ) : (
        <ProgressBar pct={s.pct} label={s.message ? `${label} — ${s.message}` : label} />
      )}
    </div>
  )
}
