import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BreakdownBar, type Segment } from '../components/BreakdownBar'
import { CheckupCard } from '../components/CheckupCard'
import { LeakBarChart } from '../components/LeakBarChart'
import { ResultCard } from '../components/ResultCard'
import { CardSkeleton } from '../components/Skeleton'
import { SourceDrawer } from '../components/SourceDrawer'
import { TrustStrip } from '../components/TrustStrip'
import type { IconName } from '../components/Icon'
import type { Tone } from '../components/tones'
import { api, type LeakFixerResult } from '../lib/api'
import { formatINR } from '../lib/format'
import { prettyMerchant } from '../lib/plain'
import { useSourceDrawer } from '../lib/useSourceDrawer'
import { useApp } from '../state/AppContext'

function look(cardId: string): { icon: IconName; tone: Tone; label: string } {
  if (cardId.startsWith('subscription_')) return { icon: 'repeat', tone: 'violet', label: 'Subscriptions' }
  if (cardId.startsWith('autopay_')) return { icon: 'wallet', tone: 'amber', label: 'AutoPay' }
  return { icon: 'bank', tone: 'slate', label: 'Loan EMI' }
}

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

  // The leak total counts subscriptions and AutoPay only; loan EMIs are shown but not counted.
  const leakCards = (result?.cards ?? []).filter((c) => !c.card_id.startsWith('loan_'))
  const segments: Segment[] = leakCards.map((c) => ({ label: prettyMerchant(c.title), amount: c.amount, tone: look(c.card_id).tone }))

  return (
    <div className="mx-auto max-w-2xl py-5 sm:py-7">
      <p className="text-muted text-sm font-medium">Fix</p>
      <h1 className="text-navy text-2xl font-extrabold leading-tight tracking-tight">Stop the leaks</h1>

      <div className="bg-leak-hero hero-shine animate-card-entrance text-navy mt-4 rounded-[28px] p-5 shadow-[0_20px_40px_-22px_rgba(255,90,95,0.8)] sm:p-6">
        <span className="text-sm font-bold opacity-80">{t('fix.heroTitle')}</span>
        <div className="mt-1 flex items-end gap-2">
          <div className="tabular text-[44px] font-extrabold leading-none sm:text-5xl">
            {result ? formatINR(result.monthly_leak_total) : formatINR(0)}
          </div>
          <span className="pb-1.5 text-sm font-bold opacity-80">{t('fix.monthLabel')}</span>
        </div>
        {result && result.annual_leak_total > 0 && (
          <p className="mt-2 inline-block rounded-full bg-white/35 px-3 py-1 text-xs font-bold">
            That is {formatINR(result.annual_leak_total)} a year
          </p>
        )}

        {result && result.cards.length > 0 && (
          <div className="mt-5">
            <LeakBarChart data={result.monthly_breakdown} />
          </div>
        )}
        {segments.length > 1 && (
          <div className="mt-5 rounded-2xl bg-white/30 p-3">
            <BreakdownBar segments={segments} />
          </div>
        )}
      </div>

      <TrustStrip />

      <div className="mt-6 flex items-center justify-between">
        <h2 className="text-navy text-lg font-extrabold tracking-tight">Things to fix</h2>
        {result && result.cards.length > 0 && (
          <span className="bg-coral-tint text-navy rounded-full px-2.5 py-0.5 text-xs font-bold">{result.cards.length}</span>
        )}
      </div>

      <div className="mt-3 flex flex-col gap-3">
        {loading && (
          <>
            <CardSkeleton />
            <CardSkeleton />
          </>
        )}
        {errorMessage && <p className="text-muted text-sm">{errorMessage}</p>}
        {!loading && result && result.cards.length === 0 && <p className="text-muted text-sm">{t('fix.empty')}</p>}
        {result?.cards.map((card, i) => {
          const l = look(card.card_id)
          return (
            <ResultCard
              key={card.card_id}
              index={i}
              icon={l.icon}
              tone={l.tone}
              title={prettyMerchant(card.title)}
              detail={card.detail}
              amount={card.amount}
              unitLabel={card.unit_label}
              sourceLabel={card.source_chip}
              actionLabel={card.action_label}
              statusLabel={card.status_label ? (card.status_label === 'idle' ? t('fix.status.idle') : t('fix.status.active')) : null}
              statusTone={card.status_label === 'idle' ? 'warn' : 'ok'}
              onAction={() => navigate(`/app/drafts/${card.card_id}`, { state: { card } })}
              onTapAmount={() => drawer.open(card.card_id)}
            />
          )
        })}
      </div>

      {sessionId && result && result.cards.length > 0 && <CheckupCard sessionId={sessionId} kind="leaks" />}

      <SourceDrawer entry={drawer.entry} loading={drawer.loading} onClose={drawer.close} />
    </div>
  )
}
