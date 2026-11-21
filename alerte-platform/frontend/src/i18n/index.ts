import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import { localGet, localSet } from '@/lib/storage'
import en from './en'
import fr from './fr'

export const LANGS = ['en', 'fr'] as const
export type Lang = (typeof LANGS)[number]
const stored = localGet('alerte.lang')
const initial: Lang = stored === 'fr' ? 'fr' : 'en'

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, fr: { translation: fr } },
  lng: initial,
  fallbackLng: 'en', // French is planned (P1): untranslated keys fall back to the complete English set
  interpolation: { escapeValue: false },
  returnNull: false,
  react: { useSuspense: false },
})

export function setLanguage(l: Lang) {
  localSet('alerte.lang', l)
  void i18n.changeLanguage(l)
  document.documentElement.lang = l
}

export default i18n
