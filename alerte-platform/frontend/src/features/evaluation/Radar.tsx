import { useTranslation } from 'react-i18next'

/** SVG radar chart. A dimension with no score ("not assessed") is NEVER plotted as 0: it gets no point and is labelled. */
export function Radar({ dims, max }: { dims: { label: string; score: number | null }[]; max: number }) {
  const { t } = useTranslation()
  const size = 340
  const c = size / 2
  const r = size / 2 - 60
  const n = dims.length
  if (n === 0) return null
  const ang = (i: number) => (Math.PI * 2 * i) / n - Math.PI / 2
  const pt = (i: number, v: number) => [c + Math.cos(ang(i)) * r * (v / max), c + Math.sin(ang(i)) * r * (v / max)] as const
  const assessed = dims.map((d, i) => (d.score === null ? null : pt(i, d.score)))
  const poly = assessed.filter((p): p is readonly [number, number] => p !== null).map((p) => p.join(',')).join(' ')
  const desc = dims.map((d) => `${d.label}: ${d.score === null ? t('common.notAssessed') : d.score.toFixed(1)}`).join('; ')
  return (
    <svg viewBox={`0 0 ${size} ${size}`} role="img" aria-label={t('evaluation.radarLabel')} className="h-auto w-full max-w-md">
      <title>{t('evaluation.radarLabel')}</title><desc>{desc}</desc>
      {[1, 2, 3, 4, 5].map((k) => <polygon key={k} points={dims.map((_, i) => pt(i, (max * k) / 5).join(',')).join(' ')} fill="none" stroke="var(--border)" strokeWidth={1} />)}
      {dims.map((d, i) => {
        const [x, y] = pt(i, max)
        const [lx, ly] = pt(i, max * 1.2)
        return (
          <g key={i}>
            <line x1={c} y1={c} x2={x} y2={y} stroke="var(--border)" />
            <text x={lx} y={ly} fontSize={9} textAnchor={lx < c - 5 ? 'end' : lx > c + 5 ? 'start' : 'middle'} fill="var(--text)">{d.label.length > 16 ? `${d.label.slice(0, 15)}…` : d.label}{d.score === null ? ` (${t('common.notAssessed')})` : ''}</text>
          </g>
        )
      })}
      {poly && <polygon points={poly} fill="var(--brand-soft)" fillOpacity={0.6} stroke="var(--brand)" strokeWidth={2} />}
      {assessed.map((p, i) => p && <circle key={i} cx={p[0]} cy={p[1]} r={3.5} fill="var(--brand)" />)}
    </svg>
  )
}
