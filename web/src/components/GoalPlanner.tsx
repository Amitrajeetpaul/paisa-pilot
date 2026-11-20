import { useState } from 'react'
import { ApiError, api, type GoalPlan } from '../lib/api'
import { formatINR } from '../lib/format'
import { useApp } from '../state/AppContext'

const GOALS = [
  ['education', 'Education'],
  ['home', 'Home'],
  ['wedding', 'Wedding'],
  ['car', 'Car'],
  ['travel', 'Travel'],
  ['medical', 'Medical'],
  ['retirement', 'Retirement'],
  ['other', 'Something else'],
] as const

/** Goal planning a planner would accept: inflation in, conservative capped returns, category only. */
export function GoalPlanner({ sessionId }: { sessionId: string }) {
  const { t } = useApp()
  const [goal, setGoal] = useState('education')
  const [cost, setCost] = useState('500000')
  const [years, setYears] = useState('5')
  const [saved, setSaved] = useState('0')
  const [plan, setPlan] = useState<GoalPlan | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setErr(null)
    try {
      setPlan(await api.planGoal(sessionId, { cost_today: Number(cost), years: Number(years), goal_type: goal, already_saved: Number(saved) || 0 }))
    } catch (e2) {
      setPlan(null)
      setErr(e2 instanceof ApiError ? e2.message : 'Could not plan that just now. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const field = 'border-line bg-white text-ink mt-1 min-h-11 w-full rounded-xl border px-3 text-base'
  return (
    <section className="card p-4" aria-labelledby="goal-h">
      <h2 id="goal-h" className="section-label">{t('ui.goal.title')}</h2>
      <p className="text-muted mt-1 text-sm">{t('ui.goal.sub')}</p>
      <form onSubmit={submit} className="mt-3 grid grid-cols-2 gap-3">
        <label className="col-span-2 text-sm font-semibold sm:col-span-1">
          {t('ui.goal.type')}
          <select value={goal} onChange={(e) => setGoal(e.target.value)} className={field}>
            {GOALS.map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </label>
        <label className="col-span-2 text-sm font-semibold sm:col-span-1">
          {t('ui.goal.cost')}
          <input inputMode="numeric" value={cost} onChange={(e) => setCost(e.target.value.replace(/[^\d]/g, ''))} className={field} required />
        </label>
        <label className="text-sm font-semibold">
          {t('ui.goal.years')}
          <input inputMode="decimal" value={years} onChange={(e) => setYears(e.target.value.replace(/[^\d.]/g, ''))} className={field} required />
        </label>
        <label className="text-sm font-semibold">
          {t('ui.goal.saved')}
          <input inputMode="numeric" value={saved} onChange={(e) => setSaved(e.target.value.replace(/[^\d]/g, ''))} className={field} />
        </label>
        <button type="submit" disabled={busy || !Number(cost) || !Number(years)} className="bg-coral-button press col-span-2 min-h-11 rounded-xl text-sm font-bold disabled:opacity-50">
          {busy ? '…' : t('ui.goal.plan')}
        </button>
      </form>
      {err && <p className="mt-3 text-sm text-red-600" role="alert">{err}</p>}
      {plan && (
        <div className="mt-4 space-y-2" aria-live="polite">
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-slate-500/10 rounded-2xl p-3">
              <p className="text-muted text-xs">{t('ui.goal.futureCost')}</p>
              <p className="tabular text-ink text-lg font-extrabold">{formatINR(plan.future_cost)}</p>
            </div>
            <div className="bg-coral-tint rounded-2xl p-3">
              <p className="text-muted text-xs">{t('ui.goal.monthly')}</p>
              <p className="tabular text-ink text-lg font-extrabold">{formatINR(plan.monthly_needed)}</p>
            </div>
          </div>
          <p className="text-sm"><span className="text-muted">{t('ui.goal.where')}: </span><span className="text-ink font-semibold">{plan.category}</span></p>
          {plan.affordable !== undefined && (
            <p className={`rounded-xl px-3 py-2 text-sm ${plan.affordable ? 'bg-emerald-500/10 text-ink' : 'bg-amber-500/10 text-ink'}`}>
              {plan.affordable ? t('ui.goal.fits') : t('ui.goal.tight')}
            </p>
          )}
          <p className="text-muted text-xs">{plan.note}</p>
        </div>
      )}
    </section>
  )
}
