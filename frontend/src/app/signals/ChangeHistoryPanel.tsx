"use client";

/* ------------------------------------------------------------------ */
/*  Collapsible panel showing signal change history                    */
/* ------------------------------------------------------------------ */

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import { formatDate, formatTimeAgo } from "@/lib/formatters";
import type { ApiResponse, SignalChangeLogEntry } from "@/types/api";
import SignalBadge from "@/components/SignalBadge";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import ErrorState from "@/components/ErrorState";
import { CONFIDENCE_STYLES } from "./constants";

interface ChangeHistoryPanelProps {
  /** Incrementing counter -- when it changes, history is re-fetched if panel is open */
  refreshKey: number;
}

export default function ChangeHistoryPanel({
  refreshKey,
}: ChangeHistoryPanelProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [entries, setEntries] = useState<SignalChangeLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const openRef = useRef(open);
  openRef.current = open;

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<ApiResponse<SignalChangeLogEntry[]>>(
        "/api/v1/signals/history?page=1&limit=20",
      );
      setEntries(res.data ?? []);
      setTotal(res.meta?.total ?? 0);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load change history",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  function handleToggle() {
    const willOpen = !open;
    setOpen(willOpen);
    if (willOpen && entries.length === 0) {
      fetchHistory();
    }
  }

  // Re-fetch when parent signals new data (e.g. after a save)
  useEffect(() => {
    if (refreshKey > 0 && openRef.current) {
      fetchHistory();
    }
  }, [refreshKey, fetchHistory]);

  return (
    <div className="mt-8">
      <button
        onClick={handleToggle}
        aria-expanded={open}
        aria-label={open ? "Collapse change history" : "Expand change history"}
        className="flex items-center gap-2 text-sm font-semibold text-slate-700 hover:text-slate-900 transition-colors"
      >
        <svg
          className={`w-4 h-4 transition-transform ${open ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9 5l7 7-7 7"
          />
        </svg>
        Change History
        {total > 0 && (
          <span className="text-xs text-slate-400 font-normal">
            ({total} entries)
          </span>
        )}
      </button>

      {open && (
        <div className="mt-4">
          {loading && <LoadingSkeleton variant="table" />}

          {error && <ErrorState message={error} onRetry={fetchHistory} />}

          {!loading && !error && entries.length === 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
              <p className="text-sm text-slate-500">
                No change history found.
              </p>
            </div>
          )}

          {!loading && !error && entries.length > 0 && (
            <HistoryTable entries={entries} />
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  History table (inner component)                                    */
/* ------------------------------------------------------------------ */

interface HistoryTableProps {
  entries: SignalChangeLogEntry[];
}

function HistoryTable({ entries }: HistoryTableProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Date
              </th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Sector
              </th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Signal Change
              </th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Confidence Change
              </th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Changed By
              </th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Reason
              </th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr
                key={entry.id}
                className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
              >
                <td className="px-4 py-3 text-sm text-slate-600">
                  <div>
                    {formatDate(entry.changed_at)}
                    <span className="block text-xs text-slate-400">
                      {formatTimeAgo(entry.changed_at)}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-sm font-medium text-slate-800">
                  {entry.sector_name}
                </td>
                <td className="px-4 py-3 text-sm">
                  <div className="flex items-center gap-1.5">
                    {entry.old_signal ? (
                      <SignalBadge signal={entry.old_signal} />
                    ) : (
                      <span className="text-xs text-slate-400">(none)</span>
                    )}
                    <span className="text-slate-400">&rarr;</span>
                    <SignalBadge signal={entry.new_signal} />
                  </div>
                </td>
                <td className="px-4 py-3 text-sm">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        CONFIDENCE_STYLES[entry.old_confidence ?? ""] ??
                        "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {entry.old_confidence ?? "--"}
                    </span>
                    <span className="text-slate-400">&rarr;</span>
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        CONFIDENCE_STYLES[entry.new_confidence] ??
                        "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {entry.new_confidence}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-sm text-slate-600">
                  {entry.changed_by}
                </td>
                <td className="px-4 py-3 text-sm text-slate-500 max-w-[200px] truncate">
                  {entry.change_reason ?? "\u2014"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
