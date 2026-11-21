import { describe, expect, it } from 'vitest'
import en from './en'
import fr from './fr'

function keys(o: Record<string, unknown>, p = ''): string[] {
  return Object.entries(o).flatMap(([k, v]) => (v && typeof v === 'object' ? keys(v as Record<string, unknown>, `${p}${k}.`) : [`${p}${k}`]))
}

describe('i18n', () => {
  it('le français couvre exactement les mêmes clés que l\'anglais', () => {
    const e = new Set(keys(en)), f = new Set(keys(fr))
    expect([...e].filter((k) => !f.has(k))).toEqual([])
    expect([...f].filter((k) => !e.has(k))).toEqual([])
  })
  it('les variables d\'interpolation sont identiques', () => {
    const flat = (o: Record<string, unknown>): Record<string, string> => Object.fromEntries(keys(o).map((k) => [k, k.split('.').reduce((a: any, c) => a[c], o) as string]))
    const E = flat(en), F = flat(fr)
    const vars = (s: string) => (s.match(/{{\s*\w+\s*}}/g) ?? []).sort().join(',')
    const bad = Object.keys(E).filter((k) => vars(E[k]) !== vars(F[k]))
    expect(bad).toEqual([])
  })
})
