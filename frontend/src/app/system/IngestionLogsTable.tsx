"use client";

import { formatTimeAgo } from "@/lib/formatters";
import type { IngestionLog } from "@/types/api";
import { formatDuration, feedDisplayName } from "./utils";

interface IngestionLogsTableProps {
  logs: IngestionLog[];
}

/**
 * Table displaying the history of ingestion runs with status,
 * record counts (inserted / updated / failed), duration, and timing.
 */
export default function IngestionLogsTable({ logs }: IngestionLogsTableProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="text-base font-semibold text-slate-800 mb-4">
        Ingestion Logs
      </h3>
      {logs.length === 0 ? (
        <p className="text-sm text-slate-400 text-center py-8">
          No ingestion logs yet
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Feed Name
                </th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Records
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Duration
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Time
                </th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <IngestionLogRow key={log.id} log={log} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ---- Internal sub-component for a single log row ---- */

interface IngestionLogRowProps {
  log: IngestionLog;
}

function IngestionLogRow({ log }: IngestionLogRowProps) {
  return (
    <tr className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
      <td className="px-4 py-3 text-sm font-medium text-teal-600">
        {feedDisplayName(log.feed_name)}
      </td>
      <td className="px-4 py-3 text-center">
        <span
          className={`inline-block rounded px-2.5 py-0.5 text-xs font-bold uppercase ${
            log.status === "SUCCESS"
              ? "bg-emerald-100 text-emerald-700"
              : log.status === "FAILURE"
                ? "bg-red-100 text-red-700"
                : "bg-amber-100 text-amber-700"
          }`}
        >
          {log.status}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-slate-600 font-mono">
        <span className="text-emerald-600">
          {log.records_inserted} ins
        </span>
        {" / "}
        <span className="text-slate-600">
          {log.records_updated} upd
        </span>
        {" / "}
        <span
          className={
            log.records_failed > 0
              ? "text-red-600"
              : "text-slate-400"
          }
        >
          {log.records_failed} fail
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-slate-500 font-mono">
        {formatDuration(log.started_at, log.completed_at)}
      </td>
      <td className="px-4 py-3 text-sm text-slate-400">
        {formatTimeAgo(log.created_at)}
      </td>
    </tr>
  );
}
