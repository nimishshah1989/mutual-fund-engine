"use client";

import { formatDate } from "@/lib/formatters";
import type { HealthReady, DataFreshnessEntry } from "@/types/api";

interface SystemHealthPanelProps {
  health: HealthReady | null;
  totalFundsScored: number;
  morningstarFreshness: DataFreshnessEntry | undefined;
}

/** Status badge that picks emerald/red based on a boolean condition */
function StatusBadge({
  label,
  isOk,
}: {
  label: string;
  isOk: boolean;
}) {
  const colorClass = isOk
    ? "bg-emerald-100 text-emerald-700"
    : "bg-red-100 text-red-700";

  return (
    <span
      className={`text-xs font-bold uppercase px-2.5 py-0.5 rounded ${colorClass}`}
    >
      {label}
    </span>
  );
}

export default function SystemHealthPanel({
  health,
  totalFundsScored,
  morningstarFreshness,
}: SystemHealthPanelProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="text-base font-semibold text-slate-800 mb-4">
        System Health
      </h3>
      {health ? (
        <div className="space-y-4">
          {/* Database status */}
          <div className="flex items-center justify-between py-3 border-b border-slate-100">
            <span className="text-sm text-slate-600">Database</span>
            <StatusBadge
              label={health.checks.database.status}
              isOk={health.checks.database.status === "ok"}
            />
          </div>

          {/* Scheduler status */}
          <div className="flex items-center justify-between py-3 border-b border-slate-100">
            <span className="text-sm text-slate-600">Scheduler</span>
            <StatusBadge
              label={
                health.checks.scheduler.status === "running"
                  ? "Running"
                  : "Stopped"
              }
              isOk={health.checks.scheduler.status === "running"}
            />
          </div>

          {/* Total funds scored */}
          <div className="flex items-center justify-between py-3 border-b border-slate-100">
            <span className="text-sm text-slate-600">Total Funds Scored</span>
            <span className="text-sm font-mono font-semibold text-slate-800">
              {totalFundsScored}
            </span>
          </div>

          {/* Last ingestion run */}
          <div className="flex items-center justify-between py-3 border-b border-slate-100">
            <span className="text-sm text-slate-600">Last Ingestion</span>
            <span className="text-xs text-slate-400">
              {formatDate(morningstarFreshness?.last_run)}
            </span>
          </div>

          {/* Morningstar API status */}
          <div className="flex items-center justify-between py-3">
            <span className="text-sm text-slate-600">Morningstar Feed</span>
            <StatusBadge
              label={morningstarFreshness?.is_stale ? "Stale" : "Fresh"}
              isOk={!morningstarFreshness?.is_stale}
            />
          </div>

          {/* Scheduler jobs */}
          {health.checks.scheduler.jobs &&
            health.checks.scheduler.jobs.length > 0 && (
              <div className="mt-4">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Scheduled Jobs
                </p>
                {health.checks.scheduler.jobs.map((job) => (
                  <div
                    key={job.id}
                    className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-slate-600">
                        {job.name}
                      </span>
                      {job.pending && (
                        <span className="text-[10px] font-medium uppercase px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">
                          Pending
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-slate-400">
                      Next: {formatDate(job.next_run)}
                    </span>
                  </div>
                ))}
              </div>
            )}
        </div>
      ) : (
        <p className="text-sm text-slate-400 text-center py-8">
          Health data unavailable
        </p>
      )}
    </div>
  );
}
