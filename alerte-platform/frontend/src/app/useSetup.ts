import { keys } from '@/api/keys'
import { useApiQuery } from '@/api/hooks'
import { computeSetup, nextStep, type SetupInput } from './setup'

/** Parcours de préparation calculé sur les données réelles (mêmes clés de cache que les pages : aucune requête en plus). */
export function useSetup() {
  const countries = useApiQuery<SetupInput['countries']>(keys.countries(false), '/countries')
  const institutions = useApiQuery<SetupInput['institutions']>(keys.institutions(undefined, false), '/institutions')
  const kbs = useApiQuery<SetupInput['kbs']>(keys.kbs(false), '/knowledge-bases')
  const mandates = useApiQuery<SetupInput['mandates']>(keys.mandates(), '/mandates')
  const reviews = useApiQuery<SetupInput['reviews']>(keys.registryReviews, '/registry-reviews')
  const agents = useApiQuery<SetupInput['agents']>(keys.agents(false), '/agents')
  const scenarios = useApiQuery<SetupInput['scenarios']>(keys.scenarios, '/scenarios')
  const exercises = useApiQuery<SetupInput['exercises']>(keys.exercises(), '/exercises')
  const all = [countries, institutions, kbs, mandates, reviews, agents, scenarios, exercises]
  const pending = all.some((q) => q.isPending)
  // un rôle sans droit de lecture (403) ou une panne ne doit pas faire croire que « rien n'est configuré »
  const unavailable = all.some((q) => q.isError)
  const steps = computeSetup({
    countries: countries.data ?? [], institutions: institutions.data ?? [], kbs: kbs.data ?? [], mandates: mandates.data ?? [],
    reviews: reviews.data ?? [], agents: agents.data ?? [], scenarios: scenarios.data ?? [], exercises: exercises.data ?? [],
  })
  return { steps, next: pending || unavailable ? null : nextStep(steps), pending, unavailable }
}
