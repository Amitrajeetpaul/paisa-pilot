import type { ReactNode } from 'react'

export function SourceChip({ label, onClick }: { label: string; onClick?: () => void }) {
  const Tag = onClick ? 'button' : 'span'
  return (
    <Tag
      onClick={onClick}
      className="bg-source-chip text-ink inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium"
    >
      <svg width="12" height="12" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <circle cx="10" cy="10" r="9" fill="#2EC4B6" />
        <path d="M6 10.5l2.5 2.5 5.5-6" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {label}
    </Tag>
  )
}

export function StatusChip({ status }: { status: 'ok' | 'check' }) {
  if (status === 'ok') {
    return (
      <span className="bg-teal-tint text-ink inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold">
        ✓ Looks right
      </span>
    )
  }
  return (
    <span className="bg-yellow text-ink inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold">
      ⚠ Please check
    </span>
  )
}

export function SampleDataTag() {
  return (
    <span className="bg-yellow text-ink inline-flex items-center rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wide">
      Sample data
    </span>
  )
}

export function Pill({ children, active = false }: { children: ReactNode; active?: boolean }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ${
        active ? 'bg-coral-tint text-ink' : 'text-muted'
      }`}
    >
      {children}
    </span>
  )
}
