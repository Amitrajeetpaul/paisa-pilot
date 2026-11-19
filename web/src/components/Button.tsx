import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'outline' | 'ghost'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  loading?: boolean
  children: ReactNode
}

const base =
  'inline-flex min-h-11 items-center justify-center gap-2 rounded-[18px] px-5 text-base font-semibold ' +
  'transition-transform duration-150 active:scale-[0.98] disabled:active:scale-100'

const variants: Record<Variant, string> = {
  // Coral gradient with NAVY text -- white-on-coral fails 4.5:1 contrast (brief rule).
  primary: 'bg-coral-button text-navy shadow-sm hover:brightness-105',
  secondary: 'bg-navy text-cream hover:bg-navy-light',
  outline: 'border-2 border-line bg-white text-navy hover:border-coral',
  ghost: 'text-muted hover:text-navy',
}

export function Button({ variant = 'primary', loading = false, disabled, children, className = '', ...rest }: ButtonProps) {
  return (
    <button
      className={`${base} ${variants[variant]} ${className}`}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden="true" />
      ) : null}
      {children}
    </button>
  )
}
