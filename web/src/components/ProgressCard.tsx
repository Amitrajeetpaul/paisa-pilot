import { useEffect, useState } from 'react'
import { api, savingOn, type MeProgress } from '../lib/api'
import { useAuth } from '../lib/auth'

/** "Since your last visit": how the person's own numbers moved, from their saved history. */
export function ProgressCard({ ready }: { ready: boolean }) {
  const user = useAuth()
  const [p, setP] = useState<MeProgress | null>(null)

  useEffect(() => {
    if (!user || !ready || !savingOn()) return
    let live = true
    ;(async () => {
      try {
        await api.meSnapshot() // record today's numbers (the server skips an identical same-day record)
        const prog = await api.meProgress()
        if (live) setP(prog)
      } catch {
        /* history is a bonus; never break the home screen for it */
      }
    })()
    return () => {
      live = false
    }
  }, [user, ready])

  if (!user || !p || !p.has_history || p.changes.length === 0) return null
  const prev = p.previous_at ? new Date(p.previous_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : 'your last visit'
  return (
    <section className="card mt-6 p-4" aria-labelledby="progress-h">
      <h2 id="progress-h" className="section-label">Since {prev}</h2>
      <ul className="mt-2 space-y-2">
        {p.changes.map((c) => (
          <li key={c.metric} className="flex items-start gap-2 text-sm">
            <span aria-hidden="true" className={c.better === true ? 'text-emerald-600' : c.better === false ? 'text-amber-600' : 'text-muted'}>
              {c.better === true ? '▲' : c.better === false ? '▼' : '•'}
            </span>
            <span className="text-ink">{c.text}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
