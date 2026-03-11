"use client";

import { useEffect, useState, useCallback } from "react";
import { listAuditLogs, AuditLogEntry, ApiError } from "@/lib/api";

const PAGE_SIZE = 25;

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await listAuditLogs({ limit: PAGE_SIZE, offset });
      setLogs(res.items);
      setTotal(res.total);
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  }, [offset]);

  useEffect(() => {
    load();
  }, [load]);

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Audit Log</h1>

      {error && (
        <div className="bg-[var(--danger)]/10 border border-[var(--danger)] text-[var(--danger)] px-4 py-2 rounded-lg mb-4 text-sm">
          {error}
        </div>
      )}

      <div className="card overflow-x-auto">
        <table className="w-full text-sm" role="table">
          <thead>
            <tr className="text-left text-[var(--muted)] border-b border-[var(--card-border)]">
              <th className="pb-3 pr-4">Timestamp</th>
              <th className="pb-3 pr-4">Action</th>
              <th className="pb-3 pr-4">Resource</th>
              <th className="pb-3">Details</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td
                  colSpan={4}
                  className="py-8 text-center text-[var(--muted)]"
                >
                  Loading...
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td
                  colSpan={4}
                  className="py-8 text-center text-[var(--muted)]"
                >
                  No audit log entries found.
                </td>
              </tr>
            ) : (
              logs.map((entry) => (
                <tr
                  key={entry.id}
                  className="border-b border-[var(--card-border)] last:border-0"
                >
                  <td className="py-3 pr-4 whitespace-nowrap text-[var(--muted)]">
                    {new Date(entry.created_at).toLocaleString()}
                  </td>
                  <td className="py-3 pr-4">
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-[var(--primary)]/10 text-[var(--primary)]">
                      {entry.action}
                    </span>
                  </td>
                  <td className="py-3 pr-4">
                    <span className="text-[var(--muted)]">
                      {entry.resource_type}
                    </span>
                    {entry.resource_id && (
                      <span className="text-xs text-[var(--muted)] ml-1">
                        #{entry.resource_id.slice(0, 8)}
                      </span>
                    )}
                  </td>
                  <td className="py-3 text-[var(--muted)] max-w-xs truncate">
                    {entry.details || "—"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 text-sm text-[var(--muted)]">
          <span>
            Page {currentPage} of {totalPages} ({total} entries)
          </span>
          <div className="flex gap-2">
            <button
              className="px-3 py-1 rounded-md border border-[var(--card-border)] disabled:opacity-40"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              Previous
            </button>
            <button
              className="px-3 py-1 rounded-md border border-[var(--card-border)] disabled:opacity-40"
              disabled={currentPage >= totalPages}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
