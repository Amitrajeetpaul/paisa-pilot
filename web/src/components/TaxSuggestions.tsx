import { useEffect, useState } from 'react'
import { api, type AgeBand, type TaxSuggestion, type TaxSuggestionsResult } from '../lib/api'
import { useApp } from '../state/AppContext'
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
            {open ? 'Hide the rule' : `The rule: ${s.law.section}${s.law.new_act_section ? ` (${s.law.new_act_section} from FY 2026-27)` : ''}`}
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
  const { t } = useApp()
  const [data, setData] = useState<TaxSuggestionsResult | null>(null)
  const [failed, setFailed] = useState(false)
  const [age, setAge] = useState<AgeBand>(() => {
    try {
      return (localStorage.getItem('pp_age_band') as AgeBand) || 'below_60'
    } catch {
      return 'below_60'
    }
  })

  useEffect(() => {
    let live = true
    api.taxSuggestions(sessionId, age).then((d) => live && setData(d)).catch(() => live && setFailed(true))
    return () => {
      live = false
    }
  }, [sessionId, age])

  if (failed) return null
  return (
    <section aria-labelledby="tax-sugg-h">
      <h2 id="tax-sugg-h" className="section-label">{t('ui.waysToSave')}</h2>
      <div className="card mt-3 p-4">
        <label className="text-muted mb-3 flex items-center gap-2 text-sm">
          {t('ui.yourAge')}
          <select
            value={age}
            onChange={(e) => {
              const v = e.target.value as AgeBand
              setAge(v)
              try {
                localStorage.setItem('pp_age_band', v)
              } catch {
                /* remembered only for this visit */
              }
            }}
            className="border-line bg-white text-ink min-h-11 rounded-xl border px-3 text-sm"
          >
            <option value="below_60">{t('ui.age.below60')}</option>
            <option value="60_79">{t('ui.age.60to79')}</option>
            <option value="80_plus">{t('ui.age.80plus')}</option>
          </select>
        </label>
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
