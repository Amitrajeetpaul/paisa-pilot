import { Icon } from './Icon'

export function TrustStrip() {
  return (
    <div className="text-muted mt-4 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-xs font-medium">
      <span className="flex items-center gap-1.5"><Icon name="lock" size={13} className="text-teal" /> Encrypted</span>
      <span className="flex items-center gap-1.5"><Icon name="trash" size={13} className="text-teal" /> Auto-deleted</span>
      <span className="flex items-center gap-1.5"><Icon name="shield" size={13} className="text-teal" /> We never file or move money</span>
    </div>
  )
}
