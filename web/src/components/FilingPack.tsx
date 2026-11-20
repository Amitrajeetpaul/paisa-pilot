import { useEffect, useState } from 'react'
import { api, type ItrPack } from '../lib/api'
import { formatINR } from '../lib/format'
import { useApp } from '../state/AppContext'

const MARK = { ok: ['✓', 'text-emerald-600'], missing: ['!', 'text-red-500'], check: ['•', 'text-amber-600'] } as const

/** Everything needed to fill the income-tax portal, from the documents the person confirmed. Nothing is filed. */
export function FilingPack({ sessionId }: { sessionId: string }) {
  const { t } = useApp()
  const [p, setP] = useState<ItrPack | null>(null)
  const [failed, setFailed] = useState(false)
  const [note, setNote] = useState<string | null>(null)

  useEffect(() => {
    setP(null)
    setFailed(false)
    api.itrPrefill(sessionId).then(setP).catch(() => setFailed(true))
  }, [sessionId])

  if (failed) return null
  if (!p) return null

  async function copy() {
    try {
      await navigator.clipboard.writeText(p!.summary_text)
      setNote('Copied. Paste it into a note or send it to your CA.')
    } catch {
      setNote('Could not copy here. Use Download instead.')
    }
  }

  function download() {
    try {
      const blob = new Blob([JSON.stringify(p, null, 2)], { type: 'application/json' })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `paisa-pilot-filing-pack-${p!.financial_year}.json`
      a.click()
      setTimeout(() => URL.revokeObjectURL(a.href), 2000)
    } catch {
      setNote('Download is not available here. Use Copy instead.')
    }
  }

  const r = p.result
  return (
    <section className="card p-4" aria-labelledby="pack-h">
      <h2 id="pack-h" className="section-label">{t('ui.filingPack')}, FY {p.financial_year}</h2>
      <div className="bg-coral-tint mt-3 rounded-2xl p-3">
        <p className="text-muted text-xs font-semibold uppercase tracking-wide">{r.refund > 0 ? 'Estimated refund' : 'Estimated tax still to pay'} on the {r.regime} regime</p>
        <p className="tabular text-ink text-2xl font-extrabold">{formatINR(r.refund > 0 ? r.refund : r.still_to_pay)}</p>
        <p className="text-muted text-xs">
          Tax {formatINR(r.tax_payable)}, less {formatINR(r.tds_credit)} already deducted (TDS). Likely form: {p.suggested_form}.
        </p>
        <p className="text-muted mt-1 text-xs">
          On the {r.alternative.regime} regime instead: {r.alternative.refund > 0 ? `a refund of about ${formatINR(r.alternative.refund)}` : `you would pay about ${formatINR(r.alternative.still_to_pay)}`}. Figures include your {formatINR(r.includes_interest)} of interest, so they can differ slightly from the salary-only cards above.
        </p>
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
        <dt className="text-muted">Salary</dt><dd className="tabular text-right">{formatINR(p.income.salary_gross)}</dd>
        <dt className="text-muted">Interest (AIS)</dt><dd className="tabular text-right">{formatINR(p.income.interest_from_deposits)}</dd>
        <dt className="text-muted">Old regime tax (with interest)</dt><dd className="tabular text-right">{formatINR(p.tax.old_regime_tax)}</dd>
        <dt className="text-muted">New regime tax (with interest)</dt><dd className="tabular text-right">{formatINR(p.tax.new_regime_tax)}</dd>
      </dl>
      <ul className="mt-3 space-y-1.5">
        {p.checklist.map((c) => (
          <li key={c.item} className="flex items-start gap-2 text-sm">
            <span aria-hidden="true" className={`w-4 shrink-0 text-center font-bold ${MARK[c.status][1]}`}>{MARK[c.status][0]}</span>
            <span><span className="text-ink font-semibold">{c.item}.</span> <span className="text-muted">{c.why}</span></span>
          </li>
        ))}
      </ul>
      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" onClick={() => void copy()} className="bg-coral-button press min-h-11 rounded-xl px-4 text-sm font-bold">Copy summary</button>
        <button type="button" onClick={download} className="bg-slate-500/15 text-ink press min-h-11 rounded-xl px-4 text-sm font-semibold">Download JSON</button>
      </div>
      {note && <p className="text-muted mt-2 text-xs" role="status">{note}</p>}
      <p className="text-muted mt-2 text-xs">{p.disclaimer} Rules as of {p.notes_as_of}{p.reviewed_by_ca ? '' : ', not yet reviewed by a CA'}.</p>
    </section>
  )
}
