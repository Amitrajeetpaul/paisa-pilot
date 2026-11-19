import { useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Button } from '../components/Button'
import { Icon } from '../components/Icon'
import { StatusChip } from '../components/Chip'
import { ReadWarning } from '../components/ReadWarning'
import { api } from '../lib/api'
import { track } from '../lib/track'
import type { TranslationKey } from '../locales'
import { useApp } from '../state/AppContext'

const CONFIDENCE_OK_THRESHOLD = 0.8

export const LIST_DOCUMENT_TYPES = ['pf_passbook', 'bank_statement', 'ais']

type Row = Record<string, string | number | null>
interface Envelope {
  value: string | null
  confidence?: number
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Raw = any

interface ColumnDef {
  key: string
  label: string
  kind: 'text' | 'number' | 'select'
  options?: string[]
}

interface Schema {
  titleKey: TranslationKey
  columns: ColumnDef[]
  rowTitle: (row: Row) => string
  canRemove: boolean
  /** Pull header values + rows out of the reader output. */
  parse: (read: Raw) => { header: Record<string, string>; rows: Row[]; lowConfidence: boolean[] }
  /** Build the exact payload api/models.py expects. */
  build: (header: Record<string, string>, rows: Row[]) => Record<string, unknown>
}

const v = (e: Envelope | null | undefined): string => (e?.value ?? '') as string
const num = (x: string | number | null): number => Number(x) || 0
const orNull = (x: string | number | null): string | null => (x === '' || x === null ? null : String(x))

const SCHEMAS: Record<string, Schema> = {
  pf_passbook: {
    titleKey: 'confirm.title.pf_passbook',
    columns: [
      { key: 'employer_name', label: 'Employer', kind: 'text' },
      { key: 'balance', label: 'Balance (₹)', kind: 'number' },
      { key: 'period_to', label: 'Left this employer on (leave blank if you still work there)', kind: 'text' },
      { key: 'status_as_printed', label: 'Status on the passbook', kind: 'text' },
    ],
    rowTitle: (r) => String(r.employer_name || 'PF account'),
    canRemove: false,
    parse: (read) => ({
      header: { member_name: v(read.member?.member_name), uan: v(read.member?.uan) },
      rows: (read.accounts ?? []).map((a: Raw) => ({
        employer_name: a.employer_name ?? '',
        member_id: a.member_id ?? '',
        period_from: a.period_from ?? '',
        period_to: a.period_to ?? '',
        balance: a.balance ?? '',
        status_as_printed: a.status_as_printed ?? '',
      })),
      lowConfidence: (read.accounts ?? []).map((a: Raw) => (a.confidence ?? 1) < CONFIDENCE_OK_THRESHOLD),
    }),
    build: (h, rows) => ({
      member_name: h.member_name,
      uan: h.uan,
      accounts: rows.map((r) => ({
        employer_name: String(r.employer_name ?? ''),
        member_id: String(r.member_id ?? ''),
        period_from: orNull(r.period_from),
        period_to: orNull(r.period_to),
        balance: r.balance === '' ? null : num(r.balance),
        status_as_printed: orNull(r.status_as_printed),
      })),
    }),
  },
  bank_statement: {
    titleKey: 'confirm.title.bank_statement',
    columns: [
      { key: 'date', label: 'Date', kind: 'text' },
      { key: 'description', label: 'Description', kind: 'text' },
      { key: 'amount', label: 'Amount (₹)', kind: 'number' },
      { key: 'type', label: 'Type', kind: 'select', options: ['debit', 'credit'] },
    ],
    rowTitle: (r) => `${r.date ?? ''}`,
    canRemove: true,
    parse: (read) => ({
      header: {
        account_holder_name: v(read.account?.account_holder_name),
        account_number_last4: v(read.account?.account_number_last4),
        statement_period_from: v(read.account?.statement_period_from),
        statement_period_to: v(read.account?.statement_period_to),
      },
      rows: (read.transactions ?? []).map((t: Raw) => ({
        date: t.date ?? '',
        description: t.description ?? '',
        amount: t.amount ?? '',
        type: t.type ?? 'debit',
        running_balance: t.running_balance ?? null,
      })),
      lowConfidence: (read.transactions ?? []).map((t: Raw) => (t.confidence ?? 1) < CONFIDENCE_OK_THRESHOLD),
    }),
    build: (h, rows) => ({
      account_holder_name: h.account_holder_name,
      account_number_last4: orNull(h.account_number_last4),
      statement_period_from: h.statement_period_from,
      statement_period_to: h.statement_period_to,
      transactions: rows.map((r) => ({
        date: String(r.date ?? ''),
        description: String(r.description ?? ''),
        amount: num(r.amount),
        type: r.type === 'credit' ? 'credit' : 'debit',
        running_balance: r.running_balance ?? null,
      })),
    }),
  },
  ais: {
    titleKey: 'confirm.title.ais',
    columns: [
      { key: 'deductor_name', label: 'Deducted by', kind: 'text' },
      { key: 'section', label: 'Section', kind: 'text' },
      { key: 'amount_paid', label: 'Amount paid (₹)', kind: 'number' },
      { key: 'tds_deducted', label: 'TDS deducted (₹)', kind: 'number' },
    ],
    rowTitle: (r) => String(r.deductor_name || 'TDS entry'),
    canRemove: true,
    parse: (read) => ({
      header: {
        taxpayer_name: v(read.taxpayer?.taxpayer_name),
        pan: v(read.taxpayer?.pan),
        financial_year: v(read.taxpayer?.financial_year),
      },
      rows: (read.tds_entries ?? []).map((e: Raw) => ({
        deductor_name: e.deductor_name ?? '',
        section: e.section ?? '',
        amount_paid: e.amount_paid ?? '',
        tds_deducted: e.tds_deducted ?? 0,
      })),
      lowConfidence: (read.tds_entries ?? []).map((e: Raw) => (e.confidence ?? 1) < CONFIDENCE_OK_THRESHOLD),
    }),
    build: (h, rows) => ({
      taxpayer_name: h.taxpayer_name,
      pan: orNull(h.pan),
      financial_year: h.financial_year,
      tds_entries: rows.map((r) => ({
        deductor_name: String(r.deductor_name ?? ''),
        section: orNull(r.section),
        amount_paid: r.amount_paid === '' ? null : num(r.amount_paid),
        tds_deducted: num(r.tds_deducted),
      })),
    }),
  },
}

export function ConfirmListScreen({ documentType }: { documentType: string }) {
  const schema = SCHEMAS[documentType]
  const location = useLocation()
  const navigate = useNavigate()
  const { t, sessionId } = useApp()
  const readResult = (location.state as { readResult?: Raw } | null)?.readResult

  const parsed = useMemo(() => schema.parse(readResult ?? {}), [schema, readResult])
  const [header] = useState(parsed.header)
  const [rows, setRows] = useState<Row[]>(parsed.rows)
  const [lowFlags, setLowFlags] = useState<boolean[]>(parsed.lowConfidence)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function setCell(i: number, key: string, value: string) {
    setRows((prev) => prev.map((r, idx) => (idx === i ? { ...r, [key]: value } : r)))
    setLowFlags((prev) => prev.map((f, idx) => (idx === i ? false : f)))
  }

  function removeRow(i: number) {
    setRows((prev) => prev.filter((_, idx) => idx !== i))
    setLowFlags((prev) => prev.filter((_, idx) => idx !== i))
  }

  async function handleConfirm() {
    if (!sessionId) return
    setSubmitting(true)
    setError(null)
    try {
      await api.confirmDocument(sessionId, documentType, schema.build(header, rows))
      track('document_confirmed', documentType)
      navigate('/app/home')
    } catch {
      setError('Could not save. Please check the values and try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const checkCount = lowFlags.filter(Boolean).length

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col px-5 py-6 md:max-w-2xl">
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

      <h1 className="text-navy mt-5 text-2xl font-extrabold">{t(schema.titleKey)}</h1>
      <p className="text-muted mt-2 text-sm leading-relaxed">{t('confirm.calm')}</p>
      <ReadWarning warnings={(readResult?.warnings as string[] | undefined) ?? []} nothingRead={parsed.rows.length === 0} />
      {checkCount > 0 && (
        <p className="text-navy bg-warning-card border-yellow mt-3 rounded-2xl border p-3 text-sm">
          {checkCount} row(s) need a second look — they are highlighted below.
        </p>
      )}

      <div className="mt-5 flex flex-col gap-3">
        {rows.length === 0 && <p className="text-muted text-sm">Nothing was read from this document.</p>}
        {rows.map((row, i) => (
          <div
            key={i}
            className={`rounded-[20px] border p-4 ${lowFlags[i] ? 'bg-warning-card border-yellow' : 'border-line bg-white'}`}
          >
            <div className="flex items-center justify-between gap-3">
              <span className="text-navy text-sm font-bold">{schema.rowTitle(row)}</span>
              <div className="flex items-center gap-2">
                <StatusChip status={lowFlags[i] ? 'check' : 'ok'} />
                {schema.canRemove && (
                  <button type="button" onClick={() => removeRow(i)} className="text-muted text-xs font-semibold underline">
                    {t('confirm.removeRow')}
                  </button>
                )}
              </div>
            </div>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {schema.columns.map((col) => (
                <label key={col.key} className="text-muted flex flex-col gap-1 text-xs font-semibold">
                  {col.label}
                  {col.kind === 'select' ? (
                    <select
                      value={String(row[col.key] ?? '')}
                      onChange={(e) => setCell(i, col.key, e.target.value)}
                      className="text-navy border-line min-h-11 rounded-xl border bg-white px-3 text-base font-bold"
                    >
                      {col.options?.map((o) => (
                        <option key={o} value={o}>
                          {o}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type={col.kind === 'number' ? 'number' : 'text'}
                      inputMode={col.kind === 'number' ? 'decimal' : undefined}
                      value={row[col.key] === null ? '' : String(row[col.key] ?? '')}
                      onChange={(e) => setCell(i, col.key, e.target.value)}
                      className="text-navy border-line min-h-11 rounded-xl border bg-white px-3 text-base font-bold"
                    />
                  )}
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>

      {error && <p className="mt-3 text-sm font-medium text-[#C0392B]">{error}</p>}

      <div className="bg-bottom-panel sticky bottom-0 mt-6 -mx-5 flex flex-col gap-3 rounded-t-[28px] p-5 md:mx-0 md:rounded-[28px]">
        <div className="flex items-center gap-2 text-sm text-white/90">
          <Icon name="lock" size={16} className="text-teal" />
          {t('confirm.lockLine')}
        </div>
        <Button variant="primary" className="w-full" loading={submitting} onClick={handleConfirm}>
          {t('confirm.confirmButton')}
        </Button>
      </div>
    </div>
  )
}
