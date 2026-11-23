import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Landmark, Radio, SearchCheck } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api, ApiError, fieldErrors } from '@/api/client'
import type { WorkspaceCreated } from '@/api/types'
import { useAuth } from '@/app/auth'
import { FictionalBanner } from '@/app/AppShell'
import { Button, Card, Field, Input, LogoMark, OneTimeSecret } from '@/components/ui'
import { errorMessage } from '@/lib/errors'

const createSchema = z.object({
  name: z.string().trim().min(1, 'required').max(200),
  slug: z.string().trim().regex(/^[a-z0-9][a-z0-9-]{1,98}$/, 'slug').or(z.literal('')).optional(),
})
type CreateForm = z.infer<typeof createSchema>

const tokenSchema = z.object({ token: z.string().trim().min(8, 'required') })
type TokenForm = z.infer<typeof tokenSchema>

export function EntryPage() {
  const { t } = useTranslation()
  const { login } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [created, setCreated] = useState<WorkspaceCreated | null>(null)
  const [saved, setSaved] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [tokenError, setTokenError] = useState<string | null>(null)

  const cf = useForm<CreateForm>({ resolver: zodResolver(createSchema) })
  const tf = useForm<TokenForm>({ resolver: zodResolver(tokenSchema) })

  const onCreate = cf.handleSubmit(async (v) => {
    setCreateError(null)
    try {
      const res = await api.post<WorkspaceCreated>('/workspaces', { name: v.name, slug: v.slug || undefined }, { token: null })
      setCreated(res)
    } catch (e) {
      for (const [k, m] of Object.entries(fieldErrors(e))) if (k === 'name' || k === 'slug') cf.setError(k, { message: m })
      setCreateError(errorMessage(e, t))
    }
  })

  const onToken = tf.handleSubmit(async (v) => {
    setTokenError(null)
    try {
      await api.get('/workspaces/current', { token: v.token })
      login(v.token)
      navigate('/')
    } catch (e) {
      setTokenError(e instanceof ApiError && e.status === 401 ? t('errors.auth.invalid_token') : errorMessage(e, t))
    }
  })

  const steps: { k: 'prepare' | 'play' | 'analyze'; icon: typeof Landmark }[] = [
    { k: 'prepare', icon: Landmark }, { k: 'play', icon: Radio }, { k: 'analyze', icon: SearchCheck },
  ]
  return (
    <div className="flex min-h-screen flex-col">
      <FictionalBanner />
      <main id="main" className="mx-auto max-w-4xl p-4 lg:p-8">
        <h1 className="mb-1 flex items-center gap-3 text-3xl font-extrabold"><LogoMark className="h-9 w-9" />{t('common.appName')}</h1>
        <p className="mb-6 text-muted">{t('common.tagline')}</p>
        <section aria-label={t('access.explain.title')} className="mb-5 rounded-md border border-line bg-surface p-4 text-sm">
          <h2 className="mb-1 text-base font-bold">{t('access.explain.title')}</h2>
          <p>{t('access.explain.text')}</p>
          <ul className="mt-2 list-disc pl-5 text-muted">
            <li>{t('access.explain.first')}</li>
            <li>{t('access.explain.existing')}</li>
            <li>{t('access.explain.demo')}</li>
          </ul>
        </section>
        {params.get('expired') && <p role="alert" className="mb-4 rounded-md border border-warn bg-warnsoft p-3 text-sm">{t('access.sessionExpired')}</p>}

        <div className="flex flex-col gap-4">
          {params.get('expired') && <p role="alert" className="rounded-lg border border-warn bg-warnsoft p-3 text-sm">{t('access.sessionExpired')}</p>}
          {created ? (
            <Card>
              <h2 className="mb-2 text-xl font-bold">{t('access.workspaceCreated', { name: created.workspace.name })}</h2>
              <OneTimeSecret value={created.owner_token} title={t('access.ownerToken')} />
              <label className="mt-4 flex items-center gap-2 text-sm">
                <input type="checkbox" checked={saved} onChange={(e) => setSaved(e.target.checked)} className="h-4 w-4" />
                {t('access.savedConfirm')}
              </label>
              <div className="mt-3">
                <Button variant="primary" disabled={!saved} onClick={() => { login(created.owner_token, 'owner'); navigate('/') }}>{t('access.continue')}</Button>
              </div>
            </Card>
          ) : (
            <>
            <Card className="border-brand/40">
              <h2 className="mb-1 text-lg font-bold">{t('access.signInTitle')}</h2>
              <p className="mb-3 text-sm text-muted">{t('access.signInHint')}</p>
              <form onSubmit={onToken} className="flex flex-col gap-3" noValidate>
                <Field label={t('access.tokenLabel')} required error={tf.formState.errors.token && t('common.required')}>
                  <Input type="password" autoComplete="off" spellCheck={false} {...tf.register('token')} />
                </Field>
                {tokenError && <p role="alert" className="text-sm text-danger">{tokenError}</p>}
                <Button type="submit" variant="primary" loading={tf.formState.isSubmitting}>{t('access.signInButton')}</Button>
              </form>
              <p className="mt-3 text-xs text-muted">{t('access.seatLinkHint')}</p>
            </Card>
            <Card>
              <h2 className="mb-1 text-lg font-bold">{t('access.createTitle')}</h2>
              <p className="mb-3 text-sm text-muted">{t('access.createHint')}</p>
              <form onSubmit={onCreate} className="flex flex-col gap-3" noValidate>
                <Field label={t('access.workspaceName')} required error={cf.formState.errors.name && t('common.required')}>
                  <Input autoComplete="organization" {...cf.register('name')} />
                </Field>
                <Field label={t('access.slug')} hint={t('access.slugHint')} error={cf.formState.errors.slug && t('access.slugInvalid')}>
                  <Input {...cf.register('slug')} />
                </Field>
                {createError && <p role="alert" className="text-sm text-danger">{createError}</p>}
                <Button type="submit" loading={cf.formState.isSubmitting}>{t('access.createButton')}</Button>
              </form>
            </Card>
            </>
          )}
        </div>
      </main>
    </div>
  )
}
