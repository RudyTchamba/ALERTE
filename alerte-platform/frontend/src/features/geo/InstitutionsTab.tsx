import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api, ApiError, fieldErrors } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { Country, Institution, InstitutionKind } from '@/api/types'
import { Button, Checkbox, Dialog, EmptyState, Field, Input, QueryState, Select, StatusBadge, Table, TBody, Td, Textarea, Th, THead, Tr, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { joinList, splitList } from '@/lib/lists'

export const INSTITUTION_KINDS: InstitutionKind[] = ['ministry', 'agency', 'regulator', 'operator', 'local_authority', 'ai_system', 'advisory', 'other']

const schema = z.object({
  code: z.string().trim().min(1).max(32).regex(/^[A-Za-z0-9_.-]+$/),
  name: z.string().trim().min(1).max(300),
  name_local: z.string().optional(),
  country_id: z.string().optional(),
  kind: z.enum(INSTITUTION_KINDS as [InstitutionKind, ...InstitutionKind[]]),
  domains: z.string().optional(),
  description: z.string().optional(),
})
type Form = z.infer<typeof schema>

export function InstitutionsTab() {
  const { t } = useTranslation()
  const toast = useToast()
  const [country, setCountry] = useState('')
  const [archived, setArchived] = useState(false)
  const countries = useApiQuery<Country[]>(keys.countries(false), '/countries')
  const q = useApiQuery<Institution[]>(keys.institutions(country || undefined, archived), '/institutions', { query: { country_id: country, include_archived: archived } })
  const [editing, setEditing] = useState<Institution | 'new' | null>(null)
  const [conflict, setConflict] = useState<Institution | null>(null)
  const cname = (id: string | null) => countries.data?.find((c) => c.id === id)?.name ?? '—'

  const archive = useApiMutation((i: Institution) => api.post(`/institutions/${i.id}/archive`), {
    invalidate: [['institutions']], onSuccess: () => { setConflict(null); toast.push(t('common.archived')) },
    onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const del = useApiMutation((i: Institution) => api.delete(`/institutions/${i.id}`), {
    invalidate: [['institutions']], onSuccess: () => toast.push(t('common.deleted')),
  })
  const onDelete = (i: Institution) => del.mutate(i, {
    onError: (e) => { if (e instanceof ApiError && e.status === 409) setConflict(i); else toast.push(errorMessage(e, t), 'danger') },
  })

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
        <div className="flex flex-wrap items-end gap-3">
          <Field label={t('geo.filterCountry')} className="w-56">
            <Select value={country} onChange={(e) => setCountry(e.target.value)}>
              <option value="">{t('common.all')}</option>
              {countries.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </Select>
          </Field>
          <Checkbox label={t('geo.showArchived')} checked={archived} onChange={(e) => setArchived(e.target.checked)} />
        </div>
        <Button variant="primary" onClick={() => setEditing('new')}>{t('geo.newInstitution')}</Button>
      </div>
      <QueryState q={q} what="(/institutions)">
        {(rows) => rows.length === 0 ? <EmptyState title={t('geo.noInstitutions')} /> : (
          <Table caption={t('geo.institutions')}>
            <THead><Tr><Th>{t('common.code')}</Th><Th>{t('common.name')}</Th><Th>{t('common.kind')}</Th><Th>{t('geo.country')}</Th><Th>{t('geo.domains')}</Th><Th>{t('common.status')}</Th><Th><span className="sr-only">{t('common.actions')}</span></Th></Tr></THead>
            <TBody>
              {rows.map((i) => (
                <Tr key={i.id}>
                  <Td className="font-mono">{i.code}</Td><Td className="font-medium">{i.name}</Td><Td>{t(`geo.kinds.${i.kind}`, i.kind)}</Td>
                  <Td>{cname(i.country_id)}</Td><Td>{joinList(i.domains) || '—'}</Td>
                  <Td><StatusBadge status={i.archived_at ? 'archived' : 'active'} /></Td>
                  <Td><div className="flex flex-wrap gap-1">
                    <Button size="sm" onClick={() => setEditing(i)}>{t('common.edit')}</Button>
                    {!i.archived_at && <Button size="sm" onClick={() => archive.mutate(i)}>{t('common.archive')}</Button>}
                    <Button size="sm" variant="danger" onClick={() => onDelete(i)}>{t('common.delete')}</Button>
                  </div></Td>
                </Tr>
              ))}
            </TBody>
          </Table>
        )}
      </QueryState>
      {editing && <InstitutionDialog inst={editing === 'new' ? null : editing} countries={countries.data ?? []} defaultCountry={country} onClose={() => setEditing(null)} />}
      <Dialog open={!!conflict} onClose={() => setConflict(null)} title={t('geo.cannotDelete')}
        footer={<><Button onClick={() => setConflict(null)}>{t('common.cancel')}</Button><Button variant="primary" onClick={() => conflict && archive.mutate(conflict)}>{t('geo.archiveInstead')}</Button></>}>
        <p className="text-sm">{t('geo.cannotDeleteHint', { name: conflict?.name })}</p>
      </Dialog>
    </div>
  )
}

function InstitutionDialog({ inst, countries, defaultCountry, onClose }: { inst: Institution | null; countries: Country[]; defaultCountry: string; onClose: () => void }) {
  const { t } = useTranslation()
  const toast = useToast()
  const { register, handleSubmit, setError, formState: { errors } } = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: {
      code: inst?.code ?? '', name: inst?.name ?? '', name_local: inst?.name_local ?? '', country_id: inst?.country_id ?? defaultCountry,
      kind: (inst?.kind as InstitutionKind) ?? 'other', domains: joinList(inst?.domains), description: inst?.description ?? '',
    },
  })
  const save = useApiMutation((v: Form) => {
    const body = { ...v, name_local: v.name_local || null, country_id: v.country_id || null, domains: splitList(v.domains), description: v.description || null }
    if (inst) { const { code: _c, ...upd } = body; void _c; return api.patch(`/institutions/${inst.id}`, upd) }
    return api.post('/institutions', body)
  }, {
    invalidate: [['institutions']],
    onSuccess: () => { toast.push(t('common.saved')); onClose() },
    onError: (e) => {
      for (const [k, m] of Object.entries(fieldErrors(e))) if (k in schema.shape) setError(k as keyof Form, { message: m })
      toast.push(errorMessage(e, t), 'danger')
    },
  })
  return (
    <Dialog open onClose={onClose} title={inst ? t('geo.editInstitution') : t('geo.newInstitution')}
      footer={<><Button onClick={onClose}>{t('common.cancel')}</Button><Button variant="primary" type="submit" form="inst-form" loading={save.isPending}>{t('common.save')}</Button></>}>
      <form id="inst-form" className="flex flex-col gap-3" noValidate onSubmit={handleSubmit((v) => save.mutate(v))}>
        <Field label={t('common.code')} required hint={t('geo.codeHint')} error={errors.code && t('geo.codeInvalid')}><Input data-autofocus disabled={!!inst} {...register('code')} /></Field>
        <Field label={t('common.name')} required error={errors.name && t('common.required')}><Input {...register('name')} /></Field>
        <Field label={t('geo.nameLocal')}><Input {...register('name_local')} /></Field>
        <Field label={t('geo.country')}>
          <Select {...register('country_id')}><option value="">—</option>{countries.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</Select>
        </Field>
        <Field label={t('common.kind')}>
          <Select {...register('kind')}>{INSTITUTION_KINDS.map((k) => <option key={k} value={k}>{t(`geo.kinds.${k}`, k)}</option>)}</Select>
        </Field>
        <Field label={t('geo.domains')} hint={t('geo.languagesHint')}><Input {...register('domains')} /></Field>
        <Field label={t('common.description')}><Textarea {...register('description')} /></Field>
      </form>
    </Dialog>
  )
}
