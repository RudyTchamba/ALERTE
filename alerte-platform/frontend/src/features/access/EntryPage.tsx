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
      <main id="main" className="mx-auto grid w-full max-w-6xl flex-1 items-center gap-10 p-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] lg:p-10">
        <section aria-labelledby="entry-title">
          <h1 id="entry-title" className="mb-8 flex items-center gap-3">
            <span className="grid h-12 w-12 place-items-center rounded-xl border border-line bg-surface2"><LogoMark className="h-7 w-7" /></span>
            <span className="flex flex-col leading-none">
              <span className="text-3xl font-black tracking-[0.18em]">{t('common.appName')}</span>
              <span className="mt-1 text-sm text-muted">{t('common.tagline')}</span>
            </span>
          </h1>
          <p className="eyebrow mb-3 flex items-center gap-2 text-brand"><span className="live-dot is-live text-brand" aria-hidden />{t('home.hero.eyebrow')}</p>
          <p className="max-w-xl text-3xl leading-tight font-black tracking-tight sm:text-4xl">{t('home.hero.title')}</p>
          <p className="mt-4 max-w-xl text-muted">{t('home.hero.lead')}</p>
          <div className="panel mt-6 max-w-xl p-4 text-sm">
            <h2 className="mb-1 text-base font-bold">{t('access.explain.title')}</h2>
            <p>{t('access.explain.text')}</p>
            <ul className="mt-2 list-disc pl-5 text-muted">
              <li>{t('access.explain.first')}</li>
              <li>{t('access.explain.existing')}</li>
              <li>{t('access.explain.demo')}</li>
            </ul>
          </div>
          <ol className="mt-8 grid gap-3 sm:grid-cols-3">
            {steps.map(({ k, icon: Icon }, i) => (
              <li key={k} className="panel p-3">
                <span className="mb-2 grid h-8 w-8 place-items-center rounded-lg border border-brand/40 text-brand"><Icon className="h-4 w-4" aria-hidden /></span>
                <span className="block text-sm font-bold"><span className="text-brand tabular">{i + 1}.</span> {t(`nav.${k}`)}</span>
                <span className="block text-xs text-muted">{t(`home.how.${k}`)}</span>
              </li>
            ))}
          </ol>
        </section>

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
