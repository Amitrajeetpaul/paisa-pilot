import { Icon, type IconName } from './Icon'
import { TONE, type Tone } from './tones'

export function IconTile({ icon, size = 44, tone = 'coral' }: { icon: IconName; size?: number; tone?: Tone }) {
  return (
    <div
      className="flex shrink-0 items-center justify-center rounded-2xl"
      style={{ width: size, height: size, background: TONE[tone].bg, color: TONE[tone].fg }}
      aria-hidden="true"
    >
      <Icon name={icon} size={Math.round(size * 0.5)} />
    </div>
  )
}
