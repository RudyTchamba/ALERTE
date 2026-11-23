import { describe, expect, it } from 'vitest'
import { quoteFrom } from './PlayerPage'

/** Même normalisation que le contrôle backend (app/agents/citations.py : normalize_text). */
const norm = (s: string) => s.normalize('NFC').toLowerCase().replace(/[\p{P}\p{Z}\n\t]/gu, ' ').split(/\s+/).filter(Boolean).join(' ')

const REAL = "Article 1er\nLa Protection Civile consiste à assurer en permanence la protection des personnes, des\nbiens et de l’environnement contre les risques d’accidents graves Des calamités ou de\ncatastrophes, ainsi que contre les effets de ces Sinistres.\nLa Protection Civile comporte des meure de prétention, de protection et d’organisation des\nsecours."

describe('quoteFrom', () => {
  it('picks the first sentence of a real excerpt, without the article heading, and it passes the citation check', () => {
    const q = quoteFrom(REAL)
    expect(q.startsWith('La Protection Civile consiste')).toBe(true)
    expect(q.endsWith('Sinistres.')).toBe(true)
    expect(q.length).toBeGreaterThanOrEqual(20)
    expect(norm(REAL)).toContain(norm(q))
  })

  it('caps long text at a word boundary and keeps it verbatim', () => {
    const long = 'Le Service des Télécommunications d’Urgence est chargé ' + 'de la conception et de la mise en œuvre des plans d’urgence '.repeat(10)
    const q = quoteFrom(long)
    expect(q.length).toBeLessThanOrEqual(240)
    expect(norm(long)).toContain(norm(q))
  })
})
