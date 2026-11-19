import { useMemo, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { Button } from '../components/Button'
import { StatusChip } from '../components/Chip'
import { api } from '../lib/api'
import type { TranslationKey } from '../locales'
import { useApp } from '../state/AppContext'
import { ConfirmListScreen, LIST_DOCUMENT_TYPES } from './ConfirmListScreen'

const CONFIDENCE_OK_THRESHOLD = 0.8

interface FieldEnvelope {
  value: string | number | null
  confidence: number
  raw_text: string | null
  notes: string | null
}

type FieldsShape = Record<string, FieldEnvelope | null | undefined>

const PAYSLIP_FIELD_ORDER = [
  'monthly_gross_salary',
  'basic_pay',
  'pf_employee_deduction',
  'tds_deducted',
  'professional_tax',
] as const

const FORM16_FIELD_ORDER = [
  'gross_salary_annual',
  'standard_deduction',
  'deductions_chapter_via_total',
  'taxable_income',
  'tds_deducted_annual',
] as const

function fieldLabelKey(documentType: string, field: string): TranslationKey {
  if (documentType === 'payslip') return `confirm.field.${field}` as TranslationKey
  return `confirm.field.${field}` as TranslationKey
}

function FieldConfirmScreen() {
  const { documentType = 'payslip' } = useParams<{ documentType: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const { t, sessionId } = useApp()
  const readResult = (location.state as { readResult?: { fields?: FieldsShape } } | null)?.readResult

  const fields = useMemo(() => readResult?.fields ?? {}, [readResult])
  const fieldOrder = documentType === 'form16' ? FORM16_FIELD_ORDER : PAYSLIP_FIELD_ORDER

  const [values, setValues] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {}
    for (const key of fieldOrder) {
      const v = fields[key]?.value
      initial[key] = v === null || v === undefined ? '' : String(v)
    }
    return initial
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const lowConfidenceFields = useMemo(
    () => new Set(fieldOrder.filter((key) => (fields[key]?.confidence ?? 1) < CONFIDENCE_OK_THRESHOLD)),
    [fieldOrder, fields],
  )

  async function handleConfirm() {
    if (!sessionId) return
    setSubmitting(true)
    setError(null)
    try {
      const payload: Record<string, unknown> = {}
      for (const key of fieldOrder) payload[key] = Number(values[key]) || 0
      // Carry through string fields the Confirm screen doesn't edit directly.
      if (documentType === 'payslip') {
        payload.employer_name = fields.employer_name?.value ?? ''
        payload.employee_name = fields.employee_name?.value ?? ''
        payload.pay_period = fields.pay_period?.value ?? ''
        payload.net_pay = fields.net_pay?.value ?? 0
        payload.hra = fields.hra?.value ?? 0
        payload.special_allowance = fields.special_allowance?.value ?? 0
      } else if (documentType === 'form16') {
        payload.employer_name = fields.employer_name?.value ?? ''
        payload.employee_name = fields.employee_name?.value ?? ''
        payload.financial_year = fields.financial_year?.value ?? ''
        payload.tax_regime_opted = fields.tax_regime_opted?.value ?? null
      }
      await api.confirmDocument(sessionId, documentType, payload)
      navigate('/app/home')
    } catch {
      setError('Could not save. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const segments = 6
  const currentStep = 3

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col px-5 py-6 md:max-w-lg">
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          aria-label={t('common.back')}
          className="flex h-10 w-10 items-center justify-center rounded-full hover:bg-black/5"
        >
          ←
        </button>
        <span className="text-muted text-sm font-semibold">{t('confirm.stepLabel')}</span>
      </div>

      <div className="mt-3 flex gap-1.5" role="progressbar" aria-valuenow={currentStep} aria-valuemin={1} aria-valuemax={segments}>
        {Array.from({ length: segments }).map((_, i) => (
          <div key={i} className={`h-1.5 flex-1 rounded-full ${i < currentStep ? 'bg-coral' : 'bg-line'}`} />
        ))}
      </div>

      <h1 className="text-navy mt-5 text-2xl font-extrabold">{t('confirm.title')}</h1>
      <p className="text-muted mt-2 text-sm leading-relaxed">{t('confirm.calm')}</p>

      <div className="mt-5 flex flex-col gap-3">
        {fieldOrder.map((key) => {
          const needsCheck = lowConfidenceFields.has(key)
          return (
            <div
              key={key}
              className={`rounded-[20px] border p-4 ${needsCheck ? 'bg-warning-card border-yellow' : 'border-line bg-white'}`}
            >
              <div className="flex items-center justify-between gap-3">
                <label htmlFor={key} className="text-muted text-sm font-semibold">
                  {t(fieldLabelKey(documentType, key))}
                </label>
                <StatusChip status={needsCheck ? 'check' : 'ok'} />
              </div>
              <input
                id={key}
                type="number"
                inputMode="decimal"
                value={values[key] ?? ''}
                onChange={(e) => setValues((prev) => ({ ...prev, [key]: e.target.value }))}
                className="text-navy mt-2 w-full border-0 bg-transparent text-3xl font-extrabold tracking-tight outline-none"
              />
              {needsCheck && <p className="text-navy mt-1 text-xs">{t('confirm.helperBlurry')}</p>}
            </div>
          )
        })}
      </div>

      {error && <p className="mt-3 text-sm font-medium text-[#C0392B]">{error}</p>}

      <div className="bg-bottom-panel sticky bottom-0 mt-6 -mx-5 flex flex-col gap-3 rounded-t-[28px] p-5 md:mx-0 md:rounded-[28px]">
        <div className="flex items-center gap-2 text-sm text-white/90">
          <span aria-hidden="true" className="text-teal">
            🔒
          </span>
          {t('confirm.lockLine')}
        </div>
        <Button variant="primary" className="w-full" loading={submitting} onClick={handleConfirm}>
          {t('confirm.confirmButton')}
        </Button>
        <button className="text-sm font-medium text-white/80 underline">{t('confirm.reupload')}</button>
      </div>
    </div>
  )
}

export function ConfirmScreen() {
  const { documentType = 'payslip' } = useParams<{ documentType: string }>()
  return LIST_DOCUMENT_TYPES.includes(documentType) ? (
    <ConfirmListScreen documentType={documentType} />
  ) : (
    <FieldConfirmScreen />
  )
}
