import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { TokenCreate, TokenCreated, TokenOut } from '@/api/types'
import { useAuth } from '@/app/auth'
import { Button, Card, ConfirmDialog, EmptyState, Field, Input, OneTimeSecret, PageHeader, QueryState, Select, StatusBadge, Table, TBody, Td, Th, THead, Tr, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { fmtDateTime } from '@/lib/format'

const schema = z.object({
  role: z.enum(['facilitator', 'observer', 'auditor']),
  label: z.string().trim().max(200).optional(),
  expires_in_hours: z.preprocess((v) => (v === '' || v === undefined || Number.isNaN(v) ? undefined : Number(v)), z.number().int().min(1).max(8760).optional()),
})
type Form = z.input<typeof schema>

export function TokensPage() {
  const { t } = useTranslation()
  const { isOwner, loading } = useAuth()
  const toast = useToast()
  const q = useApiQuery<TokenOut[]>(keys.tokens, isOwner ? '/tokens' : null)
  const [secret, setSecret] = useState<TokenCreated | null>(null)
  const [revoking, setRevoking] = useState<TokenOut | null>(null)
  const { register, handleSubmit, reset, formState: { errors } } = useForm<Form>({ resolver: zodResolver(schema), defaultValues: { role: 'observer' } })
  const create = useApiMutation((v: TokenCreate) => api.post<TokenCreated>('/tokens', v), {
    invalidate: [keys.tokens],
    onSuccess: (r) => { setSecret(r); reset({ role: 'observer', label: '' }) },
    onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const revoke = useApiMutation((id: string) => api.delete(`/tokens/${id}`), {
    invalidate: [keys.tokens],
    onSuccess: () => { setRevoking(null); toast.push(t('access.revoked')) },
    onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })

  if (loading) return null
  if (!isOwner) return <><PageHeader title={t('access.tokensTitle')} /><p role="alert">{t('access.ownerOnly')}</p></>

  return (
    <>
      <PageHeader title={t('access.tokensTitle')} description={t('access.tokensHint')} />
      {secret && <div className="mb-4"><OneTimeSecret value={secret.token} title={t('access.newToken', { role: secret.info.role })} /></div>}
      <Card className="mb-6">
        <h2 className="mb-2 text-lg font-semibold">{t('access.newTokenTitle')}</h2>
        <form className="grid gap-3 md:grid-cols-4" noValidate onSubmit={handleSubmit((v) => {
          const p = schema.parse(v)
          create.mutate({ role: p.role, label: p.label || undefined, expires_in_hours: p.expires_in_hours })
        })}>
          <Field label={t('access.role')}>
            <Select {...register('role')}>
              <option value="facilitator">facilitator</option>
              <option value="observer">observer</option>
              <option value="auditor">auditor</option>
            </Select>
          </Field>
          <Field label={t('access.label')}><Input {...register('label')} /></Field>
          <Field label={t('access.expiresIn')} error={errors.expires_in_hours && t('access.expiresInvalid')}><Input type="number" min={1} {...register('expires_in_hours')} /></Field>
          <div className="flex items-end"><Button type="submit" variant="primary" loading={create.isPending}>{t('common.create')}</Button></div>
        </form>
      </Card>
      <QueryState q={q} what="(/tokens)">
        {(rows) => rows.length === 0 ? <EmptyState title={t('common.empty')} /> : (
          <Table caption={t('access.tokensTitle')}>
            <THead><Tr><Th>{t('access.role')}</Th><Th>{t('access.label')}</Th><Th>{t('common.createdAt')}</Th><Th>{t('access.expires')}</Th><Th>{t('common.status')}</Th><Th><span className="sr-only">{t('common.actions')}</span></Th></Tr></THead>
            <TBody>
              {rows.map((r) => (
                <Tr key={r.id}>
                  <Td>{r.role}</Td><Td>{r.label ?? '—'}</Td><Td>{fmtDateTime(r.created_at)}</Td><Td>{fmtDateTime(r.expires_at)}</Td>
                  <Td><StatusBadge status={r.revoked_at ? 'revoked' : 'active'} /></Td>
                  <Td>{!r.revoked_at && <Button size="sm" variant="danger" onClick={() => setRevoking(r)}>{t('access.revoke')}</Button>}</Td>
                </Tr>
              ))}
            </TBody>
          </Table>
        )}
      </QueryState>
      <ConfirmDialog open={!!revoking} onClose={() => setRevoking(null)} danger loading={revoke.isPending}
        title={t('access.revoke')} message={t('access.revokeConfirm', { label: revoking?.label ?? revoking?.role })}
        confirmLabel={t('access.revoke')} onConfirm={() => revoking && revoke.mutate(revoking.id)} />
    </>
  )
}
