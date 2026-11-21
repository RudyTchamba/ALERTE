import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowDown, ArrowUp } from 'lucide-react'
import { api } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { ActionItem, Inject, Institution, Scenario } from '@/api/types'
import type { FaultMode, LintReport } from '@/api/loose'
import { Badge, Button, Card, ConfirmDialog, Dialog, EmptyState, Field, Input, PageHeader, QueryState, Section, Select, Table, TBody, Td, Textarea, Th, THead, Tr, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { splitList } from '@/lib/lists'

const TAGS = ['life_risk', 'rights_risk', 'harm_possible', 'ai_output_used_in_decision', 'public_communication', 'channel_abuse', 'foreign_actor', 'time_critical']

export function ScenarioBuilderPage() {
  const { t } = useTranslation()
  const { scenarioId = '' } = useParams()
  const toast = useToast()
  const sc = useApiQuery<Scenario>(keys.scenario(scenarioId), `/scenarios/${scenarioId}`)
  const injects = useApiQuery<Inject[]>(keys.injects(scenarioId), `/scenarios/${scenarioId}/injects`)
  const insts = useApiQuery<Institution[]>(keys.institutions(undefined, false), '/institutions')
  const lint = useApiQuery<LintReport>(keys.lint(scenarioId), `/scenarios/${scenarioId}/lint`)
  const [editing, setEditing] = useState<Inject | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Inject | null>(null)
  const refresh = [keys.injects(scenarioId), keys.lint(scenarioId), keys.scenario(scenarioId)] as const
  const order = useApiMutation((ids: string[]) => api.put(`/scenarios/${scenarioId}/injects/order`, { inject_ids: ids }), { invalidate: refresh, onError: (e) => toast.push(errorMessage(e, t), 'danger') })
  const del = useApiMutation((i: Inject) => api.delete(`/injects/${i.id}`), { invalidate: refresh, onSuccess: () => setDeleting(null), onError: (e) => toast.push(errorMessage(e, t), 'danger') })
  const setStatus = useApiMutation((status: string) => api.patch(`/scenarios/${scenarioId}`, { status }), { invalidate: [keys.scenario(scenarioId), keys.scenarios], onSuccess: () => toast.push(t('common.saved')), onError: (e) => toast.push(errorMessage(e, t), 'danger') })
  const iname = (id: string) => insts.data?.find((i) => i.id === id)?.code ?? id.slice(-6)

  const move = (idx: number, dir: -1 | 1) => {
    const ids = injects.data?.map((i) => i.id) ?? []
    const j = idx + dir
    if (j < 0 || j >= ids.length) return
    ;[ids[idx], ids[j]] = [ids[j], ids[idx]]
    order.mutate(ids)
  }

  return (
    <QueryState q={sc} what="(/scenarios)">
      {(s) => (
        <>
          <p className="mb-1 text-sm"><Link to="/studio/scenarios">← {t('scenarios.title')}</Link></p>
          <PageHeader title={s.title} description={`${s.code} · ${s.language}`}
            actions={<>
              <Button onClick={() => void api.download(`/scenarios/${s.id}/export.yaml`, `${s.code}.yaml`).catch((e) => toast.push(errorMessage(e, t), 'danger'))}>{t('scenarios.exportYaml')}</Button>
              <Button onClick={() => setStatus.mutate(s.status === 'ready' ? 'draft' : 'ready')}>{s.status === 'ready' ? t('scenarios.markDraft') : t('scenarios.markReady')}</Button>
              <Button variant="primary" onClick={() => setEditing('new')}>{t('scenarios.addInject')}</Button>
            </>} />
          <div className="grid gap-6 xl:grid-cols-[1fr_22rem]">
            <div>
              <Section title={t('scenarios.injects')}>
                <QueryState q={injects} what="(/injects)">
                  {(rows) => rows.length === 0 ? <EmptyState title={t('scenarios.noInjects')} hint={t('scenarios.noInjectsHint')} /> : (
                    <ol className="flex flex-col gap-2">
                      {rows.map((i, idx) => (
                        <li key={i.id} className="rounded-md border border-line bg-surface p-3">
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div>
                              <p className="font-semibold">{i.seq}. <span className="font-mono text-sm text-muted">{i.sim_time}</span> — {i.title}</p>
                              <p className="text-sm text-muted">{t('scenarios.from')}: {i.from_actor || '—'} → {i.recipients.length ? i.recipients.map(iname).join(', ') : <Badge tone="danger">{t('scenarios.noRecipient')}</Badge>}</p>
                              <p className="mt-1 flex flex-wrap gap-1">
                                {i.fault_mode !== 'none' && <Badge tone="warn">{t('scenarios.fault')}: {i.fault_mode}</Badge>}
                                {i.tags.map((tg) => <Badge key={tg} tone="info">{tg}</Badge>)}
                                {i.demands.map((d) => <Badge key={d.action_code} tone={d.derivation === 'scenario_author' ? 'warn' : 'neutral'}>{t('scenarios.demand')}: {d.action_code}</Badge>)}
                              </p>
                              {i.warnings?.map((w) => <p key={w} className="text-xs text-warn">{w}</p>)}
                            </div>
                            <div className="flex gap-1">
                              <Button size="sm" aria-label={t('scenarios.moveUp', { title: i.title })} disabled={idx === 0 || order.isPending} onClick={() => move(idx, -1)}><ArrowUp className="h-4 w-4" aria-hidden /></Button>
                              <Button size="sm" aria-label={t('scenarios.moveDown', { title: i.title })} disabled={idx === rows.length - 1 || order.isPending} onClick={() => move(idx, 1)}><ArrowDown className="h-4 w-4" aria-hidden /></Button>
                              <Button size="sm" onClick={() => setEditing(i)}>{t('common.edit')}</Button>
                              <Button size="sm" variant="danger" onClick={() => setDeleting(i)}>{t('common.delete')}</Button>
                            </div>
                          </div>
                        </li>
                      ))}
                    </ol>
                  )}
                </QueryState>
              </Section>
              <Section title={t('scenarios.whoReceives')}>
                <p className="mb-2 text-sm text-muted">{t('scenarios.whoReceivesHint')}</p>
                <QueryState q={injects} what="(/injects)">
                  {(rows) => {
                    const ids = [...new Set(rows.flatMap((r) => r.recipients))]
                    if (!ids.length) return <EmptyState title={t('scenarios.noRecipient')} />
                    return (
                      <Table caption={t('scenarios.whoReceives')}>
                        <THead><Tr><Th>{t('scenarios.inject')}</Th>{ids.map((id) => <Th key={id} className="text-center">{iname(id)}</Th>)}</Tr></THead>
                        <TBody>{rows.map((r) => (
                          <Tr key={r.id}><th scope="row" className="px-3 py-2 text-left font-medium">{r.seq}. {r.title}</th>
                            {ids.map((id) => <Td key={id} className="text-center">{r.recipients.includes(id) ? <Badge tone="ok">{t('common.yes')}</Badge> : <span className="text-muted" aria-label={t('common.no')}>—</span>}</Td>)}</Tr>
                        ))}</TBody>
                      </Table>
                    )
                  }}
                </QueryState>
              </Section>
            </div>
            <aside aria-label={t('scenarios.lint')}>
              <Card>
                <h2 className="mb-2 font-semibold">{t('scenarios.lint')}</h2>
                <QueryState q={lint} what="(/lint)">
                  {(l) => (
                    <div aria-live="polite">
                      <p className="mb-2"><Badge tone={l.ok ? 'ok' : 'danger'}>{l.ok ? t('scenarios.lintOk') : t('scenarios.lintErrors')}</Badge></p>
                      <ul className="flex flex-col gap-1 text-sm">
                        {l.issues.map((i, k) => <li key={k}><Badge tone={i.severity === 'error' ? 'danger' : 'warn'}>{i.severity === 'error' ? t('scenarios.error') : t('scenarios.warning')}</Badge> {i.message}</li>)}
                        {l.issues.length === 0 && <li className="text-muted">{t('scenarios.noIssues')}</li>}
                      </ul>
                      <p className="mt-3 text-xs text-muted">{t('scenarios.estimate', { max: l.stats.estimated_llm_calls.max, cap: l.stats.estimated_llm_calls.cap })}<br />{l.stats.estimated_llm_calls.formula}</p>
                      <p className="mt-1 text-xs text-muted">{t('scenarios.faultModes', { n: l.stats.distinct_fault_modes })}</p>
                    </div>
                  )}
                </QueryState>
              </Card>
            </aside>
          </div>
          {editing && <InjectDialog scenarioId={scenarioId} inject={editing === 'new' ? null : editing} institutions={insts.data ?? []} onClose={() => setEditing(null)} />}
          <ConfirmDialog open={!!deleting} onClose={() => setDeleting(null)} danger title={t('common.delete')} message={t('scenarios.deleteInject', { title: deleting?.title })} loading={del.isPending} onConfirm={() => deleting && del.mutate(deleting)} />
        </>
      )}
    </QueryState>
  )
}

interface DemandRow { action_code: string; derivation: 'referential' | 'scenario_author' | 'agent_proposed'; justification: string }

function InjectDialog({ scenarioId, inject, institutions, onClose }: { scenarioId: string; inject: Inject | null; institutions: Institution[]; onClose: () => void }) {
  const { t } = useTranslation()
  const toast = useToast()
  const faults = useApiQuery<FaultMode[]>(keys.faultModes, '/fault-modes')
  const actions = useApiQuery<ActionItem[]>(keys.actions, '/actions')
  const [v, setV] = useState({ sim_time: inject?.sim_time ?? 'D1 06:00', title: inject?.title ?? '', body: inject?.body ?? '', from_actor: inject?.from_actor ?? '', fault_mode: inject?.fault_mode ?? 'none', source_note: inject?.source_note ?? '' })
  const [tags, setTags] = useState<string[]>(inject?.tags ?? [])
  const [extraTags, setExtraTags] = useState('')
  const [recips, setRecips] = useState<string[]>(inject?.recipients ?? [])
  const [demands, setDemands] = useState<DemandRow[]>((inject?.demands ?? []).map((d) => ({ action_code: d.action_code, derivation: d.derivation ?? 'scenario_author', justification: d.justification ?? '' })))
  const [sysOut, setSysOut] = useState(inject?.system_output ? JSON.stringify(inject.system_output, null, 2) : '')
  const [sysErr, setSysErr] = useState<string | null>(null)

  const save = useApiMutation(async () => {
    let system_output: Record<string, unknown> | null = null
    if (sysOut.trim()) { try { system_output = JSON.parse(sysOut) } catch { setSysErr(t('scenarios.jsonInvalid')); throw new Error('json') } }
    const allTags = [...new Set([...tags, ...splitList(extraTags)])]
    const base = { ...v, source_note: v.source_note || null, system_output }
    if (inject) {
      await api.patch(`/injects/${inject.id}`, { ...base, tags: allTags })
      await api.put(`/injects/${inject.id}/recipients`, { institution_ids: recips })
      await api.put(`/injects/${inject.id}/demands`, { demands })
    } else {
      await api.post(`/scenarios/${scenarioId}/injects`, { ...base, tags: allTags, recipients: recips, demands })
    }
  }, {
    invalidate: [keys.injects(scenarioId), keys.lint(scenarioId), keys.scenario(scenarioId), keys.scenarios], onSuccess: () => { toast.push(t('common.saved')); onClose() },
    onError: (e) => { if ((e as Error).message !== 'json') toast.push(errorMessage(e, t), 'danger') },
  })
  const toggle = <T,>(list: T[], x: T, set: (l: T[]) => void) => set(list.includes(x) ? list.filter((y) => y !== x) : [...list, x])

  return (
    <Dialog open wide onClose={onClose} title={inject ? t('scenarios.editInject') : t('scenarios.addInject')}
      footer={<><Button onClick={onClose}>{t('common.cancel')}</Button><Button variant="primary" disabled={!v.title.trim()} loading={save.isPending} onClick={() => save.mutate(undefined)}>{t('common.save')}</Button></>}>
      <div className="grid gap-3 md:grid-cols-2">
        <Field label={t('scenarios.title_')} required className="md:col-span-2"><Input data-autofocus value={v.title} onChange={(e) => setV({ ...v, title: e.target.value })} /></Field>
        <Field label={t('scenarios.simTime')} hint={t('scenarios.simTimeHint')}><Input value={v.sim_time} onChange={(e) => setV({ ...v, sim_time: e.target.value })} /></Field>
        <Field label={t('scenarios.from')}><Input value={v.from_actor} onChange={(e) => setV({ ...v, from_actor: e.target.value })} /></Field>
        <Field label={t('scenarios.body')} className="md:col-span-2"><Textarea rows={4} value={v.body} onChange={(e) => setV({ ...v, body: e.target.value })} /></Field>
        <Field label={t('scenarios.fault')} hint={faults.data?.find((f) => f.code === v.fault_mode)?.description}>
          <Select value={v.fault_mode} onChange={(e) => setV({ ...v, fault_mode: e.target.value })}><option value="none">none</option>{faults.data?.map((f) => <option key={f.code} value={f.code}>{f.label} ({f.code})</option>)}</Select>
        </Field>
        <Field label={t('scenarios.sourceNote')}><Input value={v.source_note} onChange={(e) => setV({ ...v, source_note: e.target.value })} /></Field>
        <fieldset className="md:col-span-2"><legend className="mb-1 text-sm font-medium">{t('scenarios.recipients')}</legend>
          <div className="flex flex-wrap gap-3">{institutions.map((i) => <label key={i.id} className="inline-flex items-center gap-1 text-sm"><input type="checkbox" className="h-4 w-4" checked={recips.includes(i.id)} onChange={() => toggle(recips, i.id, setRecips)} />{i.code}</label>)}</div>
          {institutions.length === 0 && <p className="text-sm text-muted">{t('geo.noInstitutions')}</p>}
        </fieldset>
        <fieldset className="md:col-span-2"><legend className="mb-1 text-sm font-medium">{t('scenarios.tags')}</legend>
          <div className="flex flex-wrap gap-3">{TAGS.map((tg) => <label key={tg} className="inline-flex items-center gap-1 text-sm"><input type="checkbox" className="h-4 w-4" checked={tags.includes(tg)} onChange={() => toggle(tags, tg, setTags)} />{tg}</label>)}</div>
          <Field label={t('scenarios.moreTags')} className="mt-2"><Input value={extraTags} onChange={(e) => setExtraTags(e.target.value)} /></Field>
        </fieldset>
        <fieldset className="md:col-span-2"><legend className="mb-1 text-sm font-medium">{t('scenarios.demands')}</legend>
          <p className="mb-2 text-xs text-muted">{t('scenarios.demandsHint')}</p>
          {demands.map((d, i) => (
            <div key={i} className="mb-2 grid gap-2 rounded border border-line p-2 md:grid-cols-[1fr_1fr_2fr_auto]">
              <Select aria-label={t('geo.action')} value={d.action_code} onChange={(e) => setDemands(demands.map((x, j) => j === i ? { ...x, action_code: e.target.value } : x))}>
                <option value="">—</option>{actions.data?.map((a) => <option key={a.id} value={a.code}>{a.code}</option>)}
              </Select>
              <Select aria-label={t('geo.derivation')} value={d.derivation} onChange={(e) => setDemands(demands.map((x, j) => j === i ? { ...x, derivation: e.target.value as DemandRow['derivation'] } : x))}>
                {['referential', 'scenario_author', 'agent_proposed'].map((k) => <option key={k} value={k}>{t(`geo.derivations.${k}`)}</option>)}
              </Select>
              <Input aria-label={t('geo.justification')} placeholder={t('geo.justification')} value={d.justification} onChange={(e) => setDemands(demands.map((x, j) => j === i ? { ...x, justification: e.target.value } : x))} />
              <Button size="sm" onClick={() => setDemands(demands.filter((_, j) => j !== i))}>{t('common.delete')}</Button>
            </div>
          ))}
          <Button size="sm" onClick={() => setDemands([...demands, { action_code: '', derivation: 'scenario_author', justification: '' }])}>{t('scenarios.addDemand')}</Button>
        </fieldset>
        <Field label={t('scenarios.systemOutput')} hint={t('scenarios.systemOutputHint')} error={sysErr} className="md:col-span-2"><Textarea rows={3} className="font-mono" value={sysOut} onChange={(e) => { setSysOut(e.target.value); setSysErr(null) }} /></Field>
      </div>
    </Dialog>
  )
}
