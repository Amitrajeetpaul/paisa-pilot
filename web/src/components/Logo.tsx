export function LogoMark({ size = 34 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <g stroke="#FFFFFF" strokeOpacity="0.7" strokeWidth="2.4">
        <path d="M5 11l7 5" />
        <path d="M4 19l8 2" />
        <path d="M7 27h5" />
        <path d="M35 11l-7 5" />
        <path d="M36 19l-8 2" />
        <path d="M33 27h-5" />
      </g>
      <g stroke="#FFFFFF" strokeWidth="2.8">
        <path d="M14 12h12" />
        <path d="M14 17h12" />
        <path d="M14 12h5a5 5 0 0 1 0 10h-5" />
        <path d="M15 22l9 10" />
      </g>
    </svg>
  )
}

export function LogoTile({ size = 40 }: { size?: number }) {
  return (
    <div
      className="bg-coral-button flex shrink-0 items-center justify-center rounded-[12px]"
      style={{ width: size, height: size }}
    >
      <LogoMark size={Math.round(size * 0.85)} />
    </div>
  )
}

export function Wordmark({ withTile = true }: { withTile?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      {withTile && <LogoTile />}
      <span className="text-navy text-lg font-extrabold tracking-tight">Paisa Pilot</span>
    </div>
  )
}
