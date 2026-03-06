"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { apiFetch } from "@/lib/api";
import { formatTimeAgo } from "@/lib/formatters";
import type {
  ApiResponse,
  BenchmarkWeightsResponse,
  BenchmarkWeightItem,
  BenchmarkRefreshResponse,
} from "@/types/api";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";

/* ------------------------------------------------------------------ */
/*  BenchmarkWeightsCard                                               */
/*  Read-only card showing NIFTY 50 sector weights used for FSAS.      */
/* ------------------------------------------------------------------ */

export default function BenchmarkWeightsCard() {
  /* ---------- Data state ---------- */
  const [data, setData] = useState<BenchmarkWeightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* ---------- Refresh state ---------- */
  const [refreshing, setRefreshing] = useState(false);
  const [refreshResult, setRefreshResult] = useState<{
    message: string;
    type: "success" | "error";
  } | null>(null);

  /* ---------------------------------------------------------------- */
  /*  Fetch benchmark weights                                          */
  /* ---------------------------------------------------------------- */

  const fetchWeights = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<ApiResponse<BenchmarkWeightsResponse>>(
        "/api/v1/benchmarks",
      );
      setData(res.data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load benchmark weights",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWeights();
  }, [fetchWeights]);

  /* ---------------------------------------------------------------- */
  /*  Refresh from Morningstar                                         */
  /* ---------------------------------------------------------------- */

  async function handleRefresh() {
    setRefreshing(true);
    setRefreshResult(null);
    try {
      const res = await apiFetch<ApiResponse<BenchmarkRefreshResponse>>(
        "/api/v1/benchmarks/refresh",
        { method: "POST" },
      );
      const sectorCount = res.data?.sector_count ?? 0;
      setRefreshResult({
        message: `Refreshed ${sectorCount} sector weights from Morningstar.`,
        type: "success",
      });
      // Re-fetch to show updated data
      await fetchWeights();
    } catch (err) {
      setRefreshResult({
        message:
          err instanceof Error
            ? err.message
            : "Failed to refresh benchmark weights",
        type: "error",
      });
    } finally {
      setRefreshing(false);
    }
  }

  /* ---------------------------------------------------------------- */
  /*  Auto-dismiss refresh result after 5 seconds                      */
  /* ---------------------------------------------------------------- */

  useEffect(() => {
    if (!refreshResult) return;
    const timer = setTimeout(() => setRefreshResult(null), 5000);
    return () => clearTimeout(timer);
  }, [refreshResult]);

  /* ---------------------------------------------------------------- */
  /*  Sort sectors by weight descending                                */
  /* ---------------------------------------------------------------- */

  const sortedSectors = useMemo<BenchmarkWeightItem[]>(() => {
    if (!data?.sectors) return [];
    return [...data.sectors].sort((a, b) => b.weight_pct - a.weight_pct);
  }, [data]);

  const totalWeight = useMemo(() => {
    return sortedSectors.reduce((sum, s) => sum + s.weight_pct, 0);
  }, [sortedSectors]);

  /* ---------------------------------------------------------------- */
  /*  Loading state                                                    */
  /* ---------------------------------------------------------------- */

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="h-5 w-72 bg-slate-100 animate-pulse rounded mb-4" />
        <LoadingSkeleton variant="table" />
      </div>
    );
  }

  /* ---------------------------------------------------------------- */
  /*  Error state                                                      */
  /* ---------------------------------------------------------------- */

  if (error) {
    return <ErrorState message={error} onRetry={fetchWeights} />;
  }

  /* ---------------------------------------------------------------- */
  /*  Empty state                                                      */
  /* ---------------------------------------------------------------- */

  if (!data || sortedSectors.length === 0) {
    return (
      <EmptyState
        title="No benchmark weights found"
        description="NIFTY 50 sector weights have not been fetched yet. Refresh from Morningstar to populate."
        actionLabel="Refresh from Morningstar"
        onAction={handleRefresh}
      />
    );
  }

  /* ---------------------------------------------------------------- */
  /*  Main render                                                      */
  /* ---------------------------------------------------------------- */

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      {/* Header row: title + meta + refresh button */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-base font-semibold text-slate-800">
            NIFTY 50 Benchmark Sector Weights
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Used as the reference benchmark for FM Sector Alignment Score
            (FSAS) calculation
          </p>
        </div>
        <div className="flex items-center gap-3">
          {data.last_fetched && (
            <span className="text-xs text-slate-400">
              Last fetched: {formatTimeAgo(data.last_fetched)}
            </span>
          )}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            aria-label="Refresh benchmark weights from Morningstar"
            className="bg-white text-slate-600 font-medium px-4 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {refreshing ? (
              <>
                <svg
                  className="w-4 h-4 animate-spin text-slate-400"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Refreshing...
              </>
            ) : (
              <>
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                Refresh from Morningstar
              </>
            )}
          </button>
        </div>
      </div>

      {/* Refresh result toast */}
      {refreshResult && (
        <div
          className={`mb-4 px-4 py-2.5 rounded-lg text-sm font-medium ${
            refreshResult.type === "success"
              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
              : "bg-red-50 text-red-700 border border-red-200"
          }`}
        >
          {refreshResult.message}
        </div>
      )}

      {/* Sector weights table */}
      <table className="w-full">
        <thead>
          <tr className="border-b border-slate-200">
            <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Sector
            </th>
            <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Weight %
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedSectors.map((sector) => (
            <tr
              key={sector.sector_name}
              className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
            >
              <td className="px-4 py-3 text-sm text-slate-700">
                {sector.sector_name}
              </td>
              <td className="px-4 py-3 text-right text-sm font-mono tabular-nums text-slate-700">
                {sector.weight_pct.toFixed(1)}%
              </td>
            </tr>
          ))}

          {/* Total row */}
          <tr className="border-t-2 border-slate-300 bg-slate-50">
            <td className="px-4 py-3 text-sm font-semibold text-slate-800">
              Total
            </td>
            <td className="px-4 py-3 text-right text-sm font-mono tabular-nums font-semibold text-slate-800">
              {totalWeight.toFixed(1)}%
            </td>
          </tr>
        </tbody>
      </table>

      {/* Footer metadata */}
      <div className="mt-3 flex items-center gap-4 text-xs text-slate-400">
        <span>
          {data.sector_count} sector{data.sector_count !== 1 ? "s" : ""}
        </span>
        {data.benchmark_name && (
          <span>Benchmark: {data.benchmark_name}</span>
        )}
      </div>
    </div>
  );
}
