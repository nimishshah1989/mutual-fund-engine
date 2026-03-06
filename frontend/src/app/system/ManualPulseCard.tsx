"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import type { ApiResponse } from "@/types/api";

interface ManualPulseCardProps {
  onComplete: () => Promise<void>;
}

/**
 * Card for triggering MF Pulse operations:
 *  - Backfill: One-time 3-year NAV history fetch for all funds + Nifty 50
 *  - Refresh: Daily incremental — latest NAV + recompute snapshots
 */
export default function ManualPulseCard({ onComplete }: ManualPulseCardProps) {
  const [running, setRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleBackfill() {
    setError(null);
    setResult(null);
    setRunning(true);
    setCurrentStep("Starting 3-year NAV backfill for all funds...");

    try {
      const res = await apiFetch<ApiResponse<{ status: string; message: string }>>(
        "/api/v1/pulse/backfill?years=3",
        { method: "POST" },
      );
      setResult(res.data?.message ?? "Backfill started in background");
      setCurrentStep(null);
      await onComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Backfill failed");
      setCurrentStep(null);
    } finally {
      setRunning(false);
    }
  }

  async function handleRefresh() {
    setError(null);
    setResult(null);
    setRunning(true);
    setCurrentStep("Refreshing benchmark + latest NAVs + snapshots...");

    try {
      const res = await apiFetch<ApiResponse<{ status: string; message: string }>>(
        "/api/v1/pulse/refresh",
        { method: "POST" },
      );
      setResult(res.data?.message ?? "Refresh started in background");
      setCurrentStep(null);
      await onComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Refresh failed");
      setCurrentStep(null);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="text-base font-semibold text-slate-800 mb-2">
        MF Pulse Operations
      </h3>
      <p className="text-xs text-slate-400 mb-4">
        Manage NAV data and ratio return snapshots for MF Pulse signals.
      </p>

      {/* Live status */}
      {running && currentStep && (
        <div className="flex items-center gap-2 mb-3 px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg">
          <span className="inline-block w-3 h-3 rounded-full bg-blue-500 animate-pulse flex-shrink-0" />
          <span className="text-xs text-blue-700 font-medium">
            {currentStep}
          </span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-3 px-3 py-2 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-xs text-red-700 font-medium">{error}</p>
        </div>
      )}

      {/* Success */}
      {result && (
        <div className="mb-3 px-3 py-2 bg-emerald-50 border border-emerald-200 rounded-lg">
          <p className="text-xs text-emerald-700 font-medium">{result}</p>
        </div>
      )}

      {/* Action buttons */}
      <div className="space-y-3">
        <div>
          <button
            onClick={handleBackfill}
            disabled={running}
            className="w-full bg-teal-600 text-white font-medium px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm disabled:opacity-50"
          >
            {running ? "Running..." : "Run 3-Year Backfill"}
          </button>
          <p className="text-[11px] text-slate-400 mt-1">
            One-time: fetches 3 years of NAV history for all 535 funds + Nifty
            50. Takes ~5 minutes. Runs in background.
          </p>
        </div>

        <div>
          <button
            onClick={handleRefresh}
            disabled={running}
            className="w-full bg-slate-600 text-white font-medium px-4 py-2 rounded-lg hover:bg-slate-700 transition-colors text-sm disabled:opacity-50"
          >
            {running ? "Running..." : "Refresh (Daily)"}
          </button>
          <p className="text-[11px] text-slate-400 mt-1">
            Daily: fetches latest NAVs from AMFI bulk file + recomputes all
            pulse snapshots. Takes ~5 seconds. Runs in background.
          </p>
        </div>
      </div>
    </div>
  );
}
