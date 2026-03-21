"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useAuth } from "@/lib/auth-context";
import { PageSkeleton } from "@/components/Skeleton";
import ConfirmDialog from "@/components/ConfirmDialog";
import {
  listReviews,
  createReview,
  reviewAction,
  listReports,
  type DataReview,
  type EmissionReport,
} from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  draft:
    "bg-[var(--status-draft-bg,rgba(107,114,128,0.2))] text-[var(--muted)]",
  submitted:
    "bg-[var(--status-submitted-bg,rgba(59,130,246,0.2))] text-[var(--status-submitted-fg,#60a5fa)]",
  approved:
    "bg-[var(--status-approved-bg,rgba(16,185,129,0.2))] text-[var(--status-approved-fg,#34d399)]",
  rejected:
    "bg-[var(--status-rejected-bg,rgba(239,68,68,0.2))] text-[var(--status-rejected-fg,#f87171)]",
  revision_requested:
    "bg-[var(--status-revision-bg,rgba(234,179,8,0.2))] text-[var(--status-revision-fg,#facc15)]",
};

export default function ReviewsPage() {
  useDocumentTitle("Data Reviews");
  const { user, loading } = useAuth();
  const router = useRouter();
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [selectedReport, setSelectedReport] = useState("");
  const [rejectTarget, setRejectTarget] = useState<string | null>(null);
  const [rejectNotes, setRejectNotes] = useState("");

  const reviewsQuery = useQuery<{ items: DataReview[] }>({
    queryKey: ["reviews", user?.company_id],
    queryFn: listReviews,
    enabled: !!user && !loading,
  });

  const reportsQuery = useQuery<{ items: EmissionReport[] }>({
    queryKey: ["reviews-reports", user?.company_id],
    queryFn: listReports,
    enabled: !!user && !loading,
  });

  const reviews = reviewsQuery.data?.items ?? [];
  const reports = reportsQuery.data?.items ?? [];

  useEffect(() => {
    if (reviewsQuery.error) {
      setError(
        reviewsQuery.error instanceof Error
          ? reviewsQuery.error.message
          : "Failed to load reviews",
      );
    }
  }, [reviewsQuery.error]);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [user, loading, router]);

  const handleCreate = async () => {
    if (!selectedReport) return;
    try {
      await createReview(selectedReport);
      await reviewsQuery.refetch();
      setShowCreate(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create review");
    }
  };

  const handleAction = async (
    reviewId: string,
    action: string,
    notes?: string,
  ) => {
    try {
      await reviewAction(reviewId, action, notes);
      await reviewsQuery.refetch();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Action failed");
    }
  };

  const handleReject = async () => {
    if (!rejectTarget) return;
    await handleAction(rejectTarget, "reject", rejectNotes);
    setRejectTarget(null);
    setRejectNotes("");
  };

  if (loading || reviewsQuery.isLoading) return <PageSkeleton />;
  if (!user) return null;

  return (
    <main className="mx-auto max-w-5xl p-8">
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-3xl font-bold">Data Reviews</h1>
        <button onClick={() => setShowCreate(true)} className="btn-primary">
          New Review
        </button>
      </div>

      {error && <p className="mb-4 text-[var(--danger)]">{error}</p>}

      {showCreate && (
        <div className="mb-6 rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
          <h3 className="mb-2 font-semibold">Create Review for Report</h3>
          <div className="flex gap-4">
            <select
              className="input"
              value={selectedReport}
              onChange={(e) => setSelectedReport(e.target.value)}
              aria-label="Select report for review"
            >
              <option value="">Select a report...</option>
              {reports.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.year} — {r.total.toFixed(1)} tCO₂e
                </option>
              ))}
            </select>
            <button onClick={handleCreate} className="btn-primary">
              Create
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="text-[var(--muted)]"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {reviews.map((r) => (
          <div
            key={r.id}
            className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">
                  Report: {r.report_id.slice(0, 8)}...
                </p>
                <p className="text-sm text-[var(--muted)]">
                  Created: {new Date(r.created_at).toLocaleDateString()}
                  {r.reviewed_at &&
                    ` · Reviewed: ${new Date(r.reviewed_at).toLocaleDateString()}`}
                </p>
                {r.reviewer_notes && (
                  <p className="mt-1 text-sm text-[var(--foreground)]">
                    Notes: {r.reviewer_notes}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span
                  className={`rounded-full px-3 py-1 text-xs font-medium ${STATUS_STYLES[r.status] || "bg-gray-600"}`}
                >
                  {r.status}
                </span>
                {r.status === "draft" && (
                  <button
                    onClick={() => handleAction(r.id, "submit")}
                    className="btn-primary text-sm px-3 py-1"
                  >
                    Submit
                  </button>
                )}
                {r.status === "submitted" && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleAction(r.id, "approve")}
                      className="btn-primary text-sm px-3 py-1"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => setRejectTarget(r.id)}
                      className="btn-danger text-sm px-3 py-1"
                    >
                      Reject
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
        {reviews.length === 0 && (
          <p className="text-[var(--muted)]">
            No reviews yet. Create one for an emission report.
          </p>
        )}
      </div>

      <ConfirmDialog
        open={!!rejectTarget}
        title="Reject Review"
        message="Are you sure you want to reject this review? Please provide a reason."
        confirmLabel="Reject"
        variant="danger"
        onConfirm={handleReject}
        onCancel={() => {
          setRejectTarget(null);
          setRejectNotes("");
        }}
      />
      {rejectTarget && (
        <div className="fixed inset-0 z-40" aria-hidden="true" />
      )}
    </main>
  );
}
