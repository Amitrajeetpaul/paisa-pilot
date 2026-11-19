import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckupCard } from '../components/CheckupCard'
import { Button } from '../components/Button'
import { SourceChip } from '../components/Chip'
import { LeakBarChart } from '../components/LeakBarChart'
import { SourceDrawer } from '../components/SourceDrawer'
import { api, type LeakFixerResult } from '../lib/api'
import { formatINR } from '../lib/format'
import { prettyMerchant } from '../lib/plain'
import { useSourceDrawer } from '../lib/useSourceDrawer'
import { useApp } from '../state/AppContext'

export function FixScreen() {
  const { t, sessionId } = useApp()
  const navigate = useNavigate()
  const [result, setResult] = useState<LeakFixerResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const drawer = useSourceDrawer(sessionId)

  useEffect(() => {
    if (!sessionId) {
      navigate('/app/consent')
      return
    }
    api
      .calculateLeakFixer(sessionId)
      .then(setResult)
      .catch(() => setErrorMessage('Confirm a bank statement first to see your leaks.'))
      .finally(() => setLoading(false))
  }, [sessionId, navigate])

  return (
    <div className="mx-auto max-w-2xl py-6">
      <div className="bg-leak-hero animate-card-entrance rounded-[28px] p-6 text-navy">
        <span className="text-sm font-semibold">{t('fix.heroTitle')}</span>
        <div className="mt-2 text-5xl font-extrabold tracking-tight">
          {result ? formatINR(result.monthly_leak_total) : formatINR(0)}
        </div>
        <span className="text-sm font-semibold">{t('fix.monthLabel')}</span>

        {result && result.cards.length > 0 && (
          <div className="mt-5">
            <LeakBarChart data={result.monthly_breakdown} />
          </div>
        )}
      </div>

      <p className="text-muted mt-6 text-xs font-bold uppercase tracking-wide">
        {t('fix.sectionLabel')} · {result?.cards.length ?? 0}
      </p>

      <div className="mt-3 flex flex-col gap-4">
        {loading && <p className="text-muted text-sm">{t('common.loading')}</p>}
        {errorMessage && <p className="text-muted text-sm">{errorMessage}</p>}
        {!loading && result && result.cards.length === 0 && <p className="text-muted text-sm">{t('fix.empty')}</p>}
        {result?.cards.map((card) => (
          <div key={card.card_id} className="border-line animate-card-entrance rounded-[20px] border bg-white p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-navy text-base font-bold">{prettyMerchant(card.title)}</h3>
                <p className="text-muted mt-0.5 text-sm">{card.detail}</p>
              </div>
              {card.status_label && (
                <span
                  className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${
                    card.status_label === 'idle' ? 'bg-yellow text-navy' : 'bg-teal-tint text-navy'
                  }`}
                >
                  {card.status_label === 'idle' ? t('fix.status.idle') : t('fix.status.active')}
                </span>
              )}
            </div>

            <button
              type="button"
              onClick={() => drawer.open(card.card_id)}
              className="mt-2 flex items-baseline gap-2 rounded-lg text-left"
            >
              <span className="text-navy text-2xl font-extrabold">{formatINR(card.amount)}</span>
              <span className="text-muted text-sm font-medium">{card.unit_label}</span>
            </button>

            <div className="mt-3 flex items-center justify-between gap-3">
              <SourceChip label={card.source_chip} onClick={() => drawer.open(card.card_id)} />
              <Button
                variant="primary"
                onClick={() => navigate(`/app/drafts/${card.card_id}`, { state: { card } })}
                className="min-h-11"
              >
                {card.action_label}
              </Button>
            </div>
          </div>
        ))}
      </div>

      {sessionId && result && result.cards.length > 0 && <CheckupCard sessionId={sessionId} kind="leaks" />}

      <SourceDrawer entry={drawer.entry} loading={drawer.loading} onClose={drawer.close} />
    </div>
  )
}
