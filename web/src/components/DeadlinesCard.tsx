import { useEffect, useState } from 'react'
import { api, type Deadline } from '../lib/api'
import { formatINR } from '../lib/format'
import { isNativeAndroid, notifyOncePerDay } from '../lib/usageAccess'

function when(d: Deadline) {
  const date = new Date(d.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
  if (d.days_left === 0) return `Today, ${date}`
  if (d.days_left === 1) return `Tomorrow, ${date}`
  return `${date} · in ${d.days_left} days`
}

/** The next tax dates for this person, so nothing is missed. Reminders only: nothing is filed or paid for you. */
export function DeadlinesCard({ sessionId }: { sessionId: string }) {
  const [items, setItems] = useState<Deadline[] | null>(null)
  const [note, setNote] = useState('')

  useEffect(() => {
    let live = true
    api
      .deadlines(sessionId)
      .then((r) => {
        if (!live) return
        const list = r.deadlines.filter((d) => d.applies).slice(0, 5)
        setItems(list)
        setNote(r.note)
        if (isNativeAndroid()) {
          // A nudge when something is close. It shows when the app is opened, at most once a day for each date.
          for (const d of list.filter((x) => x.days_left <= 7)) {
            const amount = d.amount_so_far ? ` Pay about ${formatINR(d.amount_so_far)} in total so far.` : ''
            void notifyOncePerDay(d.id, d.title, `${when(d)}.${amount}`)
          }
        }
      })
      .catch(() => live && setItems([]))
    return () => {
      live = false
    }
  }, [sessionId])

  if (!items || items.length === 0) return null
  return (
    <section className="card mt-6 p-4" aria-labelledby="deadlines-h">
      <h2 id="deadlines-h" className="section-label">Dates to remember</h2>
      <ul className="mt-2 divide-y divide-[color:var(--color-line)]">
        {items.map((d) => (
          <li key={d.id} className="py-2.5">
            <div className="flex items-start justify-between gap-3">
              <p className="text-ink text-sm font-semibold leading-snug">{d.title}</p>
              <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-bold ${d.days_left <= 14 ? 'bg-amber-500/15 text-amber-600' : 'bg-slate-500/15 text-muted'}`}>
                {d.days_left === 0 ? 'Today' : `${d.days_left}d`}
              </span>
            </div>
            <p className="text-muted text-xs">{when(d)}</p>
            <p className="text-muted mt-0.5 text-xs">{d.detail}</p>
            {d.amount_so_far ? <p className="text-ink mt-0.5 text-xs font-semibold">About {formatINR(d.amount_so_far)} in total should be paid by then.</p> : null}
            {d.law && <p className="text-muted mt-0.5 text-[11px]">{d.law.section}</p>}
          </li>
        ))}
      </ul>
      <p className="text-muted mt-2 text-xs">{note}</p>
    </section>
  )
}
