"use client";

import { Fragment, useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { apiFetch } from "@/lib/api";
import { formatScore } from "@/lib/formatters";
import type { ApiResponse, FundScoreDetail } from "@/types/api";
import PageHeader from "@/components/PageHeader";
import TierBadge from "@/components/TierBadge";
import ActionBadge from "@/components/ActionBadge";
import SignalBadge from "@/components/SignalBadge";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import ErrorState from "@/components/ErrorState";

/** Horizons displayed in the metric breakdown table */
const HORIZONS = ["1y", "3y", "5y", "10y"] as const;

/** Pretty-print a metric key: "capture_down" -> "Capture Down" */
function formatMetricName(key: string): string {
  return key
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Confidence badge — color-coded HIGH/MEDIUM/LOW */
function ConfidenceBadge({ confidence }: { confidence: string }) {
  const styles: Record<string, string> = {
    HIGH: "bg-emerald-100 text-emerald-700",
    MEDIUM: "bg-amber-100 text-amber-700",
    LOW: "bg-slate-100 text-slate-600",
  };
  const style =
    styles[confidence.toUpperCase()] ?? "bg-slate-100 text-slate-600";
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium uppercase ${style}`}
    >
      {confidence}
    </span>
  );
}

export default function FundDetailPage() {
  const params = useParams<{ mstarId: string }>();
  const mstarId = params.mstarId;

  const [fund, setFund] = useState<FundScoreDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<ApiResponse<FundScoreDetail>>(
        `/api/v1/scores/${mstarId}`,
      );
      setFund(res.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load fund");
    } finally {
      setLoading(false);
    }
  }, [mstarId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /* ---------- Loading state ---------- */
  if (loading) {
    return (
      <div>
        <PageHeader
          emoji={"\uD83D\uDCC8"}
          title="Fund Detail"
          subtitle={mstarId}
        />
        <LoadingSkeleton variant="card" cardCount={3} />
        <div className="mt-6">
          <LoadingSkeleton variant="table" />
        </div>
      </div>
    );
  }

  /* ---------- Error / not-found state ---------- */
  if (error || !fund) {
    return (
      <div>
        <PageHeader
          emoji={"\uD83D\uDCC8"}
          title="Fund Detail"
          subtitle={mstarId}
        />
        <ErrorState
          message={error ?? "Fund not found"}
          onRetry={fetchData}
        />
      </div>
    );
  }

  /* ---------- Derived data ---------- */

  /* Sector contributions: convert object -> array for chart & table */
  const sectorArray = fund.fsas?.sector_contributions
    ? Object.entries(fund.fsas.sector_contributions).map(
        ([sector, sc]) => ({ sector, ...sc }),
      )
    : [];

  /* Sector data sorted by contribution (descending) for the chart */
  const sectorChartData = [...sectorArray].sort(
    (a, b) => b.contribution - a.contribution,
  );

  /* Metric scores: Object.keys gives all metric names */
  const metricNames = fund.qfs?.metric_scores
    ? Object.keys(fund.qfs.metric_scores)
    : [];

  /* Horizon score entries for the QFS card */
  const horizonScores: { label: string; value: number | null }[] = [
    { label: "1Y", value: fund.qfs?.score_1y ?? null },
    { label: "3Y", value: fund.qfs?.score_3y ?? null },
    { label: "5Y", value: fund.qfs?.score_5y ?? null },
    { label: "10Y", value: fund.qfs?.score_10y ?? null },
  ];

  /* Data completeness is already 0-100, no multiplication needed */
  const dataCompleteness = fund.qfs?.data_completeness_pct ?? 0;

  return (
    <div>
      <PageHeader
        emoji={"\uD83D\uDCC8"}
        title="Fund Detail"
        subtitle={fund.mstar_id}
      />

      {/* Back link */}
      <Link
        href="/funds"
        className="text-sm text-teal-600 hover:text-teal-700 mb-4 inline-block"
      >
        &larr; Back to Scoreboard
      </Link>

      {/* ---------------------------------------------------------------- */}
      {/*  Fund header card                                                */}
      {/* ---------------------------------------------------------------- */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-slate-800">
              {fund.mstar_id}
            </h2>
            <p className="text-sm text-slate-500 mt-0.5">
              Computed {fund.qfs?.computed_date ?? "--"}
            </p>
            <div className="flex items-center gap-3 mt-3">
              <TierBadge tier={fund.crs?.tier ?? "--"} />
              <ActionBadge action={fund.crs?.action ?? "--"} />
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs text-slate-400">Composite Recommendation Score</p>
            <p className="text-5xl font-bold font-mono text-teal-600">
              {formatScore(fund.crs?.crs)}
            </p>
            <p className="text-sm text-slate-400 font-mono">/100</p>
          </div>
        </div>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/*  Three score cards                                               */}
      {/* ---------------------------------------------------------------- */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* ---- Layer 1: Quantitative Fund Score ---- */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-800 mb-4">
            Layer 1: Quantitative Fund Score
          </h3>
          <div className="text-center mb-4">
            <span className="text-4xl font-bold font-mono text-teal-600">
              {formatScore(fund.qfs?.qfs)}
            </span>
            <span className="text-lg text-slate-400 font-mono">/100</span>
          </div>

          {/* Horizon scores */}
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Horizon Scores
          </p>
          <div className="space-y-2">
            {horizonScores.map((hs) => (
              <div
                key={hs.label}
                className="flex items-center justify-between"
              >
                <span className="text-sm text-slate-600">{hs.label}</span>
                <span className="text-sm font-mono font-semibold text-slate-800">
                  {formatScore(hs.value)}
                </span>
              </div>
            ))}
          </div>

          {/* Data completeness — value is already 0-100 */}
          <div className="mt-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-slate-500">Data Completeness</span>
              <span className="text-xs font-mono font-semibold text-slate-700">
                {Math.round(dataCompleteness)}%
              </span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${
                  dataCompleteness >= 80
                    ? "bg-emerald-500"
                    : dataCompleteness >= 60
                      ? "bg-amber-500"
                      : "bg-red-500"
                }`}
                style={{ width: `${Math.min(Math.round(dataCompleteness), 100)}%` }}
              />
            </div>
          </div>
        </div>

        {/* ---- Layer 2: Sector Alignment Score ---- */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-800 mb-4">
            Layer 2: Sector Alignment Score
          </h3>
          <div className="text-center mb-4">
            <span className="text-4xl font-bold font-mono text-teal-600">
              {formatScore(fund.fsas?.fsas)}
            </span>
            <span className="text-lg text-slate-400 font-mono">/100</span>
          </div>

          {/* Avoid exposure */}
          {fund.fsas && (
            <div className="mb-4">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500">Avoid Exposure</span>
                <span className="text-xs font-mono font-semibold text-red-600">
                  {fund.fsas.avoid_exposure_pct.toFixed(1)}%
                </span>
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-slate-500">Stale Holdings</span>
                <span
                  className={`text-xs font-bold uppercase px-2.5 py-0.5 rounded ${
                    fund.fsas.stale_holdings_flag
                      ? "bg-amber-100 text-amber-700"
                      : "bg-slate-100 text-slate-500"
                  }`}
                >
                  {fund.fsas.stale_holdings_flag ? "Yes" : "No"}
                </span>
              </div>
            </div>
          )}

          {/* Sector contribution chart */}
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Sector Contributions
          </p>
          {sectorChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={Math.max(180, sectorChartData.length * 28)}>
              <BarChart
                data={sectorChartData}
                layout="vertical"
                margin={{ left: 0, right: 10, top: 5, bottom: 5 }}
              >
                <XAxis type="number" hide />
                <YAxis
                  type="category"
                  dataKey="sector"
                  tick={{ fontSize: 10, fill: "#94a3b8" }}
                  width={90}
                />
                <Tooltip
                  contentStyle={{
                    borderRadius: "8px",
                    border: "1px solid #e2e8f0",
                    fontSize: "12px",
                  }}
                  formatter={(value) => [
                    typeof value === "number" ? value.toFixed(2) : String(value),
                    "Contribution",
                  ]}
                />
                <Bar dataKey="contribution" radius={[0, 4, 4, 0]}>
                  {sectorChartData.map((entry, idx) => (
                    <Cell
                      key={idx}
                      fill={entry.contribution >= 0 ? "#059669" : "#dc2626"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-slate-400 text-center py-6">
              No sector data available
            </p>
          )}
        </div>

        {/* ---- Layer 3: Composite Recommendation Score ---- */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-base font-semibold text-slate-800 mb-4">
            Layer 3: Composite Recommendation Score
          </h3>
          <div className="text-center mb-4">
            <span className="text-4xl font-bold font-mono text-teal-600">
              {formatScore(fund.crs?.crs)}
            </span>
            <span className="text-lg text-slate-400 font-mono">/100</span>
          </div>

          {/* Weights */}
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Score Composition
          </p>
          <div className="space-y-3">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-slate-600">Quantitative Score Weight</span>
                <span className="text-sm font-mono font-semibold text-slate-700">
                  {Math.round((fund.crs?.qfs_weight ?? 0) * 100)}%
                </span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2">
                <div
                  className="bg-teal-500 h-2 rounded-full"
                  style={{
                    width: `${Math.round((fund.crs?.qfs_weight ?? 0) * 100)}%`,
                  }}
                />
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-slate-600">Sector Alignment Weight</span>
                <span className="text-sm font-mono font-semibold text-slate-700">
                  {Math.round((fund.crs?.fsas_weight ?? 0) * 100)}%
                </span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full"
                  style={{
                    width: `${Math.round((fund.crs?.fsas_weight ?? 0) * 100)}%`,
                  }}
                />
              </div>
            </div>
          </div>

          {/* Override info */}
          <div className="mt-4 pt-4 border-t border-slate-100">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600">Override Applied</span>
              <span
                className={`text-xs font-bold uppercase px-2.5 py-0.5 rounded ${
                  fund.crs?.override_applied
                    ? "bg-amber-100 text-amber-700"
                    : "bg-slate-100 text-slate-500"
                }`}
              >
                {fund.crs?.override_applied ? "Yes" : "No"}
              </span>
            </div>
            {fund.crs?.override_reason && (
              <p className="text-xs text-slate-400 mt-1">
                {fund.crs.override_reason}
              </p>
            )}
          </div>

          {/* Action rationale */}
          {fund.crs?.action_rationale && (
            <div className="mt-4 pt-4 border-t border-slate-100">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                Action Rationale
              </p>
              <p className="text-xs text-slate-600 leading-relaxed">
                {fund.crs.action_rationale}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/*  Metric breakdown table                                          */}
      {/*  Rows = metric names, Columns = horizons (1y/3y/5y/10y)         */}
      {/*  Each horizon has Raw and Normalised sub-columns                 */}
      {/* ---------------------------------------------------------------- */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <h3 className="text-base font-semibold text-slate-800 mb-4">
          Metric Breakdown
        </h3>
        {metricNames.length === 0 ? (
          <p className="text-sm text-slate-400 text-center py-8">
            No metric data available
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
                  <th
                    rowSpan={2}
                    className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider align-bottom"
                  >
                    Metric
                  </th>
                  {HORIZONS.map((h) => (
                    <th
                      key={h}
                      colSpan={2}
                      className="text-center px-2 py-2 text-xs font-semibold text-slate-800 uppercase tracking-wider border-b border-slate-100"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
                <tr className="border-b border-slate-200">
                  {HORIZONS.map((h) => (
                    <Fragment key={h}>
                      <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400 tracking-wider">
                        Raw
                      </th>
                      <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400 tracking-wider">
                        Score
                      </th>
                    </Fragment>
                  ))}
                </tr>
              </thead>
              <tbody>
                {metricNames.map((metricKey) => {
                  const horizonData =
                    fund.qfs?.metric_scores?.[metricKey] ?? {};

                  return (
                    <tr
                      key={metricKey}
                      className="border-b border-slate-100 hover:bg-slate-50"
                    >
                      <td className="px-4 py-3 text-sm font-medium text-slate-800 whitespace-nowrap">
                        {formatMetricName(metricKey)}
                      </td>
                      {HORIZONS.map((h) => {
                        const cell = horizonData[h];
                        return (
                          <Fragment key={h}>
                            <td className="px-3 py-3 text-right text-sm font-mono text-slate-600">
                              {cell?.raw !== null && cell?.raw !== undefined
                                ? cell.raw.toFixed(2)
                                : "--"}
                            </td>
                            <td className="px-3 py-3 text-right text-sm font-mono text-slate-700">
                              {cell?.normalised !== null &&
                              cell?.normalised !== undefined
                                ? cell.normalised.toFixed(1)
                                : "--"}
                            </td>
                          </Fragment>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ---------------------------------------------------------------- */}
      {/*  Sector contribution detail table                                */}
      {/* ---------------------------------------------------------------- */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="text-base font-semibold text-slate-800 mb-4">
          Sector Contribution Detail
        </h3>
        {sectorArray.length === 0 ? (
          <p className="text-sm text-slate-400 text-center py-8">
            No sector contribution data available
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Sector
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Exposure %
                  </th>
                  <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Signal
                  </th>
                  <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Confidence
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Signal Wt
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Conf Multiplier
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Contribution
                  </th>
                </tr>
              </thead>
              <tbody>
                {sectorArray.map((sc) => (
                  <tr
                    key={sc.sector}
                    className="border-b border-slate-100 hover:bg-slate-50"
                  >
                    <td className="px-4 py-3 text-sm font-medium text-slate-800">
                      {sc.sector}
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                      {sc.exposure_pct.toFixed(1)}%
                    </td>
                    <td className="px-4 py-3 text-center">
                      <SignalBadge signal={sc.signal} />
                    </td>
                    <td className="px-4 py-3 text-center">
                      <ConfidenceBadge confidence={sc.confidence} />
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                      {sc.signal_weight.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                      {sc.confidence_multiplier.toFixed(1)}
                    </td>
                    <td
                      className={`px-4 py-3 text-right text-sm font-mono font-semibold ${
                        sc.contribution >= 0
                          ? "text-emerald-600"
                          : "text-red-600"
                      }`}
                    >
                      {sc.contribution >= 0 ? "+" : ""}
                      {sc.contribution.toFixed(2)}
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
