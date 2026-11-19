import { NavLink } from 'react-router-dom'
import { useApp } from '../state/AppContext'
import { Icon, type IconName } from './Icon'
import { Wordmark } from './Logo'

const NAV_ITEMS: { to: string; icon: IconName; key: 'nav.find' | 'nav.fix' | 'nav.advise' }[] = [
  { to: '/app/home', icon: 'search', key: 'nav.find' },
  { to: '/app/fix', icon: 'wrench', key: 'nav.fix' },
  { to: '/app/advise', icon: 'chat', key: 'nav.advise' },
]

/** Mobile: a standard fixed tab bar, as in every payments app. The active tab takes the brand colour. */
export function BottomNav() {
  const { t } = useApp()
  return (
    <nav
      aria-label="Primary"
      className="border-line fixed inset-x-0 bottom-0 z-40 flex border-t bg-white md:hidden"
      style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
    >
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.key}
          to={item.to}
          className={({ isActive }) =>
            `press relative flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 text-[11px] font-semibold ${
              isActive ? 'text-coral-dark' : 'text-muted'
            }`
          }
        >
          {({ isActive }) => (
            <>
              {isActive && <span className="bg-coral absolute inset-x-6 top-0 h-0.5 rounded-b-full" aria-hidden="true" />}
              <Icon name={item.icon} size={22} />
              {t(item.key)}
            </>
          )}
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
