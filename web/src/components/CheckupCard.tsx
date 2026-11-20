import { useCallback, useEffect, useState } from 'react'
import { formatINR } from '../lib/format'
import { stripMarkdown } from '../lib/plain'
import { Icon } from './Icon'
import { track } from '../lib/track'
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
      .runAgent(sessionId, AGENT_FOR[kind], undefined, true)
      .then((r) => {
        cache.set(key, r)
        setRun(r)
        track('checkup_viewed', kind)
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [sessionId, kind, key])

  useEffect(() => {
    if (!cache.has(key)) load()
  }, [key, load])

  const parsed = run ? parseAnswer(stripMarkdown(run.answer)) : null

  function result(tool: string): Record<string, unknown> | null {
    return run?.tool_calls.find((c) => c.tool === tool)?.result ?? null
  }

  function saveTextFile(filename: string, content: string) {
    const url = URL.createObjectURL(new Blob([content], { type: 'text/plain' }))
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const regimeResult = run ? (result('compare_tax_regimes') as { recommended_regime?: string; annual_saving_if_switch?: number } | null) : null

  /** A tax summary the person can use themselves or share. Every step comes from their own results. */
  function downloadActionPlan() {
    if (!run) return
    const steps: string[] = []
    if (regimeResult?.recommended_regime === 'new') {
      steps.push('Ask your employer\'s payroll team to calculate your TDS under the new tax regime. Confirm with them how to submit your choice.')
    } else if (regimeResult?.recommended_regime === 'old') {
      steps.push('Your current regime is already the cheaper one. Keep it, and keep your deduction proofs ready.')
    }
    const tds = result('tds_reconciliation_tool') as { claimable_extra_tds?: number; missing_from_ais?: number } | null
    if (tds?.claimable_extra_tds) steps.push(`Claim ${formatINR(tds.claimable_extra_tds)} of tax already deducted (shown in your AIS) as credit when you file.`)
    if (tds?.missing_from_ais) steps.push(`Ask your employer whether ${formatINR(tds.missing_from_ais)} of deducted tax was deposited; it is missing from your AIS.`)
    const itr = result('itr_form_tool') as { form?: string } | null
    if (itr?.form) steps.push(`Likely ITR form: ${itr.form} (assuming salary and interest income only; anything else would change this).`)
    const docs = result('filing_readiness_tool') as { missing_descriptions?: string[] } | null
    if (docs?.missing_descriptions?.length) steps.push(`Gather: ${docs.missing_descriptions.join('; ')}.`)
    steps.push('Keep your documents and investment proofs ready. For capital gains, business income or a tax notice, a CA\'s help is worth it.')

    saveTextFile(
      'Paisa_Pilot_Tax_Summary.txt',
      `PAISA PILOT: TAX CHECK-UP SUMMARY (FY 2025-26)\n` +
        `Prepared from the documents you confirmed. These are estimates from this year's published rules, not a filing. Nothing has been filed.\n\n` +
        `WHAT WE FOUND\n${run.answer.replace(/•\s*/g, '- ')}\n\n` +
        `SUGGESTED NEXT STEPS\n${steps.map((x, i) => `${i + 1}. ${x}`).join('\n')}\n`,
    )
  }

  /** A draft the person edits and sends themselves; nothing is sent for them. */
  function downloadRegimeMessage() {
    if (!regimeResult?.recommended_regime) return
    const regime = regimeResult.recommended_regime === 'new' ? 'new' : 'old'
    const saving = regimeResult.annual_saving_if_switch
    saveTextFile(
      'Draft_message_to_employer_tax_regime.txt',
      `DRAFT: review it, edit it, and send it yourself.\n\n` +
        `Subject: Tax regime for FY 2025-26\n\n` +
        `Dear Payroll team,\n\n` +
        `I would like TDS on my salary for FY 2025-26 to be calculated under the ${regime} tax regime. ` +
        `Please confirm the process and any form you need from me.\n\n` +
        (regime === 'new' && saving
          ? `My estimate suggests this could reduce my yearly tax by about ${formatINR(saving)}.\n\n`
          : '') +
        `Name: [Your name]\nEmployee ID: [Your ID]\nDate: ${new Date().toLocaleDateString('en-IN')}\n`,
    )
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
    <section className="card mt-6 p-5" aria-label={t(`checkup.${kind}.title`)}>
      <h2 className="text-ink text-base font-bold">{t(`checkup.${kind}.title`)}</h2>
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
          <button type="button" onClick={load} className="text-ink font-semibold underline">
            {t('common.tryAgain')}
          </button>
        </p>
      )}

      {parsed && run && !loading && (
        <div className="mt-4 flex flex-col gap-3">
          {kind === 'tax' && regimeResult?.recommended_regime && (
            <div className="bg-teal-tint/50 border-line mb-1 flex items-start gap-3 rounded-2xl border p-3.5">
              <Icon name="check" size={18} className="text-teal mt-0.5 shrink-0" />
              <div>
                <p className="text-teal text-[11px] font-bold uppercase tracking-wider">Our check suggests</p>
                <p className="text-ink mt-0.5 text-sm font-semibold">
                  {regimeResult.recommended_regime === 'new'
                    ? `The new tax regime looks cheaper for you${regimeResult.annual_saving_if_switch ? `, by about ${formatINR(regimeResult.annual_saving_if_switch)} a year` : ''}.`
                    : 'Your current tax regime looks like the cheaper one.'}{' '}
                  Based on your Form 16 and this year's rules.
                </p>
              </div>
            </div>
          )}

          <ul className="flex flex-col gap-2.5">
            {parsed.points.map((p, i) => (
              <li key={i} className="flex gap-2 text-sm leading-relaxed">
                <Icon name="check" size={16} className="text-teal mt-1 shrink-0" />
                <span className="text-ink">
                  {p.label && <strong className="font-bold">{p.label}: </strong>}
                  {p.text}
                </span>
              </li>
            ))}
          </ul>

          {parsed.closing && <p className="bg-warning-card text-ink whitespace-pre-line rounded-xl px-3 py-2 text-xs leading-relaxed">{parsed.closing}</p>}

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

          <div className="flex flex-col sm:flex-row flex-wrap gap-2.5">
            {kind === 'tax' && (
              <>
                <button
                  type="button"
                  onClick={downloadActionPlan}
                  className="bg-coral text-navy min-h-11 rounded-[18px] px-4 py-2 text-sm font-bold hover:opacity-90 flex items-center justify-center gap-1.5 w-full sm:w-auto text-center"
                >
                  <Icon name="check" size={16} />
                  Download my tax summary
                </button>
                {regimeResult?.recommended_regime && (
                  <button
                    type="button"
                    onClick={downloadRegimeMessage}
                    className="border-line text-ink min-h-11 rounded-[18px] border bg-cream px-4 py-2 text-sm font-semibold hover:border-coral flex items-center justify-center w-full sm:w-auto text-center"
                  >
                    Draft message to employer
                  </button>
                )}
                <button
                  type="button"
                  onClick={copy}
                  className="border-line text-ink min-h-11 rounded-[18px] border px-4 py-2 text-sm font-semibold hover:bg-black/5 flex items-center justify-center w-full sm:w-auto text-center"
                >
                  {copied ? t('checkup.copied') : t('checkup.copy')}
                </button>
              </>
            )}
            {kind === 'leaks' && (
              <button
                type="button"
                onClick={copy}
                className="border-line text-ink min-h-11 rounded-[18px] border px-4 text-sm font-semibold hover:bg-black/5"
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
