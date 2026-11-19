import { BASE } from './api'

/** Anonymous product analytics: a random id kept in this browser, event names
 * only (never documents, numbers or names). Respects Do Not Track. */
const ID_KEY = 'paisa_pilot_anon_id'

function anonId(): string {
  try {
    let id = localStorage.getItem(ID_KEY)
    if (!id) {
      id = crypto.randomUUID()
      localStorage.setItem(ID_KEY, id)
    }
    return id
  } catch {
    return 'anonymous-session'
  }
}

export function track(event: string, detail?: string): void {
  if (navigator.doNotTrack === '1') return
  try {
    void fetch(`${BASE}/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event, anon_id: anonId(), detail: detail ?? null }),
      keepalive: true,
    }).catch(() => undefined)
  } catch {
    /* analytics must never break the app */
  }
}
