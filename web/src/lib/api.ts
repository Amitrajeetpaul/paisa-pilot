import {
  SAMPLE_CONFIRMED,
  SAMPLE_MONEY_FINDER,
  SAMPLE_LEAK_FIXER,
  SAMPLE_SOURCE_TRAILS,
  SAMPLE_CONSULTANT_ANSWERS,
} from './sampleFallback'
import { currentUser, getIdToken } from './auth'
import {
  clearClientSession,
  getConfirmedDocs,
  getTrails,
  isLocalSession,
  isSampleSession,
  saveConfirmedDoc,
  saveTrails,
} from './clientSession'

// Primary: Google Cloud Run (Asia South 1); Backup: Vercel serverless
export const GCP_BASE = 'https://paisa-pilot-api-316611436028.asia-south1.run.app'
export const VERCEL_BASE = 'https://paisa-pilot-api.vercel.app'
export const BASE = import.meta.env.VITE_API_BASE_URL ?? GCP_BASE

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
  if (res.status === 404 && body.includes('Unknown session')) {
    // A session from an older visit that this server no longer knows. The app recovers quietly.
    return new ApiError('Your session expired. Please try again.', 'unknown_session')
  }
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

async function authHeaders(): Promise<Record<string, string>> {
  const token = currentUser() ? await getIdToken() : null
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = { 'Content-Type': 'application/json', ...(await authHeaders()) }
  // Accounts live only on the main server (the backup host remembers nothing), so /me never fails over.
  const canFailOver = BASE === GCP_BASE && !path.startsWith('/me')
  try {
    const res = await fetch(`${BASE}${path}`, { headers, ...options })
    if (res.ok) return (await res.json()) as T
    if (res.status >= 500 && canFailOver) {
      try {
        const backupRes = await fetch(`${VERCEL_BASE}${path}`, { headers, ...options })
        if (backupRes.ok) return (await backupRes.json()) as T
      } catch {
        /* ignore backup failure, throw original */
      }
    }
    throw await apiError(res)
  } catch (err) {
    if (canFailOver && !(err instanceof ApiError)) {
      try {
        const backupRes = await fetch(`${VERCEL_BASE}${path}`, { headers, ...options })
        if (backupRes.ok) return (await backupRes.json()) as T
      } catch {
        /* ignore */
      }
    }
    throw err
  }
}

const SAVING_KEY = 'pp_saving_on'
/** Whether this signed-in person switched saving on (remembered so confirmations sync without an extra call). */
export const savingOn = () => {
  try {
    return localStorage.getItem(SAVING_KEY) === '1'
  } catch {
    return false
  }
}
export const rememberSavingOn = (v: boolean) => {
  try {
    localStorage.setItem(SAVING_KEY, v ? '1' : '0')
  } catch {
    /* ignore */
  }
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
    try {
      const res = await fetch(`${BASE}/sessions/${sessionId}/documents/${documentType}/extract`, { method: 'POST', body: form })
      if (res.ok) return (await res.json()) as Record<string, unknown>
      if (res.status >= 500 && BASE === GCP_BASE) {
        try {
          const backupRes = await fetch(`${VERCEL_BASE}/sessions/${sessionId}/documents/${documentType}/extract`, { method: 'POST', body: form })
          if (backupRes.ok) return (await backupRes.json()) as Record<string, unknown>
        } catch {
          /* ignore backup failure, throw original */
        }
      }
      throw await apiError(res)
    } catch (err) {
      if (BASE === GCP_BASE && !(err instanceof ApiError)) {
        try {
          const backupRes = await fetch(`${VERCEL_BASE}/sessions/${sessionId}/documents/${documentType}/extract`, { method: 'POST', body: form })
          if (backupRes.ok) return (await backupRes.json()) as Record<string, unknown>
        } catch {
          /* ignore */
        }
      }
      throw err
    }
  },

  confirmDocument: async (sessionId: string, documentType: string, fields: Record<string, unknown>, opts: { sync?: boolean } = {}) => {
    const result = await request<{ status: string; fields?: Record<string, unknown> }>(
      `/sessions/${sessionId}/documents/${documentType}/confirm`,
      { method: 'POST', body: JSON.stringify(fields) },
    )
    if (isLocalSession(sessionId) && result.fields) saveConfirmedDoc(sessionId, documentType, result.fields)
    // Signed in with saving on: keep a copy in the account (best effort; the confirm itself already worked).
    if (opts.sync !== false && !isSampleSession(sessionId) && currentUser() && savingOn()) void api.meSaveDocument(documentType, result.fields ?? fields).catch(() => undefined)
    return result
  },

  // --- my account (signed-in people only) ---
  me: () => request<MeResult>('/me'),
  meConsent: (save: boolean) => request<{ saving_on: boolean }>('/me/consent', { method: 'POST', body: JSON.stringify({ save }) }),
  meSaveDocument: (documentType: string, fields: Record<string, unknown>) =>
    request<{ saved: boolean }>(`/me/documents/${documentType}`, { method: 'PUT', body: JSON.stringify({ fields }) }),
  meSnapshot: () => request<{ recorded: boolean }>('/me/snapshot', { method: 'POST', body: '{}' }),
  meProgress: () => request<MeProgress>('/me/progress'),
  meDelete: () => request<{ deleted: boolean }>('/me', { method: 'DELETE' }),

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

  gstAsk: (question: string) =>
    request<GstAskResult>('/gst/ask', { method: 'POST', body: JSON.stringify({ question }) }),

  gstSample: () => request<{ csv_text: string; period: string; annual_turnover: number; business_type: string }>('/gst/sample'),

  gstDraft: (body: { csv_text: string; period?: string; annual_turnover?: number; business_type?: string }) =>
    request<GstDraftResult>('/gst/draft', { method: 'POST', body: JSON.stringify(body) }),

  taxSuggestions: (sessionId: string) =>
    request<TaxSuggestionsResult>(`/sessions/${sessionId}/calculate/tax-suggestions`, {
      method: 'POST',
      body: stateBody(sessionId),
    }),

  spending: (sessionId: string) =>
    request<SpendingProfile>(`/sessions/${sessionId}/calculate/spending`, { method: 'POST', body: stateBody(sessionId) }),

  deadlines: (sessionId: string) =>
    request<DeadlinesResult>(`/sessions/${sessionId}/calculate/deadlines`, { method: 'POST', body: stateBody(sessionId, { days: 240 }) }),

  gstReconcileSample: () => request<{ books_csv: string; gstr2b_csv: string }>('/gst/reconcile-sample'),

  gstReconcile: (books_csv: string, gstr2b_csv: string) =>
    request<GstReconcileResult>('/gst/reconcile', { method: 'POST', body: JSON.stringify({ books_csv, gstr2b_csv }) }),

  itrPrefill: (sessionId: string) =>
    request<ItrPack>(`/sessions/${sessionId}/calculate/itr-prefill`, { method: 'POST', body: stateBody(sessionId) }),

  getUsageApps: () => request<UsageApps>('/usage/apps'),

  calculateSubscriptionUsage: (sessionId: string, usage: { app_key: string; days_used: number }[], windowDays: number) =>
    request<SubscriptionUsageResult>(`/sessions/${sessionId}/calculate/subscription-usage`, {
      method: 'POST',
      body: stateBody(sessionId, { usage, window_days: windowDays }),
    }),

  historyDays: (appKey: string, csvText: string) =>
    request<{ app_key: string; days_used: number; window_days: number }>('/usage/history-days', {
      method: 'POST',
      body: JSON.stringify({ app_key: appKey, csv_text: csvText }),
    }),

  runAgent: async (
    sessionId: string,
    agent: 'money_finder' | 'leak_fixer' | 'consultant' | 'ca_assistant',
    question?: string,
    fast = false,
  ) => {
    try {
      return await request<AgentRunResult>(`/sessions/${sessionId}/agents/${agent}/run`, {
        method: 'POST',
        body: stateBody(sessionId, { question: question ?? null, fast }),
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

export interface GstCitation {
  id: string
  section: string
  title: string
  excerpt: string
  source_url: string
}

export interface GstAskResult {
  answer: string
  citations: GstCitation[]
  grounded: boolean
  mode: 'ai' | 'notes_only' | 'not_found'
  notes_as_of: string
  reviewed_by_ca: boolean
  disclaimer: string
}

type Split = { igst: number; cgst: number; sgst: number }

export interface GstDraftResult {
  period: string
  due_date: string
  available_periods: string[]
  invoice_count: number
  outward_taxable: number
  output_tax: Split
  output_tax_total: number
  eligible_itc: Split
  eligible_itc_total: number
  blocked: { invoice: string; description: string; tax: number; reason: string; section: string }[]
  blocked_total: number
  blocked_source: { section: string; excerpt: string; source_url: string } | null
  cash_payable: Split
  carry_forward: Split
  days_late: number
  late_fee: number
  interest: number
  total_to_pay: number
  composition: null | { eligible: false; reasons: string[] } | { eligible: true; rate_percent: number; composition_tax: number; regular_cash_tax: number; cheaper: string; difference: number; note: string }
  steps: string[]
  notes_as_of: string
  reviewed_by_ca: boolean
  disclaimer: string
}

export interface TaxSuggestion {
  id: string
  title: string
  why: string
  saving: number | null
  action: string
  caveat: string
  law: { section: string; title: string; excerpt: string; source_url: string } | null
}

export interface TaxSuggestionsResult {
  picture: {
    gross_salary_annual: number
    old_regime_tax: number
    new_regime_tax: number
    cheaper_regime: 'old' | 'new'
    tax_now: number
    documents_used: string[]
  }
  suggestions: TaxSuggestion[]
  notes_as_of: string
  reviewed_by_ca: boolean
  disclaimer: string
}

export interface SpendingProfile {
  months_covered: number
  income_per_month: number
  spending_per_month: number
  invested_per_month: number
  left_over_per_month: number | null
  savings_rate_percent: number | null
  categories: { key: string; label: string; kind: string; total: number; monthly_average: number; share_percent: number }[]
  flags: { id: string; text: string; level: string }[]
  note: string
}

export interface MeResult {
  uid: string
  email: string | null
  saving_on: boolean
  documents: Record<string, Record<string, unknown>>
  documents_saved_at: Record<string, string | null>
  snapshots: { id: string; at: string; money_found_yearly?: number; leak_monthly?: number; tax_now?: number; cheaper_regime?: string }[]
}

export interface MeProgress {
  has_history: boolean
  summary: string
  latest_at: string | null
  previous_at: string | null
  changes: { metric: string; label: string; before: number; after: number; delta: number; better: boolean | null; text: string }[]
}

export interface Deadline {
  id: string
  title: string
  detail: string
  date: string
  days_left: number
  applies: boolean
  amount_so_far: number | null
  domain: 'income_tax' | 'gst'
  law: { section: string; excerpt: string; source_url: string } | null
}

export interface DeadlinesResult {
  deadlines: Deadline[]
  tax_payable_after_tds: number | null
  note: string
}

export interface ReconFinding {
  status: 'matched' | 'amount_mismatch' | 'probable_match' | 'missing_in_2b' | 'not_in_books'
  supplier_gstin: string
  supplier_name: string
  invoice_no: string
  books_tax: number | null
  gstr2b_tax: number | null
  itc_at_risk: number
  credit_not_yet_recorded: number
  message: string
  what_to_do: string
  gstin_valid: boolean
}

export interface GstReconcileResult {
  summary: {
    books_invoices: number
    gstr2b_invoices: number
    counts: Record<string, number>
    safe_to_claim: number
    itc_at_risk: number
    credit_not_yet_recorded: number
    invalid_gstins: string[]
  }
  findings: ReconFinding[]
  law: { section: string; title: string; excerpt: string; source_url: string }[]
  notes_as_of: string
  reviewed_by_ca: boolean
  disclaimer: string
}

export interface ItrPack {
  schema: string
  financial_year: string
  assessment_year: string
  disclaimer: string
  taxpayer: { name: string; pan: string | null }
  suggested_form: string
  income: { salary_gross: number; interest_from_deposits: number; gross_total_income: number }
  tax: { old_regime_tax: number; new_regime_tax: number; cheaper_regime: 'old' | 'new'; tax_on_cheaper_regime: number; regime_saving: number }
  tds: { credit_to_claim: number }
  result: {
    regime: 'old' | 'new'
    tax_payable: number
    tds_credit: number
    refund: number
    still_to_pay: number
    alternative: { regime: 'old' | 'new'; tax_payable: number; refund: number; still_to_pay: number }
    includes_interest: number
  }
  checklist: { item: string; status: 'ok' | 'missing' | 'check'; why: string }[]
  missing_count: number
  ready_to_file: boolean
  summary_text: string
  notes_as_of: string
  reviewed_by_ca: boolean
}

export interface UsageApps {
  window_days: number
  apps: { app_key: string; name: string; packages: string[] }[]
}

export interface UsageAlert {
  app_key: string
  app_name: string
  title: string
  level: 'unused' | 'rare' | 'light' | 'regular'
  days_used: number
  window_days: number
  monthly_amount: number
  cost_per_day_used: number | null
  monthly_saving: number
  annual_saving: number
  message: string
}

export interface SubscriptionUsageResult {
  window_days: number
  monthly_saving: number
  annual_saving: number
  alerts: UsageAlert[]
  tracked_app_keys: string[]
  source: string
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
