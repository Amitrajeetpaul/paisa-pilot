import { useEffect, useState } from 'react'
import { api, type SpendingProfile } from '../lib/api'
import { formatINR } from '../lib/format'
import { useApp } from '../state/AppContext'

/** Where the money goes, read from the bank statement like an adviser would. */
export function SpendingCard({ sessionId }: { sessionId: string }) {
  const { t } = useApp()
  const [p, setP] = useState<SpendingProfile | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    setP(null)
    setFailed(false)
    api.spending(sessionId).then(setP).catch(() => setFailed(true))
  }, [sessionId])

  if (failed) return null
  const max = Math.max(1, ...(p?.categories.map((c) => c.monthly_average) ?? [1]))
  return (
    <section className="mt-8" aria-labelledby="spend-h">
      <h2 id="spend-h" className="section-label">{t('ui.whereMoneyGoes')}</h2>
      <div className="card mt-3 p-4">
        {!p && <div className="animate-pulse bg-slate-500/15 h-16 rounded-xl" aria-label="Loading" />}
        {p && (
          <>
            <div className="grid grid-cols-3 gap-2 text-center">
              <div>
                <p className="text-muted text-xs">Comes in</p>
                <p className="tabular text-ink text-base font-extrabold">{formatINR(p.income_per_month)}</p>
              </div>
              <div>
                <p className="text-muted text-xs">Goes out</p>
                <p className="tabular text-ink text-base font-extrabold">{formatINR(p.spending_per_month)}</p>
              </div>
              <div>
                <p className="text-muted text-xs">Saved</p>
                <p className="tabular text-ink text-base font-extrabold">{p.savings_rate_percent === null ? '–' : `${p.savings_rate_percent}%`}</p>
              </div>
            </div>
            <p className="text-muted mt-1 text-center text-xs">Monthly average over {p.months_covered} months</p>
            <ul className="mt-3 space-y-2">
              {p.categories.slice(0, 7).map((c) => (
                <li key={c.key}>
                  <div className="flex items-baseline justify-between gap-3 text-sm">
                    <span className="text-ink">{c.label}</span>
                    <span className="tabular text-muted">{formatINR(c.monthly_average)}</span>
                  </div>
                  <div className="bg-slate-500/15 mt-1 h-1.5 overflow-hidden rounded-full" aria-hidden="true">
                    <div className="bg-coral h-full rounded-full" style={{ width: `${Math.max(4, (c.monthly_average / max) * 100)}%` }} />
                  </div>
                </li>
              ))}
            </ul>
            {p.flags.length > 0 && (
              <ul className="mt-3 space-y-1.5">
                {p.flags.map((f) => (
                  <li key={f.id} className="bg-amber-500/10 text-ink rounded-xl px-3 py-2 text-sm">{f.text}</li>
                ))}
              </ul>
            )}
            <p className="text-muted mt-3 text-xs">{p.note}</p>
          </>
        )}
      </div>
    </section>
  )
}
