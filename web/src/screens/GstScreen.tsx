import { useState } from 'react'
import { ApiError, api, type GstAskResult, type GstDraftResult } from '../lib/api'
import { formatINR } from '../lib/format'

const EXAMPLES = ['Can I claim GST credit on a laptop or a car?', 'Do I need GST as a freelancer?', 'What is the late fee for filing late?', 'How do I export services without paying GST?']

function Citations({ items }: { items: GstAskResult['citations'] }) {
  if (items.length === 0) return null
  return (
    <ul className="mt-3 space-y-2">
      {items.map((c) => (
        <li key={c.id} className="bg-slate-500/10 rounded-xl p-3 text-xs">
          <span className="text-ink font-bold">{c.section}</span>
          <span className="text-muted"> · {c.title}</span>
          <p className="text-muted mt-1">{c.excerpt}</p>
          <a href={c.source_url} target="_blank" rel="noreferrer" className="text-coral-dark mt-1 inline-block font-semibold underline">
            Official site
          </a>
        </li>
      ))}
    </ul>
  )
}

export function GstScreen() {
  const [q, setQ] = useState('')
  const [asking, setAsking] = useState(false)
  const [answer, setAnswer] = useState<GstAskResult | null>(null)
  const [draft, setDraft] = useState<GstDraftResult | null>(null)
  const [drafting, setDrafting] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [meta, setMeta] = useState<{ annual_turnover?: number; business_type?: string }>({})

  const ask = async (question: string) => {
    if (!question.trim()) return
    setQ(question)
    setAsking(true)
    setErr(null)
    try {
      setAnswer(await api.gstAsk(question))
    } catch {
      setErr('Could not reach the GST assistant. Please try again.')
    } finally {
      setAsking(false)
    }
  }

  const runDraft = async (csv_text: string, extra: { annual_turnover?: number; business_type?: string } = meta) => {
    setDrafting(true)
    setErr(null)
    try {
      setDraft(await api.gstDraft({ csv_text, ...extra }))
    } catch (e) {
      setDraft(null)
      setErr(e instanceof ApiError ? e.message : 'Could not prepare the draft. Please try again.')
    } finally {
      setDrafting(false)
    }
  }

  const trySample = async () => {
    setDrafting(true)
    setErr(null)
    try {
      const s = await api.gstSample()
      const extra = { annual_turnover: s.annual_turnover, business_type: s.business_type }
      setMeta(extra)
      await runDraft(s.csv_text, extra)
    } catch {
      setErr('Could not load the sample. Please try again.')
      setDrafting(false)
    }
  }

  const onFile = async (file: File | undefined) => {
    if (!file) return
    setMeta({})
    await runDraft(await file.text(), {})
  }

  return (
    <div className="mx-auto max-w-4xl py-5 sm:py-7">
      <p className="text-muted text-sm font-medium">GST</p>
      <h1 className="text-ink text-2xl font-extrabold leading-tight tracking-tight">GST help for your business</h1>
      <p className="text-muted mt-1 text-sm">Ask a GST question and get the rule with its section number. Or upload your invoices and we prepare your monthly GSTR-3B summary.</p>

      <section className="card mt-5 p-4" aria-labelledby="gst-ask">
        <h2 id="gst-ask" className="section-label">Ask about GST</h2>
        <form
          className="mt-3 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            void ask(q)
          }}
        >
          <input value={q} onChange={(e) => setQ(e.target.value)} maxLength={600} placeholder="For example: can I claim credit on a car?" aria-label="Your GST question" className="border-line bg-white min-h-11 min-w-0 flex-1 rounded-xl border px-3 text-sm" />
          <button type="submit" disabled={asking || !q.trim()} className="bg-coral text-ink press min-h-11 rounded-xl px-4 text-sm font-bold disabled:opacity-50">
            {asking ? 'Checking…' : 'Ask'}
          </button>
        </form>
        <div className="mt-2 flex flex-wrap gap-2">
          {EXAMPLES.map((e) => (
            <button key={e} type="button" onClick={() => void ask(e)} className="bg-slate-500/15 text-ink rounded-full px-3 py-1.5 text-xs font-semibold">
              {e}
            </button>
          ))}
        </div>
        {answer && (
          <div className="mt-4" aria-live="polite">
            <p className="text-ink text-sm leading-relaxed">{answer.answer}</p>
            <Citations items={answer.citations} />
            <p className="text-muted mt-3 text-xs">
              {answer.mode === 'ai' ? 'Explained by AI from the rules above.' : answer.mode === 'notes_only' ? 'Shown straight from our GST notes.' : ''} Notes as of {answer.notes_as_of}
              {answer.reviewed_by_ca ? '.' : ', not yet reviewed by a CA.'} {answer.disclaimer}
            </p>
          </div>
        )}
      </section>

      <section className="card mt-5 p-4" aria-labelledby="gst-draft">
        <h2 id="gst-draft" className="section-label">Prepare your GSTR-3B summary</h2>
        <p className="text-muted mt-2 text-sm">
          Upload a CSV of your sales and purchases with these columns: type (sale or purchase), invoice_no, date, taxable_value, rate, supply (intra or inter), description. We use it only to work this out and do not keep it.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <label className="bg-coral text-ink press inline-flex min-h-11 cursor-pointer items-center rounded-xl px-4 text-sm font-bold">
            Upload invoices (CSV)
            <input type="file" accept=".csv,text/csv" className="sr-only" onChange={(e) => void onFile(e.target.files?.[0])} />
          </label>
          <button type="button" onClick={() => void trySample()} className="text-ink min-h-11 rounded-xl px-3 text-sm font-semibold underline">
            Try with sample invoices
          </button>
        </div>
        {drafting && <p className="text-muted mt-3 text-sm">Working it out…</p>}
        {err && <p className="mt-3 text-sm text-red-700" role="alert">{err}</p>}
        {draft && <Draft d={draft} />}
      </section>
    </div>
  )
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className={`flex items-baseline justify-between gap-3 py-2 text-sm ${strong ? 'text-ink font-extrabold' : 'text-ink'}`}>
      <span className={strong ? '' : 'text-muted'}>{label}</span>
      <span className="tabular">{value}</span>
    </div>
  )
}

function Draft({ d }: { d: GstDraftResult }) {
  const due = new Date(d.due_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
  return (
    <div className="mt-4">
      <div className="bg-coral-tint rounded-2xl p-4">
        <p className="text-muted text-xs font-semibold uppercase tracking-wide">GST to pay for {d.period}</p>
        <p className="tabular text-ink text-3xl font-extrabold">{formatINR(d.total_to_pay)}</p>
        <p className="text-muted text-xs">Due by {due} · {d.invoice_count} invoices used</p>
      </div>
      <div className="divide-y divide-[color:var(--color-line)] mt-2">
        <Row label="Your sales (taxable value)" value={formatINR(d.outward_taxable)} />
        <Row label="GST on your sales" value={formatINR(d.output_tax_total)} />
        <Row label="Credit on your purchases" value={`− ${formatINR(d.eligible_itc_total)}`} />
        <Row label="Paid in cash" value={formatINR(d.cash_payable.igst + d.cash_payable.cgst + d.cash_payable.sgst)} />
        {d.late_fee > 0 && <Row label={`Late fee (${d.days_late} days)`} value={formatINR(d.late_fee)} />}
        {d.interest > 0 && <Row label="Interest at 18% a year" value={formatINR(d.interest)} />}
        <Row label="Total to pay" value={formatINR(d.total_to_pay)} strong />
      </div>

      {d.blocked.length > 0 && (
        <div className="mt-4 rounded-2xl bg-amber-500/10 p-3 text-sm">
          <p className="text-ink font-bold">{formatINR(d.blocked_total)} of credit is not allowed</p>
          <ul className="text-muted mt-1 space-y-1">
            {d.blocked.map((b) => (
              <li key={b.invoice}>
                {b.description} ({b.invoice}): {formatINR(b.tax)}, {b.reason}. {b.section}
              </li>
            ))}
          </ul>
          {d.blocked_source && (
            <p className="text-muted mt-2 text-xs">
              Rule: {d.blocked_source.section}.{' '}
              <a href={d.blocked_source.source_url} target="_blank" rel="noreferrer" className="underline">
                Official site
              </a>
            </p>
          )}
        </div>
      )}

      {d.composition && (
        <div className="bg-slate-500/10 mt-4 rounded-2xl p-3 text-sm">
          <p className="text-ink font-bold">Composition scheme</p>
          {d.composition.eligible ? (
            <p className="text-muted mt-1">
              At {d.composition.rate_percent}% you would pay {formatINR(d.composition.composition_tax)} this month, against {formatINR(d.composition.regular_cash_tax)} under the regular scheme. {d.composition.note}
            </p>
          ) : (
            <p className="text-muted mt-1">Not available for you: {d.composition.reasons.join('; ')}.</p>
          )}
        </div>
      )}

      <ol className="text-muted mt-4 list-decimal space-y-1 pl-5 text-xs">
        {d.steps.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ol>
      <p className="text-muted mt-3 text-xs">
        Rules as of {d.notes_as_of}{d.reviewed_by_ca ? '' : ', not yet reviewed by a CA'}. {d.disclaimer}
      </p>
    </div>
  )
}
