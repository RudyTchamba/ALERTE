import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api, fieldErrors } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { Agent, Institution, ModelProfile } from '@/api/types'
import type { PromptPreview, ProfileTest } from '@/api/loose'
import { Badge, Button, Checkbox, Dialog, EmptyState, Field, Input, Mono, PageHeader, QueryState, Section, Select, StatusBadge, Table, TBody, Td, Textarea, Th, THead, Tr, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'

const TOOLS = ['search_kb', 'ask_legal', 'post', 'decide'] as const
const ROLE_KINDS = ['institution', 'ai_system', 'legal_adviser'] as const

const schema = z.object({
  code: z.string().trim().min(1).max(40),
  name: z.string().trim().min(1).max(200),
  role_kind: z.enum(ROLE_KINDS),
  institution_id: z.string().optional(),
  mission: z.string().optional(),
  instructions: z.string().optional(),
  model_profile_id: z.string().optional(),
  tools: z.array(z.string()),
  max_steps: z.coerce.number().int().min(1).max(10),
  max_search_calls: z.coerce.number().int().min(0).max(20),
  max_legal_calls_per_inject: z.coerce.number().int().min(0).max(10),
})
type FormIn = z.input<typeof schema>
type FormOut = z.output<typeof schema>

export function AgentsPage() {
  const { t } = useTranslation()
  const toast = useToast()
  const [archived, setArchived] = useState(false)
  const agents = useApiQuery<Agent[]>(keys.agents(archived), '/agents', { query: { include_archived: archived } })
  const insts = useApiQuery<Institution[]>(keys.institutions(undefined, false), '/institutions')
  const profiles = useApiQuery<ModelProfile[]>(keys.modelProfiles, '/model-profiles')
  const [editing, setEditing] = useState<Agent | 'new' | null>(null)
  const [preview, setPreview] = useState<Agent | null>(null)
  const iname = (id: string | null) => insts.data?.find((i) => i.id === id)?.code ?? '—'
  const pname = (id: string | null) => profiles.data?.find((p) => p.id === id)

  const archive = useApiMutation((a: Agent) => api.post(`/agents/${a.id}/archive`), { invalidate: [['agents'], keys.accessMatrix], onSuccess: () => toast.push(t('common.archived')), onError: (e) => toast.push(errorMessage(e, t), 'danger') })
  const clone = useApiMutation((a: Agent) => api.post(`/agents/${a.id}/clone`, { copy_grants: true }), { invalidate: [['agents'], keys.accessMatrix], onSuccess: () => toast.push(t('agents.cloned')), onError: (e) => toast.push(errorMessage(e, t), 'danger') })

  return (
    <>
      <PageHeader title={t('agents.title')} description={t('agents.description')} actions={<Button variant="primary" onClick={() => setEditing('new')}>{t('agents.new')}</Button>} />
      <div className="mb-3"><Checkbox label={t('geo.showArchived')} checked={archived} onChange={(e) => setArchived(e.target.checked)} /></div>
      <QueryState q={agents} what="(/agents)">
        {(rows) => rows.length === 0 ? <EmptyState title={t('agents.empty')} hint={t('agents.emptyHint')} /> : (
          <Table caption={t('agents.title')}>
            <THead><Tr><Th>{t('common.code')}</Th><Th>{t('common.name')}</Th><Th>{t('agents.roleKind')}</Th><Th>{t('geo.institution')}</Th><Th>{t('agents.model')}</Th><Th>{t('agents.tools')}</Th><Th>{t('common.status')}</Th><Th><span className="sr-only">{t('common.actions')}</span></Th></Tr></THead>
            <TBody>{rows.map((a) => {
              const prof = pname(a.model_profile_id)
              return (
                <Tr key={a.id}>
                  <Td className="font-mono">{a.code}</Td><Td className="font-medium">{a.name}</Td><Td>{t(`agents.roleKinds.${a.role_kind}`, a.role_kind)}</Td><Td>{iname(a.institution_id)}</Td>
                  <Td>{prof ? <>{prof.name}{prof.provider !== 'openai_compat' && <> <Badge tone="warn">{prof.provider === 'scripted' ? t('common.noAiShort') : prof.provider}</Badge></>}</> : <Badge tone="warn">{t('agents.noProfile')}</Badge>}</Td>
                  <Td className="text-xs">{a.tools.join(', ')}</Td>
                  <Td><StatusBadge status={a.archived_at ? 'archived' : 'active'} /></Td>
                  <Td><div className="flex flex-wrap gap-1">
                    <Button size="sm" onClick={() => setEditing(a)}>{t('common.edit')}</Button>
                    <Button size="sm" onClick={() => setPreview(a)}>{t('agents.promptPreview')}</Button>
                    <Button size="sm" onClick={() => clone.mutate(a)}>{t('agents.clone')}</Button>
                    {!a.archived_at && <Button size="sm" onClick={() => archive.mutate(a)}>{t('common.archive')}</Button>}
                  </div></Td>
                </Tr>
              )
            })}</TBody>
          </Table>
        )}
      </QueryState>
      <ModelProfiles />
      {editing && <AgentDialog agent={editing === 'new' ? null : editing} institutions={insts.data ?? []} profiles={profiles.data ?? []} onClose={() => setEditing(null)} />}
      {preview && <PromptDialog agent={preview} onClose={() => setPreview(null)} />}
    </>
  )
}

function AgentDialog({ agent, institutions, profiles, onClose }: { agent: Agent | null; institutions: Institution[]; profiles: ModelProfile[]; onClose: () => void }) {
  const { t } = useTranslation()
  const toast = useToast()
  const lim = (k: string, d: number) => Number((agent?.limits as Record<string, number> | undefined)?.[k] ?? d)
  const { register, handleSubmit, setError, formState: { errors } } = useForm<FormIn, unknown, FormOut>({
    resolver: zodResolver(schema),
    defaultValues: {
      code: agent?.code ?? '', name: agent?.name ?? '', role_kind: (agent?.role_kind as typeof ROLE_KINDS[number]) ?? 'institution', institution_id: agent?.institution_id ?? '',
      mission: agent?.mission ?? '', instructions: agent?.instructions ?? '', model_profile_id: agent?.model_profile_id ?? '', tools: agent?.tools ?? ['search_kb', 'post', 'decide'],
      max_steps: lim('max_steps', 4), max_search_calls: lim('max_search_calls', 3), max_legal_calls_per_inject: lim('max_legal_calls_per_inject', 2),
    },
  })
  const save = useApiMutation((v: FormOut) => {
    const body = {
      code: v.code, name: v.name, role_kind: v.role_kind, institution_id: v.institution_id || null, mission: v.mission ?? '', instructions: v.instructions ?? '',
      model_profile_id: v.model_profile_id || null, tools: v.tools,
      limits: { max_steps: v.max_steps, max_search_calls: v.max_search_calls, max_legal_calls_per_inject: v.max_legal_calls_per_inject },
    }
    return agent ? api.patch(`/agents/${agent.id}`, body) : api.post('/agents', body)
  }, {
    invalidate: [['agents'], keys.accessMatrix], onSuccess: () => { toast.push(t('common.saved')); onClose() },
    onError: (e) => { for (const [k, m] of Object.entries(fieldErrors(e))) if (k in schema.shape) setError(k as keyof FormIn, { message: m }); toast.push(errorMessage(e, t), 'danger') },
  })
  return (
    <Dialog open wide onClose={onClose} title={agent ? t('agents.edit') : t('agents.new')}
      footer={<><Button onClick={onClose}>{t('common.cancel')}</Button><Button variant="primary" type="submit" form="agent-form" loading={save.isPending}>{t('common.save')}</Button></>}>
      <form id="agent-form" noValidate className="grid gap-3 md:grid-cols-2" onSubmit={handleSubmit((v) => save.mutate(v))}>
        <Field label={t('common.code')} required error={errors.code && t('common.required')}><Input data-autofocus {...register('code')} /></Field>
        <Field label={t('common.name')} required error={errors.name && t('common.required')}><Input {...register('name')} /></Field>
        <Field label={t('agents.roleKind')} hint={t('agents.roleKindHint')}><Select {...register('role_kind')}>{ROLE_KINDS.map((r) => <option key={r} value={r}>{t(`agents.roleKinds.${r}`)}</option>)}</Select></Field>
        <Field label={t('geo.institution')}><Select {...register('institution_id')}><option value="">—</option>{institutions.map((i) => <option key={i.id} value={i.id}>{i.code} — {i.name}</option>)}</Select></Field>
        <Field label={t('agents.mission')} className="md:col-span-2"><Textarea {...register('mission')} /></Field>
        <Field label={t('agents.instructions')} className="md:col-span-2" hint={t('agents.instructionsHint')}><Textarea rows={5} {...register('instructions')} /></Field>
        <Field label={t('agents.model')}><Select {...register('model_profile_id')}><option value="">—</option>{profiles.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.provider})</option>)}</Select></Field>
        <fieldset><legend className="mb-1 text-sm font-medium">{t('agents.tools')}</legend>
          <div className="flex flex-wrap gap-3">{TOOLS.map((tool) => <label key={tool} className="inline-flex items-center gap-1 text-sm"><input type="checkbox" value={tool} className="h-4 w-4" {...register('tools')} />{tool}</label>)}</div>
        </fieldset>
        <Field label={t('agents.maxSteps')} error={errors.max_steps && t('agents.limitInvalid')}><Input type="number" {...register('max_steps')} /></Field>
        <Field label={t('agents.maxSearch')} error={errors.max_search_calls && t('agents.limitInvalid')}><Input type="number" {...register('max_search_calls')} /></Field>
        <Field label={t('agents.maxLegal')} error={errors.max_legal_calls_per_inject && t('agents.limitInvalid')}><Input type="number" {...register('max_legal_calls_per_inject')} /></Field>
      </form>
    </Dialog>
  )
}

function PromptDialog({ agent, onClose }: { agent: Agent; onClose: () => void }) {
  const { t } = useTranslation()
  const q = useApiQuery<PromptPreview>(keys.promptPreview(agent.id), `/agents/${agent.id}/prompt-preview`)
  return (
    <Dialog open wide onClose={onClose} title={`${t('agents.promptPreview')} — ${agent.code}`}>
      <p className="mb-2 text-sm text-muted">{t('agents.promptHint')}</p>
      <QueryState q={q} what="(/prompt-preview)">
        {(p) => (
          <>
            <p className="mb-2 flex flex-wrap gap-2 text-xs"><Badge tone="info">v {p.version}</Badge><Badge tone="info">≈ {p.approx_tokens} tokens</Badge><Badge tone={p.mandates_included ? 'ok' : 'warn'}>{t('agents.mandatesIncluded', { n: p.mandates_included })}</Badge><Badge tone="info">{t('agents.grantedKbs', { n: p.granted_kb_ids.length })}</Badge></p>
            <pre className="max-h-[50vh] overflow-auto rounded bg-surface2 p-3 text-xs whitespace-pre-wrap">{p.system_prompt}</pre>
          </>
        )}
      </QueryState>
    </Dialog>
  )
}

const profileSchema = z.object({
  name: z.string().trim().min(1), provider: z.enum(['openai_compat', 'scripted', 'cassette']), endpoint_ref: z.string().optional(), model: z.string().optional(),
  temperature: z.coerce.number().min(0).max(2), max_tokens: z.coerce.number().int().min(1), timeout_s: z.coerce.number().min(1),
})
type PIn = z.input<typeof profileSchema>
type POut = z.output<typeof profileSchema>

function ModelProfiles() {
  const { t } = useTranslation()
  const toast = useToast()
  const q = useApiQuery<ModelProfile[]>(keys.modelProfiles, '/model-profiles')
  const [open, setOpen] = useState(false)
  const [results, setResults] = useState<Record<string, ProfileTest>>({})
  const test = useApiMutation((p: ModelProfile) => api.post<ProfileTest>(`/model-profiles/${p.id}/test`).then((r) => ({ id: p.id, r })), {
    onSuccess: ({ id, r }) => setResults((x) => ({ ...x, [id]: r })), onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  const { register, handleSubmit, reset, formState: { errors } } = useForm<PIn, unknown, POut>({ resolver: zodResolver(profileSchema), defaultValues: { provider: 'openai_compat', temperature: 0, max_tokens: 1024, timeout_s: 120 } })
  const create = useApiMutation((v: POut) => api.post('/model-profiles', { ...v, endpoint_ref: v.endpoint_ref || null, model: v.model || null }), {
    invalidate: [keys.modelProfiles], onSuccess: () => { setOpen(false); reset(); toast.push(t('common.created')) }, onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  return (
    <Section title={t('agents.profiles')} className="mt-8" actions={<Button onClick={() => setOpen(true)}>{t('agents.newProfile')}</Button>}>
      <p className="mb-2 text-sm text-muted">{t('agents.profilesHint')}</p>
      <QueryState q={q} what="(/model-profiles)">
        {(rows) => rows.length === 0 ? <EmptyState title={t('agents.noProfiles')} /> : (
          <Table caption={t('agents.profiles')}>
            <THead><Tr><Th>{t('common.name')}</Th><Th>{t('agents.provider')}</Th><Th>{t('agents.modelName')}</Th><Th>{t('agents.endpointRef')}</Th><Th>{t('agents.connection')}</Th></Tr></THead>
            <TBody>{rows.map((p) => {
              const r = results[p.id]
              return (
                <Tr key={p.id}>
                  <Td className="font-medium">{p.name}</Td><Td>{p.provider}{p.provider !== 'openai_compat' && <> <Badge tone="warn">{t('common.noAiShort')}</Badge></>}</Td><Td>{p.model ?? '—'}</Td><Td><Mono>{p.endpoint_ref ?? '—'}</Mono></Td>
                  <Td>
                    <Button size="sm" loading={test.isPending && test.variables?.id === p.id} onClick={() => test.mutate(p)}>{t('agents.testConnection')}</Button>
                    {r && <p role="status" className="mt-1 text-xs">{r.ok ? <Badge tone="ok">{t('agents.reachable')} · {r.ms} ms</Badge> : <Badge tone="danger">{t('agents.unreachable')}</Badge>} {r.label} {r.error && <span className="text-danger">{r.error}</span>}</p>}
                  </Td>
                </Tr>
              )
            })}</TBody>
          </Table>
        )}
      </QueryState>
      <Dialog open={open} onClose={() => setOpen(false)} title={t('agents.newProfile')}
        footer={<><Button onClick={() => setOpen(false)}>{t('common.cancel')}</Button><Button variant="primary" type="submit" form="profile-form" loading={create.isPending}>{t('common.create')}</Button></>}>
        <form id="profile-form" noValidate className="flex flex-col gap-3" onSubmit={handleSubmit((v) => create.mutate(v))}>
          <Field label={t('common.name')} required error={errors.name && t('common.required')}><Input data-autofocus {...register('name')} /></Field>
          <Field label={t('agents.provider')}><Select {...register('provider')}><option value="openai_compat">openai_compat</option><option value="scripted">scripted</option><option value="cassette">cassette</option></Select></Field>
          <Field label={t('agents.modelName')}><Input {...register('model')} /></Field>
          <Field label={t('agents.endpointRef')} hint={t('agents.endpointRefHint')}><Input {...register('endpoint_ref')} /></Field>
          <div className="grid grid-cols-3 gap-2">
            <Field label={t('agents.temperature')}><Input type="number" step="0.1" {...register('temperature')} /></Field>
            <Field label={t('agents.maxTokens')}><Input type="number" {...register('max_tokens')} /></Field>
            <Field label={t('agents.timeout')}><Input type="number" {...register('timeout_s')} /></Field>
          </div>
        </form>
      </Dialog>
    </Section>
  )
}
