/**
 * Parcours de préparation d'un exercice : 10 étapes dont l'état est CALCULÉ sur les données réellement enregistrées
 * (jamais « terminé » parce qu'une page a été ouverte). Fonction pure : testée dans setup.test.ts.
 */
export type SetupStatus = 'done' | 'partial' | 'todo' | 'locked'

export interface SetupInput {
  countries: { id: string }[]
  institutions: { id: string; country_id?: string | null }[]
  kbs: { id: string; kind?: string; country_id?: string | null; overview?: { published_version_no?: number | null } | null }[]
  mandates: { institution_id: string; validation: string; sources?: unknown[] | null }[]
  reviews: { institution_id: string; status: string }[]
  agents: { id: string; institution_id?: string | null; kb_ids?: string[] | null }[]
  scenarios: { id: string }[]
  exercises: { id: string; state: string }[]
}

export type SetupId =
  | 'country' | 'institutions' | 'kb' | 'mandates' | 'agents' | 'access' | 'scenario' | 'exercise' | 'readiness' | 'run'

export interface SetupStep {
  id: SetupId
  status: SetupStatus
  /** Où aller pour agir (route, éventuellement avec `?tab=`). */
  to: string
  /** Paramètres pour le texte de détail i18n `setup.steps.<id>.<detailKey>`. */
  detailKey: string
  detail: Record<string, number>
  /** Étapes qu'il faut terminer d'abord (affichées quand `status === 'locked'`). */
  needs: SetupId[]
}

const FINISHED = ['completed', 'stopped', 'archived']
const STARTED = ['running', 'paused', ...FINISHED]

export function computeSetup(d: SetupInput): SetupStep[] {
  const nC = d.countries.length
  const nI = d.institutions.length
  const kbPublished = d.kbs.filter((k) => k.overview?.published_version_no).length
  const kbNoCountry = d.kbs.filter((k) => !k.country_id && (k.kind ?? 'national') === 'national').length  // une base mondiale n'a pas de pays
  const validated = d.mandates.filter((m) => m.validation === 'validated')
  const validatedNoSource = validated.filter((m) => !m.sources?.length).length
  const reviewed = d.reviews.filter((r) => r.status === 'reviewed_complete').length
  const withInst = d.agents.filter((a) => a.institution_id).length
  const withKb = d.agents.filter((a) => a.kb_ids?.length).length
  const ready = d.exercises.filter((e) => e.state === 'ready' || STARTED.includes(e.state)).length
  const started = d.exercises.filter((e) => STARTED.includes(e.state)).length
  const finished = d.exercises.filter((e) => FINISHED.includes(e.state)).length

  // « terminé » dès qu'au moins un mandat est validé AVEC source ; les autres peuvent rester proposés (revue honnête, pas de complétude forcée)
  const mandatesStatus: SetupStatus = d.mandates.length === 0 ? 'todo' : validated.length - validatedNoSource > 0 ? 'done' : 'partial'
  const raw: Array<[SetupId, SetupStatus, string, string, Record<string, number>, SetupId[]]> = [
    ['country', nC > 0 ? 'done' : 'todo', '/studio/countries?tab=countries', nC > 0 ? 'some' : 'none', { n: nC }, []],
    ['institutions', nI > 0 ? 'done' : 'todo', '/studio/countries?tab=institutions', nI > 0 ? 'some' : 'none', { n: nI }, ['country']],
    ['kb', d.kbs.length === 0 ? 'todo' : kbPublished === d.kbs.length && kbNoCountry === 0 ? 'done' : 'partial', '/studio/knowledge',
      d.kbs.length === 0 ? 'none' : 'some', { n: d.kbs.length, published: kbPublished, noCountry: kbNoCountry }, []],
    ['mandates', mandatesStatus, '/studio/countries?tab=mandates', d.mandates.length === 0 ? 'none' : 'some',
      { n: d.mandates.length, validated: validated.length, noSource: validatedNoSource, reviewed, inst: nI }, ['institutions', 'kb']],
    ['agents', d.agents.length === 0 ? 'todo' : withInst === d.agents.length ? 'done' : 'partial', '/studio/agents',
      d.agents.length === 0 ? 'none' : 'some', { n: d.agents.length, noInst: d.agents.length - withInst }, ['institutions']],
    ['access', d.agents.length === 0 ? 'todo' : withKb === d.agents.length ? 'done' : withKb > 0 ? 'partial' : 'todo', '/studio/access',
      'some', { n: d.agents.length, withKb, without: d.agents.length - withKb }, ['agents', 'kb']],
    ['scenario', d.scenarios.length > 0 ? 'done' : 'todo', '/studio/scenarios', d.scenarios.length > 0 ? 'some' : 'none', { n: d.scenarios.length }, ['institutions']],
    ['exercise', d.exercises.length > 0 ? 'done' : 'todo', '/studio/exercises', d.exercises.length > 0 ? 'some' : 'none', { n: d.exercises.length }, ['scenario', 'agents', 'access']],
    ['readiness', ready > 0 ? 'done' : 'todo', '/studio/exercises', ready > 0 ? 'some' : 'none', { n: ready }, ['exercise']],
    ['run', finished > 0 ? 'done' : started > 0 ? 'partial' : 'todo', '/room', finished > 0 ? 'some' : started > 0 ? 'running' : 'none', { n: finished }, ['readiness']],
  ]
  const doneIds = new Set<SetupId>()
  const out: SetupStep[] = []
  for (const [id, status, to, detailKey, detail, needs] of raw) {
    const missing = needs.filter((n) => !doneIds.has(n) && !(out.find((o) => o.id === n)?.status === 'partial'))
    // une étape sans rien d'enregistré est « verrouillée » tant que ses prérequis ne sont pas terminés
    const finalStatus: SetupStatus = status === 'todo' && missing.length > 0 ? 'locked' : status
    out.push({ id, status: finalStatus, to, detailKey, detail, needs: finalStatus === 'locked' ? missing : [] })
    if (status === 'done') doneIds.add(id)
  }
  return out
}

/** Première étape à traiter (ni terminée ni verrouillée) : « ce qu'il faut faire maintenant ». */
export function nextStep(steps: SetupStep[]): SetupStep | null {
  return steps.find((s) => s.status === 'todo' || s.status === 'partial') ?? null
}
