import { Prereq } from '@/components/Prereq'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '@/api/client'
import { keys } from '@/api/keys'
import { useApiMutation, useApiQuery } from '@/api/hooks'
import type { AccessMatrix, Kb } from '@/api/loose'
import { Badge, EmptyState, PageHeader, QueryState, Section, Table, TBody, Td, Th, THead, Tr, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/errors'

/** Agents x knowledge bases matrix. Native checkboxes in a table with row/column headers: fully keyboard-operable. */
export function AccessPage() {
  const { t } = useTranslation()
  const toast = useToast()
  const [announce, setAnnounce] = useState('')
  const m = useApiQuery<AccessMatrix>(keys.accessMatrix, '/access-matrix')
  const kbs = useApiQuery<Kb[]>(keys.kbs(false), '/knowledge-bases')
  const save = useApiMutation((v: { agentId: string; kbIds: string[]; msg: string }) => api.put(`/agents/${v.agentId}/kb-grants`, { kb_ids: v.kbIds }).then(() => v.msg), {
    invalidate: [keys.accessMatrix, ['agents']], onSuccess: (msg) => setAnnounce(msg), onError: (e) => toast.push(errorMessage(e, t), 'danger'),
  })
  return (
    <>
      <PageHeader title={t('agents.accessTitle')} term="accessMapping" description={t('agents.accessDescription')} />
      <Prereq page="access" />
      <p className="sr-only-live" role="status" aria-live="polite">{announce}</p>
      <QueryState q={m} what="(/access-matrix)">
        {(mx) => (
          <QueryState q={kbs} what="(/knowledge-bases)">
            {(allKbs) => {
              const cols = allKbs.filter((k) => !k.archived_at)
              const agents = mx.agents.filter((a) => !a.archived)
              if (agents.length === 0 || cols.length === 0) return <EmptyState title={t('agents.matrixEmpty')} hint={t('agents.matrixEmptyHint')} />
              const has = (a: string, k: string) => mx.grants.some((g) => g.agent_id === a && g.kb_id === k)
              const grantsOf = (a: string) => mx.grants.filter((g) => g.agent_id === a).map((g) => g.kb_id)
              const orphans = agents.filter((a) => a.role_kind !== 'ai_system' && grantsOf(a.id).length === 0)
              return (
                <>
                  {orphans.length > 0 ? (
                    <p role="alert" className="mb-3 rounded border border-warn bg-warnsoft p-2 text-sm"><Badge tone="warn">{t('agents.warning')}</Badge> {t('agents.noKbAgents', { names: orphans.map((o) => o.code).join(', ') })}</p>
                  ) : <p className="mb-3"><Badge tone="ok">{t('agents.allHaveKb')}</Badge></p>}
                  <Table caption={t('agents.accessTitle')}>
                    <THead>
                      <Tr><Th><span className="sr-only">{t('agents.title')}</span></Th>
                        {cols.map((k) => <Th key={k.id} className="text-center">{k.name}</Th>)}
                        <Th>{t('agents.impact')}</Th></Tr>
                    </THead>
                    <TBody>{agents.map((a) => (
                      <Tr key={a.id}>
                        <th scope="row" className="px-3 py-2 text-left font-medium whitespace-nowrap">{a.code} <span className="font-normal text-muted">— {a.name}</span></th>
                        {cols.map((k) => (
                          <Td key={k.id} className="text-center">
                            <input type="checkbox" className="h-5 w-5 accent-[var(--brand)]" checked={has(a.id, k.id)} disabled={save.isPending}
                              aria-label={t('agents.cellLabel', { agent: a.code, kb: k.name })}
                              onChange={(e) => {
                                const cur = grantsOf(a.id)
                                const next = e.target.checked ? [...cur, k.id] : cur.filter((x) => x !== k.id)
                                save.mutate({ agentId: a.id, kbIds: next, msg: t(e.target.checked ? 'agents.granted' : 'agents.revoked', { agent: a.code, kb: k.name }) })
                              }} />
                          </Td>
                        ))}
                        <Td className="text-xs">{t('agents.readsN', { n: grantsOf(a.id).length })}</Td>
                      </Tr>
                    ))}</TBody>
                  </Table>
                  <Section title={t('agents.impactView')} className="mt-6">
                    <ul className="grid gap-3 md:grid-cols-2">{cols.map((k) => {
                      const who = agents.filter((a) => has(a.id, k.id))
                      return <li key={k.id} className="rounded-md border border-line bg-surface p-3 text-sm"><strong>{k.name}</strong>: {who.length ? who.map((w) => w.code).join(', ') : <Badge tone="neutral">{t('agents.nobody')}</Badge>}</li>
                    })}</ul>
                  </Section>
                </>
              )
            }}
          </QueryState>
        )}
      </QueryState>
    </>
  )
}
