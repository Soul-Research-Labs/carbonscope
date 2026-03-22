import { Skeleton } from "@/components/Skeleton";

export default function ComplianceLoading() {
  return (
    <div className="max-w-5xl mx-auto p-8 space-y-8">
      <Skeleton className="h-8 w-52" />
      <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6 space-y-4">
        <div className="flex gap-4">
          <Skeleton className="h-10 w-48 rounded-lg" />
          <Skeleton className="h-10 w-32 rounded-lg" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-lg" />
          ))}
        </div>
      </div>
    </div>
  );
}
