import { useId, useState } from 'react'
import { formatINR } from '../lib/format'

function monthLabel(key: string): string {
  const [year, month] = key.split('-')
  return new Date(Number(year), Number(month) - 1).toLocaleDateString('en-IN', { month: 'short' })
}

/** Single-series magnitude chart: one hue (coral), rounded data-ends,
 * baseline-anchored, per-bar hover tooltip, sr-only table fallback. Shows
 * only the months actually present in the user's statement -- never
 * padded to a fixed count, per the brief's "no invented stats" rule. */
export function LeakBarChart({ data }: { data: Record<string, number> }) {
  const [hovered, setHovered] = useState<string | null>(null)
  const tableId = useId()
  const entries = Object.entries(data)
  if (entries.length === 0) return null
  const max = Math.max(...entries.map(([, v]) => v), 1)

  return (
    <div>
      <div className="flex h-32 items-end gap-3" role="img" aria-describedby={tableId}>
        {entries.map(([month, value]) => {
          const heightPct = Math.max(6, (value / max) * 100)
          const isHovered = hovered === month
          return (
            <div key={month} className="relative flex flex-1 flex-col items-center gap-1.5">
              {isHovered && (
                <div className="bg-navy absolute -top-9 rounded-lg px-2 py-1 text-xs font-semibold text-white shadow">
                  {formatINR(value)}
                </div>
              )}
              <div
                className="bg-coral w-full cursor-default rounded-t-[4px] transition-opacity"
                style={{ height: `${heightPct}%`, opacity: isHovered ? 1 : 0.85 }}
                onMouseEnter={() => setHovered(month)}
                onMouseLeave={() => setHovered(null)}
                tabIndex={0}
                onFocus={() => setHovered(month)}
                onBlur={() => setHovered(null)}
              />
              <span className="text-muted text-xs font-semibold">{monthLabel(month)}</span>
            </div>
          )
        })}
      </div>
      <table id={tableId} className="sr-only">
        <caption>Monthly leak total by month</caption>
        <thead>
          <tr>
            <th scope="col">Month</th>
            <th scope="col">Amount</th>
          </tr>
        </thead>
        <tbody>
          {entries.map(([month, value]) => (
            <tr key={month}>
              <td>{monthLabel(month)}</td>
              <td>{formatINR(value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
