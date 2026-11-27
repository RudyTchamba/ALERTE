import { Prereq } from '@/components/Prereq'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api, fieldErrors } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { Scenario } from '@/api/types'
import type { Exercise } from '@/api/loose'
import { Badge, Button, Dialog, EmptyState, Field, Input, PageHeader, QueryState, Select, StatusBadge, Table, TBody, Td, Th, THead, Tr, useToast } from '@/components/ui'
import { exercisePath } from '@/features/home/HomePage'
import { errorMessage } from '@/lib/errors'
import { fmtDateTime } from '@/lib/format'

export function ExercisesPage() {
  const { t } = useTranslation()
  const [creating, setCreating] = useState<{ from?: Exercise } | null>(null)
  const q = useApiQuery<Exercise[]>(keys.exercises(), '/exercises')
  return (
    <>
      <PageHeader title={t('exercises.title')} term="exercise" description={t('exercises.description')} actions={<Button variant="primary" onClick={() => setCreating({})}>{t('exercises.new')}</Button>} />
      <Prereq page="exercises" />
      <QueryState q={q} what="(/exercises)">
        {(rows) => rows.length === 0 ? <EmptyState title={t('home.noExercises')} hint={t('home.noExercisesHint')} action={<Link to="/studio/scenarios">{t('journey.steps.scenarios.title')}</Link>} /> : (
          <Table caption={t('exercises.title')}>
            <THead><Tr><Th>{t('common.code')}</Th><Th>{t('home.exTitle')}</Th><Th>{t('common.status')}</Th><Th>{t('home.mode')}</Th><Th>{t('home.started')}</Th><Th><span className="sr-only">{t('common.actions')}</span></Th></Tr></THead>
            <TBody>{rows.map((e) => (
              <Tr key={e.id}>
                <Td className="font-mono">{e.code}</Td><Td><Link to={`/studio/exercises/${e.id}`} className="font-medium">{e.title}</Link></Td>
                <Td><StatusBadge status={e.state} /></Td>
                <Td>{e.ai_mode === 'ai' ? <Badge tone="ok">AI</Badge> : <Badge tone="warn">{e.ai_mode === 'cassette' ? 'REPLAY' : t('common.noAiShort')}</Badge>}</Td>
                <Td>{fmtDateTime(e.started_at)}</Td>
                <Td><div className="flex gap-1"><Link to={exercisePath(e)}>{['draft', 'ready'].includes(e.state) ? t('exercises.prepare') : t('exercises.openRoom')}</Link>
                  <Button size="sm" onClick={() => setCreating({ from: e })}>{t('exercises.cloneRun')}</Button></div></Td>
              </Tr>
            ))}</TBody>
          </Table>
        )}
      </QueryState>
      {creating && <CreateExercise from={creating.from} onClose={() => setCreating(null)} />}
    </>
  )
}

function CreateExercise({ from, onClose }: { from?: Exercise; onClose: () => void }) {
  const { t } = useTranslation()
  const toast = useToast()
  const navigate = useNavigate()
  const scenarios = useApiQuery<Scenario[]>(keys.scenarios, '/scenarios')
  const [v, setV] = useState({ scenario_id: from?.scenario_id ?? '', title: from ? `${from.title} (re-run)` : '', ai_mode: from?.ai_mode ?? 'ai', pace: from?.pace ?? 'auto', max_llm_calls: '' })
  const [errs, setErrs] = useState<Record<string, string>>({})
  const create = useApiMutation(() => api.post<Exercise>(from ? `/exercises?from=${encodeURIComponent(from.id)}` : '/exercises', {
    scenario_id: v.scenario_id || null, title: v.title || null, ai_mode: v.ai_mode, pace: v.pace,
    settings: v.max_llm_calls ? { max_llm_calls: Number(v.max_llm_calls) } : null,
  }), {
    invalidate: [['exercises']], onSuccess: (e) => { toast.push(t('common.created')); navigate(`/studio/exercises/${e.id}`) },
    onError: (e) => { setErrs(fieldErrors(e)); toast.push(errorMessage(e, t), 'danger') },
  })
  return (
    <Dialog open onClose={onClose} title={from ? t('exercises.cloneRun') : t('exercises.new')}
      footer={<><Button onClick={onClose}>{t('common.cancel')}</Button><Button variant="primary" disabled={!from && !v.scenario_id} loading={create.isPending} onClick={() => create.mutate(undefined)}>{t('common.create')}</Button></>}>
      <div className="flex flex-col gap-3">
        {from && <p className="text-sm text-muted">{t('exercises.cloneHint')}</p>}
        <Field label={t('exercises.scenario')} required error={errs.scenario_id}>
          <Select data-autofocus value={v.scenario_id} onChange={(e) => setV({ ...v, scenario_id: e.target.value })}><option value="">—</option>{scenarios.data?.map((s) => <option key={s.id} value={s.id}>{s.code} — {s.title}</option>)}</Select>
        </Field>
        <Field label={t('home.exTitle')} error={errs.title}><Input value={v.title} onChange={(e) => setV({ ...v, title: e.target.value })} /></Field>
        <Field label={t('exercises.aiMode')} hint={t('exercises.aiModeHint')}>
          <Select value={v.ai_mode} onChange={(e) => setV({ ...v, ai_mode: e.target.value })}>
            <option value="ai">{t('exercises.modes.ai')}</option><option value="scripted">{t('exercises.modes.scripted')}</option><option value="cassette">{t('exercises.modes.cassette')}</option>
          </Select>
        </Field>
        <Field label={t('exercises.pace')}>
          <Select value={v.pace} onChange={(e) => setV({ ...v, pace: e.target.value })}><option value="manual">{t('exercises.paces.manual')}</option><option value="auto">{t('exercises.paces.auto')}</option><option value="auto_delay">{t('exercises.paces.auto_delay')}</option></Select>
        </Field>
        <Field label={t('exercises.budget')} hint={t('exercises.budgetHint')}><Input type="number" min={1} value={v.max_llm_calls} onChange={(e) => setV({ ...v, max_llm_calls: e.target.value })} /></Field>
      </div>
    </Dialog>
  )
}
