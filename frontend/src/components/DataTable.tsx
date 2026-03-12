"use client";

import { type ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  emptyMessage?: string;
  total?: number;
  limit?: number;
  offset?: number;
  onPageChange?: (offset: number) => void;
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  loading = false,
  emptyMessage = "No data found.",
  total,
  limit,
  offset = 0,
  onPageChange,
}: DataTableProps<T>) {
  const hasPagination = total != null && limit != null && onPageChange != null;
  const totalPages = hasPagination ? Math.ceil(total / limit) : 0;
  const currentPage = hasPagination ? Math.floor(offset / limit) + 1 : 1;

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400"
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
          {loading ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-8 text-center text-gray-400"
              >
                Loading…
              </td>
            </tr>
          ) : data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-8 text-center text-gray-400"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, i) => (
              <tr key={(row.id as string) ?? i}>
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className="whitespace-nowrap px-4 py-3 text-sm text-gray-700 dark:text-gray-300"
                  >
                    {col.render ? col.render(row) : String(row[col.key] ?? "")}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>

      {hasPagination && totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-gray-200 px-4 py-3 dark:border-gray-700">
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Page {currentPage} of {totalPages} ({total} items)
          </span>
          <div className="flex gap-2">
            <button
              disabled={currentPage <= 1}
              onClick={() => onPageChange(offset - limit)}
              className="rounded border px-3 py-1 text-sm disabled:opacity-40"
            >
              Previous
            </button>
            <button
              disabled={currentPage >= totalPages}
              onClick={() => onPageChange(offset + limit)}
              className="rounded border px-3 py-1 text-sm disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
