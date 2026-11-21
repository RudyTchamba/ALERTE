import { useCallback, useState } from 'react'
import { localGet, localSet } from '@/lib/storage'

export type Theme = 'light' | 'dark' | 'system'

export function applyTheme(t: Theme) {
  const el = document.documentElement
  if (t === 'system') el.removeAttribute('data-theme')
  else el.setAttribute('data-theme', t)
}

export function initTheme() {
  const s = localGet('alerte.theme')
  applyTheme(s === 'light' || s === 'dark' ? s : 'system')
}

export function useTheme(): [Theme, (t: Theme) => void] {
  const [theme, setTheme] = useState<Theme>(() => {
    const s = localGet('alerte.theme')
    return s === 'light' || s === 'dark' ? s : 'system'
  })
  const set = useCallback((t: Theme) => {
    localSet('alerte.theme', t)
    applyTheme(t)
    setTheme(t)
  }, [])
  return [theme, set]
}
