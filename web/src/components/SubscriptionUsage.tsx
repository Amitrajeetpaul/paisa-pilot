import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, api, type SubscriptionUsageResult, type UsageApps } from '../lib/api'
import { formatINR } from '../lib/format'
import { hasUsageAccess, isNativeAndroid, measureUsage, notifyOncePerDay, openUsageSettings } from '../lib/usageAccess'

const LEVEL_STYLE: Record<string, string> = {
  unused: 'bg-red-500/15 text-red-500',
  rare: 'bg-amber-500/15 text-amber-600',
  light: 'bg-slate-500/15 text-muted',
  regular: 'bg-emerald-500/15 text-emerald-600',
}
const LEVEL_LABEL: Record<string, string> = { unused: 'Not used', rare: 'Hardly used', light: 'Light use', regular: 'Well used' }

/** "Are you using what you pay for?" Real phone usage (Android) or an uploaded history file. */
export function SubscriptionUsage({ sessionId }: { sessionId: string }) {
  const native = isNativeAndroid()
  const [apps, setApps] = useState<UsageApps | null>(null)
  const [granted, setGranted] = useState(false)
  const [result, setResult] = useState<SubscriptionUsageResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState<string | null>(null)
  const [pickedApp, setPickedApp] = useState('netflix')
  // Days from an account history file (covers TV and laptop); merged with phone usage by taking the higher count.
  const fileDays = useRef<Record<string, number>>({})

  const analyse = useCallback(
    async (usage: { app_key: string; days_used: number }[], windowDays: number) => {
      setBusy(true)
      setNote(null)
      try {
        const r = await api.calculateSubscriptionUsage(sessionId, usage, windowDays)
        setResult(r)
        if (r.alerts.length === 0) setNote('None of the apps we measured match a subscription on your bank statement.')
        if (native) {
          for (const a of r.alerts.filter((x) => x.monthly_saving > 0)) {
            void notifyOncePerDay(a.app_key, `${a.app_name}: you hardly use it`, a.message)
          }
        }
      } catch (e) {
        setNote(e instanceof ApiError ? e.message : 'Could not check usage right now. Please try again.')
      } finally {
        setBusy(false)
      }
    },
    [sessionId, native],
  )

  const measure = useCallback(
    async (list: UsageApps) => {
      setBusy(true)
      try {
        const m = await measureUsage(list.apps)
        const merged = m.usage.map((u) => ({ ...u, days_used: Math.max(u.days_used, fileDays.current[u.app_key] ?? 0) }))
        await analyse(merged, m.window_days)
      } catch {
        setNote('Could not read app usage from your phone. Please try again.')
        setBusy(false)
      }
    },
    [analyse],
  )

  useEffect(() => {
    api.getUsageApps().then(setApps).catch(() => setNote('Could not load the app list.'))
  }, [])

  useEffect(() => {
    if (!native || !apps) return
    const check = async () => {
      const ok = await hasUsageAccess()
      setGranted(ok)
      if (ok) void measure(apps)
    }
    void check()
    // The user comes back from Android settings: check again.
    const onVisible = () => document.visibilityState === 'visible' && void check()
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [native, apps, measure])

  const onFile = async (file: File | undefined) => {
    if (!file) return
    setBusy(true)
    setNote(null)
    try {
      const text = await file.text()
      const h = await api.historyDays(pickedApp, text)
      fileDays.current[h.app_key] = h.days_used
      if (native && apps && granted) await measure(apps)
      else await analyse(Object.entries(fileDays.current).map(([app_key, days_used]) => ({ app_key, days_used })), h.window_days)
    } catch (e) {
      setNote(e instanceof ApiError ? e.message : 'We could not read that file.')
      setBusy(false)
    }
  }

  return (
    <section className="mt-8" aria-labelledby="usage-h">
      <h2 id="usage-h" className="section-label">Are you using what you pay for?</h2>
      <div className="card mt-3 p-4">
        {native && !granted && (
          <>
            <p className="text-ink text-sm font-semibold">Connect your app usage</p>
            <p className="text-muted mt-1 text-sm">
              Allow Paisa Pilot to see how many days you open Netflix, Prime, Spotify and other apps you pay for. This is read only, stays on your phone, and you can switch it off any time in Settings.
            </p>
            <button type="button" className="bg-coral text-ink press mt-3 min-h-11 rounded-xl px-4 text-sm font-bold" onClick={() => void openUsageSettings()}>
              Allow usage access
            </button>
          </>
        )}

        {(!native || granted) && (
          <>
            {!native && !result && (
              <>
                <p className="text-ink text-sm font-semibold">See which subscriptions you hardly use</p>
                <p className="text-muted mt-1 text-sm">
                  In the Paisa Pilot Android app we read how often you open each app, once you allow it. On the web, upload the viewing history file you can download from your account.
                </p>
              </>
            )}
            {native && (
              <p className="text-muted text-sm">
                Watch on a TV or laptop too? Add your account history so we count those days as well. Netflix: Account, Security & Privacy, Download your personal information.
              </p>
            )}
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <select value={pickedApp} onChange={(e) => setPickedApp(e.target.value)} className="border-line bg-white min-h-11 rounded-xl border px-3 text-sm" aria-label="Which app">
                {(apps?.apps ?? [{ app_key: 'netflix', name: 'Netflix', packages: [] }]).map((a) => (
                  <option key={a.app_key} value={a.app_key}>{a.name}</option>
                ))}
              </select>
              <label className="bg-coral text-ink press inline-flex min-h-11 cursor-pointer items-center rounded-xl px-4 text-sm font-bold">
                Add history file
                <input type="file" accept=".csv,text/csv" className="sr-only" onChange={(e) => void onFile(e.target.files?.[0])} />
              </label>
              {!native && (
                <button type="button" className="text-ink min-h-11 rounded-xl px-3 text-sm font-semibold underline" onClick={() => void analyse([{ app_key: 'cloudnotes', days_used: 1 }], 30)}>
                  Try sample usage
                </button>
              )}
            </div>
          </>
        )}

        {busy && <p className="text-muted mt-3 text-sm">Checking your usage…</p>}
        {note && <p className="text-muted mt-3 text-sm">{note}</p>}

        {result && result.alerts.length > 0 && (
          <div>
            {result.monthly_saving > 0 && (
              <p className="bg-coral-tint text-ink mb-3 rounded-xl px-3 py-2 text-sm font-bold">
                You could save {formatINR(result.monthly_saving)} a month ({formatINR(result.annual_saving)} a year)
              </p>
            )}
            <ul className="divide-y divide-[color:var(--color-line)]">
              {result.alerts.map((a) => (
                <li key={a.app_key} className="py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-ink text-[15px] font-semibold">{a.app_name}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${LEVEL_STYLE[a.level]}`}>{LEVEL_LABEL[a.level]}</span>
                    <span className="text-muted ml-auto text-sm">{formatINR(a.monthly_amount)}/month</span>
                  </div>
                  <p className="text-muted mt-1 text-sm">{a.message}</p>
                </li>
              ))}
            </ul>
            <p className="text-muted mt-2 text-xs">{result.source}. The saving is our estimate. You decide whether to cancel.</p>
          </div>
        )}
      </div>
    </section>
  )
}
