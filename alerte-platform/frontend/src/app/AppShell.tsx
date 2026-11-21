import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Menu, LogOut, Info } from 'lucide-react'
import { cn } from '@/lib/cn'
import { LANGS, setLanguage, type Lang } from '@/i18n'
import { Button, Select } from '@/components/ui'
import { useAuth } from './auth'
import { useTheme, type Theme } from './theme'

export function FictionalBanner() {
  const { t } = useTranslation()
  return (
    <div role="note" className="flex items-center justify-center gap-2 bg-[var(--banner)] px-3 py-1.5 text-center text-sm font-bold text-[var(--bg)]">
      <Info className="h-4 w-4 shrink-0" aria-hidden />
      {t('common.fictionalBanner')}
    </div>
  )
}

const NAV: { group: string; items: { to: string; key: string; end?: boolean }[] }[] = [
  { group: 'studio', items: [
    { to: '/', key: 'home', end: true },
    { to: '/studio/countries', key: 'countries' },
    { to: '/studio/knowledge', key: 'knowledge' },
    { to: '/studio/agents', key: 'agents' },
    { to: '/studio/access', key: 'access' },
    { to: '/studio/scenarios', key: 'scenarios' },
    { to: '/studio/exercises', key: 'exercises' },
  ] },
  { group: 'room', items: [{ to: '/room', key: 'room_live' }] },
  { group: 'transverse', items: [
    { to: '/gaps', key: 'gaps' },
    { to: '/reports', key: 'reports' },
    { to: '/audit', key: 'audit' },
    { to: '/evaluation', key: 'evaluation' },
    { to: '/about/architecture', key: 'architecture' },
  ] },
  { group: 'settings', items: [{ to: '/settings/tokens', key: 'tokens' }] },
]

export function AppShell() {
  const { t, i18n } = useTranslation()
  const { workspace, role, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const [theme, setTheme] = useTheme()
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="skip-link">{t('common.skipToContent')}</a>
      <FictionalBanner />
      <header className="flex flex-wrap items-center gap-3 border-b border-line bg-surface px-4 py-2">
        <Button className="lg:hidden" aria-expanded={open} aria-controls="main-nav" aria-label={t('nav.menu')} onClick={() => setOpen((o) => !o)}>
          <Menu className="h-4 w-4" aria-hidden />
        </Button>
        <span className="text-lg font-extrabold tracking-wide">{t('common.appName')}</span>
        <span className="hidden text-sm text-muted md:inline">{t('common.tagline')}</span>
        <div className="ml-auto flex flex-wrap items-center gap-2 text-sm">
          {workspace && <span><span className="text-muted">{t('nav.workspace')}:</span> <strong>{workspace.name}</strong>{role && <span className="text-muted"> · {role}</span>}</span>}
          <label className="sr-only" htmlFor="theme-select">{t('common.theme.label')}</label>
          <Select id="theme-select" className="!w-auto !min-h-8 !py-1" value={theme} onChange={(e) => setTheme(e.target.value as Theme)}>
            <option value="system">{t('common.theme.system')}</option>
            <option value="light">{t('common.theme.light')}</option>
            <option value="dark">{t('common.theme.dark')}</option>
          </Select>
          <label className="sr-only" htmlFor="lang-select">{t('common.language')}</label>
          <Select id="lang-select" className="!w-auto !min-h-8 !py-1" value={i18n.language} onChange={(e) => setLanguage(e.target.value as Lang)}>
            {LANGS.map((l) => <option key={l} value={l}>{l.toUpperCase()}</option>)}
          </Select>
          <Button size="sm" onClick={logout} icon={<LogOut className="h-4 w-4" aria-hidden />}>{t('nav.logout')}</Button>
        </div>
      </header>
      <div className="flex flex-1">
        <nav id="main-nav" aria-label={t('nav.main')} className={cn('w-60 shrink-0 border-r border-line bg-surface p-3 lg:block', open ? 'block' : 'hidden')}>
          {NAV.map((g) => (
            <div key={g.group} className="mb-4">
              <p className="mb-1 px-2 text-xs font-bold tracking-wider text-muted uppercase">{t(`nav.${g.group}`)}</p>
              <ul>
                {g.items.map((i) => (
                  <li key={i.to}>
                    <NavLink to={i.to} end={i.end} onClick={() => setOpen(false)}
                      className={({ isActive }) => cn('block rounded px-2 py-1.5 text-sm no-underline', isActive ? 'bg-brandsoft font-semibold text-brand' : 'text-ink hover:bg-surface2')}>
                      {t(`nav.${i.key}`)}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
        <main id="main" tabIndex={-1} className="min-w-0 flex-1 p-4 lg:p-6"><Outlet /></main>
      </div>
    </div>
  )
}

/** Banner shown on every exercise-scoped screen when the exercise does not use a real model. */
export function NoAiBanner({ aiMode }: { aiMode: string | null | undefined }) {
  const { t } = useTranslation()
  if (!aiMode || aiMode === 'ai') return null
  return (
    <div role="status" className="mb-3 rounded-md border-2 border-warn bg-warnsoft px-3 py-2 text-sm font-bold text-warn">
      {aiMode === 'cassette' ? t('common.replayBanner') : t('common.noAiBanner')}
    </div>
  )
}
