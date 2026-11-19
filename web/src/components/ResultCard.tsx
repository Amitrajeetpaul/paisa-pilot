import { Button } from './Button'
import { SourceChip } from './Chip'
import type { IconName } from './Icon'
import { IconTile } from './IconTile'
import { formatINR } from '../lib/format'

interface ResultCardProps {
  icon: IconName
  title: string
  detail: string
  amount: number
  unitLabel: string
  sourceLabel: string
  actionLabel: string
  statusLabel?: string | null
  onAction: () => void
  onTapAmount: () => void
}

export function ResultCard({
  icon,
  title,
  detail,
  amount,
  unitLabel,
  sourceLabel,
  actionLabel,
  statusLabel,
  onAction,
  onTapAmount,
}: ResultCardProps) {
  return (
    <div className="border-line animate-card-entrance flex flex-col gap-3 rounded-[20px] border bg-white p-5">
      <div className="flex items-start gap-3">
        <IconTile icon={icon} />
        <div className="min-w-0 flex-1">
          <h3 className="text-navy text-base font-bold">{title}</h3>
          <p className="text-muted mt-0.5 text-sm">{detail}</p>
        </div>
      </div>

      <button
        type="button"
        onClick={onTapAmount}
        className="flex items-baseline gap-2 self-start rounded-lg text-left"
        aria-label={`${title}: ${formatINR(amount)} ${unitLabel}. Tap to see source.`}
      >
        <span className="text-navy text-3xl font-extrabold tracking-tight">{formatINR(amount)}</span>
        <span className="text-muted text-sm font-medium">{unitLabel}</span>
      </button>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <SourceChip label={sourceLabel} onClick={onTapAmount} />
          {statusLabel && (
            <span className="bg-coral-tint text-navy rounded-full px-2.5 py-1 text-xs font-semibold capitalize">
              {statusLabel}
            </span>
          )}
        </div>
        <Button variant="primary" onClick={onAction} className="min-w-[120px]">
          {actionLabel}
        </Button>
      </div>
    </div>
  )
}
