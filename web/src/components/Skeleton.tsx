export function CardSkeleton() {
  return (
    <div className="card p-5" role="status" aria-label="Loading">
      <div className="flex items-start gap-3">
        <div className="bg-line h-11 w-11 animate-pulse rounded-2xl" />
        <div className="flex-1">
          <div className="bg-line h-4 w-2/3 animate-pulse rounded" />
          <div className="bg-line mt-2 h-3 w-5/6 animate-pulse rounded" />
        </div>
      </div>
      <div className="bg-line mt-4 h-8 w-32 animate-pulse rounded" />
      <div className="mt-4 flex items-center justify-between">
        <div className="bg-line h-7 w-28 animate-pulse rounded-full" />
        <div className="bg-line h-11 w-28 animate-pulse rounded-[18px]" />
      </div>
    </div>
  )
}
