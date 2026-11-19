import { NavLink } from 'react-router-dom'
import { useApp } from '../state/AppContext'
import { Icon, type IconName } from './Icon'
import { Wordmark } from './Logo'

const NAV_ITEMS: { to: string; icon: IconName; key: 'nav.find' | 'nav.fix' | 'nav.advise' }[] = [
  { to: '/app/home', icon: 'search', key: 'nav.find' },
  { to: '/app/fix', icon: 'wrench', key: 'nav.fix' },
  { to: '/app/advise', icon: 'chat', key: 'nav.advise' },
]

export function BottomNav() {
  const { t } = useApp()
  return (
    <nav
      aria-label="Primary"
      className="border-line fixed inset-x-0 bottom-0 z-40 flex justify-around border-t bg-white/95 px-2 py-2 backdrop-blur md:hidden"
    >
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.key}
          to={item.to}
          className={({ isActive }) =>
            `flex min-h-11 min-w-16 flex-col items-center justify-center gap-0.5 rounded-2xl px-3 py-1.5 text-xs font-semibold ${
              isActive ? 'bg-coral-tint text-navy' : 'text-muted'
            }`
          }
        >
          <Icon name={item.icon} size={20} />
          {t(item.key)}
        </NavLink>
      ))}
    </nav>
  )
}

export function SideNav() {
  const { t } = useApp()
  return (
    <nav
      aria-label="Primary"
      className="border-line sticky top-0 hidden h-screen w-56 flex-col gap-1 border-r bg-white px-4 py-6 md:flex"
    >
      <div className="mb-8 px-2">
        <Wordmark />
      </div>
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.key}
          to={item.to}
          className={({ isActive }) =>
            `flex min-h-11 items-center gap-3 rounded-2xl px-3 py-2 text-sm font-semibold ${
              isActive ? 'bg-coral-tint text-navy' : 'text-muted hover:text-navy'
            }`
          }
        >
          <Icon name={item.icon} size={20} />
          {t(item.key)}
        </NavLink>
      ))}
    </nav>
  )
}
