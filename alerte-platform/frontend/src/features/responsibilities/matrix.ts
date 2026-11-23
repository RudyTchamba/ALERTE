/**
 * Carte des responsabilités : classement pur (sans appel réseau) des couples action × institution
 * à partir du registre des mandats. Garde-fou : une absence n'est affirmée (« personne ») que si le
 * registre de TOUTES les institutions concernées a été déclaré complet par un humain.
 */

export interface MAction { code: string; label: string; reference_note?: string | null }
export interface MInstitution { id: string; code: string; name: string }
export interface MSource { article?: string | null; quote?: string | null; page?: number | null }
export interface MMandate {
  id: string; institution_id: string; action_code: string; kind: string; active?: boolean; validation: string
  procedure_status?: string; has_deadline?: boolean; description?: string; sources?: MSource[]
}

/** Types de mandat qui font d'une institution un « responsable » de l'action (et non un simple rôle annexe). */
export const OWNER_KINDS = new Set(['duty', 'power', 'lead', 'procedure', 'coordination'])

export type CellState = 'lead' | 'responsible' | 'proposed' | 'involved' | 'none'
export type RowState = 'covered' | 'overlap' | 'orphan' | 'undetermined'

export interface Cell { state: CellState; mandates: MMandate[] }
export interface Row { action: MAction; cells: Record<string, Cell>; state: RowState; owners: string[] }

export function cellOf(ms: MMandate[]): Cell {
  const active = ms.filter((m) => m.active)
  if (active.some((m) => m.kind === 'lead')) return { state: 'lead', mandates: ms }
  if (active.some((m) => OWNER_KINDS.has(m.kind))) return { state: 'responsible', mandates: ms }
  if (active.length > 0) return { state: 'involved', mandates: ms }
  if (ms.some((m) => m.validation !== 'rejected')) return { state: 'proposed', mandates: ms }
  return { state: 'none', mandates: ms }
}

export function buildMatrix(actions: MAction[], institutions: MInstitution[], mandates: MMandate[], reviewedComplete: Set<string>): Row[] {
  const allReviewed = institutions.length > 0 && institutions.every((i) => reviewedComplete.has(i.id))
  return actions.map((action) => {
    const cells: Record<string, Cell> = {}
    for (const inst of institutions) cells[inst.id] = cellOf(mandates.filter((m) => m.action_code === action.code && m.institution_id === inst.id))
    const owners = institutions.filter((i) => cells[i.id].state === 'lead' || cells[i.id].state === 'responsible').map((i) => i.id)
    const hasLead = institutions.some((i) => cells[i.id].state === 'lead')
    let state: RowState
    if (owners.length === 0) state = allReviewed ? 'orphan' : 'undetermined'
    else if (owners.length > 1 && !hasLead) state = 'overlap'
    else state = 'covered'
    return { action, cells, state, owners }
  })
}

export function summarize(rows: Row[]) {
  const by = (s: RowState) => rows.filter((r) => r.state === s).length
  const covered = by('covered')
  return { total: rows.length, covered, overlap: by('overlap'), orphan: by('orphan'), undetermined: by('undetermined'),
    coverage: rows.length ? Math.round(((covered + by('overlap')) / rows.length) * 100) : 0 }
}
