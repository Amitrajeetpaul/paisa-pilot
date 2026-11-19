export type Tone = 'indigo' | 'teal' | 'amber' | 'coral' | 'violet' | 'cyan' | 'slate'

export const TONE: Record<Tone, { fg: string; bg: string }> = {
  indigo: { fg: '#4a4ac0', bg: '#ececfb' },
  teal: { fg: '#16998d', bg: '#dff6f3' },
  amber: { fg: '#c47f0a', bg: '#fff1d6' },
  coral: { fg: '#e8484d', bg: '#ffe6e3' },
  violet: { fg: '#7040e0', bg: '#f0e9ff' },
  cyan: { fg: '#0f8fa8', bg: '#dff4f9' },
  slate: { fg: '#475569', bg: '#eceff3' },
}

export const SOLID: Record<Tone, string> = {
  indigo: '#5b5bd6',
  teal: '#2ec4b6',
  amber: '#f5a524',
  coral: '#ff5a5f',
  violet: '#8b5cf6',
  cyan: '#19b5d4',
  slate: '#64748b',
}
