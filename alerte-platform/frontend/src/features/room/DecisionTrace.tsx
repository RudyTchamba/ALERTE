import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useApiQuery } from '@/api/hooks'
import type { StreamEvent } from '@/api/sse'
import { Badge, Button, Dialog, EmptyState, Mono, QueryState } from '@/components/ui'
import { buildTrace } from './trace'
import { OutcomeBadge, VerifiedBadge } from './parts'
import type { DecisionItem } from './state'

type Ev = Pick<StreamEvent, 'seq' | 'type' | 'actor' | 'seat' | 'payload' | 'sim_time' | 'real_time' | 'visibility'>

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="mb-4"><h3 className="mb-1 font-semibold">{title}</h3>{children}</section>
}

interface BlobPart { sha256: string | null; available: boolean; intact: boolean | null; content: string | null }
interface LlmCallDetail { seq: number; request: BlobPart; response: BlobPart }

function pretty(s: string | null): string {
  if (!s) return ''
  try { return JSON.stringify(JSON.parse(s), null, 2) } catch { return s }
}

/** Prompt et réponse bruts d'un appel au modèle (rôles d'audit), chargés à la demande, intégrité contrôlée. */
function LlmCallRaw({ exerciseId, seq }: { exerciseId: string; seq: number }) {
  const { t } = useTranslation()
  const q = useApiQuery<LlmCallDetail>(['llm-call', exerciseId, seq], `/exercises/${exerciseId}/llm-calls/${seq}`)
  return (
    <QueryState q={q} what="(/llm-calls)">
      {(d) => (
        <div className="mt-2 grid gap-2 md:grid-cols-2">
          {(['request', 'response'] as const).map((part) => (
            <div key={part}>
              <p className="mb-1 flex items-center gap-2 font-semibold">{t(`room.trace.${part}`)}
                {d[part].available ? <Badge tone={d[part].intact ? 'ok' : 'danger'}>{d[part].intact ? t('room.trace.intact') : t('room.trace.altered')}</Badge> : <Badge tone="neutral">{t('room.trace.unavailable')}</Badge>}</p>
              {d[part].content && <pre className="max-h-80 overflow-auto rounded-lg border border-line bg-bg p-2 font-mono text-xs leading-relaxed whitespace-pre-wrap">{pretty(d[part].content)}</pre>}
            </div>
          ))}
        </div>
      )}
    </QueryState>
  )
}

function LlmCallToggle({ exerciseId, seq }: { exerciseId: string; seq: number }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  return <>
    <Button size="sm" variant="ghost" aria-expanded={open} onClick={() => setOpen((o) => !o)}>{open ? t('room.trace.hideRaw') : t('room.trace.showRaw')}</Button>
    {open && <LlmCallRaw exerciseId={exerciseId} seq={seq} />}
  </>
}

/** Decision trace: context -> retrievals (scores) -> model calls -> citation checks -> validated decision. */
export function DecisionTraceDialog({ decision, events, onClose, exerciseId }: { decision: DecisionItem | null; events: Ev[]; onClose: () => void; exerciseId?: string }) {
  const { t } = useTranslation()
  const tr = decision ? buildTrace(events, decision.decisionId) : null
  return (
    <Dialog open={!!decision} wide onClose={onClose} title={decision ? t('room.trace.title', { seat: decision.seat }) : ''}>
      {decision && (
        <div className="text-sm">
          <p className="mb-3 text-muted">{t('room.trace.hint')}</p>
          <Section title={t('room.trace.decision')}>
            <p className="flex flex-wrap items-center gap-2"><VerifiedBadge d={decision} /><OutcomeBadge outcome={decision.outcome} />{decision.confidence && <Badge tone="neutral">{t('room.confidence')}: {decision.confidence}</Badge>}{decision.evidenceTag && <Badge tone="info">{decision.evidenceTag}</Badge>}</p>
            <p className="mt-1 font-medium">{decision.action}</p>
            {decision.rationale && <p className="text-muted">“{decision.rationale}”</p>}
            {decision.legalBasis.length === 0 && <p className="mt-1"><Badge tone="warn">{t('room.trace.noBasis')}</Badge></p>}
            <ul className="mt-2 flex flex-col gap-2">{decision.legalBasis.map((lb, i) => {
              const ok = lb.check ? lb.check === 'pass' : lb.pass
              return (
                <li key={i} className="rounded border border-line p-2">
                  <p>{ok === undefined ? null : <Badge tone={ok ? 'ok' : 'danger'}>{ok ? t('room.trace.citationPass') : t('room.trace.citationFail')}</Badge>} {lb.article ? `Art. ${lb.article}` : ''} <Mono>{lb.chunk_id}</Mono></p>
                  {lb.quote && <p className="mt-1 italic">“{lb.quote}”</p>}
                  {lb.reason && <p className="text-danger">{lb.reason}</p>}
                </li>
              )
            })}</ul>
          </Section>
          {!tr ? <EmptyState title={t('room.trace.noEvents')} hint={t('room.trace.noEventsHint')} /> : (
            <>
              <Section title={t('room.trace.retrievals')}>
                {tr.retrievals.length === 0 ? <p className="text-muted">—</p> : tr.retrievals.map((r) => {
                  const results = (r.payload.results as { chunk_id: string; score: number; rank: number }[] | undefined) ?? []
                  const sig = r.payload.signals as { degraded?: boolean } | undefined
                  return (
                    <div key={r.seq} className="mb-2 rounded border border-line p-2">
                      <p>#{r.seq} “{String(r.payload.query)}” {sig?.degraded && <Badge tone="warn">{t('kb.lexicalOnly')}</Badge>}</p>
                      <ol className="list-decimal pl-5 text-xs">{results.map((h) => <li key={h.chunk_id}><Mono>{h.chunk_id}</Mono> — {t('kb.score')} {Number(h.score).toFixed(4)}</li>)}</ol>
                    </div>
                  )
                })}
              </Section>
              <Section title={t('room.trace.toolCalls')}>
                {tr.toolCalls.length === 0 ? <p className="text-muted">—</p> : <ul>{tr.toolCalls.map((c) => <li key={c.seq}>#{c.seq} <strong>{String(c.payload.tool)}</strong> {c.payload.ok === false && <Badge tone="danger">{String(c.payload.error ?? 'error')}</Badge>} <span className="text-muted">{String(c.payload.rationale ?? '')}</span></li>)}</ul>}
              </Section>
              <Section title={t('room.trace.llmCalls')}>
                {tr.llmCalls.length === 0 ? <p className="text-muted">{t('room.trace.noLlm')}</p> : <ul className="flex flex-col gap-1">{tr.llmCalls.map((c) => (
                  <li key={c.seq} className="rounded border border-line p-2 text-xs">
                    #{c.seq} {String(c.payload.provider)} / {String(c.payload.model)} · {String(c.payload.tokens_in ?? '?')}→{String(c.payload.tokens_out ?? '?')} tokens · {String(c.payload.ms ?? '?')} ms · {c.payload.valid === false ? <Badge tone="danger">{t('room.trace.invalid')}</Badge> : <Badge tone="ok">{t('room.trace.valid')}</Badge>} {c.payload.retried === true && <Badge tone="warn">{t('room.trace.retried')}</Badge>}
                    <br />prompt <Mono>{String(c.payload.request_blob_sha256 ?? '').slice(0, 16)}</Mono> · response <Mono>{String(c.payload.response_blob_sha256 ?? '').slice(0, 16)}</Mono>
                    {exerciseId && <div className="mt-1"><LlmCallToggle exerciseId={exerciseId} seq={c.seq} /></div>}
                  </li>))}</ul>}
                <p className="mt-1 text-xs text-muted">{t('room.trace.blobNote')}</p>
              </Section>
              <Section title={t('room.trace.citations')}>
                {tr.citationChecks.length === 0 ? <p className="text-muted">—</p> : tr.citationChecks.map((c) => (
                  <ul key={c.seq}>{((c.payload.citations as { chunk_id: string; pass: boolean; reason?: string | null }[]) ?? []).map((x, i) => <li key={i}><Badge tone={x.pass ? 'ok' : 'danger'}>{x.pass ? t('room.trace.citationPass') : t('room.trace.citationFail')}</Badge> <Mono>{x.chunk_id}</Mono> {x.reason}</li>)}</ul>
                ))}
              </Section>
              {tr.errors.length > 0 && <Section title={t('room.trace.errors')}><ul>{tr.errors.map((e) => <li key={e.seq}><Badge tone="danger">{String(e.payload.component)}</Badge> {String(e.payload.message)}</li>)}</ul></Section>}
            </>
          )}
        </div>
      )}
    </Dialog>
  )
}
