"use client";

import { useEffect, useState, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { formatDate, formatTimeAgo } from "@/lib/formatters";
import type {
  ApiResponse,
  HealthReady,
  DataFreshnessEntry,
  IngestionLog,
  ScoreComputeResult,
  ScoreComputePayload,
} from "@/types/api";
import PageHeader from "@/components/PageHeader";
import StatCard from "@/components/StatCard";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import ErrorState from "@/components/ErrorState";

type LayerValue = "qfs" | "fsas" | "all";

const LAYER_OPTIONS: { value: LayerValue; label: string }[] = [
  { value: "all", label: "Full Pipeline (QFS → Shortlist → FSAS → Recommend)" },
  { value: "qfs", label: "Layer 1 — Quantitative Fund Score" },
  { value: "fsas", label: "Layer 2 — Sector Alignment Score (Shortlisted Only)" },
];

/**
 * Calculate duration in human-readable form from two ISO timestamps.
 */
function formatDuration(
  startIso: string | null | undefined,
  endIso: string | null | undefined,
): string {
  if (!startIso || !endIso) return "--";
  const start = new Date(startIso).getTime();
  const end = new Date(endIso).getTime();
  const diffMs = end - start;
  if (diffMs < 0) return "--";
  if (diffMs < 1000) return `${diffMs}ms`;
  const seconds = diffMs / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainSec = Math.round(seconds % 60);
  return `${minutes}m ${remainSec}s`;
}

/**
 * Friendly display name for data feed keys.
 */
function feedDisplayName(key: string): string {
  const map: Record<string, string> = {
    MORNINGSTAR_API: "Morningstar API",
    JHV_MASTER: "JHV Master Data",
    MONTHLY_RECOMPUTE: "Monthly Recompute",
  };
  return map[key] ?? key;
}

export default function SystemPage() {
  const [health, setHealth] = useState<HealthReady | null>(null);
  const [logs, setLogs] = useState<IngestionLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* Ingestion form */
  const [ingestIds, setIngestIds] = useState("");
  const [ingesting, setIngesting] = useState(false);
  const [ingestResult, setIngestResult] = useState<string | null>(null);
  const [ingestError, setIngestError] = useState<string | null>(null);

  /* Score compute form */
  const [selectedLayer, setSelectedLayer] = useState<LayerValue>("all");
  const [categoryName, setCategoryName] = useState("");
  const [computing, setComputing] = useState(false);
  const [computeResult, setComputeResult] =
    useState<ScoreComputeResult | null>(null);
  const [computeError, setComputeError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthRes, logsRes] = await Promise.all([
        apiFetch<HealthReady>("/health/ready"),
        apiFetch<ApiResponse<IngestionLog[]>>("/api/v1/ingest/logs"),
      ]);
      setHealth(healthRes);
      setLogs(logsRes.data ?? []);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load system data",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /* Handle ingestion */
  async function handleIngest(e: React.FormEvent) {
    e.preventDefault();
    setIngestError(null);
    setIngestResult(null);

    const ids = ingestIds
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    if (ids.length === 0) {
      setIngestError("Enter at least one Morningstar ID");
      return;
    }

    setIngesting(true);
    try {
      const res = await apiFetch<ApiResponse<{ message: string }>>(
        "/api/v1/ingest/morningstar",
        {
          method: "POST",
          body: JSON.stringify({ mstar_ids: ids }),
        },
      );
      setIngestResult(
        res.data?.message ?? `Ingestion triggered for ${ids.length} fund(s)`,
      );
      setIngestIds("");
      await fetchData();
    } catch (err) {
      setIngestError(
        err instanceof Error ? err.message : "Ingestion failed",
      );
    } finally {
      setIngesting(false);
    }
  }

  /* Handle score compute */
  async function handleCompute(e: React.FormEvent) {
    e.preventDefault();
    setComputeError(null);
    setComputeResult(null);

    setComputing(true);
    try {
      const payload: ScoreComputePayload = {
        layer: selectedLayer,
        trigger_event: "manual_compute",
      };
      const trimmedCategory = categoryName.trim();
      if (trimmedCategory) {
        payload.category_name = trimmedCategory;
      }

      const res = await apiFetch<ApiResponse<ScoreComputeResult>>(
        "/api/v1/scores/compute",
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
      );
      setComputeResult(res.data ?? null);
      setCategoryName("");
      await fetchData();
    } catch (err) {
      setComputeError(
        err instanceof Error ? err.message : "Compute failed",
      );
    } finally {
      setComputing(false);
    }
  }

  /* Derived values from health */
  const dbOk = health?.checks.database.status === "ok";
  const schedulerRunning = health?.checks.scheduler.status === "running";
  const schedulerJobs = health?.checks.scheduler.jobs ?? [];
  const dataFeeds = health?.checks.data_freshness
    ? Object.entries(health.checks.data_freshness)
    : [];
  const morningstarFeed = health?.checks.data_freshness?.MORNINGSTAR_API;
  const warnings = health?.warnings ?? [];

  if (loading) {
    return (
      <div>
        <PageHeader
          emoji="&#x2699;&#xFE0F;"
          title="System"
          subtitle="Administration & monitoring"
        />
        <LoadingSkeleton variant="card" cardCount={4} />
        <div className="mt-6">
          <LoadingSkeleton variant="table" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <PageHeader
          emoji="&#x2699;&#xFE0F;"
          title="System"
          subtitle="Administration & monitoring"
        />
        <ErrorState message={error} onRetry={fetchData} />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        emoji="&#x2699;&#xFE0F;"
        title="System"
        subtitle="Administration & monitoring"
      />

      {/* Warnings banner */}
      {warnings.length > 0 && (
        <div className="mb-6 bg-amber-50 border border-amber-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <span className="text-amber-600 text-lg leading-none mt-0.5">
              &#x26A0;&#xFE0F;
            </span>
            <div>
              <p className="text-sm font-semibold text-amber-800">
                System Warnings ({warnings.length})
              </p>
              <ul className="mt-1 space-y-0.5">
                {warnings.map((warning, idx) => (
                  <li key={idx} className="text-sm text-amber-700">
                    {warning}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Overall status badge */}
      {health && (
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
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Database"
          value={dbOk ? "OK" : "Error"}
          colored={dbOk}
          alert={!dbOk}
        />
        <StatCard
          label="Scheduler"
          value={schedulerRunning ? "Running" : "Stopped"}
          subtext={
            schedulerRunning
              ? `${health?.checks.scheduler.job_count ?? 0} jobs`
              : undefined
          }
          colored={schedulerRunning}
          alert={!schedulerRunning}
        />
        <StatCard
          label="Funds Ingested"
          value={String(morningstarFeed?.records_total ?? 0)}
          subtext={
            morningstarFeed?.last_run
              ? `Last: ${formatTimeAgo(morningstarFeed.last_run)}`
              : "Never run"
          }
          colored
        />
        <StatCard
          label="Data Feeds"
          value={`${dataFeeds.length}`}
          subtext={`${dataFeeds.filter(([, f]) => f.is_stale).length} stale`}
          colored={dataFeeds.every(([, f]) => !f.is_stale)}
          alert={dataFeeds.some(([, f]) => f.is_stale)}
        />
      </div>

      {/* Data Freshness + Scheduler */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Data freshness — iterate all feeds */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-800 mb-4">
            Data Freshness
          </h3>
          {dataFeeds.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-4">
              No data feeds configured
            </p>
          ) : (
            <div className="space-y-1">
              {dataFeeds.map(([feedKey, feed]: [string, DataFreshnessEntry]) => (
                <div
                  key={feedKey}
                  className="flex items-center justify-between py-3 border-b border-slate-100 last:border-0"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-800">
                      {feedDisplayName(feedKey)}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                      {/* Status badge */}
                      <span
                        className={`inline-block rounded px-2 py-0.5 text-xs font-bold uppercase ${
                          feed.last_status === "SUCCESS" ||
                          feed.status === undefined
                            ? feed.is_stale
                              ? "bg-amber-100 text-amber-700"
                              : "bg-emerald-100 text-emerald-700"
                            : feed.status === "never_run"
                              ? "bg-slate-100 text-slate-500"
                              : "bg-red-100 text-red-700"
                        }`}
                      >
                        {feed.last_status ??
                          feed.status ??
                          (feed.is_stale ? "STALE" : "OK")}
                      </span>
                      {feed.is_stale && feed.last_status === "SUCCESS" && (
                        <span className="text-xs text-amber-600 font-medium">
                          Stale
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-right shrink-0 ml-4">
                    {feed.last_run ? (
                      <>
                        <p className="text-sm text-slate-700">
                          {formatDate(feed.last_run)}
                        </p>
                        <p className="text-xs text-slate-400">
                          {formatTimeAgo(feed.last_run)}
                          {feed.age_hours !== undefined && (
                            <span>
                              {" "}
                              &middot; {feed.age_hours.toFixed(1)}h old
                            </span>
                          )}
                        </p>
                        {feed.records_total !== undefined && (
                          <p className="text-xs text-slate-400 font-mono">
                            {feed.records_succeeded ?? 0}/
                            {feed.records_total} succeeded
                          </p>
                        )}
                      </>
                    ) : (
                      <p className="text-sm text-slate-400 italic">
                        Never run
                      </p>
                    )}
                    <p className="text-xs text-slate-300 mt-0.5">
                      Threshold: {feed.threshold_hours}h
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Scheduler jobs */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-800 mb-4">
            Scheduled Jobs
          </h3>
          {schedulerJobs.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-4">
              No scheduled jobs
            </p>
          ) : (
            <div className="space-y-2">
              {schedulerJobs.map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0"
                >
                  <div>
                    <p className="text-sm font-medium text-slate-800">
                      {job.name}
                    </p>
                    <p className="text-xs text-slate-400 font-mono">
                      {job.id}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-500">Next run</p>
                    <p className="text-xs font-mono text-slate-700">
                      {formatDate(job.next_run)}
                    </p>
                    {job.pending && (
                      <span className="inline-block mt-0.5 rounded px-2 py-0.5 text-xs font-bold bg-amber-100 text-amber-700 uppercase">
                        Pending
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Manual operations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Manual ingestion */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-800 mb-2">
            Manual Ingestion
          </h3>
          <p className="text-xs text-slate-400 mb-4">
            Enter Morningstar IDs (comma-separated) to trigger data ingestion
          </p>
          <form onSubmit={handleIngest}>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">
                Morningstar IDs
              </label>
              <input
                type="text"
                value={ingestIds}
                onChange={(e) => setIngestIds(e.target.value)}
                placeholder="e.g. F00000XYZR, F00000ABCD"
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
              />
            </div>
            {ingestError && (
              <p className="text-xs text-red-600 mt-2">{ingestError}</p>
            )}
            {ingestResult && (
              <p className="text-xs text-emerald-600 mt-2">{ingestResult}</p>
            )}
            <button
              type="submit"
              disabled={ingesting}
              className="mt-3 bg-teal-600 text-white font-medium px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm disabled:opacity-50"
            >
              {ingesting ? "Ingesting..." : "Trigger Ingestion"}
            </button>
          </form>
        </div>

        {/* Manual score compute */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-800 mb-2">
            Manual Score Compute
          </h3>
          <p className="text-xs text-slate-400 mb-4">
            Select a scoring layer to run. Optionally filter by category name.
          </p>
          <form onSubmit={handleCompute}>
            {/* Layer radio buttons */}
            <div className="mb-3">
              <label className="text-xs text-slate-500 mb-2 block">
                Layer
              </label>
              <div className="space-y-2">
                {LAYER_OPTIONS.map((opt) => (
                  <label
                    key={opt.value}
                    className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer"
                  >
                    <input
                      type="radio"
                      name="compute-layer"
                      value={opt.value}
                      checked={selectedLayer === opt.value}
                      onChange={() => setSelectedLayer(opt.value)}
                      className="border-slate-300 text-teal-600 focus:ring-teal-500"
                    />
                    {opt.label}
                  </label>
                ))}
              </div>
            </div>

            <div>
              <label className="text-xs text-slate-500 mb-1 block">
                Category Name (optional)
              </label>
              <input
                type="text"
                value={categoryName}
                onChange={(e) => setCategoryName(e.target.value)}
                placeholder="e.g. ELSS (Tax Savings) — leave blank for all"
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
              />
            </div>

            {computeError && (
              <p className="text-xs text-red-600 mt-2">{computeError}</p>
            )}
            {computeResult && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 mt-2">
                <p className="text-xs text-emerald-700 font-medium">
                  Computed {computeResult.total_funds_computed} funds across{" "}
                  {computeResult.total_categories} categories
                </p>
                {computeResult.results.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {computeResult.results.map((cat, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between text-xs"
                      >
                        <span className="text-emerald-700">{cat.category}</span>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-emerald-600">
                            {cat.fund_count} funds
                          </span>
                          <span
                            className={`inline-block rounded px-1.5 py-0.5 font-bold uppercase ${
                              cat.status === "completed"
                                ? "bg-emerald-100 text-emerald-700"
                                : "bg-red-100 text-red-700"
                            }`}
                          >
                            {cat.status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <button
              type="submit"
              disabled={computing}
              className="mt-3 bg-teal-600 text-white font-medium px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm disabled:opacity-50"
            >
              {computing ? "Computing..." : "Run Score Compute"}
            </button>
          </form>
        </div>
      </div>

      {/* Ingestion logs */}
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
                  <tr
                    key={log.id}
                    className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
                  >
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
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
