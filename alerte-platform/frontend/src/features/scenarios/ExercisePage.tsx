import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { Agent, Inject, Institution, SeatIn } from '@/api/types'
import type { CommandResult, Exercise, InviteResult, Readiness } from '@/api/loose'
import { NoAiBanner } from '@/app/AppShell'
import { Badge, Button, Card, Input, OneTimeSecret, PageHeader, QueryState, Section, Select, StatusBadge, Table, TBody, Td, Th, THead, Tr, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'

type SeatRow = { code: string; institution_id: string; agent_id: string; controller: 'agent' | 'human' | 'scripted'; human_name: string }

export function ExercisePage() {
  const { exerciseId = '' } = useParams()
  const q = useApiQuery<Exercise>(keys.exercise(exerciseId), `/exercises/${exerciseId}`)
  return (
    <QueryState q={q} what="(/exercises)">
      {(ex) => <ExerciseView ex={ex} />}
    </QueryState>
  )
}

function ExerciseView({ ex }: { ex: Exercise }) {
  const { t } = useTranslation()
  const toast = useToast()
  const navigate = useNavigate()
  const editable = ex.state === 'draft' || ex.state === 'ready'
  const insts = useApiQuery<Institution[]>(keys.institutions(undefined, false), '/institutions')
  const agents = useApiQuery<Agent[]>(keys.agents(false), '/agents')
  const injects = useApiQuery<Inject[]>(keys.injects(ex.scenario_id), `/scenarios/${ex.scenario_id}/injects`)
  const readiness = useApiQuery<Readiness>(keys.readiness(ex.id), editable ? `/exercises/${ex.id}/readiness` : null)
  const [rows, setRows] = useState<SeatRow[]>(() => (ex.seats ?? []).map((s) => ({ code: s.code, institution_id: s.institution_id, agent_id: s.agent_id ?? '', controller: s.controller as SeatRow['controller'], human_name: s.human_name ?? '' })))
  const [dirty, setDirty] = useState(false)
  const [invite, setInvite] = useState<InviteResult | null>(null)
  const refresh = [keys.exercise(ex.id), keys.readiness(ex.id), ['exercises']] as const

  const saveSeats = useApiMutation(() => api.put(`/exercises/${ex.id}/seats`, { seats: rows.map((r) => ({ code: r.code, institution_id: r.institution_id, agent_id: r.agent_id || null, controller: r.controller, human_name: r.controller === 'human' ? r.human_name || null : null }) satisfies SeatIn) }), {
    invalidate: refresh, onSuccess: () => { setDirty(false); toast.push(t('common.saved')) }, onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const inviteM = useApiMutation((code: string) => api.post<InviteResult>(`/exercises/${ex.id}/seats/${encodeURIComponent(code)}/invite`, {}), { onSuccess: setInvite, onError: (e) => toast.push(errorMessage(e, t), 'danger') })
  const markReady = useApiMutation(() => api.post(`/exercises/${ex.id}/ready`), { invalidate: refresh, onSuccess: () => toast.push(t('exercises.markedReady')), onError: (e) => toast.push(errorMessage(e, t), 'danger') })
  const start = useApiMutation(() => api.post<CommandResult>(`/exercises/${ex.id}/commands`, { kind: 'start' }), {
    invalidate: refresh, onSuccess: () => navigate(`/room/${ex.id}`), onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const del = useApiMutation(() => api.delete(`/exercises/${ex.id}`), { invalidate: [['exercises']], onSuccess: () => navigate('/studio/exercises'), onError: (e) => toast.push(errorMessage(e, t), 'danger') })

  const set = (i: number, patch: Partial<SeatRow>) => { setRows(rows.map((r, j) => (j === i ? { ...r, ...patch } : r))); setDirty(true) }
  const iname = (id: string) => insts.data?.find((x) => x.id === id)?.code ?? ''
  const addAllFromScenario = () => {
    const ids = [...new Set((injects.data ?? []).flatMap((i) => i.recipients))].filter((id) => !rows.some((r) => r.institution_id === id))
    const add = ids.map((id) => ({ code: iname(id) || id.slice(-6), institution_id: id, agent_id: agents.data?.find((a) => a.institution_id === id && !a.archived_at)?.id ?? '', controller: 'agent' as const, human_name: '' }))
    setRows([...rows, ...add]); setDirty(true)
  }
  const blocking = readiness.data?.blocking ?? []
  const warnings = readiness.data?.warnings ?? []

  return (
    <>
      <p className="mb-1 text-sm"><Link to="/studio/exercises">← {t('exercises.title')}</Link></p>
      <NoAiBanner aiMode={ex.ai_mode} />
      <PageHeader title={ex.title} description={`${ex.code} · ${t(`exercises.modes.${ex.ai_mode}`, ex.ai_mode)} · ${t('exercises.pace')}: ${ex.pace}`}
        actions={<>
          <StatusBadge status={ex.state} />
          {!editable && <Link to={`/room/${ex.id}`}>{t('exercises.openRoom')}</Link>}
          {ex.state === 'draft' && <Button variant="danger" onClick={() => del.mutate(undefined)}>{t('common.delete')}</Button>}
        </>} />
      <Section title={t('exercises.seats')}
        actions={editable && <div className="flex gap-2"><Button onClick={addAllFromScenario}>{t('exercises.addFromScenario')}</Button><Button onClick={() => { setRows([...rows, { code: '', institution_id: '', agent_id: '', controller: 'agent', human_name: '' }]); setDirty(true) }}>{t('exercises.addSeat')}</Button></div>}>
        <p className="mb-2 text-sm text-muted">{t('exercises.seatsHint')}</p>
        {rows.length === 0 ? <p className="text-sm text-muted">{t('exercises.noSeats')}</p> : (
          <Table caption={t('exercises.seats')}>
            <THead><Tr><Th>{t('common.code')}</Th><Th>{t('geo.institution')}</Th><Th>{t('exercises.controller')}</Th><Th>{t('agents.title')}</Th><Th>{t('exercises.humanName')}</Th><Th><span className="sr-only">{t('common.actions')}</span></Th></Tr></THead>
            <TBody>{rows.map((r, i) => (
              <Tr key={i}>
                <Td><Input aria-label={t('common.code')} disabled={!editable} value={r.code} onChange={(e) => set(i, { code: e.target.value })} className="!w-28" /></Td>
                <Td><Select aria-label={t('geo.institution')} disabled={!editable} value={r.institution_id} onChange={(e) => set(i, { institution_id: e.target.value, agent_id: agents.data?.find((a) => a.institution_id === e.target.value && !a.archived_at)?.id ?? '' })}><option value="">—</option>{insts.data?.map((x) => <option key={x.id} value={x.id}>{x.code}</option>)}</Select></Td>
                <Td><Select aria-label={t('exercises.controller')} disabled={!editable} value={r.controller} onChange={(e) => set(i, { controller: e.target.value as SeatRow['controller'] })}><option value="agent">{t('exercises.ctrl.agent')}</option><option value="human">{t('exercises.ctrl.human')}</option><option value="scripted">{t('exercises.ctrl.scripted')}</option></Select></Td>
                <Td><Select aria-label={t('agents.title')} disabled={!editable} value={r.agent_id} onChange={(e) => set(i, { agent_id: e.target.value })}><option value="">—</option>{agents.data?.filter((a) => !a.archived_at).map((a) => <option key={a.id} value={a.id}>{a.code}</option>)}</Select></Td>
                <Td>{r.controller === 'human' ? <Input aria-label={t('exercises.humanName')} disabled={!editable} value={r.human_name} onChange={(e) => set(i, { human_name: e.target.value })} /> : <span className="text-muted">—</span>}</Td>
                <Td><div className="flex gap-1">
                  {r.controller === 'human' && !dirty && !['completed', 'stopped', 'archived'].includes(ex.state) && <Button size="sm" onClick={() => inviteM.mutate(r.code)}>{t('exercises.seatLink')}</Button>}
                  {editable && <Button size="sm" onClick={() => { setRows(rows.filter((_, j) => j !== i)); setDirty(true) }}>{t('common.delete')}</Button>}
                </div></Td>
              </Tr>
            ))}</TBody>
          </Table>
        )}
        {editable && <div className="mt-3"><Button variant="primary" disabled={!dirty} loading={saveSeats.isPending} onClick={() => saveSeats.mutate(undefined)}>{t('exercises.saveSeats')}</Button></div>}
        {invite && <div className="mt-3"><OneTimeSecret value={`${window.location.origin}${invite.link}`} title={t('exercises.seatLinkFor', { seat: invite.seat, name: invite.human_name })}><span className="text-xs text-muted">{t('exercises.seatLinkHint')}</span></OneTimeSecret></div>}
      </Section>
      {editable && (
        <Section title={t('exercises.readiness')}>
          <QueryState q={readiness} what="(/readiness)">
            {(r) => (
              <Card aria-live="polite">
                <p className="mb-2"><Badge tone={r.ok ? 'ok' : 'danger'}>{r.ok ? t('exercises.readyToLaunch') : t('exercises.blocked', { n: blocking.length })}</Badge> {warnings.length > 0 && <Badge tone="warn">{t('exercises.nWarnings', { n: warnings.length })}</Badge>}</p>
                {blocking.length > 0 && <ul className="mb-2 flex flex-col gap-1 text-sm">{blocking.map((c, i) => <li key={i}><Badge tone="danger">{t('exercises.blockingLabel')}</Badge> {c.message}{c.subject ? ` (${c.subject})` : ''} <span className="font-mono text-xs text-muted">{c.code}</span></li>)}</ul>}
                {warnings.length > 0 && <ul className="mb-2 flex flex-col gap-1 text-sm">{warnings.map((c, i) => <li key={i}><Badge tone="warn">{t('scenarios.warning')}</Badge> {c.message}{c.subject ? ` (${c.subject})` : ''}</li>)}</ul>}
                <div className="flex flex-wrap gap-2">
                  <Button onClick={() => void readiness.refetch()}>{t('exercises.recheck')}</Button>
                  {ex.state === 'draft' && <Button disabled={!r.ok || dirty} loading={markReady.isPending} onClick={() => markReady.mutate(undefined)}>{t('exercises.markReady')}</Button>}
                  <Button variant="primary" disabled={ex.state !== 'ready' || dirty} loading={start.isPending} onClick={() => start.mutate(undefined)}>{t('exercises.launch')}</Button>
                </div>
                {ex.state === 'draft' && <p className="mt-2 text-xs text-muted">{t('exercises.launchHint')}</p>}
              </Card>
            )}
          </QueryState>
        </Section>
      )}
    </>
  )
}
