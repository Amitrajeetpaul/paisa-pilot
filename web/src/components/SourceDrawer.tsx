import { useEffect, useRef } from 'react'
import { useApp } from '../state/AppContext'
import type { SourceTrailEntry } from '../lib/api'
import { formatInputValue, humanizeKey } from '../lib/plain'
import { Button } from './Button'

interface SourceDrawerProps {
  entry: SourceTrailEntry | null
  loading?: boolean
  onClose: () => void
}

export function SourceDrawer({ entry, loading, onClose }: SourceDrawerProps) {
  const { t } = useApp()
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const open = entry !== null || loading

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
      <button
        aria-label="Close source details"
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        tabIndex={-1}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Number source"
        className="animate-drawer-slide-up relative max-h-[80vh] w-full max-w-lg overflow-y-auto rounded-t-[28px] bg-white p-6 shadow-2xl md:rounded-[28px]"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-navy text-lg font-bold">{t('common.source')}</h2>
          <button
            ref={closeButtonRef}
            onClick={onClose}
            aria-label="Close"
            className="text-muted flex h-9 w-9 items-center justify-center rounded-full hover:bg-black/5"
          >
            ✕
          </button>
        </div>

        {loading && <p className="text-muted text-sm">{t('common.loading')}</p>}

        {entry && (
          <div className="flex flex-col gap-4">
            <div>
              <h3 className="text-muted text-xs font-bold uppercase tracking-wide">{entry.label}</h3>
            </div>
            <div>
              <h4 className="text-navy text-sm font-semibold">What we used</h4>
              <dl className="border-line mt-1 divide-y rounded-xl border text-sm">
                {Object.entries(entry.inputs_used).map(([key, value]) => (
                  <div key={key} className="flex justify-between gap-3 px-3 py-2">
                    <dt className="text-muted">{humanizeKey(key)}</dt>
                    <dd className="text-navy max-w-[60%] text-right font-medium">{formatInputValue(key, value)}</dd>
                  </div>
                ))}
              </dl>
            </div>
            <div>
              <h4 className="text-navy text-sm font-semibold">How we worked it out</h4>
              <p className="text-muted mt-1 text-sm">{entry.rule_or_formula}</p>
            </div>
            {entry.config_version && (
              <div>
                <h4 className="text-navy text-sm font-semibold">Tax rules used</h4>
                <p className="text-muted mt-1 text-sm">Financial year {entry.config_version.replace(/^fy/i, '')}</p>
              </div>
            )}
            {entry.source_url && (
              <div>
                <h4 className="text-navy text-sm font-semibold">Read the official rules</h4>
                <a
                  href={entry.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-teal mt-1 inline-block break-all text-sm underline"
                >
                  {entry.source_url}
                </a>
              </div>
            )}
            <Button variant="outline" className="mt-2">
              {t('common.reportWrongNumber')}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
