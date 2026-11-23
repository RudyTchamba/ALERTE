import { Prereq } from '@/components/Prereq'
import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api, fieldErrors } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { Country, Scenario } from '@/api/types'
import type { ScenarioImportResult } from '@/api/loose'
import { Badge, Button, Checkbox, ConfirmDialog, Dialog, EmptyState, Field, Input, PageHeader, QueryState, Select, StatusBadge, Table, TBody, Td, Textarea, Th, THead, Tr, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'

const schema = z.object({
  code: z.string().trim().min(1).max(64), title: z.string().trim().min(1).max(300),
  description: z.string().optional(), language: z.string().min(2).max(8), country_id: z.string().optional(),
})
type Form = z.infer<typeof schema>

export function ScenariosPage() {
  const { t } = useTranslation()
  const toast = useToast()
  const navigate = useNavigate()
  const [archived] = useState(false)
  const q = useApiQuery<Scenario[]>(keys.scenarios, '/scenarios', { query: { include_archived: archived } })
  const countries = useApiQuery<Country[]>(keys.countries(false), '/countries')
  const [creating, setCreating] = useState(false)
  const [delTarget, setDelTarget] = useState<Scenario | null>(null)
  const [showArchived, setShowArchived] = useState(false)
  const file = useRef<HTMLInputElement>(null)
  const list = useApiQuery<Scenario[]>(['scenarios', { showArchived }], '/scenarios', { query: { include_archived: showArchived } })
  const clone = useApiMutation((s: Scenario) => api.post<Scenario>(`/scenarios/${s.id}/clone`, {}), { invalidate: [['scenarios']], onSuccess: () => toast.push(t('scenarios.cloned')), onError: (e) => toast.push(errorMessage(e, t), 'danger') })
  const archive = useApiMutation((s: Scenario) => api.post(`/scenarios/${s.id}/archive`), { invalidate: [['scenarios']], onSuccess: () => toast.push(t('common.archived')), onError: (e) => toast.push(errorMessage(e, t), 'danger') })
  const del = useApiMutation((s: Scenario) => api.delete(`/scenarios/${s.id}`), { invalidate: [['scenarios']], onSuccess: () => { setDelTarget(null); toast.push(t('common.deleted')) }, onError: (e) => { setDelTarget(null); toast.push(errorMessage(e, t), 'danger') } })
  const importYaml = useApiMutation(async (f: File) => api.postText<ScenarioImportResult>('/scenarios/import', await f.text(), 'application/yaml'), {
    invalidate: [['scenarios']], onSuccess: (r) => { toast.push(t('scenarios.imported', { n: r.warnings.length })); navigate(`/studio/scenarios/${r.scenario.id}`) }, onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  void q
  return (
    <>
      <PageHeader title={t('scenarios.title')} term="scenario" description={t('scenarios.description')}
        actions={<>
          <input ref={file} type="file" accept=".yaml,.yml,text/yaml" className="sr-only" aria-label={t('scenarios.importYaml')} onChange={(e) => { const f = e.target.files?.[0]; if (f) importYaml.mutate(f); e.target.value = '' }} />
          <Button loading={importYaml.isPending} onClick={() => file.current?.click()}>{t('scenarios.importYaml')}</Button>
          <Button variant="primary" onClick={() => setCreating(true)}>{t('scenarios.new')}</Button>
        </>} />
      <Prereq page="scenarios" />
      <div className="mb-3"><Checkbox label={t('geo.showArchived')} checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} /></div>
      <QueryState q={list} what="(/scenarios)">
        {(rows) => rows.length === 0 ? <EmptyState title={t('scenarios.empty')} hint={t('scenarios.emptyHint')} /> : (
          <Table caption={t('scenarios.title')}>
            <THead><Tr><Th>{t('common.code')}</Th><Th>{t('scenarios.scTitle')}</Th><Th>{t('kb.language')}</Th><Th>{t('scenarios.injects')}</Th><Th>{t('common.status')}</Th><Th><span className="sr-only">{t('common.actions')}</span></Th></Tr></THead>
            <TBody>{rows.map((s) => (
              <Tr key={s.id}>
                <Td className="font-mono">{s.code}</Td><Td><Link to={`/studio/scenarios/${s.id}`} className="font-medium">{s.title}</Link></Td><Td>{s.language}</Td><Td>{s.inject_count ?? '—'}</Td>
                <Td><StatusBadge status={s.status} />{s.is_template && <> <Badge tone="info">{t('scenarios.template')}</Badge></>}</Td>
                <Td><div className="flex flex-wrap gap-1">
                  <Button size="sm" onClick={() => navigate(`/studio/scenarios/${s.id}`)}>{t('common.edit')}</Button>
                  <Button size="sm" onClick={() => clone.mutate(s)}>{t('scenarios.clone')}</Button>
                  {s.status !== 'archived' && <Button size="sm" onClick={() => archive.mutate(s)}>{t('common.archive')}</Button>}
                  <Button size="sm" variant="danger" onClick={() => setDelTarget(s)}>{t('common.delete')}</Button>
                </div></Td>
              </Tr>
            ))}</TBody>
          </Table>
        )}
      </QueryState>
      {creating && <CreateDialog countries={countries.data ?? []} onClose={() => setCreating(false)} onCreated={(id) => navigate(`/studio/scenarios/${id}`)} />}
      <ConfirmDialog open={!!delTarget} onClose={() => setDelTarget(null)} danger title={t('common.delete')} message={t('scenarios.deleteConfirm', { title: delTarget?.title })} loading={del.isPending} onConfirm={() => delTarget && del.mutate(delTarget)} />
    </>
  )
}

function CreateDialog({ countries, onClose, onCreated }: { countries: Country[]; onClose: () => void; onCreated: (id: string) => void }) {
  const { t } = useTranslation()
  const toast = useToast()
  const { register, handleSubmit, setError, formState: { errors } } = useForm<Form>({ resolver: zodResolver(schema), defaultValues: { language: 'en' } })
  const create = useApiMutation((v: Form) => api.post<Scenario>('/scenarios', { ...v, country_id: v.country_id || null, description: v.description ?? '' }), {
    invalidate: [['scenarios']], onSuccess: (s) => onCreated(s.id),
    onError: (e) => { for (const [k, m] of Object.entries(fieldErrors(e))) if (k in schema.shape) setError(k as keyof Form, { message: m }); toast.push(errorMessage(e, t), 'danger') },
  })
  return (
    <Dialog open onClose={onClose} title={t('scenarios.new')} footer={<><Button onClick={onClose}>{t('common.cancel')}</Button><Button variant="primary" type="submit" form="sc-form" loading={create.isPending}>{t('common.create')}</Button></>}>
      <form id="sc-form" noValidate className="flex flex-col gap-3" onSubmit={handleSubmit((v) => create.mutate(v))}>
        <Field label={t('common.code')} required error={errors.code && t('common.required')}><Input data-autofocus {...register('code')} /></Field>
        <Field label={t('scenarios.scTitle')} required error={errors.title && t('common.required')}><Input {...register('title')} /></Field>
        <Field label={t('common.description')}><Textarea {...register('description')} /></Field>
        <Field label={t('kb.language')}><Input {...register('language')} /></Field>
        <Field label={t('geo.country')}><Select {...register('country_id')}><option value="">—</option>{countries.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</Select></Field>
      </form>
    </Dialog>
  )
}
