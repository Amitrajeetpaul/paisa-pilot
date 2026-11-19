import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AgentActivity } from '../components/AgentActivity'
import { CountUp } from '../components/CountUp'
import { ResultCard } from '../components/ResultCard'
import { SampleDataTag } from '../components/Chip'
import { SourceDrawer } from '../components/SourceDrawer'
import { api, type MoneyFinderResult } from '../lib/api'
import { formatINR } from '../lib/format'
import { useSourceDrawer } from '../lib/useSourceDrawer'
import { useApp } from '../state/AppContext'

const ICONS: Record<string, string> = {
  tax_regime_switch: '🧾',
  extra_tds_refund: '💸',
  old_pf_accounts: '📘',
  refund_hunter: '🔁',
}

export function HomeScreen() {
  const { t, sessionId, sampleData } = useApp()
  const navigate = useNavigate()
  const [result, setResult] = useState<MoneyFinderResult | null>(null)
  const [loading, setLoading] = useState(true)
  const drawer = useSourceDrawer(sessionId)

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
  }, [sessionId, navigate])

  return (
    <div className="mx-auto max-w-2xl py-6">
      <p className="text-navy text-xl font-bold">{t('home.greetingPrefix')}, Riya</p>

      <div className="bg-hero-card animate-card-entrance mt-4 rounded-[28px] p-6 text-white">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-white/80">{t('home.heroTitle')}</span>
          {sampleData && <SampleDataTag />}
        </div>
        <div className="mt-2 text-5xl font-extrabold tracking-tight">
          {result ? <CountUp value={result.total_found} /> : formatINR(0)}
        </div>
        <div className="mt-5 flex gap-3">
          <div className="flex-1 rounded-2xl bg-white/10 p-3">
            <div className="text-lg font-bold">{result ? formatINR(result.yearly_total) : '—'}</div>
            <div className="text-xs text-white/70">{t('home.heroYearly')}</div>
          </div>
          <div className="flex-1 rounded-2xl bg-white/10 p-3">
            <div className="text-lg font-bold">{result ? formatINR(result.one_time_total) : '—'}</div>
            <div className="text-xs text-white/70">{t('home.heroOneTime')}</div>
          </div>
        </div>
      </div>

      <p className="text-muted mt-6 text-xs font-bold uppercase tracking-wide">
        {t('home.sectionLabel')} · {result?.cards.length ?? 0}
      </p>

      <div className="mt-3 flex flex-col gap-4">
        {loading && <p className="text-muted text-sm">{t('common.loading')}</p>}
        {!loading && result && result.cards.length === 0 && <p className="text-muted text-sm">{t('home.empty')}</p>}
        {result?.cards.map((card) => (
          <ResultCard
            key={card.card_id}
            icon={ICONS[card.card_id] ?? '💰'}
            title={card.title}
            detail={card.detail}
            amount={card.amount}
            unitLabel={card.unit_label}
            sourceLabel={card.source_chip}
            actionLabel={card.action_label}
            onAction={() => navigate(`/app/drafts/${card.card_id}`, { state: { card } })}
            onTapAmount={() => drawer.open(card.card_id)}
          />
        ))}
      </div>

      {sessionId && <AgentActivity sessionId={sessionId} agent="money_finder" />}
      {sessionId && <AgentActivity sessionId={sessionId} agent="ca_assistant" />}

      <p className="text-muted mt-6 text-center text-xs">{t('home.feeNote')}</p>

      <SourceDrawer entry={drawer.entry} loading={drawer.loading} onClose={drawer.close} />
    </div>
  )
}
