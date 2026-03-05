"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { apiFetch } from "@/lib/api";
import { formatScore, formatDate } from "@/lib/formatters";
import type {
  ApiResponse,
  ShortlistItem,
  AlignmentSummary,
  SectorAlignmentEntry,
} from "@/types/api";
import PageHeader from "@/components/PageHeader";
import TierBadge from "@/components/TierBadge";
import ActionBadge from "@/components/ActionBadge";
import SignalBadge from "@/components/SignalBadge";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";

/* ------------------------------------------------------------------ */
/*  Helper: score color class based on threshold                       */
/* ------------------------------------------------------------------ */
function scoreColorClass(score: number | null): string {
  if (score === null || score === undefined) return "text-slate-400";
  if (score >= 70) return "text-emerald-600";
  if (score >= 40) return "text-slate-600";
  return "text-red-600";
}

/* ------------------------------------------------------------------ */
/*  Helper: avoid exposure color class                                 */
/* ------------------------------------------------------------------ */
function avoidExposureClass(pct: number | null): string {
  if (pct === null || pct === undefined) return "text-slate-400";
  if (pct >= 15) return "text-red-600 font-semibold";
  return "text-slate-500";
}

/* ------------------------------------------------------------------ */
/*  Helper: group funds by category (preserving sort order within)     */
/* ------------------------------------------------------------------ */
interface CategoryGroup {
  category: string;
  funds: ShortlistItem[];
}

function groupByCategory(funds: ShortlistItem[]): CategoryGroup[] {
  const map = new Map<string, ShortlistItem[]>();
  for (const fund of funds) {
    const cat = fund.category_name || "Uncategorized";
    if (!map.has(cat)) {
      map.set(cat, []);
    }
    map.get(cat)!.push(fund);
  }

  // Sort categories alphabetically, then within each keep QFS descending
  const groups: CategoryGroup[] = [];
  const sortedKeys = Array.from(map.keys()).sort((a, b) =>
    a.localeCompare(b),
  );
  for (const key of sortedKeys) {
    const catFunds = map.get(key)!;
    catFunds.sort((a, b) => (b.qfs_score ?? 0) - (a.qfs_score ?? 0));
    groups.push({ category: key, funds: catFunds });
  }
  return groups;
}

/* ------------------------------------------------------------------ */
/*  Helper: extract top aligned sector names                           */
/* ------------------------------------------------------------------ */
function topAlignedSectorNames(
  summary: AlignmentSummary | null,
): string {
  if (!summary || !summary.top_aligned || summary.top_aligned.length === 0) {
    return "--";
  }
  return summary.top_aligned
    .slice(0, 3)
    .map((s) => s.sector)
    .join(", ");
}

/* ------------------------------------------------------------------ */
/*  Expanded row detail — sector alignment breakdown                   */
/* ------------------------------------------------------------------ */
function AlignmentDetail({
  summary,
  rationale,
}: {
  summary: AlignmentSummary;
  rationale: string | null;
}) {
  return (
    <tr>
      <td colSpan={10} className="p-0">
        <div className="bg-slate-50 border-l-4 border-l-teal-500 p-6">
          {/* Action rationale */}
          {rationale && (
            <p className="text-sm text-slate-600 mb-4 italic">
              {rationale}
            </p>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Aligned sectors */}
            <div>
              <h4 className="text-sm font-semibold text-emerald-700 mb-3 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                Aligned Sectors
              </h4>
              {summary.aligned_sectors.length === 0 ? (
                <p className="text-xs text-slate-400">
                  No aligned sectors for this fund.
                </p>
              ) : (
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="text-left px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Sector
                      </th>
                      <th className="text-center px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Signal
                      </th>
                      <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Exposure
                      </th>
                      <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Contribution
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.aligned_sectors.map((entry) => (
                      <tr
                        key={entry.sector}
                        className="border-b border-slate-100"
                      >
                        <td className="px-3 py-2 text-sm text-slate-700">
                          {entry.sector}
                        </td>
                        <td className="px-3 py-2 text-center">
                          <SignalBadge signal={entry.signal} />
                        </td>
                        <td className="px-3 py-2 text-right text-sm font-mono text-slate-600">
                          {entry.exposure_pct.toFixed(1)}%
                        </td>
                        <td className="px-3 py-2 text-right text-sm font-mono text-emerald-600">
                          +{entry.contribution.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* Misaligned sectors */}
            <div>
              <h4 className="text-sm font-semibold text-red-600 mb-3 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-red-500" />
                Misaligned Sectors
              </h4>
              {summary.misaligned_sectors.length === 0 ? (
                <p className="text-xs text-slate-400">
                  No misaligned sectors for this fund.
                </p>
              ) : (
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="text-left px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Sector
                      </th>
                      <th className="text-center px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Signal
                      </th>
                      <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Exposure
                      </th>
                      <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Contribution
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.misaligned_sectors.map((entry) => (
                      <tr
                        key={entry.sector}
                        className="border-b border-slate-100"
                      >
                        <td className="px-3 py-2 text-sm text-slate-700">
                          {entry.sector}
                        </td>
                        <td className="px-3 py-2 text-center">
                          <SignalBadge signal={entry.signal} />
                        </td>
                        <td className="px-3 py-2 text-right text-sm font-mono text-slate-600">
                          {entry.exposure_pct.toFixed(1)}%
                        </td>
                        <td className="px-3 py-2 text-right text-sm font-mono text-red-600">
                          {entry.contribution.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          {/* Neutral sectors (if any) */}
          {summary.neutral_sectors.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-200">
              <p className="text-xs text-slate-400">
                <span className="font-semibold text-slate-500">
                  Neutral sectors:{" "}
                </span>
                {summary.neutral_sectors.join(", ")}
              </p>
            </div>
          )}
        </div>
      </td>
    </tr>
  );
}

/* ------------------------------------------------------------------ */
/*  Page component                                                     */
/* ------------------------------------------------------------------ */
export default function ShortlistPage() {
  /* ----- data state ----- */
  const [funds, setFunds] = useState<ShortlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* ----- UI state ----- */
  const [expandedId, setExpandedId] = useState<string | null>(null);

  /* ----- fetch shortlisted funds ----- */
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<ApiResponse<ShortlistItem[]>>(
        "/api/v1/scores/shortlist",
      );
      setFunds(res.data ?? []);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load shortlist",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /* ----- derived stats ----- */
  const stats = useMemo(() => {
    const totalFunds = funds.length;

    const categoriesSet = new Set(
      funds.map((f) => f.category_name),
    );
    const categoriesCovered = categoriesSet.size;

    const qfsScores = funds
      .map((f) => f.qfs_score)
      .filter((s): s is number => s !== null && s !== undefined);
    const avgQfs =
      qfsScores.length > 0
        ? qfsScores.reduce((sum, s) => sum + s, 0) / qfsScores.length
        : 0;

    const fundsWithFsas = funds.filter(
      (f) => f.fsas !== null && f.fsas !== undefined,
    ).length;

    return { totalFunds, categoriesCovered, avgQfs, fundsWithFsas };
  }, [funds]);

  /* ----- grouped data ----- */
  const categoryGroups = useMemo(() => groupByCategory(funds), [funds]);

  /* ----- row expand toggle ----- */
  function toggleExpand(mstarId: string) {
    setExpandedId((prev) => (prev === mstarId ? null : mstarId));
  }

  /* ----- loading state ----- */
  if (loading) {
    return (
      <div>
        <PageHeader
          emoji="⭐"
          title="Shortlisted Funds"
          subtitle="Top funds per category — FM recommendation output"
        />
        <LoadingSkeleton variant="card" cardCount={4} />
        <div className="mt-6">
          <LoadingSkeleton variant="table" />
        </div>
      </div>
    );
  }

  /* ----- error state ----- */
  if (error) {
    return (
      <div>
        <PageHeader
          emoji="⭐"
          title="Shortlisted Funds"
          subtitle="Top funds per category — FM recommendation output"
        />
        <ErrorState message={error} onRetry={fetchData} />
      </div>
    );
  }

  /* ----- empty state ----- */
  if (funds.length === 0) {
    return (
      <div>
        <PageHeader
          emoji="⭐"
          title="Shortlisted Funds"
          subtitle="Top funds per category — FM recommendation output"
        />
        <EmptyState
          title="No shortlisted funds yet"
          description="Run the scoring engine with FM signals to generate shortlisted fund recommendations."
        />
      </div>
    );
  }

  /* ----- global row counter across category groups ----- */
  let globalIndex = 0;

  /* ----- success state ----- */
  return (
    <div>
      <PageHeader
        emoji="⭐"
        title="Shortlisted Funds"
        subtitle={`Top funds per category — FM recommendation output${funds.length > 0 && funds[0].computed_date ? ` · Scored: ${formatDate(funds[0].computed_date)}` : ""}`}
      />

      {/* Summary stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-sm text-slate-500">Total Shortlisted</p>
          <p className="text-2xl font-bold font-mono text-teal-600 mt-1">
            {stats.totalFunds}
          </p>
          <p className="text-xs text-slate-400 mt-1">Funds recommended</p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-sm text-slate-500">Categories Covered</p>
          <p className="text-2xl font-bold font-mono text-slate-800 mt-1">
            {stats.categoriesCovered}
          </p>
          <p className="text-xs text-slate-400 mt-1">SEBI categories</p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-sm text-slate-500">Average QFS</p>
          <p className="text-2xl font-bold font-mono text-teal-600 mt-1">
            {stats.avgQfs.toFixed(1)}
          </p>
          <p className="text-xs text-slate-400 mt-1">
            Across shortlisted funds
          </p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-sm text-slate-500">Funds with FSAS</p>
          <p className="text-2xl font-bold font-mono text-slate-800 mt-1">
            {stats.fundsWithFsas}
          </p>
          <p className="text-xs text-slate-400 mt-1">
            Sector alignment scored
          </p>
        </div>
      </div>

      {/* Main table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider w-10">
                  #
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Fund Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Category
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  QFS
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  QFS Rank
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  FSAS
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Tier
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Action
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Top Aligned Sectors
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Avoid Exp %
                </th>
              </tr>
            </thead>
            <tbody>
              {categoryGroups.map((group) => {
                const rows: React.ReactNode[] = [];

                {/* Category separator row */}
                rows.push(
                  <tr key={`cat-${group.category}`}>
                    <td
                      colSpan={10}
                      className="bg-slate-50 px-4 py-2.5 font-semibold text-slate-600 text-sm border-b border-slate-200"
                    >
                      {group.category}
                      <span className="ml-2 text-xs font-normal text-slate-400">
                        ({group.funds.length}{" "}
                        {group.funds.length === 1 ? "fund" : "funds"})
                      </span>
                    </td>
                  </tr>,
                );

                {/* Fund rows within this category */}
                for (const fund of group.funds) {
                  globalIndex += 1;
                  const isExpanded = expandedId === fund.mstar_id;
                  const hasAlignment = fund.alignment_summary !== null;

                  rows.push(
                    <tr
                      key={fund.mstar_id}
                      onClick={
                        hasAlignment
                          ? () => toggleExpand(fund.mstar_id)
                          : undefined
                      }
                      className={`border-b border-slate-100 transition-colors ${
                        hasAlignment
                          ? "cursor-pointer hover:bg-slate-50"
                          : ""
                      } ${isExpanded ? "bg-teal-50/40" : ""}`}
                    >
                      {/* Row number */}
                      <td className="px-4 py-3 text-sm text-slate-400 font-mono tabular-nums">
                        {globalIndex}
                      </td>

                      {/* Fund Name */}
                      <td className="px-4 py-3 text-sm font-medium text-slate-800">
                        <div className="flex items-center gap-2">
                          {fund.fund_name ?? fund.mstar_id}
                          {hasAlignment && (
                            <span
                              className={`text-slate-400 text-xs transition-transform ${
                                isExpanded ? "rotate-90" : ""
                              }`}
                            >
                              &#9654;
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Category */}
                      <td className="px-4 py-3 text-sm text-slate-500">
                        {fund.category_name}
                      </td>

                      {/* QFS */}
                      <td
                        className={`px-4 py-3 text-right text-sm font-mono tabular-nums font-semibold ${scoreColorClass(
                          fund.qfs_score,
                        )}`}
                      >
                        {formatScore(fund.qfs_score)}
                      </td>

                      {/* QFS Rank */}
                      <td className="px-4 py-3 text-right text-sm font-mono tabular-nums text-slate-600">
                        {fund.qfs_rank}/{fund.total_in_category}
                      </td>

                      {/* FSAS */}
                      <td
                        className={`px-4 py-3 text-right text-sm font-mono tabular-nums font-semibold ${scoreColorClass(
                          fund.fsas,
                        )}`}
                      >
                        {formatScore(fund.fsas)}
                      </td>

                      {/* Tier */}
                      <td className="px-4 py-3 text-center">
                        {fund.tier ? (
                          <TierBadge tier={fund.tier} />
                        ) : (
                          <span className="text-xs text-slate-400">--</span>
                        )}
                      </td>

                      {/* Action */}
                      <td className="px-4 py-3 text-center">
                        {fund.action ? (
                          <ActionBadge action={fund.action} />
                        ) : (
                          <span className="text-xs text-slate-400">--</span>
                        )}
                      </td>

                      {/* Top Aligned Sectors */}
                      <td className="px-4 py-3 text-sm text-slate-500 max-w-[200px] truncate">
                        {topAlignedSectorNames(fund.alignment_summary)}
                      </td>

                      {/* Avoid Exposure % */}
                      <td
                        className={`px-4 py-3 text-right text-sm font-mono tabular-nums ${avoidExposureClass(
                          fund.avoid_exposure_pct,
                        )}`}
                      >
                        {fund.avoid_exposure_pct !== null &&
                        fund.avoid_exposure_pct !== undefined
                          ? `${fund.avoid_exposure_pct.toFixed(1)}%`
                          : "--"}
                      </td>
                    </tr>,
                  );

                  {/* Expanded detail row */}
                  if (isExpanded && fund.alignment_summary) {
                    rows.push(
                      <AlignmentDetail
                        key={`detail-${fund.mstar_id}`}
                        summary={fund.alignment_summary}
                        rationale={
                          /* Pull action_rationale if present on the shortlist item.
                             The ShortlistItem type does not include it explicitly,
                             but it may come from the API as part of alignment_summary
                             or we default to null. */
                          null
                        }
                      />,
                    );
                  }
                }

                return rows;
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer metadata */}
      <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
        <p>
          Showing {funds.length} shortlisted funds across{" "}
          {stats.categoriesCovered} categories
        </p>
        <p>
          Last computed:{" "}
          {funds.length > 0 ? formatDate(funds[0].computed_date) : "--"}
        </p>
      </div>
    </div>
  );
}
