import { useNavigate } from 'react-router-dom'
import { Icon, type IconName } from './Icon'
import type { Tone } from './tones'

interface Action {
  label: string
  icon: IconName
  tone: Tone
  to?: string
  scrollTo?: string
}

const ACTIONS: Action[] = [
  { label: 'Add documents', icon: 'upload', tone: 'indigo', to: '/app/consent' },
  { label: 'Tax check-up', icon: 'percent', tone: 'teal', scrollTo: 'tax-checkup' },
  { label: 'Fix leaks', icon: 'wrench', tone: 'amber', to: '/app/fix' },
  { label: 'Ask AI', icon: 'chat', tone: 'coral', to: '/app/advise' },
]

/** PhonePe-style round shortcuts: the four things people do most. */
export function QuickActions() {
  const navigate = useNavigate()
  return (
    <nav aria-label="Quick actions" className="card mt-4 grid grid-cols-4 gap-1 p-2">
      {ACTIONS.map((a) => (
        <button
          key={a.label}
          type="button"
          onClick={() => (a.to ? navigate(a.to) : document.getElementById(a.scrollTo!)?.scrollIntoView({ behavior: 'smooth', block: 'start' }))}
          className="press flex min-h-11 flex-col items-center gap-1.5 rounded-xl py-2"
        >
          <span className="bg-navy/[0.06] text-ink flex h-12 w-12 items-center justify-center rounded-full">
            <Icon name={a.icon} size={22} />
          </span>
          <span className="text-ink text-center text-[10px] sm:text-[11px] font-semibold leading-tight w-full px-0.5 line-clamp-2 h-7 flex items-center justify-center">
            {a.label}
          </span>
        </button>
      ))}
    </nav>
  )
}
