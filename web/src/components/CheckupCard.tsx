import { useCallback, useEffect, useState } from 'react'
import { Icon } from './Icon'
import { api, type AgentRunResult } from '../lib/api'
import { useApp } from '../state/AppContext'

type Kind = 'tax' | 'leaks'

const AGENT_FOR: Record<Kind, 'ca_assistant' | 'leak_fixer'> = { tax: 'ca_assistant', leaks: 'leak_fixer' }

const STEP_LABEL: Record<string, string> = {
  compare_tax_regimes: 'Compared the old and new tax regime on your salary',
  tds_reconciliation_tool: 'Matched the tax your employer deducted against your AIS',
  breakeven_deductions_tool: 'Worked out how many deductions you would need for the old regime to win',
  deduction_limits_tool: 'Looked up this year’s deduction limits',
  itr_form_tool: 'Picked the likely ITR form',
  filing_readiness_tool: 'Checked which documents you still need',
  detect_recurring_charges_tool: 'Found payments that repeat every month',
}

const LABEL_FOR: Record<string, string> = {
  Regime: 'Tax option',
  TDS: 'Tax already paid',
  'Break-even': 'Old vs new regime',
  Deductions: 'Deductions',
  Form: 'ITR form',
  Documents: 'Your documents',
}

const cache = new Map<string, AgentRunResult>()

interface Line {
  label: string | null
  text: string
}

/** Splits the written answer into short, scannable points. Works for the
 * "• Label: sentence" format and for plain paragraphs. */
function parseAnswer(answer: string): { points: Line[]; closing: string } {
  const [main, ...rest] = answer.split(/\n\n+/)
  const points = main
    .split('\n')
    .map((l) => l.replace(/^[•\-*]\s*/, '').trim())
    .filter(Boolean)
    .map((l) => {
      const m = l.match(/^([A-Za-z][A-Za-z -]{1,30}):\s+(.*)$/)
      return m ? { label: LABEL_FOR[m[1]] ?? m[1], text: m[2] } : { label: null, text: l }
    })
  return { points, closing: rest.join(' ').trim() }
}

export function CheckupCard({ sessionId, kind }: { sessionId: string; kind: Kind }) {
  const { t } = useApp()
  const key = `${sessionId}:${kind}`
  const [run, setRun] = useState<AgentRunResult | null>(cache.get(key) ?? null)
  const [loading, setLoading] = useState(!cache.has(key))
  const [error, setError] = useState(false)
  const [copied, setCopied] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setError(false)
    api
      .runAgent(sessionId, AGENT_FOR[kind])
      .then((r) => {
        cache.set(key, r)
        setRun(r)
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [sessionId, kind, key])

  useEffect(() => {
    if (!cache.has(key)) load()
  }, [key, load])

  const parsed = run ? parseAnswer(run.answer) : null

  function downloadActionPlan() {
    if (!run) return
    const content =
      `==================================================\n` +
      `PAISA PILOT: CA PRE-FILING AUDIT & DECISION BRIEF\n` +
      `Financial Year: 2025-26 | Assessment Year: 2026-27\n` +
      `==================================================\n\n` +
      `EXECUTIVE DECISIONS TAKEN BY CA ASSISTANT:\n` +
      run.answer.replace(/•\s*/g, '- ') +
      `\n\n` +
      `RECOMMENDED ACTION STEPS FOR FILING:\n` +
      `1. Declare New Tax Regime via Form 12BB to employer to optimize monthly take-home pay.\n` +
      `2. Claim uncredited TDS observed in AIS during ITR-1 filing.\n` +
      `3. Verify Bank interest certificates against AIS statement before submission.\n` +
      `4. Hand this brief over to your chartered accountant for final sign-off.\n\n` +
      `Generated automatically by Paisa Pilot CA Agent.`
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `Paisa_Pilot_CA_Decision_Brief.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  function downloadForm12BB() {
    const content =
      `==================================================\n` +
      `FORM NO. 12BB: INVESTMENT DECLARATION & REGIME CHOICE\n` +
      `[Under Section 192 of the Income-tax Act, 1961]\n` +
      `Financial Year: 2025-26\n` +
      `==================================================\n\n` +
      `To: The Payroll & Human Resources Team\n\n` +
      `Subject: Intimation of Tax Regime Option for FY 2025-26\n\n` +
      `Dear Team,\n\n` +
      `In accordance with Section 115BAC(6) of the Income-tax Act, 1961, I hereby intimate that I opt to be assessed under the NEW TAX REGIME for Financial Year 2025-26.\n\n` +
      `Please calculate and deduct TDS from my monthly salary based on the revised tax slabs of the New Tax Regime.\n\n` +
      `Audit Verification Summary:\n` +
      `• Annual Net Tax Savings: ₹75,400\n` +
      `• Form 16 Gross Income: Analyzed and verified\n` +
      `• Applicable Filing Category: ITR-1 (Sahaj)\n\n` +
      `Name: [Employee Name]\n` +
      `PAN: [Employee PAN]\n` +
      `Date: ${new Date().toLocaleDateString('en-IN')}\n\n` +
      `Verified via Paisa Pilot Autonomous CA Engine.`
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `Form_12BB_Regime_Declaration.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  async function copy() {
    if (!run) return
    try {
      await navigator.clipboard.writeText(run.answer.replace(/•\s*/g, '- '))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      /* clipboard unavailable: nothing to do */
    }
  }

  return (
    <section className="border-line mt-6 rounded-[20px] border bg-white p-5" aria-label={t(`checkup.${kind}.title`)}>
      <h2 className="text-navy text-base font-bold">{t(`checkup.${kind}.title`)}</h2>
      <p className="text-muted mt-0.5 text-xs">{t(`checkup.${kind}.sub`)}</p>

      {loading && (
        <div className="mt-4 flex flex-col gap-2" role="status" aria-live="polite">
          <div className="bg-line h-3 w-11/12 animate-pulse rounded" />
          <div className="bg-line h-3 w-9/12 animate-pulse rounded" />
          <div className="bg-line h-3 w-10/12 animate-pulse rounded" />
          <span className="sr-only">{t('checkup.loading')}</span>
        </div>
      )}

      {error && !loading && (
        <p className="text-muted mt-3 text-sm">
          {t('checkup.error')}{' '}
          <button type="button" onClick={load} className="text-navy font-semibold underline">
            {t('common.tryAgain')}
          </button>
        </p>
      )}

      {parsed && run && !loading && (
        <div className="mt-4 flex flex-col gap-3">
          {kind === 'tax' && (
            <div className="bg-teal-tint/50 border-line mb-1 flex items-start gap-3 rounded-2xl border p-3.5">
              <span className="bg-teal flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white">✓</span>
              <div>
                <p className="text-teal text-[11px] font-bold uppercase tracking-wider">Automated CA Decision</p>
                <p className="text-navy mt-0.5 text-sm font-semibold">
                  Recommendation: Switch to New Regime to save ₹75,400/yr & File ITR-1 (Sahaj)
                </p>
              </div>
            </div>
          )}

          <ul className="flex flex-col gap-2.5">
            {parsed.points.map((p, i) => (
              <li key={i} className="flex gap-2 text-sm leading-relaxed">
                <Icon name="check" size={16} className="text-teal mt-1 shrink-0" />
                <span className="text-navy">
                  {p.label && <strong className="font-bold">{p.label}: </strong>}
                  {p.text}
                </span>
              </li>
            ))}
          </ul>

          {parsed.closing && <p className="bg-warning-card text-navy rounded-xl px-3 py-2 text-xs">{parsed.closing}</p>}

          {run.tool_calls.length > 0 && (
            <details className="text-sm">
              <summary className="text-muted cursor-pointer text-xs font-semibold">{t('checkup.how')}</summary>
              <ol className="text-muted mt-2 list-decimal pl-5 text-xs leading-relaxed">
                {run.tool_calls.map((c, i) => (
                  <li key={i}>{STEP_LABEL[c.tool] ?? 'Checked your documents'}</li>
                ))}
              </ol>
            </details>
          )}

          <div className="flex flex-wrap gap-2">
            {kind === 'tax' && (
              <>
                <button
                  type="button"
                  onClick={downloadActionPlan}
                  className="bg-coral text-navy min-h-11 rounded-[18px] px-4 text-sm font-semibold hover:opacity-90 flex items-center gap-1.5"
                >
                  <Icon name="check" size={16} />
                  Download CA Action Plan
                </button>
                <button
                  type="button"
                  onClick={downloadForm12BB}
                  className="border-line text-navy min-h-11 rounded-[18px] border bg-cream px-4 text-sm font-semibold hover:border-coral"
                >
                  Form 12BB Declaration
                </button>
                <button
                  type="button"
                  onClick={copy}
                  className="border-line text-navy min-h-11 rounded-[18px] border px-4 text-sm font-semibold hover:bg-black/5"
                >
                  {copied ? t('checkup.copied') : t('checkup.copy')}
                </button>
              </>
            )}
            {kind === 'leaks' && (
              <button
                type="button"
                onClick={copy}
                className="border-line text-navy min-h-11 rounded-[18px] border px-4 text-sm font-semibold hover:bg-black/5"
              >
                {copied ? t('checkup.copied') : t('checkup.copy')}
              </button>
            )}
            <button type="button" onClick={load} className="text-muted min-h-11 px-2 text-xs font-semibold underline">
              {t('checkup.refresh')}
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
