export function CardSkeleton() {
  return (
    <div className="flex items-center gap-3 px-4 py-3.5" role="status" aria-label="Loading">
      <div className="bg-line h-10 w-10 animate-pulse rounded-full" />
      <div className="flex-1">
        <div className="bg-line h-3.5 w-2/5 animate-pulse rounded" />
        <div className="bg-line mt-2 h-3 w-3/5 animate-pulse rounded" />
      </div>
      <div className="bg-line h-4 w-16 animate-pulse rounded" />
    </div>
  )
}
