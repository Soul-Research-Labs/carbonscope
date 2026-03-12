export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded bg-[var(--card-border)] ${className}`}
      role="status"
      aria-label="Loading"
    />
  );
}

export function CardSkeleton() {
  return (
    <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6" role="status" aria-label="Loading">
      <Skeleton className="h-5 w-1/3 mb-4" />
      <Skeleton className="h-4 w-full mb-2" />
      <Skeleton className="h-4 w-2/3 mb-2" />
      <Skeleton className="h-4 w-1/2" />
    </div>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3" role="status" aria-label="Loading">
      <Skeleton className="h-10 w-full" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-8 w-full" />
      ))}
    </div>
  );
}

/** Table body skeleton — renders placeholder <tr> elements for loading tables. */
export function SkeletonRows({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <>
      {Array.from({ length: rows }, (_, r) => (
        <tr key={r} className="border-b border-[var(--card-border)] last:border-0">
          {Array.from({ length: columns }, (_, c) => (
            <td key={c} className="py-3 px-4">
              <Skeleton className="h-4 w-full" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

export function PageSkeleton() {
  return (
    <div className="max-w-6xl mx-auto p-8 space-y-6">
      <Skeleton className="h-8 w-64 mb-6" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>
      <TableSkeleton />
    </div>
  );
}
