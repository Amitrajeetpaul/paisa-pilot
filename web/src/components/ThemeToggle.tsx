import { useApp } from '../state/AppContext'
import { Icon } from './Icon'

export function ThemeToggle({ className = '' }: { className?: string }) {
  const { theme, toggleTheme } = useApp()
  const dark = theme === 'dark'
  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
      aria-pressed={dark}
      className={`text-muted border-line hover:text-ink press flex h-11 w-11 items-center justify-center rounded-full border ${className}`}
    >
      <Icon name={dark ? 'sun' : 'moon'} size={18} />
    </button>
  )
}
