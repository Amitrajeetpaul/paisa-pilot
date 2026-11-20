import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BreakdownBar, type Segment } from '../components/BreakdownBar'
import { CheckupCard } from '../components/CheckupCard'
import { LeakBarChart } from '../components/LeakBarChart'
import { ResultRow } from '../components/ResultRow'
import { CardSkeleton } from '../components/Skeleton'
import { SourceDrawer } from '../components/SourceDrawer'
import { TrustStrip } from '../components/TrustStrip'
import type { IconName } from '../components/Icon'
import type { Tone } from '../components/tones'
import { ApiError, api, type LeakFixerCard, type LeakFixerResult } from '../lib/api'
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
  const { t, sessionId, setSessionId } = useApp()
  const navigate = useNavigate()
  const [result, setResult] = useState<LeakFixerResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const drawer = useSourceDrawer(sessionId)
  const [active, setActive] = useState<LeakFixerCard | null>(null)

  useEffect(() => {
    if (!sessionId) {
      navigate('/app/consent')
      return
    }
    api
      .calculateLeakFixer(sessionId)
      .then(setResult)
      .catch((e) => {
        if (e instanceof ApiError && e.code === 'unknown_session') setSessionId(null)
        setErrorMessage('Confirm a bank statement first to see your leaks.')
      })
      .finally(() => setLoading(false))
  }, [sessionId, navigate])

  // The leak total counts subscriptions and AutoPay only; loan EMIs are shown but not counted.
  const leakCards = (result?.cards ?? []).filter((c) => !c.card_id.startsWith('loan_'))
  const segments: Segment[] = leakCards.map((c) => ({ label: prettyMerchant(c.title), amount: c.amount, tone: look(c.card_id).tone }))

  return (
    <div className="mx-auto max-w-6xl py-5 sm:py-7">
      <p className="text-muted text-sm font-medium">Fix</p>
      <h1 className="text-ink text-2xl font-extrabold leading-tight tracking-tight">Stop the leaks</h1>

      <div className="mt-4 lg:grid lg:grid-cols-12 lg:items-start lg:gap-8">
        {/* Left Column: Leak Hero & Things to Fix */}
        <div className="lg:col-span-7 xl:col-span-7">
          <div className="bg-leak-hero animate-card-entrance rounded-[20px] p-5 text-white sm:p-6">
            <span className="text-xs font-semibold uppercase tracking-wider text-white/70">{t('fix.heroTitle')}</span>
            <div className="mt-1 flex items-end gap-2">
              <div className="tabular text-[44px] font-extrabold leading-none sm:text-5xl">
                {result ? formatINR(result.monthly_leak_total) : formatINR(0)}
              </div>
              <span className="pb-1.5 text-sm font-semibold text-white/70">{t('fix.monthLabel')}</span>
            </div>
            {result && result.annual_leak_total > 0 && (
              <p className="mt-2 inline-block rounded-md bg-white/15 px-2.5 py-1 text-xs font-semibold">
                That is {formatINR(result.annual_leak_total)} a year
              </p>
            )}

            {result && result.cards.length > 0 && (
              <div className="mt-5">
                <LeakBarChart data={result.monthly_breakdown} />
              </div>
            )}
            {segments.length > 1 && (
              <div className="mt-5">
                <BreakdownBar segments={segments} dark />
              </div>
            )}
          </div>

          <TrustStrip />

          <div className="mt-6 flex items-center justify-between">
            <h2 className="section-label">Things to fix</h2>
            {result && result.cards.length > 0 && (
              <span className="bg-coral-tint text-ink rounded-full px-2.5 py-0.5 text-xs font-bold">{result.cards.length}</span>
            )}
          </div>

          <div className="card mt-3 divide-y divide-[color:var(--color-line)] overflow-hidden">
            {loading && (
              <>
                <CardSkeleton />
                <CardSkeleton />
              </>
            )}
            {errorMessage && <p className="text-muted p-4 text-sm">{errorMessage}</p>}
            {!loading && result && result.cards.length === 0 && <p className="text-muted p-4 text-sm">{t('fix.empty')}</p>}
            {result?.cards.map((card) => {
              const l = look(card.card_id)
              return (
                <ResultRow
                  key={card.card_id}
                  icon={l.icon}
                  tone={l.tone}
                  title={prettyMerchant(card.title)}
                  subtitle={card.detail}
                  amount={card.amount}
                  unitLabel={card.unit_label}
                  badge={card.status_label ? (card.status_label === 'idle' ? t('fix.status.idle') : t('fix.status.active')) : null}
                  badgeTone={card.status_label === 'idle' ? 'warn' : 'ok'}
                  onOpen={() => {
                    setActive(card)
                    drawer.open(card.card_id)
                  }}
                />
              )
            })}
          </div>
        </div>

        {/* Right Column: AI Assistant Leaks Explanation (Sticky on Desktop) */}
        <div className="mt-6 flex flex-col gap-6 lg:sticky lg:top-20 lg:col-span-5 lg:mt-0 xl:col-span-5">
          {sessionId && result && result.cards.length > 0 && <CheckupCard sessionId={sessionId} kind="leaks" />}
        </div>
      </div>

      <SourceDrawer
        entry={drawer.entry}
        loading={drawer.loading}
        onClose={() => {
          drawer.close()
          setActive(null)
        }}
        headline={active ? { title: prettyMerchant(active.title), amount: active.amount, unit: active.unit_label } : null}
        primaryAction={active ? { label: active.action_label, onClick: () => navigate(`/app/drafts/${active.card_id}`, { state: { card: active } }) } : null}
      />
    </div>
  )
}
