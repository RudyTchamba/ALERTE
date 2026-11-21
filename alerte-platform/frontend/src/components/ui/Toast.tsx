import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { X } from 'lucide-react'
import { Badge, type Tone } from './Badge'

interface ToastItem { id: number; tone: Tone; text: string }
interface ToastApi { push: (text: string, tone?: Tone) => void }
const Ctx = createContext<ToastApi>({ push: () => undefined })

export function ToastProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  const [items, setItems] = useState<ToastItem[]>([])
  const push = useCallback((text: string, tone: Tone = 'ok') => {
    const id = Date.now() + Math.random()
    setItems((l) => [...l, { id, tone, text }])
    setTimeout(() => setItems((l) => l.filter((x) => x.id !== id)), tone === 'danger' ? 9000 : 5000)
  }, [])
  const api = useMemo(() => ({ push }), [push])
  return (
    <Ctx.Provider value={api}>
      {children}
      <div className="fixed right-3 bottom-3 z-[60] flex w-80 max-w-[calc(100vw-1.5rem)] flex-col gap-2" role="region" aria-label={t('common.notifications')}>
        {items.map((i) => (
          <div key={i.id} role={i.tone === 'danger' ? 'alert' : 'status'} className="flex items-start gap-2 rounded-md border border-line bg-surface p-3 text-sm shadow-lg">
            <Badge tone={i.tone}>{t(`common.tone.${i.tone}`)}</Badge>
            <span className="flex-1">{i.text}</span>
            <button type="button" aria-label={t('common.close')} onClick={() => setItems((l) => l.filter((x) => x.id !== i.id))}><X className="h-4 w-4" aria-hidden /></button>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  )
}
export const useToast = () => useContext(Ctx)
