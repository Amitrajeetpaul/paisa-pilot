import { api, rememberSavingOn, type MeResult } from './api'
import { isSampleSession } from './clientSession'

const DOC_TYPES = ['payslip', 'form16', 'bank_statement', 'pf_passbook', 'ais'] as const

interface SessionSetters {
  setSessionId: (id: string | null) => void
  setSampleData: (v: boolean) => void
  setDisplayName: (n: string) => void
}

/**
 * Bring a returning person's saved documents back: start a fresh session and confirm each saved
 * document into it, so every screen works exactly as it does for a first visit. Returns how many came back.
 */
export async function restoreFromAccount(me: MeResult, s: SessionSetters): Promise<number> {
  rememberSavingOn(me.saving_on)
  const entries = Object.entries(me.documents)
  if (entries.length === 0) return 0
  const { session_id } = await api.giveConsent(true)
  let restored = 0
  for (const [type, fields] of entries) {
    try {
      await api.confirmDocument(session_id, type, fields, { sync: false })
      restored++
    } catch {
      /* one bad document should not block the rest; the person can re-confirm it */
    }
  }
  if (restored === 0) return 0
  s.setSessionId(session_id)
  s.setSampleData(false)
  const payslip = me.documents.payslip as Record<string, unknown> | undefined
  const name = String(payslip?.employee_name ?? '').trim().split(/\s+/)[0]
  if (name) s.setDisplayName(name)
  return restored
}

/** When a person switches saving on, copy what they have already confirmed in this session into their account. */
export async function pushCurrentDocs(sessionId: string): Promise<number> {
  // The built-in sample profile is demo data, never someone's own: it must not end up in their account.
  if (isSampleSession(sessionId)) return 0
  let n = 0
  for (const type of DOC_TYPES) {
    try {
      const fields = await api.getConfirmed(sessionId, type)
      await api.meSaveDocument(type, fields)
      n++
    } catch {
      /* not confirmed in this session */
    }
  }
  return n
}
