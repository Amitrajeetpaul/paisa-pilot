import type { IconName } from './Icon'
import { IconTile } from './IconTile'
import { formatINR } from '../lib/format'
import type { Tone } from './tones'

interface ResultRowProps {
  icon: IconName
  tone?: Tone
  title: string
  subtitle: string
  amount: number
  unitLabel: string
  badge?: string | null
  badgeTone?: 'warn' | 'ok'
  onOpen: () => void
}

/** One finding as a list row, like a transaction in a payments app. Tapping it opens
 * the proof and the next step. Nothing here can wrap into the amount or overlap. */
export function ResultRow({ icon, tone = 'coral', title, subtitle, amount, unitLabel, badge, badgeTone = 'warn', onOpen }: ResultRowProps) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="press flex w-full items-center gap-3 px-4 py-3.5 text-left"
      aria-label={`${title}: ${formatINR(amount)} ${unitLabel}. Open details.`}
    >
      <IconTile icon={icon} tone={tone} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 flex-wrap sm:flex-nowrap">
          <p className="text-ink text-[14px] sm:text-[15px] font-semibold leading-snug line-clamp-2">{title}</p>
          {badge && (
            <span
              className={`shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${
                badgeTone === 'ok' ? 'bg-teal-tint text-ink' : 'bg-yellow text-ink'
              }`}
            >
              {badge}
            </span>
          )}
        </div>
        <p className="text-muted mt-0.5 truncate text-[12px] sm:text-[13px] leading-tight">{subtitle}</p>
      </div>
      <div className="shrink-0 text-right pl-1.5">
        <p className="tabular text-ink text-[14px] sm:text-[15px] font-bold leading-tight">{formatINR(amount)}</p>
        <p className="text-muted mt-0.5 text-[10px] sm:text-[11px] leading-tight">{unitLabel}</p>
      </div>
      <span className="text-muted shrink-0 text-lg leading-none" aria-hidden="true">
        ›
      </span>
    </button>
  )
}
