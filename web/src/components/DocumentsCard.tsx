import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { Icon, type IconName } from './Icon'

const DOCS: { type: string; label: string; unlocks: string; icon: IconName }[] = [
  { type: 'payslip', label: 'Payslip', unlocks: 'salary breakdown and savings targets', icon: 'file' },
  { type: 'form16', label: 'Form 16', unlocks: 'the better tax option and refund check', icon: 'receipt' },
  { type: 'bank_statement', label: 'Bank statement', unlocks: 'leaks and failed or double payments', icon: 'bank' },
  { type: 'pf_passbook', label: 'PF passbook', unlocks: 'old PF accounts to transfer', icon: 'book' },
  { type: 'ais', label: 'AIS', unlocks: 'extra tax you can claim back', icon: 'chart' },
]

/** Shows which documents are in and what each missing one would unlock, so the
 * next step is always obvious. */
export function DocumentsCard({ sessionId, refreshKey }: { sessionId: string; refreshKey?: unknown }) {
  const navigate = useNavigate()
  const [have, setHave] = useState<Record<string, boolean> | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.all(
      DOCS.map((d) =>
        api
          .getConfirmed(sessionId, d.type)
          .then(() => [d.type, true] as const)
          .catch(() => [d.type, false] as const),
      ),
    ).then((rows) => {
      if (!cancelled) setHave(Object.fromEntries(rows))
    })
    return () => {
      cancelled = true
    }
  }, [sessionId, refreshKey])

  if (!have) return null
  const count = DOCS.filter((d) => have[d.type]).length
  const missing = DOCS.filter((d) => !have[d.type])

  if (missing.length === 0) {
    return (
      <div className="bg-teal-tint text-navy mt-5 flex items-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold">
        <Icon name="shield" size={18} className="text-teal" /> All 5 documents added. You are getting the full picture.
      </div>
    )
  }

  return (
    <section className="border-line mt-5 rounded-[20px] border bg-white p-5" aria-label="Your documents">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-navy text-base font-bold">Find more money</h2>
        <span className="text-muted text-xs font-semibold">
          {count} of {DOCS.length} documents added
        </span>
      </div>
      <div className="bg-line mt-2 h-1.5 overflow-hidden rounded-full" role="progressbar" aria-valuenow={count} aria-valuemin={0} aria-valuemax={DOCS.length}>
        <div className="bg-teal h-full rounded-full transition-all" style={{ width: `${(count / DOCS.length) * 100}%` }} />
      </div>
      <ul className="mt-3 flex flex-col gap-2">
        {missing.slice(0, 3).map((d) => (
          <li key={d.type} className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <span className="bg-icon-tile text-coral-dark flex h-9 w-9 shrink-0 items-center justify-center rounded-xl">
                <Icon name={d.icon} size={18} />
              </span>
              <p className="text-navy min-w-0 text-sm">
                <span className="font-semibold">{d.label}</span>
                <span className="text-muted"> unlocks {d.unlocks}</span>
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate('/app/consent')}
              className="border-line text-navy hover:border-coral inline-flex min-h-11 shrink-0 items-center gap-1 rounded-[18px] border-2 px-3 text-sm font-semibold"
            >
              <Icon name="plus" size={16} /> Add
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
