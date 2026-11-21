import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api, ApiError, fieldErrors } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { Country } from '@/api/types'
import { Button, Checkbox, Dialog, EmptyState, Field, Input, QueryState, StatusBadge, Table, TBody, Td, Textarea, Th, THead, Tr, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { joinList, splitList } from '@/lib/lists'

const schema = z.object({
  name: z.string().trim().min(1).max(200),
  iso2: z.string().trim().length(2).or(z.literal('')).optional(),
  languages: z.string().optional(),
  notes: z.string().optional(),
})
type Form = z.infer<typeof schema>

export function CountriesTab() {
  const { t } = useTranslation()
  const toast = useToast()
  const [archived, setArchived] = useState(false)
  const q = useApiQuery<Country[]>(keys.countries(archived), '/countries', { query: { include_archived: archived } })
  const [editing, setEditing] = useState<Country | 'new' | null>(null)
  const [conflict, setConflict] = useState<Country | null>(null)

  const archive = useApiMutation((c: Country) => api.post<Country>(`/countries/${c.id}/archive`), {
    invalidate: [['countries']],
    onSuccess: () => { setConflict(null); toast.push(t('common.archived')) },
    onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const del = useApiMutation((c: Country) => api.delete(`/countries/${c.id}`).then(() => c), {
    invalidate: [['countries']],
    onSuccess: () => toast.push(t('common.deleted')),
    onError: (e, ) => { if (!(e instanceof ApiError && e.status === 409)) toast.push(errorMessage(e, t), 'danger') },
  })
  const onDelete = (c: Country) => del.mutate(c, { onError: (e) => { if (e instanceof ApiError && e.status === 409) setConflict(c) } })

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <Checkbox label={t('geo.showArchived')} checked={archived} onChange={(e) => setArchived(e.target.checked)} />
        <Button variant="primary" onClick={() => setEditing('new')}>{t('geo.newCountry')}</Button>
      </div>
      <QueryState q={q} what="(/countries)">
        {(rows) => rows.length === 0 ? <EmptyState title={t('geo.noCountries')} hint={t('geo.noCountriesHint')} /> : (
          <Table caption={t('geo.countries')}>
            <THead><Tr><Th>{t('common.name')}</Th><Th>ISO</Th><Th>{t('geo.languages')}</Th><Th>{t('common.status')}</Th><Th><span className="sr-only">{t('common.actions')}</span></Th></Tr></THead>
            <TBody>
              {rows.map((c) => (
                <Tr key={c.id}>
                  <Td className="font-medium">{c.name}</Td><Td>{c.iso2 ?? '—'}</Td><Td>{joinList(c.languages) || '—'}</Td>
                  <Td><StatusBadge status={c.archived_at ? 'archived' : 'active'} /></Td>
                  <Td>
                    <div className="flex flex-wrap gap-1">
                      <Button size="sm" onClick={() => setEditing(c)}>{t('common.edit')}</Button>
                      {!c.archived_at && <Button size="sm" onClick={() => archive.mutate(c)}>{t('common.archive')}</Button>}
                      <Button size="sm" variant="danger" onClick={() => onDelete(c)}>{t('common.delete')}</Button>
                    </div>
                  </Td>
                </Tr>
              ))}
            </TBody>
          </Table>
        )}
      </QueryState>
      {editing && <CountryDialog country={editing === 'new' ? null : editing} onClose={() => setEditing(null)} />}
      <Dialog open={!!conflict} onClose={() => setConflict(null)} title={t('geo.cannotDelete')}
        footer={<><Button onClick={() => setConflict(null)}>{t('common.cancel')}</Button><Button variant="primary" loading={archive.isPending} onClick={() => conflict && archive.mutate(conflict)}>{t('geo.archiveInstead')}</Button></>}>
        <p className="text-sm">{t('geo.cannotDeleteHint', { name: conflict?.name })}</p>
      </Dialog>
    </div>
  )
}

function CountryDialog({ country, onClose }: { country: Country | null; onClose: () => void }) {
  const { t } = useTranslation()
  const toast = useToast()
  const { register, handleSubmit, setError, formState: { errors } } = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: { name: country?.name ?? '', iso2: country?.iso2 ?? '', languages: joinList(country?.languages), notes: country?.notes ?? '' },
  })
  const save = useApiMutation((v: Form) => {
    const body = { name: v.name, iso2: v.iso2 || null, languages: splitList(v.languages), notes: v.notes || null }
    return country ? api.patch(`/countries/${country.id}`, body) : api.post('/countries', body)
  }, {
    invalidate: [['countries']],
    onSuccess: () => { toast.push(t('common.saved')); onClose() },
    onError: (e) => {
      for (const [k, m] of Object.entries(fieldErrors(e))) if (k in schema.shape) setError(k as keyof Form, { message: m })
      toast.push(errorMessage(e, t), 'danger')
    },
  })
  return (
    <Dialog open onClose={onClose} title={country ? t('geo.editCountry') : t('geo.newCountry')}
      footer={<><Button onClick={onClose}>{t('common.cancel')}</Button><Button variant="primary" type="submit" form="country-form" loading={save.isPending}>{t('common.save')}</Button></>}>
      <form id="country-form" className="flex flex-col gap-3" noValidate onSubmit={handleSubmit((v) => save.mutate(v))}>
        <Field label={t('common.name')} required error={errors.name && t('common.required')}><Input data-autofocus {...register('name')} /></Field>
        <Field label="ISO 3166-1 alpha-2" hint={t('geo.isoHint')} error={errors.iso2 && t('geo.isoInvalid')}><Input maxLength={2} {...register('iso2')} /></Field>
        <Field label={t('geo.languages')} hint={t('geo.languagesHint')}><Input {...register('languages')} /></Field>
        <Field label={t('geo.notes')}><Textarea {...register('notes')} /></Field>
      </form>
    </Dialog>
  )
}
