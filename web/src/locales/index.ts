import en, { type TranslationKey } from './en'
import hi from './hi'

export type Language = 'en' | 'hi'

const dictionaries: Record<Language, Record<TranslationKey, string>> = { en, hi }

export function translate(language: Language, key: TranslationKey): string {
  return dictionaries[language][key] ?? dictionaries.en[key] ?? key
}

export type { TranslationKey }
