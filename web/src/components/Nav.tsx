import { NavLink } from 'react-router-dom'
import { useApp } from '../state/AppContext'
import { Icon, type IconName } from './Icon'
import { Wordmark } from './Logo'

const NAV_ITEMS: { to: string; icon: IconName; key: 'nav.find' | 'nav.fix' | 'nav.advise' }[] = [
  { to: '/app/home', icon: 'search', key: 'nav.find' },
  { to: '/app/fix', icon: 'wrench', key: 'nav.fix' },
  { to: '/app/advise', icon: 'chat', key: 'nav.advise' },
]

/** Mobile: a floating glass bar like the best money apps. The active tab lifts into a coral pill. */
export function BottomNav() {
  const { t } = useApp()
  return (
    <nav
      aria-label="Primary"
      className="glass border-line fixed inset-x-4 bottom-3 z-40 flex justify-around rounded-[26px] border p-1.5 shadow-[0_12px_32px_-10px_rgba(34,34,59,0.35)] md:hidden"
      style={{ paddingBottom: 'calc(0.375rem + env(safe-area-inset-bottom, 0px))' }}
    >
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.key}
          to={item.to}
          className={({ isActive }) =>
            `press flex min-h-12 flex-1 flex-col items-center justify-center gap-0.5 rounded-[20px] text-[11px] font-bold transition-colors ${
              isActive ? 'bg-coral-button text-navy shadow-sm' : 'text-muted'
            }`
          }
        >
          <Icon name={item.icon} size={21} />
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
      className="border-line sticky top-0 hidden h-screen w-60 flex-col gap-1.5 border-r bg-white/80 px-4 py-6 backdrop-blur md:flex"
    >
      <div className="mb-8 px-2">
        <Wordmark />
      </div>
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.key}
          to={item.to}
          className={({ isActive }) =>
            `press relative flex min-h-12 items-center gap-3 rounded-2xl px-3.5 text-sm font-bold transition-colors ${
              isActive ? 'bg-coral-tint text-navy' : 'text-muted hover:bg-black/[0.04] hover:text-navy'
            }`
          }
        >
          {({ isActive }) => (
            <>
              {isActive && <span className="bg-coral absolute left-0 top-2.5 h-7 w-1 rounded-r-full" aria-hidden="true" />}
              <Icon name={item.icon} size={20} className={isActive ? 'text-coral-dark' : ''} />
              {t(item.key)}
            </>
          )}
        </NavLink>
      ))}
      <div className="bg-teal-tint text-navy mt-auto rounded-2xl p-3.5 text-xs leading-relaxed">
        <p className="flex items-center gap-1.5 font-bold">
          <Icon name="shield" size={14} className="text-teal" /> Your data, your control
        </p>
        <p className="mt-1 opacity-80">Uploads auto-delete. Use the account menu to delete everything now.</p>
      </div>
    </nav>
  )
}
