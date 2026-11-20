/** The browser-held half of a stateless session: the values the person confirmed.
 * On serverless hosts the API remembers nothing, so these travel with each request. */

const confirmedKey = (sid: string) => `pp_confirmed_${sid}`
const trailsKey = (sid: string) => `pp_trails_${sid}`

export const isLocalSession = (sid: string) => sid.startsWith('local-')
export const isSampleSession = (sid: string) => sid.startsWith('sample-')

type Docs = Record<string, Record<string, unknown>>

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

function write(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* storage full or blocked: the person simply re-confirms next time */
  }
}

export const getConfirmedDocs = (sid: string): Docs => read<Docs>(confirmedKey(sid), {})

export function saveConfirmedDoc(sid: string, type: string, fields: Record<string, unknown>) {
  write(confirmedKey(sid), { ...getConfirmedDocs(sid), [type]: fields })
}

export const getTrails = (sid: string): Record<string, unknown> => read(trailsKey(sid), {})

export function saveTrails(sid: string, trails: Record<string, unknown>) {
  write(trailsKey(sid), { ...getTrails(sid), ...trails })
}

export function clearClientSession(sid: string) {
  try {
    localStorage.removeItem(confirmedKey(sid))
    localStorage.removeItem(trailsKey(sid))
  } catch {
    /* nothing to clear */
  }
}
