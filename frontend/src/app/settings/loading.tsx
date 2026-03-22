import { Skeleton } from "@/components/Skeleton";

function FormCardSkeleton({ fields }: { fields: number }) {
  return (
    <div className="rounded-xl border border-[var(--card-border)] bg-[var(--card)] p-6 mb-8 space-y-4">
      <Skeleton className="h-5 w-36" />
      {Array.from({ length: fields }, (_, i) => (
        <div key={i} className="space-y-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-10 w-full rounded-lg" />
        </div>
      ))}
      <Skeleton className="h-10 w-28 rounded-lg" />
    </div>
  );
}

export default function SettingsLoading() {
  return (
    <div className="max-w-2xl mx-auto p-8">
      <div className="mb-6">
        <Skeleton className="h-8 w-32 mb-2" />
        <Skeleton className="h-4 w-60" />
      </div>
      <FormCardSkeleton fields={2} />
      <FormCardSkeleton fields={2} />
      <FormCardSkeleton fields={5} />
    </div>
  );
}
