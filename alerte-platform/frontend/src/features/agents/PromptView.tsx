import { Fragment, type ReactNode } from 'react'

/**
 * Mise en forme lisible du prompt système (texte « ## N. Titre », puces « - », sous-étapes « 1. »).
 * Purement visuelle : le texte affiché est exactement celui envoyé au modèle.
 */
type Line =
  | { kind: 'item'; text: string; notes: string[] }
  | { kind: 'step'; n: string; text: string }
  | { kind: 'text'; text: string }

interface Sec { n: string; title: string; lines: Line[] }

export function parsePrompt(src: string): Sec[] {
  const secs: Sec[] = []
  let cur: Sec | null = null
  for (const raw of src.split('\n')) {
    const line = raw.trimEnd()
    const h = /^##\s+(?:(\d+)\.\s*)?(.*)$/.exec(line)
    if (h) { cur = { n: h[1] ?? '', title: h[2], lines: [] }; secs.push(cur); continue }
    if (!cur) { cur = { n: '', title: '', lines: [] }; secs.push(cur) }
    if (!line.trim()) continue
    const step = /^\s+(\d+)\.\s+(.*)$/.exec(line)
    const last = cur.lines[cur.lines.length - 1]
    if (step) cur.lines.push({ kind: 'step', n: step[1], text: step[2] })
    else if (line.startsWith('- ')) cur.lines.push({ kind: 'item', text: line.slice(2), notes: [] })
    else if (/^\s+\(/.test(line) && last?.kind === 'item') last.notes.push(line.trim())
    else cur.lines.push({ kind: 'text', text: line.trim() })
  }
  return secs
}

/** Repère les « "littéraux" », les <balises> et les identifiants_techniques pour les afficher en police à chasse fixe. */
function Inline({ text }: { text: string }) {
  const parts = text.split(/("[^"\n]{1,80}"|<[a-z_]+>|\b[a-z]+_[a-z_]+\b)/g)
  return <>{parts.map((p, i) => i % 2 === 1
    ? <code key={i} className="rounded bg-surface2 px-1 py-px font-mono text-[0.85em] text-ink">{p}</code>
    : <Fragment key={i}>{p}</Fragment>)}</>
}

/** « Clé : valeur » en tête de ligne ; une valeur vide ou un « (gabarit) » est signalé comme tel. */
function KeyValue({ text, intro = false }: { text: string; intro?: boolean }) {
  const m = /^([A-Z][A-Za-z ]{1,30}):\s*(.*)$/.exec(text)
  if (!m || m[2].includes('{') || (intro && !m[2].trim())) return <Inline text={text} />
  const v = m[2].trim()
  const val: ReactNode = !v ? <span className="text-muted italic">—</span>
    : /^\(.*\)$/.test(v) ? <span className="text-muted italic">{v}</span>
    : <Inline text={v.replace(/\s{2,}/g, ' · ')} />
  return <><strong className="font-semibold">{m[1]} :</strong> {val}</>
}

/** Une puce d'outil « nom: {json} » : le nom en évidence, le JSON en bloc de code indenté. */
function Item({ text, notes }: { text: string; notes: string[] }) {
  const j = /^([a-z_]+):\s*(\{.*\})\s*(\(.*\))?$/.exec(text)
  if (j) {
    let pretty = j[2]
    try { pretty = JSON.stringify(JSON.parse(j[2]), null, 2) } catch { /* gabarit non JSON : tel quel */ }
    return (
      <div className="flex flex-col gap-1.5">
        <code className="self-start rounded bg-brandsoft px-1.5 py-0.5 font-mono text-sm font-bold text-brand">{j[1]}</code>
        <pre className="overflow-x-auto rounded-lg border border-line bg-bg p-3 font-mono text-[0.8rem] leading-relaxed text-ink">{pretty}</pre>
        {[j[3], ...notes].filter(Boolean).map((x, i) => <p key={i} className="text-sm text-muted"><Inline text={x!.replace(/^\(|\)$/g, '')} /></p>)}
      </div>
    )
  }
  return <>
    <KeyValue text={text} intro />
    {notes.map((x, i) => <p key={i} className="mt-1 text-sm text-muted"><Inline text={x.replace(/^\(|\)$/g, '')} /></p>)}
  </>
}

export function PromptView({ text }: { text: string }) {
  const secs = parsePrompt(text)
  return (
    <div className="flex flex-col gap-4">
      {secs.map((s, si) => (
        <section key={si} className="rounded-xl border border-line bg-surface2/40 p-4">
          {s.title && (
            <h3 className="mb-3 flex items-center gap-2 text-base font-bold text-ink">
              {s.n && <span aria-hidden className="grid h-6 w-6 shrink-0 place-items-center rounded-md bg-brand text-sm font-black text-brandfg">{s.n}</span>}
              {s.title}
            </h3>
          )}
          <div className="flex flex-col gap-2.5 text-[0.95rem] leading-relaxed text-ink">
            {s.lines.map((l, i) => l.kind === 'step'
              ? <div key={i} className="ml-6 flex gap-2"><span className="w-5 shrink-0 text-right font-bold text-brand">{l.n}.</span><span><Inline text={l.text} /></span></div>
              : l.kind === 'item'
                ? <div key={i} className="flex gap-2.5"><span aria-hidden className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand" /><div className="min-w-0 flex-1"><Item text={l.text} notes={l.notes} /></div></div>
                : <p key={i}><KeyValue text={l.text} /></p>)}
          </div>
        </section>
      ))}
    </div>
  )
}
