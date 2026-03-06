"use client";

import type { HealthReady } from "@/types/api";

interface SystemStatusBadgeProps {
  health: HealthReady;
}

/**
 * Displays the overall system health status with version and environment info.
 */
export default function SystemStatusBadge({ health }: SystemStatusBadgeProps) {
  return (
    <div className="mb-6 flex items-center gap-3">
      <span className="text-sm text-slate-500">System Status:</span>
      <span
        className={`inline-block rounded px-2.5 py-0.5 text-xs font-bold uppercase ${
          health.status === "healthy"
            ? "bg-emerald-100 text-emerald-700"
            : health.status === "degraded"
              ? "bg-amber-100 text-amber-700"
              : "bg-red-100 text-red-700"
        }`}
      >
        {health.status}
      </span>
      <span className="text-xs text-slate-400">
        v{health.version} &middot; {health.environment}
      </span>
    </div>
  );
}
