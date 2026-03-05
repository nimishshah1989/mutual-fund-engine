"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { formatScore, formatDate } from "@/lib/formatters";
import type { ApiResponse, FundScoreOverview } from "@/types/api";
import PageHeader from "@/components/PageHeader";
import TierBadge from "@/components/TierBadge";
import ActionBadge from "@/components/ActionBadge";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";

/* ------------------------------------------------------------------ */
/*  Sortable column keys — v2: QFS-based, no CRS                      */
/* ------------------------------------------------------------------ */
type SortField = "qfs" | "data_completeness_pct" | "qfs_rank";

/* ------------------------------------------------------------------ */
/*  Page component                                                     */
/* ------------------------------------------------------------------ */
export default function FundUniversePage() {
  const [funds, setFunds] = useState<FundScoreOverview[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalFunds, setTotalFunds] = useState(0);

  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [tierFilter, setTierFilter] = useState("");
  const [actionFilter, setActionFilter] = useState("");

  const [sortField, setSortField] = useState<SortField>("qfs");
  const [sortDesc, setSortDesc] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [fundsRes, catsRes] = await Promise.all([
        apiFetch<ApiResponse<FundScoreOverview[]>>(
          "/api/v1/scores/overview?limit=1000",
        ),
        apiFetch<ApiResponse<string[]>>("/api/v1/scores/categories"),
      ]);

      setFunds(fundsRes.data ?? []);
      setTotalFunds(fundsRes.meta?.total ?? fundsRes.data?.length ?? 0);
      setCategories(catsRes.data ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load funds");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const displayFunds = useMemo(() => {
    let filtered = [...funds];

    if (search.trim()) {
      const q = search.trim().toLowerCase();
      filtered = filtered.filter((f) => {
        const name = (f.fund_name ?? f.mstar_id).toLowerCase();
        return name.includes(q);
      });
    }

    if (categoryFilter) {
      filtered = filtered.filter((f) => f.category_name === categoryFilter);
    }

    if (tierFilter) {
      filtered = filtered.filter(
        (f) => (f.tier ?? "").toUpperCase() === tierFilter.toUpperCase(),
      );
    }

    if (actionFilter) {
      filtered = filtered.filter(
        (f) => (f.action ?? "").toUpperCase() === actionFilter.toUpperCase(),
      );
    }

    filtered.sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];

      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;

      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortDesc ? bVal - aVal : aVal - bVal;
      }

      return 0;
    });

    return filtered;
  }, [funds, search, categoryFilter, tierFilter, actionFilter, sortField, sortDesc]);

  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortDesc((d) => !d);
    } else {
      setSortField(field);
      setSortDesc(true);
    }
  }

  function sortIndicator(field: SortField): string {
    if (sortField !== field) return "";
    return sortDesc ? " \u25BC" : " \u25B2";
  }

  if (loading) {
    return (
      <div>
        <PageHeader
          emoji="🏆"
          title="Fund Universe"
          subtitle="Master fund scoreboard"
        />
        <LoadingSkeleton variant="table" />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <PageHeader
          emoji="🏆"
          title="Fund Universe"
          subtitle="Master fund scoreboard"
        />
        <ErrorState message={error} onRetry={fetchData} />
      </div>
    );
  }

  if (funds.length === 0) {
    return (
      <div>
        <PageHeader
          emoji="🏆"
          title="Fund Universe"
          subtitle="Master fund scoreboard"
        />
        <EmptyState
          title="No funds scored yet"
          description="Ingest fund data and run scoring from the System page to populate this table."
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        emoji="🏆"
        title="Fund Universe"
        subtitle={`All ${totalFunds} funds with QFS scores and QFS-based tier classification${funds.length > 0 && funds[0].computed_date ? ` · Scored: ${formatDate(funds[0].computed_date)}` : ""}`}
      />

      {/* Filter controls */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 mb-4">
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="text"
            placeholder="Search by fund name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-64 bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
          />

          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>

          <select
            value={tierFilter}
            onChange={(e) => setTierFilter(e.target.value)}
            className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
          >
            <option value="">All Tiers</option>
            <option value="CORE">CORE</option>
            <option value="QUALITY">QUALITY</option>
            <option value="WATCH">WATCH</option>
            <option value="CAUTION">CAUTION</option>
            <option value="EXIT">EXIT</option>
          </select>

          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
          >
            <option value="">All Actions</option>
            <option value="BUY">BUY</option>
            <option value="SIP">SIP</option>
            <option value="HOLD_PLUS">HOLD+</option>
            <option value="HOLD">HOLD</option>
            <option value="REDUCE">REDUCE</option>
            <option value="EXIT">EXIT</option>
          </select>

          <div className="ml-auto text-sm text-slate-500">
            Showing{" "}
            <span className="font-semibold text-slate-700">
              {displayFunds.length}
            </span>{" "}
            of{" "}
            <span className="font-semibold text-slate-700">{totalFunds}</span>{" "}
            funds
          </div>
        </div>
      </div>

      {/* Table */}
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
                <th
                  onClick={() => handleSort("qfs")}
                  className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-600 select-none"
                >
                  QFS{sortIndicator("qfs")}
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Tier
                </th>
                <th
                  onClick={() => handleSort("qfs_rank")}
                  className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-600 select-none"
                >
                  QFS Rank{sortIndicator("qfs_rank")}
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Action
                </th>
                <th
                  onClick={() => handleSort("data_completeness_pct")}
                  className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-600 select-none"
                >
                  Data Completeness{sortIndicator("data_completeness_pct")}
                </th>
              </tr>
            </thead>
            <tbody>
              {displayFunds.map((fund, idx) => (
                <tr
                  key={fund.mstar_id}
                  className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
                >
                  <td className="px-4 py-3 text-sm text-slate-400 font-mono">
                    {idx + 1}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/funds/${fund.mstar_id}`}
                      className="text-sm font-medium text-slate-800 hover:text-teal-600 transition-colors"
                    >
                      {fund.fund_name ?? fund.mstar_id}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-500 max-w-[200px] truncate">
                    {fund.category_name ?? "--"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <ScoreCell value={fund.qfs} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <TierBadge tier={fund.tier ?? "--"} />
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-mono tabular-nums text-slate-600">
                    {fund.qfs_rank != null ? (
                      <span>
                        {fund.qfs_rank}
                        {fund.category_rank_pct != null && (
                          <span className="text-xs text-slate-400 ml-1">
                            ({Math.round(fund.category_rank_pct)}th pct)
                          </span>
                        )}
                      </span>
                    ) : (
                      "--"
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <ActionBadge action={fund.action ?? "--"} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <DataCompletenessBar value={fund.data_completeness_pct} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {displayFunds.length === 0 && (
            <div className="py-12 text-center">
              <p className="text-sm font-medium text-slate-600">
                No funds match your filters
              </p>
              <p className="text-xs text-slate-400 mt-1">
                Try adjusting your search or filter criteria
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Score cell — color-coded QFS score                                 */
/* ------------------------------------------------------------------ */
function ScoreCell({ value }: { value: number | null }) {
  if (value === null || value === undefined) {
    return <span className="text-sm text-slate-400 font-mono">--</span>;
  }

  let colorClass = "text-slate-600";
  if (value >= 70) colorClass = "text-emerald-600";
  else if (value < 40) colorClass = "text-red-600";

  return (
    <span className={`text-sm font-mono tabular-nums font-semibold ${colorClass}`}>
      {formatScore(value)}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Data Completeness bar                                              */
/* ------------------------------------------------------------------ */
function DataCompletenessBar({ value }: { value: number | null }) {
  if (value === null || value === undefined) {
    return <span className="text-xs text-slate-400">--</span>;
  }

  const pct = Math.round(value);
  let barColor = "bg-emerald-500";
  if (pct < 60) barColor = "bg-red-500";
  else if (pct < 80) barColor = "bg-amber-500";

  return (
    <div className="flex items-center justify-end gap-2">
      <span className="text-xs font-mono text-slate-600">{pct}%</span>
      <div className="w-16 bg-slate-100 rounded-full h-1.5">
        <div
          className={`${barColor} h-1.5 rounded-full`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
