import { Icon, type IconName } from './Icon'

export function IconTile({ icon, size = 44 }: { icon: IconName; size?: number }) {
  return (
    <div
      className="bg-icon-tile text-coral-dark flex shrink-0 items-center justify-center rounded-2xl"
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <Icon name={icon} size={Math.round(size * 0.5)} />
    </div>
  )
}
