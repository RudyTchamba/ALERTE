import type { ComponentType } from 'react'
import { useTranslation } from 'react-i18next'
import { BookOpenText, Landmark, MessagesSquare, Radio, Scale, SearchCheck } from 'lucide-react'
import { cn } from '@/lib/cn'
import { BOARD, GAPS, LEGAL, SCENARIO, kbOf, type FlowStep, type SeatVisual, type StepTone } from './narrate'

const W = 1000
const H = 560
const CX = 500
const CY = 300

interface Pt { x: number; y: number }

/** Disposition : sièges en ellipse autour du tableau ; documents de chaque siège vers l'extérieur ; acteurs fixes dans trois coins. */
export function layout(seats: string[]): Record<string, Pt> {
  const pos: Record<string, Pt> = {
    [SCENARIO]: { x: 110, y: 70 }, [GAPS]: { x: 890, y: 70 }, [LEGAL]: { x: 110, y: 515 }, [BOARD]: { x: CX, y: CY },
  }
  const n = Math.max(seats.length, 1)
  const rx = 290, ry = 170
  seats.forEach((code, i) => {
    // Départ à gauche, répartition régulière ; les coins restent aux acteurs fixes (scénario, lacunes, conseiller).
    const a = Math.PI + (i * 2 * Math.PI) / n
    const ux = Math.cos(a), uy = Math.sin(a)
    pos[code] = { x: CX + rx * ux, y: CY + ry * uy }
    pos[kbOf(code)] = { x: CX + (rx + 150) * ux, y: CY + (ry + 95) * uy }
  })
  for (const k of Object.keys(pos)) pos[k] = { x: Math.min(W - 58, Math.max(58, pos[k].x)), y: Math.min(H - 30, Math.max(30, pos[k].y)) }
  return pos
}

/** Courbe légère entre deux points (plus lisible que des lignes droites qui se croisent au centre). */
function seg(a: Pt, b: Pt): string {
  const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2
  const dx = b.x - a.x, dy = b.y - a.y
  const k = 0.12
  return `Q ${mx - dy * k} ${my + dx * k} ${b.x} ${b.y}`
}
function pathD(nodes: string[], pos: Record<string, Pt>): string | null {
  const pts = nodes.map((n) => pos[n]).filter(Boolean)
  if (pts.length < 2) return null
  return `M ${pts[0].x} ${pts[0].y} ` + pts.slice(1).map((p, i) => seg(pts[i], p)).join(' ')
}

const TONE_VAR: Record<StepTone, string> = {
  brand: 'var(--brand)', ok: 'var(--ok)', danger: 'var(--danger)', warn: 'var(--warn)', info: 'var(--info)', neutral: 'var(--text-muted)',
}
const SEAT_STROKE: Record<SeatVisual, string> = {
  idle: 'var(--border)', thinking: 'var(--info)', verified: 'var(--ok)', refused: 'var(--danger)', unrecorded: 'var(--danger)', waiting: 'var(--warn)',
}

function Node({ p, icon: Icon, label, sub, active, stroke, small, tone }: {
  p: Pt; icon: ComponentType<{ className?: string; x?: number; y?: number; width?: number; height?: number }>; label: string; sub?: string
  active?: boolean; stroke?: string; small?: boolean; tone?: string
}) {
  const w = small ? 108 : 150
  const h = small ? 40 : 58
  return (
    <g transform={`translate(${p.x - w / 2} ${p.y - h / 2})`} className={cn('transition-opacity', active === false && 'opacity-80')}>
      {active && <rect x={-6} y={-6} width={w + 12} height={h + 12} rx={16} fill="none" stroke={tone ?? 'var(--brand)'} strokeWidth={2} opacity={0.55} className="flow-halo" />}
      <rect width={w} height={h} rx={12} fill="var(--surface)" stroke={stroke ?? 'var(--border)'} strokeWidth={active ? 2.5 : 1.5} />
      <Icon x={10} y={(h - (small ? 16 : 20)) / 2} width={small ? 16 : 20} height={small ? 16 : 20} className="text-muted" />
      <text x={small ? 32 : 38} y={sub ? h / 2 - 3 : h / 2 + 5} fill="var(--text)" fontSize={small ? 12 : 15} fontWeight={800} fontFamily="var(--font-mono)">{label}</text>
      {sub && <text x={small ? 32 : 38} y={h / 2 + 14} fill="var(--text-muted)" fontSize={12.5}>{sub}</text>}
    </g>
  )
}

/** Bulle « bande dessinée » accrochée au nœud principal de l'étape (au-dessus, ou en dessous près du haut). */
function Callout({ at, text, tone }: { at: Pt; text: string; tone: string }) {
  const w = 270, h = 74
  const below = at.y < 150
  const x = Math.min(W - w - 8, Math.max(8, at.x - w / 2))
  const y = below ? at.y + 40 : at.y - 40 - h
  return (
    <g className="flow-callout">
      <line x1={at.x} y1={below ? at.y + 30 : at.y - 30} x2={at.x} y2={below ? y : y + h} stroke={tone} strokeWidth={1.5} strokeDasharray="2 3" />
      <foreignObject x={x} y={y} width={w} height={h}>
        <div style={{ borderColor: tone }} className="flex h-full items-center rounded-xl border-2 bg-surface px-3 py-1.5 text-sm leading-snug font-semibold text-ink shadow-lg">
          <span className="line-clamp-3">{text}</span>
        </div>
      </foreignObject>
    </g>
  )
}

export function FlowDiagram({ seats, step, visuals, title, callout, className }: { seats: string[]; step: FlowStep | null; visuals: Record<string, SeatVisual>; title: string; callout?: string | null; className?: string }) {
  const { t } = useTranslation()
  const pos = layout(seats)
  const tone = step ? TONE_VAR[step.tone] : 'var(--brand)'
  const isOn = (id: string) => !!step && (step.focus === id || step.paths.some((pp) => pp.includes(id)))
  // Sans étape en cours, rien n'est atténué.
  const on = (id: string) => (step ? isOn(id) : undefined)
  const seatSub = (v: SeatVisual | undefined) => t(`room.flow.seat.${v ?? 'idle'}`)
  // Liens permanents (discrets) : scénario→sièges, siège↔documents, siège↔tableau, tableau→lacunes, sièges↔conseiller.
  const links: string[][] = [[BOARD, GAPS]]
  for (const c of seats) links.push([SCENARIO, c], [c, kbOf(c)], [c, BOARD], [c, LEGAL])

  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title} className={cn('select-none', className ?? 'h-auto w-full')}>
      <defs>
        <radialGradient id="flow-hub" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="var(--brand)" stopOpacity="0.18" /><stop offset="100%" stopColor="var(--brand)" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx={CX} cy={CY} r={150} fill="url(#flow-hub)" />
      <ellipse cx={CX} cy={CY} rx={290} ry={170} fill="none" stroke="var(--border)" strokeDasharray="3 7" opacity={0.6} />
      {links.map((l) => {
        const d = pathD(l, pos)
        return d ? <path key={l.join('>')} d={d} fill="none" stroke="var(--border)" strokeWidth={1.2} opacity={0.7} /> : null
      })}

      {/* Trajets de l'étape en cours : trait lumineux + impulsion qui voyage (relancée à chaque étape via la clé). */}
      {step && step.paths.map((pp, i) => {
        const d = pathD(pp, pos)
        if (!d) return null
        const dur = pp.length > 2 ? 1.4 : 0.9
        return (
          <g key={`${step.seq}-${i}`}>
            <path d={d} fill="none" stroke={tone} strokeWidth={3} strokeLinecap="round" className="flow-trail" />
            <circle r={7} fill={tone} className="flow-pulse">
              <animateMotion dur={`${dur}s`} repeatCount="indefinite" path={d} />
            </circle>
            <circle r={14} fill={tone} opacity={0.25} className="flow-pulse">
              <animateMotion dur={`${dur}s`} repeatCount="indefinite" path={d} />
            </circle>
          </g>
        )
      })}

      <Node p={pos[SCENARIO]} icon={Radio} label={t('room.flow.node.scenario')} sub={t('room.flow.node.scenarioSub')} active={on(SCENARIO)} tone={tone} stroke="var(--brand)" />
      <Node p={pos[GAPS]} icon={SearchCheck} label={t('room.flow.node.gaps')} sub={t('room.flow.node.gapsSub')} active={on(GAPS)} tone={tone} stroke={isOn(GAPS) ? 'var(--danger)' : undefined} />
      <Node p={pos[LEGAL]} icon={Scale} label={t('room.flow.node.legal')} sub={t('room.flow.node.legalSub')} active={on(LEGAL)} tone={tone} />
      <Node p={pos[BOARD]} icon={MessagesSquare} label={t('room.flow.node.board')} sub={t('room.flow.node.boardSub')} active={on(BOARD)} tone={tone} />
      {seats.map((c) => (
        <g key={c}>
          <Node p={pos[kbOf(c)]} icon={BookOpenText} label={t('room.flow.node.docs')} small active={on(kbOf(c))} tone={tone} />
          <Node p={pos[c]} icon={Landmark} label={c} sub={seatSub(visuals[c])} active={on(c)} tone={tone} stroke={SEAT_STROKE[visuals[c] ?? 'idle']} />
        </g>
      ))}
      {step && callout && step.focus && pos[step.focus] && <Callout at={pos[step.focus]} text={callout} tone={tone} key={`c-${step.seq}`} />}
    </svg>
  )
}
