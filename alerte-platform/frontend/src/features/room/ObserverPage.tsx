import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiQuery } from '@/api/hooks'
import type { Exercise } from '@/api/loose'
import { FictionalBanner, NoAiBanner } from '@/app/AppShell'
import { Badge, ErrorState, LoadingState, StatusBadge } from '@/components/ui'
import { DecisionTraceDialog } from './DecisionTrace'
import { BoardPanel, SeatCards, SignalsPanel, Timeline } from './RoomPanels'
import type { DecisionItem } from './state'
import { useSeatToken } from './seatSession'
import { useExerciseStream } from './useExerciseStream'

/** Read-only view (observer token in the URL fragment). Visibility is enforced by the server according to the token. */
export function ObserverPage() {
  const { t } = useTranslation()
  const token = useSeatToken('alerte.observer_token')
  // The observer token is bound to one exercise: the list endpoint only returns that exercise.
  const ex = useApiQuery<Exercise[]>([...keys.exercises(), 'observer', token], token ? '/exercises' : null, { token })
  const exercise = ex.data?.[0]
  return (
    <div className="min-h-screen">
      <FictionalBanner />
      <main id="main" className="mx-auto max-w-7xl p-3 lg:p-6">
        {!token ? <p role="alert">{t('room.invalidLink')}</p> : ex.isPending ? <LoadingState /> : ex.isError ? <ErrorState error={ex.error} /> : !exercise ? <p role="alert">{t('room.invalidLink')}</p> : <ObserverView ex={exercise} token={token} />}
      </main>
    </div>
  )
}

function ObserverView({ ex, token }: { ex: Exercise; token: string }) {
  const { t } = useTranslation()
  const { state, status, seed } = useExerciseStream(ex.id, { authToken: token })
  const [trace, setTrace] = useState<DecisionItem | null>(null)
  useEffect(() => { void api; if (ex.seats) seed(ex.seats.map((s) => ({ code: s.code, controller: s.controller, human_name: s.human_name }))) }, [ex.seats, seed])
  const seats = useMemo(() => Object.values(state.seats).sort((a, b) => a.code.localeCompare(b.code)), [state.seats])
  return (
    <>
      <NoAiBanner aiMode={ex.ai_mode} />
      <h1 className="text-xl font-bold">{ex.title}</h1>
      <p className="mb-4 flex flex-wrap items-center gap-2 text-sm"><Badge tone="info">{t('room.readOnly')}</Badge><StatusBadge status={state.exerciseState ?? ex.state} /><span>{t('room.clock')}: <strong>{state.simTime ?? '—'}</strong></span><Badge tone={status === 'open' ? 'ok' : 'warn'}>{t(`room.stream.${status}`)}</Badge></p>
      <div className="grid gap-4 lg:grid-cols-[17rem_1fr]">
        <Timeline injects={state.injects} current={state.currentInject} />
        <div className="flex flex-col gap-6">
          <SeatCards seats={seats} decisions={state.decisions} onSeat={() => undefined} onDecision={setTrace} />
          <BoardPanel board={state.board} />
          <SignalsPanel signals={state.signals} canSeeAudit={false} />
        </div>
      </div>
      <p className="sr-only-live" aria-live="polite" role="log">{state.announcements.slice(-1)[0] ?? ''}</p>
      <DecisionTraceDialog decision={trace} events={state.events} onClose={() => setTrace(null)} />
    </>
  )
}
