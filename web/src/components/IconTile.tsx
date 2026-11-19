export function IconTile({ icon, size = 44 }: { icon: string; size?: number }) {
  return (
    <div
      className="bg-icon-tile flex shrink-0 items-center justify-center rounded-2xl text-xl"
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      {icon}
    </div>
  )
}
