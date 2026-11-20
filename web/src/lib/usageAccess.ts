import { Capacitor, registerPlugin } from '@capacitor/core'

interface UsagePlugin {
  hasAccess(): Promise<{ granted: boolean }>
  openSettings(): Promise<void>
  getDaysUsed(opts: { packages: string[]; days: number }): Promise<{ days: Record<string, string[]> }>
  notify(opts: { title: string; body: string; id?: number }): Promise<{ shown: boolean; needsPermission?: boolean }>
}

const Native = registerPlugin<UsagePlugin>('UsageAccess')

/** True only inside the Android app, where Usage Access exists. */
export const isNativeAndroid = () => Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android'

const HISTORY_KEY = 'pp_usage_days_v1'
type History = Record<string, string[]> // app_key -> sorted YYYY-MM-DD days it was opened

function readHistory(): History {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) ?? '{}') as History
  } catch {
    return {}
  }
}
function writeHistory(h: History) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(h))
  } catch {
    /* storage can be unavailable; usage just will not be remembered */
  }
}

export const hasUsageAccess = async () => {
  try {
    return (await Native.hasAccess()).granted
  } catch {
    return false
  }
}
export const openUsageSettings = () => Native.openSettings()

const isoDay = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

export interface AppToMeasure {
  app_key: string
  name: string
  packages: string[]
}

/**
 * Reads the phone's recent usage (Android keeps about a week of daily detail), merges it into what
 * we saved on earlier visits, and returns days-opened over the window we have really observed (7 to 30).
 */
export async function measureUsage(apps: AppToMeasure[]): Promise<{ usage: { app_key: string; days_used: number }[]; window_days: number }> {
  const allPackages = apps.flatMap((a) => a.packages)
  const { days } = await Native.getDaysUsed({ packages: allPackages, days: 7 })
  const history = readHistory()
  const firstSeenKey = 'pp_usage_first_seen'
  let first = new Date()
  try {
    const saved = localStorage.getItem(firstSeenKey)
    if (saved) first = new Date(saved)
    else localStorage.setItem(firstSeenKey, first.toISOString())
  } catch {
    /* ignore */
  }
  const today = new Date()
  const cutoff = new Date(today)
  cutoff.setDate(cutoff.getDate() - 30)
  const cutoffKey = isoDay(cutoff)

  const usage = apps.map((app) => {
    const merged = new Set(history[app.app_key] ?? [])
    for (const pkg of app.packages) for (const d of days[pkg] ?? []) merged.add(d)
    const kept = [...merged].filter((d) => d > cutoffKey).sort()
    history[app.app_key] = kept
    return { app_key: app.app_key, days_used: kept.length }
  })
  writeHistory(history)
  // Android gives us 7 days straight away; each later visit extends what we can honestly say, up to 30.
  const observed = Math.min(30, Math.max(7, Math.floor((today.getTime() - first.getTime()) / 86_400_000) + 7))
  return { usage, window_days: observed }
}

/** Shows an Android notification at most once a day for each app. */
export async function notifyOncePerDay(appKey: string, title: string, body: string) {
  const key = `pp_notified_${appKey}`
  const today = isoDay(new Date())
  try {
    if (localStorage.getItem(key) === today) return
  } catch {
    /* ignore */
  }
  try {
    const r = await Native.notify({ title, body, id: Math.abs(hash(appKey)) })
    if (r.shown) localStorage.setItem(key, today)
  } catch {
    /* notifications are a bonus; never break the screen */
  }
}

function hash(s: string) {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0
  return h % 100000
}
