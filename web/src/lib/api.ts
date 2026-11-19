// Local dev: Vite's dev-server proxy (vite.config.ts) forwards "/api" to
// the FastAPI server, so the default is enough. Production (Cloud Run):
// the web and api services get separate URLs with no shared domain by
// default, so the built bundle needs the api service's URL baked in at
// build time -- see infra/web.Dockerfile and infra/deploy.md.
const BASE = import.meta.env.VITE_API_BASE_URL ?? '/api'

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

export const api = {
  giveConsent: (consentGiven: boolean) =>
    request<{ session_id: string }>('/consent', {
      method: 'POST',
      body: JSON.stringify({ consent_given: consentGiven }),
    }),

  createSampleSession: () =>
    request<{ session_id: string; sample_data: boolean; confirmed: Record<string, unknown> }>(
      '/demo/sample-session',
      { method: 'POST' },
    ),

  uploadDocument: async (sessionId: string, documentType: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BASE}/sessions/${sessionId}/documents/${documentType}/upload`, {
      method: 'POST',
      body: form,
    })
    if (!res.ok) throw await apiError(res)
    return res.json() as Promise<{ upload_key: string }>
  },

  readDocument: (sessionId: string, documentType: string, uploadKey: string) =>
    request<Record<string, unknown>>(`/sessions/${sessionId}/documents/${documentType}/read`, {
      method: 'POST',
      body: JSON.stringify({ upload_key: uploadKey }),
    }),

  confirmDocument: (sessionId: string, documentType: string, fields: Record<string, unknown>) =>
    request<{ status: string }>(`/sessions/${sessionId}/documents/${documentType}/confirm`, {
      method: 'POST',
      body: JSON.stringify(fields),
    }),

  getConfirmed: (sessionId: string, documentType: string) =>
    request<Record<string, unknown>>(`/sessions/${sessionId}/documents/${documentType}/confirmed`),

  calculateMoneyFinder: (sessionId: string) =>
    request<MoneyFinderResult>(`/sessions/${sessionId}/calculate/money-finder`, { method: 'POST' }),

  calculateLeakFixer: (sessionId: string) =>
    request<LeakFixerResult>(`/sessions/${sessionId}/calculate/leak-fixer`, { method: 'POST' }),

  runAgent: (sessionId: string, agent: 'money_finder' | 'leak_fixer' | 'consultant' | 'ca_assistant', question?: string) =>
    request<AgentRunResult>(`/sessions/${sessionId}/agents/${agent}/run`, {
      method: 'POST',
      body: JSON.stringify({ question: question ?? null }),
    }),

  deleteMyData: (sessionId: string) =>
    request<{ deleted: boolean; uploads_deleted: number }>(`/sessions/${sessionId}`, { method: 'DELETE' }),

  getSourceTrail: (sessionId: string, cardId: string) =>
    request<SourceTrailEntry>(`/sessions/${sessionId}/source-trail/${cardId}`),

  askConsultant: (sessionId: string, question: string) =>
    request<ConsultantAnswer>(`/sessions/${sessionId}/consultant/ask`, {
      method: 'POST',
      body: JSON.stringify({ question }),
    }),
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
  monthly_leak_total: number
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
