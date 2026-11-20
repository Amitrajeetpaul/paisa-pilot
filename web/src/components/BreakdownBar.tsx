import { formatINR } from '../lib/format'
import { SOLID, type Tone } from './tones'

export interface Segment {
  label: string
  amount: number
  tone: Tone
}

/** A stacked bar with a legend: where the money comes from at a glance. */
export function BreakdownBar({ segments, dark = false }: { segments: Segment[]; dark?: boolean }) {
  const total = segments.reduce((sum, s) => sum + s.amount, 0)
  if (total <= 0) return null
  return (
    <div>
      <div className="flex h-2.5 w-full gap-0.5 overflow-hidden rounded-full" role="img" aria-label="Breakdown by category">
        {segments.map((s) => (
          <div
            key={s.label}
            title={`${s.label}: ${formatINR(s.amount)}`}
            style={{ width: `${(s.amount / total) * 100}%`, background: SOLID[s.tone] }}
            className="min-w-1.5 first:rounded-l-full last:rounded-r-full"
          />
        ))}
      </div>
      <ul className="mt-3 grid grid-cols-1 gap-x-6 gap-y-1.5 min-[520px]:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
        {segments.map((s) => (
          <li key={s.label} className="flex items-center justify-between gap-2 text-xs">
            <span className={`flex min-w-0 items-center gap-1.5 ${dark ? 'text-white/80' : 'text-muted'}`}>
              <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: SOLID[s.tone] }} />
              <span>{s.label}</span>
            </span>
            <span className={`tabular font-semibold ${dark ? 'text-white' : 'text-ink'}`}>{formatINR(s.amount)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
