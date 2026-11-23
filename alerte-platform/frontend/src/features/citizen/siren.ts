import type { TFunction } from 'i18next'

/**
 * Signal d'attention des alertes d'urgence (853 Hz + 960 Hz superposés, par impulsions), plus vibration.
 * L'AudioContext doit être créé ou repris pendant un geste de l'utilisateur (bouton « Je suis prêt ») :
 * les navigateurs mobiles bloquent le son sinon.
 */
export function unlockAudio(): AudioContext | null {
  try {
    const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!Ctor) return null
    const ctx = new Ctor()
    void ctx.resume()
    // Un son silencieux très court « débloque » la sortie audio sur iOS.
    const o = ctx.createOscillator(), g = ctx.createGain()
    g.gain.value = 0
    o.connect(g).connect(ctx.destination)
    o.start(); o.stop(ctx.currentTime + 0.05)
    return ctx
  } catch {
    return null
  }
}

const VIBRATE = [500, 200, 500, 200, 500, 800]

export function startSiren(ctx: AudioContext | null, seconds = 10): () => void {
  let stopped = false
  const nodes: OscillatorNode[] = []
  try { navigator.vibrate?.(Array.from({ length: 4 }, () => VIBRATE).flat()) } catch { /* vibration facultative */ }
  if (ctx) {
    try {
      void ctx.resume()
      const gain = ctx.createGain()
      gain.connect(ctx.destination)
      const t0 = ctx.currentTime
      // Impulsions de 0,5 s toutes les 0,7 s.
      for (let t = 0; t < seconds; t += 0.7) {
        gain.gain.setValueAtTime(0.25, t0 + t)
        gain.gain.setValueAtTime(0, t0 + t + 0.5)
      }
      for (const f of [853, 960]) {
        const o = ctx.createOscillator()
        o.type = 'sine'
        o.frequency.value = f
        o.connect(gain)
        o.start(t0)
        o.stop(t0 + seconds)
        nodes.push(o)
      }
    } catch { /* son facultatif */ }
  }
  return () => {
    if (stopped) return
    stopped = true
    for (const o of nodes) { try { o.stop() } catch { /* déjà arrêté */ } }
    try { navigator.vibrate?.(0) } catch { /* vibration facultative */ }
  }
}

/** « 4 h », « 1 h 30 », « 45 min », « 1 j 6 h ». */
export function humanDelay(minutes: number, t: TFunction): string {
  const m = Math.max(0, Math.round(minutes))
  if (m < 60) return t('citizen.dur.m', { m })
  const d = Math.floor(m / 1440), h = Math.floor((m % 1440) / 60), r = m % 60
  if (d) return t('citizen.dur.d', { d, h })
  return r ? t('citizen.dur.hm', { h, m: String(r).padStart(2, '0') }) : t('citizen.dur.h', { h })
}
