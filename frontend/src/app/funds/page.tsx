"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { formatScore } from "@/lib/formatters";
import type { ApiResponse, FundScoreOverview } from "@/types/api";
import PageHeader from "@/components/PageHeader";
import TierBadge from "@/components/TierBadge";
import ActionBadge from "@/components/ActionBadge";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";

/* ------------------------------------------------------------------ */
/*  Sortable column keys                                               */
/* ------------------------------------------------------------------ */
type SortField = "crs" | "qfs" | "fsas" | "data_completeness_pct";

/* ------------------------------------------------------------------ */
/*  Categories response shape                                          */
/* ------------------------------------------------------------------ */
interface CategoriesResponse {
  success: boolean;
  data: string[];
}

/* ------------------------------------------------------------------ */
/*  Page component                                                     */
/* ------------------------------------------------------------------ */
export default function FundScoreboardPage() {
  /* ----- data state ----- */
  const [funds, setFunds] = useState<FundScoreOverview[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalFunds, setTotalFunds] = useState(0);

  /* ----- filter state ----- */
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [tierFilter, setTierFilter] = useState("");
  const [actionFilter, setActionFilter] = useState("");

  /* ----- sort state ----- */
  const [sortField, setSortField] = useState<SortField>("crs");
  const [sortDesc, setSortDesc] = useState(true);

  /* ----- fetch all funds + categories ----- */
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [fundsRes, catsRes] = await Promise.all([
        apiFetch<ApiResponse<FundScoreOverview[]>>(
          "/api/v1/scores/overview?limit=1000",
        ),
        apiFetch<CategoriesResponse>("/api/v1/scores/categories"),
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

  /* ----- client-side filter + sort ----- */
  const displayFunds = useMemo(() => {
    let filtered = [...funds];

    /* Search by fund name (case-insensitive partial match) */
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      filtered = filtered.filter((f) => {
        const name = (f.fund_name ?? f.mstar_id).toLowerCase();
        return name.includes(q);
      });
    }

    /* Category exact match */
    if (categoryFilter) {
      filtered = filtered.filter((f) => f.category_name === categoryFilter);
    }

    /* Tier exact match (uppercase) */
    if (tierFilter) {
      filtered = filtered.filter(
        (f) => (f.tier ?? "").toUpperCase() === tierFilter.toUpperCase(),
      );
    }

    /* Action exact match (uppercase) */
    if (actionFilter) {
      filtered = filtered.filter(
        (f) => (f.action ?? "").toUpperCase() === actionFilter.toUpperCase(),
      );
    }

    /* Sort */
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

  /* ----- sort helpers ----- */
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

  /* ----- loading state ----- */
  if (loading) {
    return (
      <div>
        <PageHeader
          emoji="\uD83D\uDCCA"
          title="Fund Scoreboard"
          subtitle="MF Recommendation Engine"
        />
        <LoadingSkeleton variant="table" />
      </div>
    );
  }

  /* ----- error state ----- */
  if (error) {
    return (
      <div>
        <PageHeader
          emoji="\uD83D\uDCCA"
          title="Fund Scoreboard"
          subtitle="MF Recommendation Engine"
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
          emoji="\uD83D\uDCCA"
          title="Fund Scoreboard"
          subtitle="MF Recommendation Engine"
        />
        <EmptyState
          title="No funds scored yet"
          description="Ingest fund data and run scoring from the System page to populate this table."
        />
      </div>
    );
  }

  /* ----- success state ----- */
  return (
    <div>
      <PageHeader
        emoji="\uD83D\uDCCA"
        title="Fund Scoreboard"
        subtitle={`MF Recommendation Engine \u2014 ${totalFunds} funds scored`}
      />

      {/* Filter controls */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 mb-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search input */}
          <input
            type="text"
            placeholder="Search by fund name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-64 bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
          />

          {/* Category dropdown */}
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

          {/* Tier filter */}
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

          {/* Action filter */}
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
          >
            <option value="">All Actions</option>
            <option value="BUY">BUY</option>
            <option value="SIP">SIP</option>
            <option value="HOLD">HOLD</option>
            <option value="SWITCH">SWITCH</option>
            <option value="EXIT">EXIT</option>
          </select>

          {/* Fund count display */}
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
                  onClick={() => handleSort("crs")}
                  className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-600 select-none"
                >
                  Composite Score{sortIndicator("crs")}
                </th>
                <th
                  onClick={() => handleSort("qfs")}
                  className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-600 select-none"
                >
                  Quantitative Score{sortIndicator("qfs")}
                </th>
                <th
                  onClick={() => handleSort("fsas")}
                  className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-600 select-none"
                >
                  Sector Alignment{sortIndicator("fsas")}
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Tier
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
                  {/* Row number */}
                  <td className="px-4 py-3 text-sm text-slate-400 font-mono">
                    {idx + 1}
                  </td>

                  {/* Fund Name — clickable link */}
                  <td className="px-4 py-3">
                    <Link
                      href={`/funds/${fund.mstar_id}`}
                      className="text-sm font-medium text-slate-800 hover:text-teal-600 transition-colors"
                    >
                      {fund.fund_name ?? fund.mstar_id}
                    </Link>
                  </td>

                  {/* Category */}
                  <td className="px-4 py-3 text-sm text-slate-500">
                    {fund.category_name ?? "--"}
                  </td>

                  {/* Composite Score (CRS) */}
                  <td className="px-4 py-3 text-right text-sm font-mono font-semibold text-slate-800">
                    {formatScore(fund.crs)}
                  </td>

                  {/* Quantitative Score (QFS) */}
                  <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                    {formatScore(fund.qfs)}
                  </td>

                  {/* Sector Alignment (FSAS) */}
                  <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                    {formatScore(fund.fsas)}
                  </td>

                  {/* Tier */}
                  <td className="px-4 py-3 text-center">
                    <TierBadge tier={fund.tier ?? "--"} />
                  </td>

                  {/* Action */}
                  <td className="px-4 py-3 text-center">
                    <ActionBadge action={fund.action ?? "--"} />
                  </td>

                  {/* Data Completeness */}
                  <td className="px-4 py-3 text-right">
                    <DataCompletenessBar value={fund.data_completeness_pct} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* No results after filtering */}
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
/*  Data Completeness bar — inline component                           */
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
