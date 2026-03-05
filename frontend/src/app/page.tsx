"use client";

import { useEffect, useState, useCallback } from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";
import { apiFetch } from "@/lib/api";
import { formatScore, formatDate, formatTimeAgo } from "@/lib/formatters";
import type {
  ApiResponse,
  FundScoreOverview,
  HealthReady,
} from "@/types/api";
import PageHeader from "@/components/PageHeader";
import StatCard from "@/components/StatCard";
import TierBadge from "@/components/TierBadge";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import ErrorState from "@/components/ErrorState";

/* Chart colours aligned with tier badges */
const TIER_COLORS: Record<string, string> = {
  CORE: "#059669",
  QUALITY: "#2563eb",
  WATCH: "#f59e0b",
  CAUTION: "#f97316",
  EXIT: "#dc2626",
};

interface TierCount {
  name: string;
  value: number;
}

interface TierActionRow {
  tier: string;
  buy: number;
  sip: number;
  hold_plus: number;
  hold: number;
  reduce: number;
  exit: number;
  total: number;
}

export default function DashboardPage() {
  const [funds, setFunds] = useState<FundScoreOverview[]>([]);
  const [health, setHealth] = useState<HealthReady | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [scoresRes, healthRes] = await Promise.all([
        apiFetch<ApiResponse<FundScoreOverview[]>>("/api/v1/scores/overview?limit=1000"),
        apiFetch<HealthReady>("/health/ready"),
      ]);

      setFunds(scoresRes.data ?? []);
      setHealth(healthRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /* ---- Derived metrics ---- */
  const totalFunds = funds.length;

  const avgQFS =
    funds.length > 0
      ? funds.reduce((sum, f) => sum + (f.qfs ?? 0), 0) / funds.length
      : 0;

  const coreCount = funds.filter(
    (f) => (f.tier ?? "").toUpperCase() === "CORE",
  ).length;
  const qualityCount = funds.filter(
    (f) => (f.tier ?? "").toUpperCase() === "QUALITY",
  ).length;
  const shortlistedCount = funds.filter(
    (f) => f.qfs_rank != null && f.qfs_rank <= 5,
  ).length;

  /* Data freshness from health checks */
  const morningstarFreshness =
    health?.checks?.data_freshness?.MORNINGSTAR_API;
  const dataFreshness = morningstarFreshness?.last_run
    ? formatTimeAgo(morningstarFreshness.last_run)
    : "--";

  /* Last scored date — most recent computed_date from funds */
  const lastScoredDate = funds.length > 0
    ? funds.reduce((latest, f) => {
        if (!f.computed_date) return latest;
        return f.computed_date > latest ? f.computed_date : latest;
      }, "")
    : null;

  /* Tier distribution for donut chart */
  const tierCounts: TierCount[] = (() => {
    const map: Record<string, number> = {};
    funds.forEach((f) => {
      const t = (f.tier ?? "UNSCORED").toUpperCase();
      map[t] = (map[t] ?? 0) + 1;
    });
    return Object.entries(map).map(([name, value]) => ({ name, value }));
  })();

  /* Tier x Action breakdown — v2 actions */
  const tierActionRows: TierActionRow[] = (() => {
    const map: Record<string, TierActionRow> = {};
    funds.forEach((f) => {
      const t = (f.tier ?? "UNSCORED").toUpperCase();
      if (!map[t]) {
        map[t] = { tier: t, buy: 0, sip: 0, hold_plus: 0, hold: 0, reduce: 0, exit: 0, total: 0 };
      }
      const a = (f.action ?? "").toUpperCase();
      if (a === "BUY") map[t].buy++;
      else if (a === "SIP") map[t].sip++;
      else if (a === "HOLD_PLUS") map[t].hold_plus++;
      else if (a === "HOLD") map[t].hold++;
      else if (a === "REDUCE") map[t].reduce++;
      else if (a === "EXIT") map[t].exit++;
      map[t].total++;
    });
    return Object.values(map);
  })();

  if (loading) {
    return (
      <div>
        <PageHeader
          emoji="📊"
          title="Dashboard"
          subtitle="MF Recommendation Engine"
        />
        <LoadingSkeleton variant="card" cardCount={6} />
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
          emoji="📊"
          title="Dashboard"
          subtitle="MF Recommendation Engine"
        />
        <ErrorState message={error} onRetry={fetchData} />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        emoji="📊"
        title="Dashboard"
        subtitle={
          lastScoredDate
            ? `MF Recommendation Engine · Last scored: ${formatDate(lastScoredDate)}`
            : "MF Recommendation Engine"
        }
      />

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard label="Total Funds" value={String(totalFunds)} colored />
        <StatCard
          label="Avg QFS"
          value={formatScore(avgQFS)}
          colored
        />
        <StatCard
          label="Shortlisted"
          value={String(shortlistedCount)}
          subtext="Top funds per category"
        />
        <StatCard
          label="Core Tier"
          value={String(coreCount)}
          subtext={`${totalFunds > 0 ? ((coreCount / totalFunds) * 100).toFixed(0) : 0}% of total`}
        />
        <StatCard
          label="Quality Tier"
          value={String(qualityCount)}
          subtext={`${totalFunds > 0 ? ((qualityCount / totalFunds) * 100).toFixed(0) : 0}% of total`}
        />
        <StatCard
          label="Last Scored"
          value={lastScoredDate ? formatDate(lastScoredDate) : "--"}
          subtext={`Data: ${dataFreshness}`}
        />
      </div>

      {/* Two-column section: donut + system health */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        {/* Tier distribution donut */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-800 mb-4">
            Tier Distribution
          </h3>
          {tierCounts.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-8">
              No scored funds yet
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={tierCounts}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={3}
                  dataKey="value"
                  nameKey="name"
                >
                  {tierCounts.map((entry) => (
                    <Cell
                      key={entry.name}
                      fill={TIER_COLORS[entry.name] ?? "#94a3b8"}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    borderRadius: "8px",
                    border: "1px solid #e2e8f0",
                    fontSize: "12px",
                  }}
                />
                <Legend
                  verticalAlign="middle"
                  align="right"
                  layout="vertical"
                  iconType="circle"
                  iconSize={10}
                  formatter={(value: string) => (
                    <span className="text-xs text-slate-600">{value}</span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* System health */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-800 mb-4">
            System Health
          </h3>
          {health ? (
            <div className="space-y-4">
              {/* Database status */}
              <div className="flex items-center justify-between py-3 border-b border-slate-100">
                <span className="text-sm text-slate-600">Database</span>
                <span
                  className={`text-xs font-bold uppercase px-2.5 py-0.5 rounded ${
                    health.checks.database.status === "ok"
                      ? "bg-emerald-100 text-emerald-700"
                      : "bg-red-100 text-red-700"
                  }`}
                >
                  {health.checks.database.status}
                </span>
              </div>

              {/* Scheduler status */}
              <div className="flex items-center justify-between py-3 border-b border-slate-100">
                <span className="text-sm text-slate-600">Scheduler</span>
                <span
                  className={`text-xs font-bold uppercase px-2.5 py-0.5 rounded ${
                    health.checks.scheduler.status === "running"
                      ? "bg-emerald-100 text-emerald-700"
                      : "bg-red-100 text-red-700"
                  }`}
                >
                  {health.checks.scheduler.status === "running"
                    ? "Running"
                    : "Stopped"}
                </span>
              </div>

              {/* Total funds scored (from live scores data) */}
              <div className="flex items-center justify-between py-3 border-b border-slate-100">
                <span className="text-sm text-slate-600">Total Funds Scored</span>
                <span className="text-sm font-mono font-semibold text-slate-800">
                  {funds.length}
                </span>
              </div>

              {/* Last ingestion run */}
              <div className="flex items-center justify-between py-3 border-b border-slate-100">
                <span className="text-sm text-slate-600">
                  Last Ingestion
                </span>
                <span className="text-xs text-slate-400">
                  {formatDate(morningstarFreshness?.last_run)}
                </span>
              </div>

              {/* Morningstar API status */}
              <div className="flex items-center justify-between py-3">
                <span className="text-sm text-slate-600">
                  Morningstar Feed
                </span>
                <span
                  className={`text-xs font-bold uppercase px-2.5 py-0.5 rounded ${
                    morningstarFreshness?.is_stale
                      ? "bg-amber-100 text-amber-700"
                      : "bg-emerald-100 text-emerald-700"
                  }`}
                >
                  {morningstarFreshness?.is_stale ? "Stale" : "Fresh"}
                </span>
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
      </div>

      {/* Tier x Action breakdown table — v2 actions */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mt-6">
        <h3 className="text-base font-semibold text-slate-800 mb-4">
          Tier &times; Action Breakdown
        </h3>
        {tierActionRows.length === 0 ? (
          <p className="text-sm text-slate-400 text-center py-8">
            No scored funds yet
          </p>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Tier
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  BUY
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  SIP
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  HOLD+
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  HOLD
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  REDUCE
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  EXIT
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Total
                </th>
              </tr>
            </thead>
            <tbody>
              {tierActionRows.map((row) => (
                <tr
                  key={row.tier}
                  className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
                >
                  <td className="px-4 py-3">
                    <TierBadge tier={row.tier} />
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                    {row.buy || "--"}
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                    {row.sip || "--"}
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                    {row.hold_plus || "--"}
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                    {row.hold || "--"}
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                    {row.reduce || "--"}
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                    {row.exit || "--"}
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-mono font-semibold text-slate-800">
                    {row.total}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
