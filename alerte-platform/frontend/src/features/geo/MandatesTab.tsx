import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api, fieldErrors } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { ActionItem, ImportReport, Institution, Mandate, MandateCreate, MandateKind, RegistryReview, RegistryStatus, SourceIn } from '@/api/types'
import type { Kb, SearchResult } from '@/api/loose'
import { Badge, Button, Dialog, EmptyState, Field, Input, QueryState, Section, Select, StatusBadge, Table, TBody, Td, Textarea, Th, THead, Tr, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'

export const MANDATE_KINDS: MandateKind[] = ['power', 'duty', 'lead', 'coordination', 'information_sharing', 'procedure', 'human_oversight', 'liability', 'inclusion', 'channel_protection', 'international_agreement', 'prohibition']
const REGISTRY: RegistryStatus[] = ['unreviewed', 'partial', 'reviewed_complete']

export function MandatesTab() {
  const { t } = useTranslation()
  const toast = useToast()
  const [inst, setInst] = useState('')
  const insts = useApiQuery<Institution[]>(keys.institutions(undefined, false), '/institutions')
  const mandates = useApiQuery<Mandate[]>(keys.mandates({ inst }), '/mandates', { query: { institution_id: inst } })
  const reviews = useApiQuery<RegistryReview[]>(keys.registryReviews, '/registry-reviews')
  const [creating, setCreating] = useState(false)
  const [rejecting, setRejecting] = useState<Mandate | null>(null)
  const [note, setNote] = useState('')
  const iname = (id: string) => insts.data?.find((i) => i.id === id)?.code ?? id.slice(-6)

  const validate = useApiMutation((m: Mandate) => api.post(`/mandates/${m.id}/validate`, {}), {
    invalidate: [['mandates']], onSuccess: () => toast.push(t('geo.validatedToast')), onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const reject = useApiMutation((v: { m: Mandate; note: string }) => api.post(`/mandates/${v.m.id}/reject`, { note: v.note }), {
    invalidate: [['mandates']], onSuccess: () => { setRejecting(null); setNote('') }, onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const del = useApiMutation((m: Mandate) => api.delete(`/mandates/${m.id}`), {
    invalidate: [['mandates']], onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const setReview = useApiMutation((v: { id: string; status: RegistryStatus }) => api.put(`/institutions/${v.id}/registry-review`, { status: v.status }), {
    invalidate: [keys.registryReviews], onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const rstatus = (id: string) => reviews.data?.find((r) => r.institution_id === id)?.status ?? 'unreviewed'

  return (
    <div>
      <Section title={t('geo.registryReview')}>
        <p className="mb-2 text-sm text-muted">{t('geo.registryReviewHint')}</p>
        <QueryState q={insts} what="(/institutions)">
          {(rows) => rows.length === 0 ? <EmptyState title={t('geo.noInstitutions')} /> : (
            <Table caption={t('geo.registryReview')}>
              <THead><Tr><Th>{t('geo.institutions')}</Th><Th>{t('common.status')}</Th><Th>{t('geo.setStatus')}</Th></Tr></THead>
              <TBody>{rows.map((i) => (
                <Tr key={i.id}>
                  <Td>{i.code} — {i.name}</Td>
                  <Td><StatusBadge status={rstatus(i.id)} /></Td>
                  <Td>
                    <Select aria-label={`${t('geo.setStatus')} ${i.code}`} className="!w-auto" value={rstatus(i.id)}
                      onChange={(e) => setReview.mutate({ id: i.id, status: e.target.value as RegistryStatus })}>
                      {REGISTRY.map((r) => <option key={r} value={r}>{r.replaceAll('_', ' ')}</option>)}
                    </Select>
                  </Td>
                </Tr>
              ))}</TBody>
            </Table>
          )}
        </QueryState>
      </Section>

      <Section title={t('geo.mandates')} actions={<div className="flex gap-2"><CsvImport /><Button variant="primary" onClick={() => setCreating(true)}>{t('geo.newMandate')}</Button></div>}>
        <Field label={t('geo.filterInstitution')} className="mb-3 w-72">
          <Select value={inst} onChange={(e) => setInst(e.target.value)}><option value="">{t('common.all')}</option>{insts.data?.map((i) => <option key={i.id} value={i.id}>{i.code} — {i.name}</option>)}</Select>
        </Field>
        <QueryState q={mandates} what="(/mandates)">
          {(rows) => rows.length === 0 ? <EmptyState title={t('geo.noMandates')} hint={t('geo.noMandatesHint')} /> : (
            <Table caption={t('geo.mandates')}>
              <THead><Tr><Th>{t('geo.institution')}</Th><Th>{t('common.kind')}</Th><Th>{t('geo.action')}</Th><Th>{t('common.description')}</Th><Th>{t('geo.sources')}</Th><Th>{t('common.status')}</Th><Th><span className="sr-only">{t('common.actions')}</span></Th></Tr></THead>
              <TBody>{rows.map((m) => (
                <Tr key={m.id}>
                  <Td className="font-mono">{iname(m.institution_id)}</Td><Td>{m.kind.replaceAll('_', ' ')}</Td><Td className="font-mono">{m.action_code}</Td>
                  <Td className="max-w-md">{m.description}</Td>
                  <Td>{m.sources?.length ? m.sources.map((s) => (
                    <div key={s.id} className="text-xs">{s.article ? `Art. ${s.article}` : ''}{s.page ? ` p.${s.page}` : ''} {s.quote_found === false && <Badge tone="danger">{t('geo.quoteNotFound')}</Badge>}</div>
                  )) : <Badge tone="warn">{t('geo.noSource')}</Badge>}</Td>
                  <Td><div className="flex flex-col gap-1"><StatusBadge status={m.validation} />{m.active === false && <Badge tone="warn">{t('geo.inactive')}</Badge>}</div>
                    {m.inactive_reason && <p className="text-xs text-muted">{m.inactive_reason}</p>}</Td>
                  <Td><div className="flex flex-wrap gap-1">
                    {m.validation !== 'validated' && <Button size="sm" onClick={() => validate.mutate(m)}>{t('geo.validate')}</Button>}
                    {m.validation !== 'rejected' && <Button size="sm" onClick={() => setRejecting(m)}>{t('geo.reject')}</Button>}
                    <Button size="sm" variant="danger" onClick={() => del.mutate(m)}>{t('common.delete')}</Button>
                  </div></Td>
                </Tr>
              ))}</TBody>
            </Table>
          )}
        </QueryState>
      </Section>

      <ActionsCatalogue />
      {creating && <MandateDialog institutions={insts.data ?? []} onClose={() => setCreating(false)} />}
      <Dialog open={!!rejecting} onClose={() => setRejecting(null)} title={t('geo.reject')}
        footer={<><Button onClick={() => setRejecting(null)}>{t('common.cancel')}</Button><Button variant="danger" disabled={!note.trim()} loading={reject.isPending} onClick={() => rejecting && reject.mutate({ m: rejecting, note })}>{t('geo.reject')}</Button></>}>
        <Field label={t('geo.rejectReason')} required><Textarea data-autofocus value={note} onChange={(e) => setNote(e.target.value)} /></Field>
      </Dialog>
    </div>
  )
}

const mSchema = z.object({
  institution_id: z.string().min(1),
  kind: z.enum(MANDATE_KINDS as [MandateKind, ...MandateKind[]]),
  action_code: z.string().min(1),
  description: z.string().optional(),
  procedure_status: z.enum(['specific', 'general', 'none', 'unknown']),
})
type MForm = z.infer<typeof mSchema>

function MandateDialog({ institutions, onClose }: { institutions: Institution[]; onClose: () => void }) {
  const { t } = useTranslation()
  const toast = useToast()
  const actions = useApiQuery<ActionItem[]>(keys.actions, '/actions')
  const [sources, setSources] = useState<SourceIn[]>([])
  const { register, handleSubmit, setError, formState: { errors } } = useForm<MForm>({ resolver: zodResolver(mSchema), defaultValues: { kind: 'power', procedure_status: 'unknown', institution_id: '', action_code: '' } })
  const save = useApiMutation((v: MForm) => api.post('/mandates', { ...v, sources } satisfies MandateCreate), {
    invalidate: [['mandates']], onSuccess: () => { toast.push(t('common.created')); onClose() },
    onError: (e) => { for (const [k, m] of Object.entries(fieldErrors(e))) if (k in mSchema.shape) setError(k as keyof MForm, { message: m }); toast.push(errorMessage(e, t), 'danger') },
  })
  return (
    <Dialog open wide onClose={onClose} title={t('geo.newMandate')}
      footer={<><Button onClick={onClose}>{t('common.cancel')}</Button><Button variant="primary" type="submit" form="mandate-form" loading={save.isPending}>{t('common.create')}</Button></>}>
      <form id="mandate-form" noValidate className="grid gap-3 md:grid-cols-2" onSubmit={handleSubmit((v) => save.mutate(v))}>
        <Field label={t('geo.institution')} required error={errors.institution_id && t('common.required')}>
          <Select data-autofocus {...register('institution_id')}><option value="">—</option>{institutions.map((i) => <option key={i.id} value={i.id}>{i.code} — {i.name}</option>)}</Select>
        </Field>
        <Field label={t('common.kind')}><Select {...register('kind')}>{MANDATE_KINDS.map((k) => <option key={k} value={k}>{k.replaceAll('_', ' ')}</option>)}</Select></Field>
        <Field label={t('geo.action')} required error={errors.action_code && t('common.required')} hint={t('geo.actionHint')}>
          <Select {...register('action_code')}><option value="">—</option>{actions.data?.map((a) => <option key={a.id} value={a.code}>{a.code} — {a.label}</option>)}</Select>
        </Field>
        <Field label={t('geo.procedure')}><Select {...register('procedure_status')}>{['specific', 'general', 'none', 'unknown'].map((s) => <option key={s}>{s}</option>)}</Select></Field>
        <Field label={t('common.description')} className="md:col-span-2"><Textarea {...register('description')} /></Field>
      </form>
      <SourcePicker sources={sources} onChange={setSources} />
    </Dialog>
  )
}

/** Chooses mandate sources by searching a knowledge base: the quote is copied from the real chunk text. */
function SourcePicker({ sources, onChange }: { sources: SourceIn[]; onChange: (s: SourceIn[]) => void }) {
  const { t } = useTranslation()
  const kbs = useApiQuery<Kb[]>(keys.kbs(false), '/knowledge-bases')
  const [kb, setKb] = useState('')
  const [query, setQuery] = useState('')
  const search = useApiMutation((v: { kb: string; q: string }) => api.post<SearchResult>(`/knowledge-bases/${v.kb}/search`, { query: v.q, k: 5 }))
  return (
    <fieldset className="mt-4 rounded-md border border-line p-3">
      <legend className="px-1 text-sm font-semibold">{t('geo.sources')}</legend>
      {sources.map((s, i) => (
        <div key={i} className="mb-1 flex items-center justify-between gap-2 text-sm">
          <span className="truncate">{s.article ? `Art. ${s.article} · ` : ''}{s.page ? `p.${s.page} · ` : ''}“{s.quote}”</span>
          <Button size="sm" onClick={() => onChange(sources.filter((_, j) => j !== i))}>{t('common.delete')}</Button>
        </div>
      ))}
      <div className="flex flex-wrap items-end gap-2">
        <Field label={t('geo.kb')}><Select value={kb} onChange={(e) => setKb(e.target.value)}><option value="">—</option>{kbs.data?.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}</Select></Field>
        <Field label={t('geo.searchText')} className="min-w-48 flex-1"><Input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); if (kb && query) search.mutate({ kb, q: query }) } }} /></Field>
        <Button disabled={!kb || !query} loading={search.isPending} onClick={() => search.mutate({ kb, q: query })}>{t('common.search')}</Button>
      </div>
      {search.error && <p role="alert" className="mt-2 text-sm text-danger">{errorMessage(search.error, t)}</p>}
      {search.data?.hits.map((h) => (
        <div key={h.chunk_id} className="mt-2 rounded border border-line p-2 text-sm">
          <p className="font-medium">{h.doc_code} {h.article ? `· Art. ${h.article}` : ''} {h.page ? `· p.${h.page}` : ''}</p>
          <p className="text-muted">{h.snippet}</p>
          <Button size="sm" className="mt-1" onClick={() => onChange([...sources, { document_version_id: h.document_version_id, chunk_id: h.chunk_id, article: h.article, page: h.page, quote: h.text.slice(0, 240) }])}>{t('geo.useSource')}</Button>
        </div>
      ))}
    </fieldset>
  )
}

function CsvImport() {
  const { t } = useTranslation()
  const toast = useToast()
  const [open, setOpen] = useState(false)
  const [csv, setCsv] = useState('')
  const [report, setReport] = useState<ImportReport | null>(null)
  const run = useApiMutation((v: { dry: boolean }) => api.postText<ImportReport>(`/mandates/import-csv?dry_run=${v.dry}`, csv, 'text/csv'), {
    invalidate: [['mandates']],
    onSuccess: (r) => { setReport(r); if (!r.dry_run) toast.push(t('geo.importDone', { n: r.created })) },
    onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  return (
    <>
      <Button onClick={() => setOpen(true)}>{t('geo.importCsv')}</Button>
      <Dialog open={open} wide onClose={() => setOpen(false)} title={t('geo.importCsv')}
        footer={<><Button disabled={!csv} loading={run.isPending} onClick={() => run.mutate({ dry: true })}>{t('geo.dryRun')}</Button>
          <Button variant="primary" disabled={!csv || !report?.dry_run || report.errors.length > 0} onClick={() => run.mutate({ dry: false })}>{t('geo.confirmImport')}</Button></>}>
        <p className="mb-2 text-sm text-muted">{t('geo.importCsvHint')}</p>
        <input type="file" accept=".csv,text/csv" aria-label={t('geo.csvFile')} onChange={async (e) => { const f = e.target.files?.[0]; if (f) { setCsv(await f.text()); setReport(null) } }} />
        <Textarea className="mt-2 font-mono" rows={6} value={csv} onChange={(e) => { setCsv(e.target.value); setReport(null) }} aria-label="CSV" />
        {report && (
          <div className="mt-3 text-sm" role="status">
            <p><strong>{report.dry_run ? t('geo.dryRunResult') : t('geo.importResult')}</strong>: {t('geo.importCounts', { created: report.created, skipped: report.skipped, errors: report.errors.length })}</p>
            <ul className="list-disc pl-5">{report.errors.map((er, i) => <li key={i} className="text-danger">{t('geo.line')} {er.line}: {er.error}</li>)}</ul>
          </div>
        )}
      </Dialog>
    </>
  )
}

function ActionsCatalogue() {
  const { t } = useTranslation()
  const toast = useToast()
  const q = useApiQuery<ActionItem[]>(keys.actions, '/actions')
  const [open, setOpen] = useState(false)
  const [v, setV] = useState({ code: '', label: '', derivation: 'referential', justification: '', reference_note: '' })
  const create = useApiMutation(() => api.post('/actions', { ...v, justification: v.justification || null, reference_note: v.reference_note || null }), {
    invalidate: [keys.actions], onSuccess: () => { setOpen(false); toast.push(t('common.created')) }, onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  return (
    <Section title={t('geo.actionsCatalogue')} actions={<Button onClick={() => setOpen(true)}>{t('geo.newAction')}</Button>}>
      <p className="mb-2 text-sm text-muted">{t('geo.actionsHint')}</p>
      <QueryState q={q} what="(/actions)">
        {(rows) => rows.length === 0 ? <EmptyState title={t('geo.noActions')} /> : (
          <Table caption={t('geo.actionsCatalogue')}>
            <THead><Tr><Th>{t('common.code')}</Th><Th>{t('geo.label')}</Th><Th>{t('geo.derivation')}</Th><Th>{t('geo.justification')}</Th></Tr></THead>
            <TBody>{rows.map((a) => (
              <Tr key={a.id}><Td className="font-mono">{a.code}</Td><Td>{a.label}</Td>
                <Td><Badge tone={a.derivation === 'scenario_author' ? 'warn' : 'info'}>{t(`geo.derivations.${a.derivation}`, a.derivation)}</Badge></Td>
                <Td className="max-w-md text-xs">{a.justification ?? '—'}{a.reference_note ? ` (${a.reference_note})` : ''}</Td></Tr>
            ))}</TBody>
          </Table>
        )}
      </QueryState>
      <Dialog open={open} onClose={() => setOpen(false)} title={t('geo.newAction')}
        footer={<><Button onClick={() => setOpen(false)}>{t('common.cancel')}</Button><Button variant="primary" disabled={!v.code || !v.label} loading={create.isPending} onClick={() => create.mutate(undefined)}>{t('common.create')}</Button></>}>
        <div className="flex flex-col gap-3">
          <Field label={t('common.code')} required><Input data-autofocus value={v.code} onChange={(e) => setV({ ...v, code: e.target.value })} /></Field>
          <Field label={t('geo.label')} required><Input value={v.label} onChange={(e) => setV({ ...v, label: e.target.value })} /></Field>
          <Field label={t('geo.derivation')} hint={t('geo.derivationHint')}><Select value={v.derivation} onChange={(e) => setV({ ...v, derivation: e.target.value })}>{['referential', 'scenario_author', 'agent_proposed'].map((d) => <option key={d} value={d}>{t(`geo.derivations.${d}`)}</option>)}</Select></Field>
          <Field label={t('geo.justification')}><Textarea value={v.justification} onChange={(e) => setV({ ...v, justification: e.target.value })} /></Field>
          <Field label={t('geo.referenceNote')}><Input value={v.reference_note} onChange={(e) => setV({ ...v, reference_note: e.target.value })} /></Field>
        </div>
      </Dialog>
    </Section>
  )
}
