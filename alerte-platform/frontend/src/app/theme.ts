import { useCallback, useState } from 'react'
import { localGet, localSet } from '@/lib/storage'

export type Theme = 'light' | 'dark' | 'system'

export function applyTheme(t: Theme) {
  const el = document.documentElement
  if (t === 'system') el.removeAttribute('data-theme')
  else el.setAttribute('data-theme', t)
}

/** Thème enregistré ; à défaut, sombre (ambiance « centre de crise »). « system » suit le système d'exploitation. */
function storedTheme(): Theme {
  const s = localGet('alerte.theme')
  return s === 'light' || s === 'dark' || s === 'system' ? s : 'dark'
}

export function initTheme() {
  applyTheme(storedTheme())
}

export function useTheme(): [Theme, (t: Theme) => void] {
  const [theme, setTheme] = useState<Theme>(storedTheme)
  const set = useCallback((t: Theme) => {
    localSet('alerte.theme', t)
    applyTheme(t)
    setTheme(t)
  }, [])
  return [theme, set]
}
