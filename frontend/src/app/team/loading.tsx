import { Skeleton, TableSkeleton } from "@/components/Skeleton";

export default function TeamLoading() {
  return (
    <div className="max-w-5xl mx-auto p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-32" />
        </div>
        <Skeleton className="h-10 w-40 rounded-lg" />
      </div>
      <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
        <Skeleton className="h-5 w-24 mb-4" />
        <TableSkeleton rows={4} />
      </div>
      <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
        <Skeleton className="h-5 w-40 mb-4" />
        <TableSkeleton rows={2} />
      </div>
    </div>
  );
}
