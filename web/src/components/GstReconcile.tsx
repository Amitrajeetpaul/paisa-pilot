import { useState } from 'react'
import { ApiError, api, type GstReconcileResult, type ReconFinding } from '../lib/api'
import { formatINR } from '../lib/format'

const STATUS: Record<ReconFinding['status'], { label: string; cls: string }> = {
  missing_in_2b: { label: 'Not in GSTR-2B', cls: 'bg-red-500/15 text-red-500' },
  amount_mismatch: { label: 'Amount differs', cls: 'bg-amber-500/15 text-amber-600' },
  probable_match: { label: 'Check the number', cls: 'bg-amber-500/15 text-amber-600' },
  not_in_books: { label: 'Not in your books', cls: 'bg-sky-500/15 text-sky-600' },
  matched: { label: 'Matched', cls: 'bg-emerald-500/15 text-emerald-600' },
}

/** Which input credit is safe to claim: your purchase register against what your suppliers reported (GSTR-2B). */
export function GstReconcile() {
  const [books, setBooks] = useState<{ name: string; text: string } | null>(null)
  const [twob, setTwob] = useState<{ name: string; text: string } | null>(null)
  const [result, setResult] = useState<GstReconcileResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [showMatched, setShowMatched] = useState(false)

  async function run(b: string, g: string) {
    setBusy(true)
    setErr(null)
    try {
      setResult(await api.gstReconcile(b, g))
    } catch (e) {
      setResult(null)
      setErr(e instanceof ApiError ? e.message : 'Could not compare the files. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  async function sample() {
    setBusy(true)
    try {
      const s = await api.gstReconcileSample()
      setBooks({ name: 'sample purchase register', text: s.books_csv })
      setTwob({ name: 'sample GSTR-2B', text: s.gstr2b_csv })
      await run(s.books_csv, s.gstr2b_csv)
    } catch {
      setErr('Could not load the sample. Please try again.')
      setBusy(false)
    }
  }

  const pick = (set: (v: { name: string; text: string }) => void) => async (f: File | undefined) => {
    if (f) set({ name: f.name, text: await f.text() })
  }

  const shown = result ? result.findings.filter((f) => showMatched || f.status !== 'matched') : []
  return (
    <section className="card mt-5 p-4" aria-labelledby="gst-recon">
      <h2 id="gst-recon" className="section-label">Check your input credit against GSTR-2B</h2>
      <p className="text-muted mt-2 text-sm">
        You can claim credit only on invoices your suppliers have reported. Upload your purchase register and your GSTR-2B (both CSV with supplier_gstin, invoice_no, taxable_value and tax, or igst/cgst/sgst) and we show what is safe to claim.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <label className="bg-slate-500/15 text-ink press inline-flex min-h-11 cursor-pointer items-center rounded-xl px-3 text-sm font-semibold">
          {books ? `Purchases: ${books.name}` : 'Purchase register'}
          <input type="file" accept=".csv,text/csv" className="sr-only" onChange={(e) => void pick(setBooks)(e.target.files?.[0])} />
        </label>
        <label className="bg-slate-500/15 text-ink press inline-flex min-h-11 cursor-pointer items-center rounded-xl px-3 text-sm font-semibold">
          {twob ? `GSTR-2B: ${twob.name}` : 'GSTR-2B file'}
          <input type="file" accept=".csv,text/csv" className="sr-only" onChange={(e) => void pick(setTwob)(e.target.files?.[0])} />
        </label>
        <button type="button" disabled={!books || !twob || busy} onClick={() => books && twob && void run(books.text, twob.text)} className="bg-coral-button press min-h-11 rounded-xl px-4 text-sm font-bold disabled:opacity-50">
          Compare
        </button>
        <button type="button" onClick={() => void sample()} className="text-ink min-h-11 rounded-xl px-3 text-sm font-semibold underline">
          Try with sample files
        </button>
      </div>
      {busy && <p className="text-muted mt-3 text-sm">Comparing…</p>}
      {err && <p className="mt-3 text-sm text-red-600" role="alert">{err}</p>}

      {result && (
        <div className="mt-4">
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            <div className="bg-emerald-500/10 rounded-2xl p-3"><p className="text-muted text-xs">Safe to claim</p><p className="tabular text-ink text-xl font-extrabold">{formatINR(result.summary.safe_to_claim)}</p></div>
            <div className="bg-red-500/10 rounded-2xl p-3"><p className="text-muted text-xs">Credit at risk</p><p className="tabular text-ink text-xl font-extrabold">{formatINR(result.summary.itc_at_risk)}</p></div>
            <div className="bg-sky-500/10 rounded-2xl p-3"><p className="text-muted text-xs">Credit you may be missing</p><p className="tabular text-ink text-xl font-extrabold">{formatINR(result.summary.credit_not_yet_recorded)}</p></div>
          </div>
          {result.summary.invalid_gstins.length > 0 && (
            <p className="bg-amber-500/10 text-ink mt-3 rounded-xl p-3 text-sm">These supplier GSTINs do not look valid: {result.summary.invalid_gstins.join(', ')}. Check them.</p>
          )}
          <ul className="divide-y divide-[color:var(--color-line)] mt-3">
            {shown.map((f, i) => (
              <li key={`${f.invoice_no}-${i}`} className="py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${STATUS[f.status].cls}`}>{STATUS[f.status].label}</span>
                  <span className="text-ink text-sm font-semibold">{f.supplier_name || f.supplier_gstin}</span>
                  <span className="text-muted text-xs">invoice {f.invoice_no}</span>
                  {f.itc_at_risk > 0 && <span className="text-ink ml-auto text-sm font-bold">{formatINR(f.itc_at_risk)} at risk</span>}
                  {f.credit_not_yet_recorded > 0 && <span className="text-ink ml-auto text-sm font-bold">{formatINR(f.credit_not_yet_recorded)} to record</span>}
                </div>
                <p className="text-muted mt-1 text-sm">{f.message}</p>
                {f.what_to_do && <p className="text-ink mt-1 text-sm">{f.what_to_do}</p>}
              </li>
            ))}
          </ul>
          {result.summary.counts.matched ? (
            <button type="button" onClick={() => setShowMatched((v) => !v)} className="text-coral-dark mt-2 min-h-11 text-sm font-semibold underline">
              {showMatched ? 'Hide matched invoices' : `Show ${result.summary.counts.matched} matched invoice${result.summary.counts.matched === 1 ? '' : 's'}`}
            </button>
          ) : null}
          <p className="text-muted mt-2 text-xs">
            Rule: {result.law.map((l) => l.section).join('; ')}. Notes as of {result.notes_as_of}{result.reviewed_by_ca ? '' : ', not yet reviewed by a CA'}. {result.disclaimer}
          </p>
        </div>
      )}
    </section>
  )
}
