import { useTranslation } from 'react-i18next'
import { useJob, type JobState } from '@/api/useJob'
import { ProgressBar } from '@/components/ui'

interface BuildOutcome { vectorization?: { status: string; embedded: number; chunks: number; error?: string | null } }

/** A finished build whose vectorization failed or stopped short is NOT a success, even though the job itself ended normally. */
function vecProblem(result: unknown) {
  const v = (result as BuildOutcome | null | undefined)?.vectorization
  return v && v.status !== 'complete' ? v : null
}

/** Progress of a background job, fed by its SSE stream. Announces completion/failure politely. */
export function JobProgress({ jobId, label, onFinished }: { jobId: string; label: string; onFinished?: (s: JobState) => void }) {
  const { t } = useTranslation()
  const s = useJob(jobId, onFinished)
  const vec = s.status === 'done' ? vecProblem(s.result) : null
  return (
    <div className="w-full">
      {s.status === 'failed' ? (
        <p role="alert" className="text-sm text-danger">{label}: {t('kb.jobFailed')} — {s.error}</p>
      ) : vec ? (
        <p role="alert" className="text-sm text-danger" data-testid="vectorization-failed">
          {label}: {t('kb.build.vectorsIncomplete', { embedded: vec.embedded, chunks: vec.chunks })}
          {vec.error ? ` — ${vec.error}` : ''} {t('kb.build.vectorsRetry')}
        </p>
      ) : s.status === 'done' ? (
        <p role="status" className="text-sm text-ok">{label}: {t('kb.jobDone')}</p>
      ) : (
        <ProgressBar pct={s.pct} label={s.message ? `${label} — ${s.message}` : label} />
      )}
    </div>
  )
}
