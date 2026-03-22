import { Skeleton, TableSkeleton } from "@/components/Skeleton";

export default function AuditLogsLoading() {
  return (
    <div className="p-6 max-w-6xl mx-auto">
      <Skeleton className="h-8 w-36 mb-6" />
      <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6">
        <TableSkeleton rows={8} />
      </div>
    </div>
  );
}
