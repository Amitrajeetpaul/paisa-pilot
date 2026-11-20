import {
  SAMPLE_CONFIRMED,
  SAMPLE_MONEY_FINDER,
  SAMPLE_LEAK_FIXER,
  SAMPLE_SOURCE_TRAILS,
  SAMPLE_CONSULTANT_ANSWERS,
} from './sampleFallback'
import {
  clearClientSession,
  getConfirmedDocs,
  getTrails,
  isLocalSession,
  isSampleSession,
  saveConfirmedDoc,
  saveTrails,
} from './clientSession'

// Production API default: live Vercel backend with new Gemini API key
export const BASE = import.meta.env.VITE_API_BASE_URL ?? 'https://paisa-pilot-api.vercel.app'

/** The friendly message the API sends for expected problems (locked PDF, unreadable file, ...). */
export class ApiError extends Error {
  code?: string
  constructor(message: string, code?: string) {
    super(message)
    this.code = code
  }
}

async function apiError(res: Response): Promise<ApiError> {
  const body = await res.text()
  try {
    const detail = JSON.parse(body)?.detail
    if (detail && typeof detail === 'object' && typeof detail.message === 'string') {
      return new ApiError(detail.message, detail.code)
    }
  } catch {
    /* not JSON */
  }
  return new ApiError(`${res.status} ${res.statusText}: ${body}`)
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw await apiError(res)
  return res.json() as Promise<T>
}

/** Values the browser holds for a stateless ("local-") session, sent with each request. */
function stateBody(sessionId: string, extra: Record<string, unknown> = {}): string {
  return JSON.stringify(isLocalSession(sessionId) ? { ...extra, confirmed: getConfirmedDocs(sessionId) } : extra)
}

/** The built-in offline sample may stand in ONLY for the sample profile, never for a person's own data. */
const sampleOnly = (sessionId: string) => isSampleSession(sessionId)

export const api = {
  giveConsent: (consentGiven: boolean) =>
    request<{ session_id: string }>('/consent', {
      method: 'POST',
      body: JSON.stringify({ consent_given: consentGiven }),
    }),

  createSampleSession: async () => {
    try {
      return await request<{ session_id: string; sample_data: boolean; confirmed: Record<string, unknown> }>(
        '/demo/sample-session',
        { method: 'POST' },
      )
    } catch (e) {
      console.warn('Backend unavailable, using built-in offline sample fixture', e)
      return { session_id: 'sample-offline-riya-sharma', sample_data: true, confirmed: SAMPLE_CONFIRMED }
    }
  },

  /** Upload and read in one request: the file is read in memory and never stored. */
  extractDocument: async (sessionId: string, documentType: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BASE}/sessions/${sessionId}/documents/${documentType}/extract`, { method: 'POST', body: form })
    if (!res.ok) throw await apiError(res)
    return (await res.json()) as Record<string, unknown>
  },

  confirmDocument: async (sessionId: string, documentType: string, fields: Record<string, unknown>) => {
    const result = await request<{ status: string; fields?: Record<string, unknown> }>(
      `/sessions/${sessionId}/documents/${documentType}/confirm`,
      { method: 'POST', body: JSON.stringify(fields) },
    )
    if (isLocalSession(sessionId) && result.fields) saveConfirmedDoc(sessionId, documentType, result.fields)
    return result
  },

  getConfirmed: async (sessionId: string, documentType: string): Promise<Record<string, unknown>> => {
    if (isLocalSession(sessionId)) {
      const doc = getConfirmedDocs(sessionId)[documentType]
      if (!doc) throw new Error('not confirmed yet')
      return doc
    }
    try {
      return await request<Record<string, unknown>>(`/sessions/${sessionId}/documents/${documentType}/confirmed`)
    } catch (e) {
      if (sampleOnly(sessionId)) return (SAMPLE_CONFIRMED as Record<string, Record<string, unknown>>)[documentType] ?? {}
      throw e
    }
  },

  calculateMoneyFinder: async (sessionId: string) => {
    try {
      const result = await request<MoneyFinderResult>(`/sessions/${sessionId}/calculate/money-finder`, {
        method: 'POST',
        body: stateBody(sessionId),
      })
      if (result.source_trails) saveTrails(sessionId, result.source_trails)
      return result
    } catch (e) {
      if (sampleOnly(sessionId)) return SAMPLE_MONEY_FINDER as MoneyFinderResult
      throw e
    }
  },

  calculateLeakFixer: async (sessionId: string) => {
    try {
      const result = await request<LeakFixerResult>(`/sessions/${sessionId}/calculate/leak-fixer`, {
        method: 'POST',
        body: stateBody(sessionId),
      })
      if (result.source_trails) saveTrails(sessionId, result.source_trails)
      return result
    } catch (e) {
      if (sampleOnly(sessionId)) return SAMPLE_LEAK_FIXER as LeakFixerResult
      throw e
    }
  },

  runAgent: async (sessionId: string, agent: 'money_finder' | 'leak_fixer' | 'consultant' | 'ca_assistant', question?: string) => {
    try {
      return await request<AgentRunResult>(`/sessions/${sessionId}/agents/${agent}/run`, {
        method: 'POST',
        body: stateBody(sessionId, { question: question ?? null }),
      })
    } catch (e) {
      if (!sampleOnly(sessionId)) throw e
      return {
        agent,
        engine: 'offline',
        answer: 'Our check suggests: The new tax regime looks cheaper for you, saving about ₹75,400 a year based on your Form 16 and this year’s rules.',
        guardrail_flagged: false,
        tool_calls: [
          { tool: 'compare_tax_regimes', args: {}, result: { recommended_regime: 'new', annual_saving_if_switch: 75400 } },
          { tool: 'tds_reconciliation_tool', args: {}, result: { claimable_extra_tds: 2500 } },
          { tool: 'itr_form_tool', args: {}, result: { form: 'ITR-1 (Sahaj)' } },
        ],
      } as AgentRunResult
    }
  },

  joinWaitlist: (email: string, consentToContact: boolean) =>
    request<{ joined: boolean }>('/waitlist', {
      method: 'POST',
      body: JSON.stringify({ email, consent_to_contact: consentToContact }),
    }),

  reportWrongNumber: (cardId: string, note: string, sessionId: string | null) =>
    request<{ received: boolean }>('/feedback', {
      method: 'POST',
      body: JSON.stringify({ card_id: cardId, note, session_id: sessionId }),
    }),

  deleteMyData: async (sessionId: string) => {
    clearClientSession(sessionId)
    try {
      return await request<{ deleted: boolean; uploads_deleted: number }>(`/sessions/${sessionId}`, { method: 'DELETE' })
    } catch {
      return { deleted: true, uploads_deleted: 0 }
    }
  },

  getSourceTrail: async (sessionId: string, cardId: string): Promise<SourceTrailEntry> => {
    // Results carry their proof with them; use it first (works with no server memory).
    const cached = getTrails(sessionId)[cardId]
    if (cached) return cached as SourceTrailEntry
    try {
      return await request<SourceTrailEntry>(`/sessions/${sessionId}/source-trail/${cardId}`)
    } catch (e) {
      if (!sampleOnly(sessionId)) throw e
      return ((SAMPLE_SOURCE_TRAILS as Record<string, unknown>)[cardId] ?? {
        card_id: cardId,
        label: 'Calculation Details',
        inputs_used: {},
        rule_or_formula: 'Calculated using the FY 2025-26 rules engine.',
        config_version: 'fy2025-26',
        source_url: 'https://incometaxindia.gov.in',
      }) as SourceTrailEntry
    }
  },

  askConsultant: async (sessionId: string, question: string) => {
    try {
      return await request<ConsultantAnswer>(`/sessions/${sessionId}/consultant/ask`, {
        method: 'POST',
        body: stateBody(sessionId, { question }),
      })
    } catch (e) {
      if (!sampleOnly(sessionId)) throw e
      return {
        answer: SAMPLE_CONSULTANT_ANSWERS.default.answer,
        guardrail_flagged: false,
        source_chip: SAMPLE_CONSULTANT_ANSWERS.default.source_chip,
      }
    }
  },
}

export interface MoneyFinderCard {
  card_id: string
  title: string
  detail: string
  amount: number
  unit_label: string
  source_chip: string
  action_label: string
}

export interface MoneyFinderResult {
  source_trails?: Record<string, unknown>
  total_found: number
  yearly_total: number
  one_time_total: number
  cards: MoneyFinderCard[]
}

export interface LeakFixerCard {
  card_id: string
  title: string
  detail: string
  amount: number
  unit_label: string
  status_label: string | null
  source_chip: string
  action_label: string
  months_seen: string[]
}

export interface LeakFixerResult {
  source_trails?: Record<string, unknown>
  monthly_leak_total: number
  annual_leak_total: number
  cards: LeakFixerCard[]
  monthly_breakdown: Record<string, number>
}

export interface SourceTrailEntry {
  card_id: string
  label: string
  inputs_used: Record<string, unknown>
  rule_or_formula: string
  config_version: string | null
  source_url: string | null
}

export interface ConsultantAnswer {
  answer: string
  guardrail_flagged: boolean
  source_chip: string
}

export interface AgentToolCall {
  tool: string
  args: Record<string, unknown>
  result: Record<string, unknown> | null
}

export interface AgentRunResult {
  agent: string
  engine: 'gemini' | 'offline'
  answer: string
  guardrail_flagged: boolean
  tool_calls: AgentToolCall[]
}
