import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BreakdownBar, type Segment } from '../components/BreakdownBar'
import { CheckupCard } from '../components/CheckupCard'
import { CountUp } from '../components/CountUp'
import { DocumentsCard } from '../components/DocumentsCard'
import type { IconName } from '../components/Icon'
import { QuickActions } from '../components/QuickActions'
import { ResultRow } from '../components/ResultRow'
import { SampleDataTag } from '../components/Chip'
import { CardSkeleton } from '../components/Skeleton'
import { SourceDrawer } from '../components/SourceDrawer'
import { TrustStrip } from '../components/TrustStrip'
import type { Tone } from '../components/tones'
import { api, type MoneyFinderCard, type MoneyFinderResult } from '../lib/api'
import { formatINR } from '../lib/format'
import { greetingForNow } from '../lib/plain'
import { useSourceDrawer } from '../lib/useSourceDrawer'
import { useApp } from '../state/AppContext'

const LOOK: Record<string, { icon: IconName; tone: Tone; label: string }> = {
  tax_regime_switch: { icon: 'receipt', tone: 'indigo', label: 'Tax option' },
  extra_tds_refund: { icon: 'percent', tone: 'teal', label: 'Extra TDS' },
  ais_extra_tds: { icon: 'percent', tone: 'cyan', label: 'Tax credit' },
  old_pf_accounts: { icon: 'book', tone: 'amber', label: 'Old PF' },
  refund_hunter: { icon: 'repeat', tone: 'coral', label: 'Refunds' },
}

export function HomeScreen() {
  const { t, sessionId, sampleData, displayName, setDisplayName } = useApp()
  const navigate = useNavigate()
  const [result, setResult] = useState<MoneyFinderResult | null>(null)
  const [loading, setLoading] = useState(true)
  const drawer = useSourceDrawer(sessionId)
  const [active, setActive] = useState<MoneyFinderCard | null>(null)

  useEffect(() => {
    if (!sessionId) {
      navigate('/app/consent')
      return
    }
    api
      .calculateMoneyFinder(sessionId)
      .then(setResult)
      .catch(() => setResult(null))
      .finally(() => setLoading(false))

    // Greet the person by the name on their own documents.
    const firstNameFrom = (doc: Record<string, unknown>) =>
      String(doc.employee_name ?? doc.taxpayer_name ?? doc.account_holder_name ?? doc.member_name ?? '')
        .trim()
        .split(/\s+/)[0]
    ;(async () => {
      for (const type of ['payslip', 'form16', 'ais', 'bank_statement', 'pf_passbook']) {
        try {
          const name = firstNameFrom(await api.getConfirmed(sessionId, type))
          if (name) return setDisplayName(name)
        } catch {
          /* that document has not been confirmed yet */
        }
      }
    })()
  }, [sessionId, navigate, setDisplayName])

  const segments: Segment[] = (result?.cards ?? [])
    .filter((c) => LOOK[c.card_id])
    .map((c) => ({ label: LOOK[c.card_id].label, amount: c.amount, tone: LOOK[c.card_id].tone }))

  return (
    <div className="mx-auto max-w-2xl py-5 sm:py-7">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-muted text-sm font-medium">{t(`home.greeting.${greetingForNow()}`)}</p>
          <p className="text-navy text-2xl font-extrabold leading-tight tracking-tight">{displayName || 'Welcome'}</p>
        </div>
        {sampleData && <SampleDataTag />}
      </div>

      <div className="bg-hero-card animate-card-entrance mt-4 rounded-[20px] p-5 text-white sm:p-6">
        <span className="text-xs font-semibold uppercase tracking-wider text-white/70">{t('home.heroTitle')}</span>
        <div className="tabular mt-1 text-[44px] font-extrabold leading-none sm:text-5xl">
          {result ? <CountUp value={result.total_found} /> : formatINR(0)}
        </div>
        <div className="mt-4 flex gap-2.5">
          <div className="flex-1 rounded-xl bg-white/10 px-3 py-2.5">
            <div className="tabular text-base font-bold">{result ? formatINR(result.yearly_total) : '—'}</div>
            <div className="text-[11px] text-white/70">{t('home.heroYearly')}</div>
          </div>
          <div className="flex-1 rounded-xl bg-white/10 px-3 py-2.5">
            <div className="tabular text-base font-bold">{result ? formatINR(result.one_time_total) : '—'}</div>
            <div className="text-[11px] text-white/70">{t('home.heroOneTime')}</div>
          </div>
        </div>
        {segments.length > 0 && (
          <div className="mt-5">
            <BreakdownBar segments={segments} dark />
          </div>
        )}
      </div>

      <QuickActions />
      <TrustStrip />

      {sessionId && <DocumentsCard sessionId={sessionId} />}

      <div className="mt-6 flex items-center justify-between">
        <h2 className="section-label">Found for you</h2>
        {result && result.cards.length > 0 && (
          <span className="bg-coral-tint text-navy rounded-full px-2.5 py-0.5 text-xs font-bold">{result.cards.length}</span>
        )}
      </div>

      <div className="card mt-3 divide-y divide-[color:var(--color-line)] overflow-hidden">
        {loading && (
          <>
            <CardSkeleton />
            <CardSkeleton />
          </>
        )}
        {!loading && result && result.cards.length === 0 && <p className="text-muted p-4 text-sm">{t('home.empty')}</p>}
        {result?.cards.map((card) => (
          <ResultRow
            key={card.card_id}
            icon={LOOK[card.card_id]?.icon ?? 'wallet'}
            tone={LOOK[card.card_id]?.tone ?? 'slate'}
            title={card.title}
            subtitle={card.source_chip}
            amount={card.amount}
            unitLabel={card.unit_label}
            onOpen={() => {
              setActive(card)
              drawer.open(card.card_id)
            }}
          />
        ))}
      </div>

      <div id="tax-checkup" className="scroll-mt-24">
        {sessionId && !loading && result && result.cards.length > 0 && <CheckupCard sessionId={sessionId} kind="tax" />}
      </div>

      <p className="text-muted mt-6 text-center text-xs">{t('home.feeNote')}</p>

      <SourceDrawer
        entry={drawer.entry}
        loading={drawer.loading}
        onClose={() => {
          drawer.close()
          setActive(null)
        }}
        headline={active ? { title: active.title, amount: active.amount, unit: active.unit_label } : null}
        primaryAction={active ? { label: active.action_label, onClick: () => navigate(`/app/drafts/${active.card_id}`, { state: { card: active } }) } : null}
      />
    </div>
  )
}
