import { useState, type ComponentType } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  BookOpenText, Bot, FileBarChart2, Flag, FlaskConical, Gauge, Grid3x3, Home, KeyRound, Landmark, LogOut, Menu, Network, Radio, ScrollText,
  SearchCheck, ShieldCheck, TriangleAlert, Workflow, X, CircleHelp,
} from 'lucide-react'
import { cn } from '@/lib/cn'
import { LANGS, setLanguage, type Lang } from '@/i18n'
import { Button, LogoMark, Select } from '@/components/ui'
import { JourneyBar } from '@/components/JourneyBar'
import { useAuth } from './auth'
import { useTheme, type Theme } from './theme'

export function FictionalBanner() {
  const { t } = useTranslation()
  return (
    <aside aria-label={t('common.fictionalBanner')} className="hazard flex items-center justify-center gap-2 px-3 py-1 text-center text-xs font-extrabold tracking-[0.14em] uppercase">
      <span className="flex items-center gap-2 rounded bg-banner px-2 py-0.5">
        <TriangleAlert className="h-3.5 w-3.5 shrink-0" aria-hidden />
        {t('common.fictionalBanner')}
      </span>
    </aside>
  )
}

type NavItem = { to: string; key: string; icon: ComponentType<{ className?: string }>; end?: boolean }
type NavGroup = { group: string; step?: number; hint?: string; items: NavItem[] }

/** Navigation par phases d'un exercice : Préparer → Jouer → Analyser. */
const NAV: NavGroup[] = [
  { group: 'prepare', step: 1, hint: 'prepareHint', items: [
    { to: '/studio/countries', key: 'countries', icon: Landmark },
    { to: '/studio/knowledge', key: 'knowledge', icon: BookOpenText },
    { to: '/studio/agents', key: 'agents', icon: Bot },
    { to: '/studio/access', key: 'access', icon: ShieldCheck },
    { to: '/studio/scenarios', key: 'scenarios', icon: Workflow },
  ] },
  { group: 'play', step: 2, hint: 'playHint', items: [
    { to: '/studio/exercises', key: 'exercises', icon: Flag },
    { to: '/room', key: 'room_live', icon: Radio },
  ] },
  { group: 'analyze', step: 3, hint: 'analyzeHint', items: [
    { to: '/responsibilities', key: 'responsibilities', icon: Grid3x3 },
    { to: '/gaps', key: 'gaps', icon: SearchCheck },
    { to: '/what-if', key: 'whatif', icon: FlaskConical },
    { to: '/reports', key: 'reports', icon: FileBarChart2 },
    { to: '/audit', key: 'audit', icon: ScrollText },
    { to: '/evaluation', key: 'evaluation', icon: Gauge },
  ] },
  { group: 'system', items: [
    { to: '/about/architecture', key: 'architecture', icon: Network },
    { to: '/settings/tokens', key: 'tokens', icon: KeyRound },
    { to: '/help/glossary', key: 'glossary', icon: CircleHelp },
  ] },
]

function NavEntry({ item, onNavigate }: { item: NavItem; onNavigate: () => void }) {
  const { t } = useTranslation()
  const Icon = item.icon
  return (
    <NavLink to={item.to} end={item.end} onClick={onNavigate}
      className={({ isActive }) => cn(
        'group relative flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm no-underline transition-colors',
        isActive ? 'bg-brandsoft font-semibold text-brand' : 'text-ink hover:bg-surface2',
      )}>
      {({ isActive }) => (
        <>
          {isActive && <span aria-hidden className="absolute top-1.5 bottom-1.5 -left-3 w-1 rounded-r bg-brand" />}
          <Icon className={cn('h-4 w-4 shrink-0', isActive ? 'text-brand' : 'text-muted group-hover:text-ink')} aria-hidden />
          {t(`nav.${item.key}`)}
        </>
      )}
    </NavLink>
  )
}

export function AppShell() {
  const { t, i18n } = useTranslation()
  const { workspace, role, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const [theme, setTheme] = useTheme()
  const close = () => setOpen(false)
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="skip-link">{t('common.skipToContent')}</a>
      <FictionalBanner />
      <header className="sticky top-0 z-30 flex flex-wrap items-center gap-3 border-b border-line bg-surface/85 px-4 py-2 shadow-[0_8px_24px_-20px_rgba(0,0,0,0.6)] backdrop-blur-md">
        <Button size="sm" variant="ghost" className="lg:hidden" aria-expanded={open} aria-controls="main-nav" aria-label={open ? t('nav.closeMenu') : t('nav.openMenu')} onClick={() => setOpen((o) => !o)}>
          {open ? <X className="h-5 w-5" aria-hidden /> : <Menu className="h-5 w-5" aria-hidden />}
        </Button>
        <NavLink to="/" className="flex items-center gap-2.5 text-ink no-underline" aria-label={`${t('common.appName')} — ${t('nav.home')}`}>
          <span className="grid h-9 w-9 place-items-center rounded-xl border border-brand/40 bg-brandsoft shadow-[0_6px_18px_-8px_var(--brand)]"><LogoMark className="h-5 w-5" /></span>
          <span className="flex flex-col leading-none">
            <span className="text-base font-black tracking-[0.18em]">{t('common.appName')}</span>
            <span className="hidden text-xs text-muted md:inline">{t('common.tagline')}</span>
          </span>
        </NavLink>
        <div className="ml-auto flex flex-wrap items-center gap-2 text-sm">
          {workspace && (
            <span className="hidden items-center gap-2 rounded-lg border border-line bg-surface2 px-2.5 py-1 sm:inline-flex">
              <span className="eyebrow">{t('nav.workspace')}</span>
              <strong className="max-w-48 truncate">{workspace.name}</strong>
              {role && <span className="rounded bg-brandsoft px-1.5 text-xs font-semibold text-brand">{role}</span>}
            </span>
          )}
          <label className="sr-only" htmlFor="theme-select">{t('common.theme.label')}</label>
          <Select id="theme-select" className="!w-auto !min-h-8 !py-1" value={theme} onChange={(e) => setTheme(e.target.value as Theme)}>
            <option value="dark">{t('common.theme.dark')}</option>
            <option value="light">{t('common.theme.light')}</option>
            <option value="system">{t('common.theme.system')}</option>
          </Select>
          <label className="sr-only" htmlFor="lang-select">{t('common.language')}</label>
          <Select id="lang-select" className="!w-auto !min-h-8 !py-1" value={i18n.language} onChange={(e) => setLanguage(e.target.value as Lang)}>
            {LANGS.map((l) => <option key={l} value={l}>{l.toUpperCase()}</option>)}
          </Select>
          <Button size="sm" variant="ghost" onClick={logout} icon={<LogOut className="h-4 w-4" aria-hidden />}>{t('nav.logout')}</Button>
        </div>
      </header>
      <div className="flex flex-1">
        <div className={cn('w-64 shrink-0 border-r border-line bg-surface/80 backdrop-blur lg:block', open ? 'block' : 'hidden')}>
        <nav id="main-nav" aria-label={t('nav.main')} className="px-3 py-4 lg:sticky lg:top-[3.25rem] lg:max-h-[calc(100vh-3.25rem)] lg:overflow-y-auto">
          <div className="mb-4"><NavEntry item={{ to: '/', key: 'home', icon: Home, end: true }} onNavigate={close} /></div>
          {NAV.map((g) => (
            <div key={g.group} className="mb-5">
              <div className="mb-1.5 flex items-center gap-2 px-2.5">
                {g.step && <span aria-hidden className="grid h-5 w-5 place-items-center rounded-md border border-line bg-surface2 text-xs font-bold text-brand tabular">{g.step}</span>}
                <p className="eyebrow">{t(`nav.${g.group}`)}</p>
              </div>
              {g.hint && <p className="mb-1.5 px-2.5 text-xs leading-snug text-muted">{t(`nav.${g.hint}`)}</p>}
              <ul className="flex flex-col gap-0.5">
                {g.items.map((i) => <li key={i.to}><NavEntry item={i} onNavigate={close} /></li>)}
              </ul>
            </div>
          ))}
        </nav>
        </div>
        <main id="main" tabIndex={-1} className="min-w-0 flex-1 p-4 lg:p-8"><div className="mx-auto max-w-[1600px]"><JourneyBar /><Outlet /></div></main>
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
