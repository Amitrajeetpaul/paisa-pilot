import { useCallback, useEffect, useState } from 'react'
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
          <ul className="flex flex-col gap-2.5">
            {parsed.points.map((p, i) => (
              <li key={i} className="flex gap-2 text-sm leading-relaxed">
                <span aria-hidden="true" className="text-teal mt-0.5">
                  ✓
                </span>
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
              <button
                type="button"
                onClick={copy}
                className="border-line text-navy min-h-11 rounded-[18px] border px-4 text-sm font-semibold"
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
