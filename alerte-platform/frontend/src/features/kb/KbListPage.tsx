import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api, fieldErrors } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { Country, KBCreate, KBKind } from '@/api/types'
import type { Kb } from '@/api/loose'
import { Badge, Button, Checkbox, Dialog, EmptyState, Field, Input, PageHeader, QueryState, Select, Stepper, StatusBadge, Table, TBody, Td, Textarea, Th, THead, Tr, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { fmtPct } from '@/lib/format'
import { splitList } from '@/lib/lists'
import { ImportArchive } from './ImportArchive'

export const KB_KINDS: KBKind[] = ['national', 'global_practices', 'scenario', 'prior_reports', 'mixed']

const schema = z.object({
  name: z.string().trim().min(1).max(200),
  description: z.string().optional(),
  kind: z.enum(KB_KINDS as [KBKind, ...KBKind[]]),
  country_id: z.string().optional(),
  domain: z.string().optional(),
  languages: z.string().optional(),
})
type Form = z.infer<typeof schema>

export function KbListPage() {
  const { t } = useTranslation()
  const [archived, setArchived] = useState(false)
  const [wizard, setWizard] = useState(false)
  const [importing, setImporting] = useState(false)
  const q = useApiQuery<Kb[]>(keys.kbs(archived), '/knowledge-bases', { query: { include_archived: archived } })
  return (
    <>
      <PageHeader title={t('kb.title')} term="knowledgeBase" description={t('kb.description')}
        actions={<><Button onClick={() => setImporting((v) => !v)}>{t('kb.importArchive')}</Button><Button variant="primary" onClick={() => setWizard(true)}>{t('kb.newKb')}</Button></>} />
      {importing && <div className="mb-4"><ImportArchive /></div>}
      <div className="mb-3"><Checkbox label={t('geo.showArchived')} checked={archived} onChange={(e) => setArchived(e.target.checked)} /></div>
      <QueryState q={q} what="(/knowledge-bases)">
        {(rows) => rows.length === 0 ? <EmptyState title={t('kb.empty')} hint={t('kb.emptyHint')} action={<Button variant="primary" onClick={() => setWizard(true)}>{t('kb.newKb')}</Button>} /> : (
          <Table caption={t('kb.title')}>
            <THead><Tr><Th>{t('common.name')}</Th><Th>{t('common.kind')}</Th><Th>{t('kb.languages')}</Th><Th>{t('kb.published')}</Th><Th>{t('kb.documents')}</Th><Th>{t('kb.indexed')}</Th><Th>{t('kb.coverage')}</Th><Th>{t('common.status')}</Th></Tr></THead>
            <TBody>{rows.map((k) => {
              const o = k.overview
              return (
                <Tr key={k.id}>
                  <Td><Link to={`/studio/knowledge/${k.id}`} className="font-medium">{k.name}</Link><div className="font-mono text-xs text-muted">{k.code}</div></Td>
                  <Td>{t(`kb.kinds.${k.kind}`, k.kind)}</Td><Td>{k.languages.join(', ') || '—'}</Td>
                  <Td>{o?.published_version_no ? `v${o.published_version_no}` : <Badge tone="warn">{t('kb.unpublished')}</Badge>}</Td>
                  <Td>{o?.documents ?? '—'}</Td>
                  <Td>{o ? `${o.embedded_chunks}/${o.chunks}` : '—'}</Td>
                  <Td>{o?.coverage.ratio === null || o?.coverage.ratio === undefined ? <span className="text-muted">{t('kb.noExpected')}</span> : `${fmtPct(o.coverage.ratio)} (${o.coverage.present}/${o.coverage.expected})`}</Td>
                  <Td><StatusBadge status={k.archived_at ? 'archived' : k.status} /></Td>
                </Tr>
              )
            })}</TBody>
          </Table>
        )}
      </QueryState>
      {wizard && <KbWizard onClose={() => setWizard(false)} />}
    </>
  )
}

function KbWizard({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation()
  const toast = useToast()
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const countries = useApiQuery<Country[]>(keys.countries(false), '/countries')
  const { register, handleSubmit, trigger, getValues, setError, formState: { errors } } = useForm<Form>({ resolver: zodResolver(schema), defaultValues: { kind: 'national' } })
  const create = useApiMutation((v: Form) => api.post<Kb>('/knowledge-bases', {
    name: v.name, description: v.description || null, kind: v.kind, country_id: v.country_id || null, domain: v.domain || null, languages: splitList(v.languages),
  } satisfies KBCreate), {
    invalidate: [['kbs']],
    onSuccess: (kb) => { toast.push(t('common.created')); navigate(`/studio/knowledge/${kb.id}?welcome=1`) },
    onError: (e) => { for (const [k, m] of Object.entries(fieldErrors(e))) if (k in schema.shape) setError(k as keyof Form, { message: m }); toast.push(errorMessage(e, t), 'danger') },
  })
  const steps = [t('kb.wizard.basics'), t('kb.wizard.scope'), t('kb.wizard.confirm')]
  const next = async () => { if (await trigger(step === 0 ? ['name', 'kind'] : [])) setStep(step + 1) }
  const v = getValues()
  return (
    <Dialog open onClose={onClose} title={t('kb.newKb')} wide
      footer={<>
        <Button onClick={step === 0 ? onClose : () => setStep(step - 1)}>{step === 0 ? t('common.cancel') : t('common.back')}</Button>
        {step < 2 ? <Button variant="primary" onClick={() => void next()}>{t('common.next')}</Button>
          : <Button variant="primary" loading={create.isPending} onClick={handleSubmit((x) => create.mutate(x))}>{t('common.create')}</Button>}
      </>}>
      <Stepper steps={steps} current={step} />
      <form noValidate onSubmit={(e) => e.preventDefault()}>
        <div hidden={step !== 0} className="flex flex-col gap-3">
          <Field label={t('common.name')} required error={errors.name && t('common.required')}><Input data-autofocus {...register('name')} /></Field>
          <Field label={t('common.description')}><Textarea {...register('description')} /></Field>
          <Field label={t('common.kind')} hint={t('kb.kindHint')}><Select {...register('kind')}>{KB_KINDS.map((k) => <option key={k} value={k}>{t(`kb.kinds.${k}`)}</option>)}</Select></Field>
        </div>
        <div hidden={step !== 1} className="flex flex-col gap-3">
          <Field label={t('geo.country')}><Select {...register('country_id')}><option value="">—</option>{countries.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</Select></Field>
          <Field label={t('kb.domain')} hint={t('kb.domainHint')}><Input {...register('domain')} /></Field>
          <Field label={t('kb.languages')} hint={t('geo.languagesHint')}><Input {...register('languages')} /></Field>
        </div>
        {step === 2 && (
          <div>
            <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
              <dt className="font-medium">{t('common.name')}</dt><dd>{v.name}</dd>
              <dt className="font-medium">{t('common.kind')}</dt><dd>{t(`kb.kinds.${v.kind}`)}</dd>
              <dt className="font-medium">{t('geo.country')}</dt><dd>{countries.data?.find((c) => c.id === v.country_id)?.name ?? '—'}</dd>
              <dt className="font-medium">{t('kb.languages')}</dt><dd>{v.languages || '—'}</dd>
            </dl>
            <p className="mt-3 text-sm text-muted">{t('kb.wizard.next')}</p>
          </div>
        )}
      </form>
    </Dialog>
  )
}
