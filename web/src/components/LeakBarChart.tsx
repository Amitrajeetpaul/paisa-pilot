import { useId, useState } from 'react'
import { formatINR } from '../lib/format'

const TRACK_HEIGHT_PX = 96

function monthLabel(key: string): string {
  const [year, month] = key.split('-')
  return new Date(Number(year), Number(month) - 1).toLocaleDateString('en-IN', { month: 'short' })
}

/** Single-series magnitude chart: one hue (navy, for contrast against the
 * amber-to-coral hero background), rounded data-ends, baseline-anchored,
 * per-bar hover tooltip, sr-only table fallback. Shows only the months
 * actually present in the user's statement -- never padded to a fixed
 * count, per the brief's "no invented stats" rule. */
export function LeakBarChart({ data }: { data: Record<string, number> }) {
  const [hovered, setHovered] = useState<string | null>(null)
  const tableId = useId()
  const entries = Object.entries(data)
  if (entries.length === 0) return null
  const max = Math.max(...entries.map(([, v]) => v), 1)

  return (
    <div>
      <div className="flex gap-3" role="img" aria-describedby={tableId}>
        {entries.map(([month, value]) => {
          const heightPct = Math.max(6, (value / max) * 100)
          const isHovered = hovered === month
          return (
            <div key={month} className="flex flex-1 flex-col items-center gap-1.5">
              <div className="relative flex w-full items-end justify-center rounded-t-lg bg-white/10" style={{ height: TRACK_HEIGHT_PX }}>
                {isHovered && (
                  <div className="absolute -top-9 left-1/2 bg-white text-navy -translate-x-1/2 whitespace-nowrap rounded-lg px-2 py-1 text-xs font-semibold shadow">
                    {formatINR(value)}
                  </div>
                )}
                <div
                  className="w-3/5 max-w-16 cursor-default rounded-t-md bg-white transition-opacity"
                  style={{ height: `${heightPct}%`, opacity: isHovered ? 1 : 0.9 }}
                  onMouseEnter={() => setHovered(month)}
                  onMouseLeave={() => setHovered(null)}
                  tabIndex={0}
                  onFocus={() => setHovered(month)}
                  onBlur={() => setHovered(null)}
                />
              </div>
              <span className="text-xs font-semibold text-white/80">{monthLabel(month)}</span>
              <span className="tabular -mt-1 text-xs font-semibold text-white">{formatINR(value)}</span>
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
