import type { ReactNode } from 'react'
import { useApp } from '../state/AppContext'
import { AccountMenu } from './AccountMenu'
import { Wordmark } from './Logo'
import { BottomNav, SideNav } from './Nav'

export function AppShell({ children }: { children: ReactNode }) {
  const { t, language, setLanguage, largeText, setLargeText } = useApp()

  return (
    <div className="flex min-h-screen">
      <SideNav />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-line sticky top-0 z-30 flex items-center justify-between border-b bg-white/90 px-4 py-3 backdrop-blur md:hidden">
          <Wordmark />
          <div className="flex items-center gap-2">
            <button
              onClick={() => setLanguage(language === 'en' ? 'hi' : 'en')}
              className="text-muted min-h-11 rounded-full px-2 text-sm font-semibold"
            >
              {t('common.language')}
            </button>
            <AccountMenu />
          </div>
        </header>

        <div className="hidden items-center justify-end gap-3 px-6 py-4 md:flex">
          <button
            onClick={() => setLargeText(!largeText)}
            aria-pressed={largeText}
            className="text-muted min-h-11 rounded-full border border-line px-3 text-sm font-semibold hover:text-navy"
          >
            {t('common.largeText')}
          </button>
          <button
            onClick={() => setLanguage(language === 'en' ? 'hi' : 'en')}
            className="text-muted min-h-11 rounded-full border border-line px-3 text-sm font-semibold hover:text-navy"
          >
            {t('common.language')}
          </button>
          <AccountMenu />
        </div>

        <main className="flex-1 px-4 pb-24 md:px-8 md:pb-10">{children}</main>
        <BottomNav />
      </div>
    </div>
  )
}
