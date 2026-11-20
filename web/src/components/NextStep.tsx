import { formatINR } from '../lib/format'
import { useApp } from '../state/AppContext'
import { Icon } from './Icon'

interface Card {
  card_id: string
  title: string
  amount: number
  unit_label: string
  action_label: string
}

/** The single most valuable thing to do now, so a first-time user knows where to start. */
export function NextStep({ cards, onOpen }: { cards: Card[]; onOpen: (c: Card) => void }) {
  const { t } = useApp()
  if (cards.length === 0) return null
  // yearly savings first (they repeat every year), then the biggest one-time amount
  const yearly = cards.filter((c) => /year/i.test(c.unit_label))
  const best = [...(yearly.length ? yearly : cards)].sort((a, b) => b.amount - a.amount)[0]
  return (
    <button
      type="button"
      onClick={() => onOpen(best)}
      className="card press mt-4 flex w-full items-center gap-3 p-4 text-left"
      aria-label={`${t('ui.nextStep')}: ${best.title}. ${best.action_label}`}
    >
      <span className="bg-coral-tint text-coral-dark flex h-11 w-11 shrink-0 items-center justify-center rounded-xl">
        <Icon name="check" size={20} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="text-muted block text-xs font-semibold uppercase tracking-wide">{t('ui.nextStep')}</span>
        <span className="text-ink block text-[15px] font-bold leading-snug">{best.title}</span>
        <span className="text-muted block text-xs">
          {t('ui.nextStepWorth')} {formatINR(best.amount)} {best.unit_label}
        </span>
      </span>
      <span className="text-coral-dark shrink-0 text-sm font-bold">{best.action_label} →</span>
    </button>
  )
}
