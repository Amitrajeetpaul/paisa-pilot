import { Icon, type IconName } from './Icon'
import { SOLID, type Tone } from './tones'

/** Solid circular icon, like the best payment apps: colour for meaning, white glyph. */
export function IconTile({ icon, size = 40, tone = 'coral' }: { icon: IconName; size?: number; tone?: Tone }) {
  return (
    <div
      className="flex shrink-0 items-center justify-center rounded-full text-white"
      style={{ width: size, height: size, background: SOLID[tone] }}
      aria-hidden="true"
    >
      <Icon name={icon} size={Math.round(size * 0.48)} />
    </div>
  )
}
