import { useEffect, useState } from 'react'
import { api, type TaxSuggestion, type TaxSuggestionsResult } from '../lib/api'
import { formatINR } from '../lib/format'

function Card({ s }: { s: TaxSuggestion }) {
  const [open, setOpen] = useState(false)
  const informational = s.id === 'insight'
  return (
    <li className="py-3">
      <div className="flex items-start justify-between gap-3">
        <p className="text-ink text-[15px] font-semibold leading-snug">{s.title}</p>
        {s.saving ? (
          <span className="bg-emerald-500/15 text-emerald-600 shrink-0 rounded-full px-2.5 py-0.5 text-xs font-bold">Save about {formatINR(s.saving)} a year</span>
        ) : informational ? null : (
          <span className="bg-slate-500/15 text-muted shrink-0 rounded-full px-2.5 py-0.5 text-xs font-bold">Needs a document</span>
        )}
      </div>
      <p className="text-muted mt-1 text-sm">{s.why}</p>
      <p className="text-ink mt-1 text-sm">{s.action}</p>
      {s.caveat && <p className="text-muted mt-1 text-xs">{s.caveat}</p>}
      {s.law && (
        <>
          <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="text-coral-dark mt-1 min-h-9 text-xs font-semibold underline">
            {open ? 'Hide the rule' : `The rule: ${s.law.section}`}
          </button>
          {open && (
            <div className="bg-slate-500/10 mt-1 rounded-xl p-3 text-xs">
              <p className="text-muted">{s.law.excerpt}</p>
              <a href={s.law.source_url} target="_blank" rel="noreferrer" className="text-coral-dark mt-1 inline-block font-semibold underline">Official site</a>
            </div>
          )}
        </>
      )}
    </li>
  )
}

/** Ways to legally pay less tax, worked out from the person's own documents. */
export function TaxSuggestions({ sessionId }: { sessionId: string }) {
  const [data, setData] = useState<TaxSuggestionsResult | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    setData(null)
    setFailed(false)
    api.taxSuggestions(sessionId).then(setData).catch(() => setFailed(true))
  }, [sessionId])

  if (failed) return null
  return (
    <section className="mt-8" aria-labelledby="tax-sugg-h">
      <h2 id="tax-sugg-h" className="section-label">Ways to pay less tax</h2>
      <div className="card mt-3 p-4">
        {!data && <div className="animate-pulse bg-slate-500/15 h-16 rounded-xl" aria-label="Loading" />}
        {data && (
          <>
            <p className="text-muted text-sm">
              On your salary of {formatINR(data.picture.gross_salary_annual)}: tax is about {formatINR(data.picture.new_regime_tax)} under the new regime and {formatINR(data.picture.old_regime_tax)} under the old one.{' '}
              <span className="text-ink font-semibold">The {data.picture.cheaper_regime} regime is cheaper for you.</span>
            </p>
            <ul className="divide-y divide-[color:var(--color-line)] mt-2">
              {data.suggestions.map((s) => (
                <Card key={s.id} s={s} />
              ))}
            </ul>
            <p className="text-muted mt-2 text-xs">
              Rules as of {data.notes_as_of}{data.reviewed_by_ca ? '' : ', not yet reviewed by a CA'}. {data.disclaimer}
            </p>
          </>
        )}
      </div>
    </section>
  )
}
