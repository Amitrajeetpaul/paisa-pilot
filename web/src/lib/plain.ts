import { formatINR } from './format'

const MONEY_WORDS = ['amount', 'salary', 'income', 'tax', 'tds', 'balance', 'deduction', 'saving', 'pay', 'emi', 'principal', 'cover']

/** "tds_credited_in_your_ais" -> "TDS credited in your AIS" */
export function humanizeKey(key: string): string {
  const words = key.replace(/_/g, ' ').trim()
  const spaced = words.charAt(0).toUpperCase() + words.slice(1)
  return spaced.replace(/\b(tds|ais|pf|emi|itr|pan)\b/gi, (m) => m.toUpperCase())
}

/** Shows a stored input the way a person would read it: rupees, counts, words. */
export function formatInputValue(key: string, value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'number') {
    return MONEY_WORDS.some((w) => key.toLowerCase().includes(w)) ? formatINR(value) : value.toLocaleString('en-IN')
  }
  if (Array.isArray(value)) return `${value.length} item${value.length === 1 ? '' : 's'}`
  if (typeof value === 'object') return 'Details on file'
  return String(value)
}

/** "UPI AUTOPAY-FITZONE GYM-fitzone@upi" -> "Fitzone Gym" */
export function prettyMerchant(raw: string): string {
  let s = raw.replace(/[-\s]*[a-z0-9._]+@[a-z0-9.\-_]+$/i, '')
  s = s.replace(/^(UPI AUTOPAY|UPI|NEFT|IMPS|RTGS|ACH|NACH|POS)[-\s]+/i, '')
  s = s.replace(/-[A-Z]{2}\d{4,}$/i, '').replace(/[-_]+/g, ' ').trim()
  const title = s.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())
  return title.replace(/\bEmi\b/g, 'EMI') || raw
}

export function greetingForNow(): 'morning' | 'afternoon' | 'evening' {
  const h = new Date().getHours()
  return h < 12 ? 'morning' : h < 17 ? 'afternoon' : 'evening'
}
