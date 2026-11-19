/**
 * ORIGYN design tokens. Source of truth for the palette, radius scale, and
 * gradients -- mirrored into src/index.css's @theme block so Tailwind
 * utilities (bg-coral, text-navy, ...) and these JS constants (for inline
 * gradient styles) never drift apart.
 */

export const colors = {
  coral: '#FF5A5F',
  navy: '#22223B',
  cream: '#FFF8F3',
  yellow: '#FFC94D',
  teal: '#2EC4B6',
  rose: '#F2B8B5',
  muted: '#5B5B73',
  coralTint: '#FFE9E4',
  tealTint: '#D5F3EF',
  line: '#F0E4DC',
  warnTint: '#FFF3D1',
} as const

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  card: 20,
  button: 18,
  hero: 28,
  pill: 9999,
} as const

export const gradients = {
  pageBackground: 'linear-gradient(180deg, #FFF8F3 0%, #FFEEE6 60%, #FFF8F3 100%)',
  heroCard:
    'radial-gradient(circle at 85% 0%, rgba(255,90,95,0.38), transparent 55%), ' +
    'radial-gradient(circle at 10% 100%, rgba(46,196,182,0.24), transparent 55%), ' +
    'linear-gradient(145deg, #30305A, #22223B)',
  coralButton: 'linear-gradient(135deg, #FF5A5F, #FF7B6B)',
  sourceChip: 'linear-gradient(135deg, #D5F3EF, #EAFAF7)',
  iconTile: 'linear-gradient(135deg, #FFE3DD, #FFF3EE)',
  warningCard: 'linear-gradient(135deg, #FFF0C7, #FFF9E6)',
  bottomPanel:
    'radial-gradient(circle at 85% 0%, rgba(255,90,95,0.35), transparent 55%), ' +
    'linear-gradient(145deg, #2A2A4D, #22223B)',
  leakHero: 'linear-gradient(135deg, #FFC94D, #FF5A5F)',
} as const

export type ColorToken = keyof typeof colors
