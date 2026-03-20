"use client";

export default function ResetPasswordError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex items-center justify-center min-h-screen px-4">
      <div className="card w-full max-w-md text-center space-y-4">
        <h2 className="text-xl font-bold text-[var(--danger)]">
          Something went wrong
        </h2>
        <p className="text-[var(--muted)] text-sm">{error.message}</p>
        <button onClick={reset} className="btn-primary">
          Try again
        </button>
      </div>
    </div>
  );
}
