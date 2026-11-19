import { useEffect, useRef, useState } from 'react'
import { api, type SourceTrailEntry } from '../lib/api'
import { formatINR } from '../lib/format'
import { formatInputValue, humanizeKey } from '../lib/plain'
import { useApp } from '../state/AppContext'

interface SourceDrawerProps {
  entry: SourceTrailEntry | null
  loading?: boolean
  onClose: () => void
  /** What this number is, shown big at the top of the sheet. */
  headline?: { title: string; amount: number; unit: string } | null
  /** The next step for this finding (draft a message, claim, cancel...). */
  primaryAction?: { label: string; onClick: () => void } | null
}

/** Detail sheet: the number, the proof behind it, and the next step. */
export function SourceDrawer({ entry, loading, onClose, headline, primaryAction }: SourceDrawerProps) {
  const { t, sessionId } = useApp()
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const open = entry !== null || loading
  const [reporting, setReporting] = useState(false)
  const [note, setNote] = useState('')
  const [sent, setSent] = useState(false)

  useEffect(() => {
    setReporting(false)
    setNote('')
    setSent(false)
  }, [entry?.card_id])

  async function sendReport() {
    if (!entry || !note.trim()) return
    try {
      await api.reportWrongNumber(entry.card_id, note.trim(), sessionId)
      setSent(true)
    } catch {
      /* leave the form open so the person can try again */
    }
  }

  useEffect(() => {
    if (open) closeButtonRef.current?.focus()
  }, [open])

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    if (open) document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center md:items-center" role="presentation">
      <button aria-label="Close details" className="absolute inset-0 bg-black/40" onClick={onClose} tabIndex={-1} />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Details"
        className="animate-drawer-slide-up relative flex max-h-[88vh] w-full max-w-lg flex-col overflow-hidden rounded-t-[24px] bg-white shadow-2xl md:rounded-[24px]"
      >
        <div className="mx-auto mt-2 h-1 w-10 rounded-full bg-black/10 md:hidden" aria-hidden="true" />
        <div className="flex items-start justify-between gap-3 px-5 pb-3 pt-4">
          <div className="min-w-0">
            <p className="section-label">{headline?.title ?? entry?.label ?? t('common.source')}</p>
            {headline && (
              <p className="tabular text-ink mt-1 text-3xl font-extrabold leading-none">
                {formatINR(headline.amount)} <span className="text-muted text-sm font-medium">{headline.unit}</span>
              </p>
            )}
          </div>
          <button
            ref={closeButtonRef}
            onClick={onClose}
            aria-label="Close"
            className="text-muted flex h-9 w-9 shrink-0 items-center justify-center rounded-full hover:bg-black/5"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 pb-4">
          {loading && <p className="text-muted text-sm">{t('common.loading')}</p>}
          {entry && (
            <div className="flex flex-col gap-5">
              <section>
                <h4 className="section-label">How we worked it out</h4>
                <p className="text-ink mt-1.5 text-sm leading-relaxed">{entry.rule_or_formula}</p>
              </section>
              {Object.keys(entry.inputs_used).length > 0 && (
                <section>
                  <h4 className="section-label">What we used</h4>
                  <dl className="border-line mt-1.5 divide-y rounded-xl border text-sm">
                    {Object.entries(entry.inputs_used).map(([key, value]) => (
                      <div key={key} className="flex justify-between gap-3 px-3 py-2.5">
                        <dt className="text-muted">{humanizeKey(key)}</dt>
                        <dd className="text-ink text-right font-semibold">{formatInputValue(key, value)}</dd>
                      </div>
                    ))}
                  </dl>
                </section>
              )}
              {(entry.config_version || entry.source_url) && (
                <section>
                  <h4 className="section-label">Rules used</h4>
                  <p className="text-ink mt-1.5 text-sm">
                    {entry.config_version && <>Financial year {entry.config_version.replace(/^fy/i, '')}. </>}
                    {entry.source_url && (
                      <a href={entry.source_url} target="_blank" rel="noreferrer" className="text-teal underline">
                        Read the official rules
                      </a>
                    )}
                  </p>
                </section>
              )}
              {sent ? (
                <p className="text-teal text-sm font-semibold" role="status">
                  Thanks, we will look into it.
                </p>
              ) : reporting ? (
                <div className="flex flex-col gap-2">
                  <label htmlFor="wrong-note" className="text-ink text-sm font-semibold">
                    What looks wrong?
                  </label>
                  <textarea
                    id="wrong-note"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    maxLength={500}
                    rows={3}
                    className="border-line text-ink rounded-xl border p-3 text-sm outline-none"
                    placeholder="For example: my gross salary is different"
                  />
                  <button
                    type="button"
                    onClick={sendReport}
                    disabled={!note.trim()}
                    className="bg-navy min-h-11 rounded-xl text-sm font-semibold text-white disabled:opacity-50"
                  >
                    Send
                  </button>
                </div>
              ) : (
                <button type="button" onClick={() => setReporting(true)} className="text-muted self-start text-sm font-semibold underline">
                  {t('common.reportWrongNumber')}
                </button>
              )}
            </div>
          )}
        </div>

        {primaryAction && (
          <div className="border-line border-t bg-white p-4" style={{ paddingBottom: 'calc(1rem + env(safe-area-inset-bottom, 0px))' }}>
            <button
              type="button"
              onClick={primaryAction.onClick}
              className="bg-coral-button press min-h-12 w-full rounded-xl text-base font-bold"
            >
              {primaryAction.label}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
