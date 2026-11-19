import { useNavigate } from 'react-router-dom'
import { Icon, type IconName } from './Icon'
import { TONE, type Tone } from './tones'

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
    <nav aria-label="Quick actions" className="mt-5 grid grid-cols-4 gap-2">
      {ACTIONS.map((a) => (
        <button
          key={a.label}
          type="button"
          onClick={() => (a.to ? navigate(a.to) : document.getElementById(a.scrollTo!)?.scrollIntoView({ behavior: 'smooth', block: 'start' }))}
          className="press flex min-h-11 flex-col items-center gap-2 rounded-2xl py-2"
        >
          <span
            className="flex h-14 w-14 items-center justify-center rounded-full shadow-sm"
            style={{ background: TONE[a.tone].bg, color: TONE[a.tone].fg }}
          >
            <Icon name={a.icon} size={24} />
          </span>
          <span className="text-navy text-center text-xs font-semibold leading-tight">{a.label}</span>
        </button>
      ))}
    </nav>
  )
}
