import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { type Language, translate, type TranslationKey } from '../locales'

interface AppContextValue {
  sessionId: string | null
  setSessionId: (id: string | null) => void
  sampleData: boolean
  setSampleData: (v: boolean) => void
  language: Language
  setLanguage: (l: Language) => void
  displayName: string
  setDisplayName: (n: string) => void
  theme: 'light' | 'dark'
  toggleTheme: () => void
  largeText: boolean
  setLargeText: (v: boolean) => void
  t: (key: TranslationKey) => string
}

const AppContext = createContext<AppContextValue | null>(null)

const SESSION_KEY = 'paisa_pilot_session_id'
const SAMPLE_KEY = 'paisa_pilot_sample_data'
const LANG_KEY = 'paisa_pilot_language'
const TEXT_SIZE_KEY = 'paisa_pilot_large_text'
const NAME_KEY = 'paisa_pilot_display_name'
const THEME_KEY = 'paisa_pilot_theme'

export function AppProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionIdState] = useState<string | null>(() => localStorage.getItem(SESSION_KEY))
  const [sampleData, setSampleDataState] = useState<boolean>(() => localStorage.getItem(SAMPLE_KEY) === '1')
  const [language, setLanguageState] = useState<Language>(() => (localStorage.getItem(LANG_KEY) as Language) || 'en')
  const [largeText, setLargeTextState] = useState<boolean>(() => localStorage.getItem(TEXT_SIZE_KEY) === '1')

  const [displayName, setDisplayNameState] = useState<string>(() => localStorage.getItem(NAME_KEY) ?? '')

  const [theme, setThemeState] = useState<'light' | 'dark'>(() => {
    const saved = localStorage.getItem(THEME_KEY)
    if (saved === 'light' || saved === 'dark') return saved
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })

  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => {
      const next = prev === 'dark' ? 'light' : 'dark'
      localStorage.setItem(THEME_KEY, next)
      return next
    })
  }, [])

  useEffect(() => {
    document.documentElement.lang = language
    document.documentElement.dataset.textSize = largeText ? 'large' : 'normal'
  }, [language, largeText])

  const setSessionId = useCallback((id: string | null) => {
    setSessionIdState(id)
    if (id) localStorage.setItem(SESSION_KEY, id)
    else localStorage.removeItem(SESSION_KEY)
  }, [])

  const setSampleData = useCallback((v: boolean) => {
    setSampleDataState(v)
    localStorage.setItem(SAMPLE_KEY, v ? '1' : '0')
  }, [])

  const setDisplayName = useCallback((n: string) => {
    setDisplayNameState(n)
    localStorage.setItem(NAME_KEY, n)
  }, [])

  const setLanguage = useCallback((l: Language) => {
    setLanguageState(l)
    localStorage.setItem(LANG_KEY, l)
  }, [])

  const setLargeText = useCallback((v: boolean) => {
    setLargeTextState(v)
    localStorage.setItem(TEXT_SIZE_KEY, v ? '1' : '0')
  }, [])

  const t = useCallback((key: TranslationKey) => translate(language, key), [language])

  const value = useMemo(
    () => ({ sessionId, setSessionId, sampleData, setSampleData, language, setLanguage, displayName, setDisplayName, theme, toggleTheme, largeText, setLargeText, t }),
    [sessionId, setSessionId, sampleData, setSampleData, language, setLanguage, displayName, setDisplayName, theme, toggleTheme, largeText, setLargeText, t],
  )

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used within AppProvider')
  return ctx
}
