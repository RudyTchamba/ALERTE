import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { EvalMetric, EvaluationResult, Exercise, Kb, Scorecard } from '@/api/loose'
import type { Scenario } from '@/api/types'
import { Badge, Button, Card, Field, Input, PageHeader, QueryState, Section, Select, Table, TBody, Td, Th, THead, Tr, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { fmtPct } from '@/lib/format'
import { Radar } from './Radar'

const METRICS = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6'] as const

export function EvaluationPage() {
  const { t } = useTranslation()
  const exs = useApiQuery<Exercise[]>(keys.exercises(), '/exercises')
  const [ex, setEx] = useState('')
  return (
    <>
      <PageHeader title={t('evaluation.title')} description={t('evaluation.description')} />
      <Field label={t('gaps.exercise')} className="mb-4 w-80">
        <Select value={ex} onChange={(e) => setEx(e.target.value)}><option value="">—</option>{exs.data?.filter((x) => !['draft', 'ready'].includes(x.state)).map((x) => <option key={x.id} value={x.id}>{x.code} — {x.title}</option>)}</Select>
      </Field>
      {ex ? <><Metrics exerciseId={ex} exercises={exs.data ?? []} /><ScorecardView exerciseId={ex} /></> : <p className="text-sm text-muted">{t('evaluation.pick')}</p>}
    </>
  )
}

function fmtValue(m: EvalMetric, t: (k: string) => string): string {
  if (m.status !== 'computed' || m.value === null || m.value === undefined) return t('common.notComputed')
  if (m.metric === 'T6') return `${Math.round(m.value)} s`
  return fmtPct(m.value, 1)
}

function Metrics({ exerciseId, exercises }: { exerciseId: string; exercises: Exercise[] }) {
  const { t } = useTranslation()
  const toast = useToast()
  const q = useApiQuery<EvaluationResult>(keys.evaluation(exerciseId), `/evaluation/exercises/${exerciseId}`)
  const kbs = useApiQuery<Kb[]>(keys.kbs(false), '/knowledge-bases')
  const scenarios = useApiQuery<Scenario[]>(keys.scenarios, '/scenarios')
  const [kb, setKb] = useState('')
  const [code, setCode] = useState('')
  const [clones, setClones] = useState('')
  const run = useApiMutation((metric: string) => {
    const params = new URLSearchParams({ metric })
    if (metric === 'T1' && kb) params.append('kb_id', kb)
    if (metric === 'T3' && code) params.set('scenario_code', code)
    if (metric === 'T5') for (const c of clones.split(',').map((x) => x.trim()).filter(Boolean)) params.append('clone_id', c)
    return api.post(`/evaluation/exercises/${exerciseId}/run?${params.toString()}`)
  }, { invalidate: [keys.evaluation(exerciseId)], onSuccess: () => toast.push(t('evaluation.ran')), onError: (e) => toast.push(errorMessage(e, t), 'danger') })
  return (
    <Section title={t('evaluation.metrics')}>
      <QueryState q={q} what="(/evaluation)">
        {(r) => (
          <>
            <Table caption={t('evaluation.metrics')}>
              <THead><Tr><Th>{t('evaluation.metric')}</Th><Th>{t('evaluation.threshold')}</Th><Th>{t('evaluation.value')}</Th><Th>{t('common.status')}</Th><Th>{t('evaluation.source')}</Th><Th><span className="sr-only">{t('common.actions')}</span></Th></Tr></THead>
              <TBody>{METRICS.map((k) => {
                const m = r.metrics[k]
                if (!m) return null
                const computed = m.status === 'computed'
                const extra = Object.entries(m).filter(([key]) => !['metric', 'status', 'value', 'passed', 'reason', 'threshold', 'run_id', 'run_at'].includes(key))
                return (
                  <Tr key={k}>
                    <Td className="font-bold">{k}</Td><Td className="text-xs">{m.threshold?.label ?? '—'}</Td>
                    <Td className="text-lg font-semibold">{fmtValue(m, t)}</Td>
                    <Td>{!computed ? <Badge tone="neutral">{t('common.notComputed')}</Badge> : m.passed === null ? <Badge tone="info">{t('evaluation.noVerdict')}</Badge> : <Badge tone={m.passed ? 'ok' : 'danger'}>{m.passed ? t('evaluation.met') : t('evaluation.notMet')}</Badge>}</Td>
                    <Td className="max-w-sm text-xs">{m.reason && <p>{m.reason}</p>}{m.run_at && <p className="text-muted">{m.run_at}</p>}{extra.length > 0 && <details><summary className="cursor-pointer">{t('common.showDetails')}</summary><pre className="overflow-x-auto whitespace-pre-wrap">{JSON.stringify(Object.fromEntries(extra), null, 1)}</pre></details>}</Td>
                    <Td><Button size="sm" loading={run.isPending && run.variables === k} onClick={() => run.mutate(k)}>{computed ? t('evaluation.rerun') : t('evaluation.run')}</Button></Td>
                  </Tr>
                )
              })}</TBody>
            </Table>
            <Card className="mt-3">
              <p className="mb-2 text-sm font-medium">{t('evaluation.params')}</p>
              <div className="grid gap-3 sm:grid-cols-3">
                <Field label={t('evaluation.t1Kb')}><Select value={kb} onChange={(e) => setKb(e.target.value)}><option value="">—</option>{kbs.data?.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}</Select></Field>
                <Field label={t('evaluation.t3Scenario')}><Select value={code} onChange={(e) => setCode(e.target.value)}><option value="">—</option>{scenarios.data?.map((s) => <option key={s.id} value={s.code}>{s.code}</option>)}</Select></Field>
                <Field label={t('evaluation.t5Clones')} hint={exercises.filter((e) => e.parent_exercise_id === exerciseId).map((e) => e.id).join(', ') || undefined}><Input value={clones} onChange={(e) => setClones(e.target.value)} /></Field>
              </div>
            </Card>
          </>
        )}
      </QueryState>
    </Section>
  )
}

const ANSWERS = ['yes', 'partial', 'no', 'not_assessed'] as const

function ScorecardView({ exerciseId }: { exerciseId: string }) {
  const { t } = useTranslation()
  const toast = useToast()
  const q = useApiQuery<Scorecard>(keys.scorecard(exerciseId), `/scorecard/exercises/${exerciseId}`)
  const [edits, setEdits] = useState<Record<string, string>>({})
  const [reviewer, setReviewer] = useState('')
  const save = useApiMutation(() => api.put(`/scorecard/exercises/${exerciseId}`, { answers: Object.entries(edits).map(([criterion_id, answer]) => ({ criterion_id, answer })), reviewed_by: reviewer || null }), {
    invalidate: [keys.scorecard(exerciseId)], onSuccess: () => { setEdits({}); toast.push(t('common.saved')) }, onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const assess = useApiMutation(() => api.post(`/scorecard/exercises/${exerciseId}/assess`), { onError: (e) => toast.push(errorMessage(e, t), 'danger') })
  return (
    <Section title={t('evaluation.scorecard')} actions={<Button loading={assess.isPending} onClick={() => assess.mutate(undefined)}>{t('evaluation.llmJudge')}</Button>}>
      <p className="mb-2 text-sm text-muted">{t('evaluation.scorecardHint')}</p>
      <QueryState q={q} what="(/scorecard)">
        {(s) => (
          <>
            <p className="mb-3 flex flex-wrap items-center gap-2 text-sm" role="status">
              <Badge tone={s.overall_status === 'assessed' ? 'ok' : 'neutral'}>{s.overall_score === null ? t('common.notAssessed') : t('evaluation.overall', { score: s.overall_score.toFixed(2) })}</Badge>
              <span>{t('evaluation.assessedN', { n: s.dimensions_assessed, total: s.dimensions_total })}</span><span className="text-xs text-muted">{s.note}</span>
            </p>
            <div className="mb-4 flex justify-center"><Radar dims={s.dimensions.map((d) => ({ label: d.short_name ?? d.name, score: d.score }))} max={5} /></div>
            <Table caption={t('evaluation.scorecard')}>
              <THead><Tr><Th>#</Th><Th>{t('evaluation.dimension')}</Th><Th>{t('evaluation.score')}</Th><Th>{t('evaluation.criteria')}</Th></Tr></THead>
              <TBody>{s.dimensions.map((d) => (
                <Tr key={d.dimension_id}>
                  <Td>{d.number}</Td><Td className="font-medium">{d.name}{d.factor && <div className="text-xs text-muted">{d.factor}</div>}</Td>
                  <Td>{d.score === null ? <Badge tone="neutral">{t('common.notAssessed')}</Badge> : <strong>{d.score.toFixed(2)} / 5</strong>}<div className="text-xs text-muted">{d.assessed}/{d.total}</div></Td>
                  <Td><details><summary className="cursor-pointer text-sm">{t('evaluation.criteriaN', { n: d.criteria.length })}</summary>
                    <ul className="mt-2 flex flex-col gap-2">{d.criteria.map((c) => (
                      <li key={c.criterion_id} className="text-sm"><label className="block" htmlFor={`c-${c.criterion_id}`}>{c.text}</label>
                        <Select id={`c-${c.criterion_id}`} className="!w-auto" value={edits[c.criterion_id] ?? c.answer} onChange={(e) => setEdits({ ...edits, [c.criterion_id]: e.target.value })}>{ANSWERS.map((a) => <option key={a} value={a}>{t(`evaluation.answers.${a}`)}</option>)}</Select>
                        {c.assessor && <span className="ml-2 text-xs text-muted">{c.assessor}</span>}</li>
                    ))}</ul></details></Td>
                </Tr>
              ))}</TBody>
            </Table>
            <div className="mt-3 flex flex-wrap items-end gap-2"><Field label={t('evaluation.reviewedBy')}><Input value={reviewer} onChange={(e) => setReviewer(e.target.value)} /></Field>
              <Button variant="primary" disabled={!Object.keys(edits).length} loading={save.isPending} onClick={() => save.mutate(undefined)}>{t('evaluation.saveAnswers', { n: Object.keys(edits).length })}</Button></div>
          </>
        )}
      </QueryState>
    </Section>
  )
}
