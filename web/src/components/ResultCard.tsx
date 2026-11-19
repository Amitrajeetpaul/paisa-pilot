import type { IconName } from './Icon'
import { IconTile } from './IconTile'
import { SourceChip } from './Chip'
import { formatINR } from '../lib/format'
import type { Tone } from './tones'

interface ResultCardProps {
  icon: IconName
  tone?: Tone
  title: string
  detail: string
  amount: number
  unitLabel: string
  sourceLabel: string
  actionLabel: string
  statusLabel?: string | null
  statusTone?: 'warn' | 'ok'
  index?: number
  onAction: () => void
  onTapAmount: () => void
}

/** One finding: what it is, how much, where it came from, and the next step.
 * The amount sits front and centre (and is tappable for its proof). */
export function ResultCard({
  icon, tone = 'coral', title, detail, amount, unitLabel, sourceLabel, actionLabel, statusLabel, statusTone = 'warn', index = 0, onAction, onTapAmount,
}: ResultCardProps) {
  return (
    <div className="card card-hover stagger p-4 sm:p-5" style={{ animationDelay: `${index * 70}ms` }}>
      <div className="flex items-start gap-3">
        <IconTile icon={icon} tone={tone} />
        <div className="min-w-0 flex-1">
          <h3 className="text-ink text-[15px] font-bold leading-snug">{title}</h3>
          <p className="text-muted mt-0.5 line-clamp-2 text-[13px] leading-snug">{detail}</p>
        </div>
        <button
          type="button"
          onClick={onTapAmount}
          className="press shrink-0 text-right"
          aria-label={`${title}: ${formatINR(amount)} ${unitLabel}. Tap to see source.`}
        >
          <div className="tabular text-ink text-xl font-extrabold leading-tight">{formatINR(amount)}</div>
          <div className="text-muted text-[11px] font-medium leading-tight">{unitLabel}</div>
        </button>
      </div>

      <div className="border-line mt-3.5 flex items-center justify-between gap-3 border-t pt-3">
        <div className="flex min-w-0 items-center gap-2">
          <SourceChip label={sourceLabel} onClick={onTapAmount} />
          {statusLabel && (
            <span
              className={`rounded-full px-2.5 py-1 text-xs font-bold capitalize ${statusTone === 'ok' ? 'bg-teal-tint text-ink' : 'bg-yellow text-ink'}`}
            >
              {statusLabel}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={onAction}
          className="bg-coral-button text-ink press inline-flex min-h-10 shrink-0 items-center gap-1 rounded-full px-4 text-sm font-bold shadow-sm"
        >
          {actionLabel}
          <span aria-hidden="true">›</span>
        </button>
      </div>
    </div>
  )
}
