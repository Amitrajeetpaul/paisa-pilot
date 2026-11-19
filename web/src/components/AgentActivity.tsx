import { useState } from 'react'
import { api, type AgentRunResult } from '../lib/api'

const AGENT_LABEL = { money_finder: 'Money Finder agent', leak_fixer: 'Leak Fixer agent', ca_assistant: 'CA Assistant agent' } as const

const TOOL_LABEL: Record<string, string> = {
  compare_tax_regimes: 'Compared old vs new tax regime',
  review_pf_accounts_tool: 'Reviewed PF accounts',
  find_refund_opportunities: 'Scanned for failed / double payments',
  detect_recurring_charges_tool: 'Detected recurring charges',
  tds_reconciliation_tool: 'Checked Form 16 TDS against your AIS',
  deduction_limits_tool: 'Looked up deduction limits',
  breakeven_deductions_tool: 'Worked out the old-regime break-even',
  itr_form_tool: 'Picked the likely ITR form',
  filing_readiness_tool: 'Checked which documents are missing',
}

/** Shows what an ADK agent did: the tools it called (each backed by the rules
 * engine) and the answer it wrote from those results. Run on demand so the
 * page never waits on a model call. */
export function AgentActivity({ sessionId, agent }: { sessionId: string; agent: keyof typeof AGENT_LABEL }) {
  const [run, setRun] = useState<AgentRunResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function start() {
    setLoading(true)
    setError(null)
    try {
      setRun(await api.runAgent(sessionId, agent))
    } catch {
      setError('The agent could not run. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="border-line mt-6 rounded-[20px] border bg-white p-5" aria-label="Agent activity">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-navy text-base font-bold">🤖 {AGENT_LABEL[agent]}</h2>
          <p className="text-muted text-xs">A Google ADK agent. It calls the rules engine; it never makes up a number.{agent === 'ca_assistant' && ' Prepares you for a CA; it is not a CA.'}</p>
        </div>
        {!run && (
          <button
            type="button"
            onClick={start}
            disabled={loading}
            className="bg-coral-button text-navy min-h-11 shrink-0 rounded-[18px] px-4 text-sm font-semibold disabled:opacity-60"
          >
            {loading ? 'Running…' : 'Run agent'}
          </button>
        )}
      </div>

      {error && <p className="mt-3 text-sm font-medium text-[#C0392B]">{error}</p>}

      {run && (
        <div className="mt-4 flex flex-col gap-3">
          <span className="bg-teal-tint text-navy w-fit rounded-full px-2.5 py-1 text-xs font-semibold">
            {run.engine === 'gemini' ? 'Driven by Gemini' : 'Driven by offline model (Gemini unavailable or in demo mode)'}
          </span>
          <ol className="flex flex-col gap-2">
            {run.tool_calls.map((c, i) => (
              <li key={i} className="border-line rounded-2xl border p-3">
                <p className="text-navy text-sm font-semibold">
                  {i + 1}. {TOOL_LABEL[c.tool] ?? c.tool}
                </p>
                <details className="mt-1">
                  <summary className="text-muted cursor-pointer text-xs">Tool result</summary>
                  <pre className="text-muted mt-1 max-h-40 overflow-auto text-xs">{JSON.stringify(c.result, null, 2)}</pre>
                </details>
              </li>
            ))}
          </ol>
          <p className="text-navy whitespace-pre-line text-sm leading-relaxed">{run.answer}</p>
          <button type="button" onClick={start} className="text-muted w-fit text-xs font-semibold underline">
            Run again
          </button>
        </div>
      )}
    </section>
  )
}
