"use client";

import { useState, useMemo } from "react";
import { formatDate } from "@/lib/formatters";
import type { PulsePeriod, PulseSignal } from "@/types/pulse";
import PageHeader from "@/components/PageHeader";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import { usePulseData, usePulseCategories } from "@/hooks/usePulseData";
import CategoryHeatmap from "@/components/pulse/CategoryHeatmap";
import PulseTable from "@/components/pulse/PulseTable";

/* ---- Period options ---- */
const PERIOD_OPTIONS: { value: PulsePeriod; label: string }[] = [
  { value: "1m", label: "1M" },
  { value: "3m", label: "3M" },
  { value: "6m", label: "6M" },
  { value: "1y", label: "1Y" },
  { value: "2y", label: "2Y" },
  { value: "3y", label: "3Y" },
];

/* ---- Signal filter options ---- */
const SIGNAL_OPTIONS: { value: PulseSignal; label: string }[] = [
  { value: "STRONG_OW", label: "Strong OW" },
  { value: "OVERWEIGHT", label: "Overweight" },
  { value: "NEUTRAL", label: "Neutral" },
  { value: "UNDERWEIGHT", label: "Underweight" },
  { value: "STRONG_UW", label: "Strong UW" },
];

export default function MFPulsePage() {
  const [period, setPeriod] = useState<PulsePeriod>("1m");
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [signalFilter, setSignalFilter] = useState<PulseSignal | null>(null);
  const [sortField, setSortField] = useState("ratio_return");
  const [sortDesc, setSortDesc] = useState(true);

  const {
    funds,
    loading: fundsLoading,
    error: fundsError,
    total,
    snapshotDate,
    refetch: refetchFunds,
  } = usePulseData({
    period,
    category: categoryFilter,
    signal: signalFilter,
    sortBy: sortField,
    sortDesc,
    limit: 1000,
  });

  const {
    categories,
    loading: catsLoading,
    error: catsError,
  } = usePulseCategories(period);

  /* ---- Sort handler ---- */
  function handleSort(field: string) {
    if (sortField === field) {
      setSortDesc((d) => !d);
    } else {
      setSortField(field);
      setSortDesc(true);
    }
  }

  /* ---- Locally sort funds (API returns pre-sorted, but we re-sort client-side for column clicks) ---- */
  const sortedFunds = useMemo(() => {
    const sorted = [...funds];
    sorted.sort((a, b) => {
      const aVal = (a as unknown as Record<string, unknown>)[sortField];
      const bVal = (b as unknown as Record<string, unknown>)[sortField];
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortDesc ? bVal - aVal : aVal - bVal;
      }
      if (typeof aVal === "string" && typeof bVal === "string") {
        return sortDesc ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
      }
      return 0;
    });
    return sorted;
  }, [funds, sortField, sortDesc]);

  const loading = fundsLoading || catsLoading;
  const error = fundsError || catsError;

  /* ---- Loading state ---- */
  if (loading) {
    return (
      <div>
        <PageHeader title="MF Pulse" subtitle="Fund signals relative to Nifty 50" />
        <LoadingSkeleton variant="card" cardCount={8} />
        <div className="mt-6">
          <LoadingSkeleton variant="table" />
        </div>
      </div>
    );
  }

  /* ---- Error state ---- */
  if (error) {
    return (
      <div>
        <PageHeader title="MF Pulse" subtitle="Fund signals relative to Nifty 50" />
        <ErrorState message={error} onRetry={refetchFunds} />
      </div>
    );
  }

  /* ---- Empty state ---- */
  if (funds.length === 0 && categories.length === 0) {
    return (
      <div>
        <PageHeader title="MF Pulse" subtitle="Fund signals relative to Nifty 50" />
        <EmptyState
          title="No pulse data available"
          description="Run the Pulse backfill from the System page to populate NAV data and compute ratio returns."
        />
      </div>
    );
  }

  /* ---- Subtitle with stats ---- */
  const subtitle = [
    `${total} funds`,
    snapshotDate ? `Snapshot: ${formatDate(snapshotDate)}` : null,
  ]
    .filter(Boolean)
    .join(" \u00B7 ");

  return (
    <div>
      <PageHeader title="MF Pulse" subtitle={subtitle} />

      {/* ---- Filters ---- */}
      <div className="flex flex-wrap items-center gap-3 mb-5">
        {/* Period selector */}
        <div className="flex items-center gap-1 bg-white border border-slate-200 rounded-lg p-0.5">
          {PERIOD_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setPeriod(opt.value)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                period === opt.value
                  ? "bg-teal-600 text-white"
                  : "text-slate-500 hover:text-slate-700 hover:bg-slate-50"
              }`}
              aria-pressed={period === opt.value}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* Signal filter */}
        <select
          value={signalFilter ?? ""}
          onChange={(e) =>
            setSignalFilter((e.target.value || null) as PulseSignal | null)
          }
          className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-600 focus:outline-none focus:ring-2 focus:ring-teal-500"
          aria-label="Filter by signal"
        >
          <option value="">All Signals</option>
          {SIGNAL_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {/* Category clear */}
        {categoryFilter && (
          <button
            onClick={() => setCategoryFilter(null)}
            className="flex items-center gap-1.5 bg-teal-50 text-teal-700 px-3 py-2 rounded-lg text-xs font-medium hover:bg-teal-100 transition-colors"
            aria-label={`Clear category filter: ${categoryFilter}`}
          >
            {categoryFilter}
            <span className="text-teal-400">&times;</span>
          </button>
        )}
      </div>

      {/* ---- Category heatmap cards ---- */}
      {categories.length > 0 && (
        <div className="mb-6">
          <CategoryHeatmap
            categories={categories}
            selectedCategory={categoryFilter}
            onCategoryClick={setCategoryFilter}
          />
        </div>
      )}

      {/* ---- Fund table ---- */}
      <PulseTable
        funds={sortedFunds}
        sortField={sortField}
        sortDesc={sortDesc}
        onSort={handleSort}
      />

      {/* ---- Pagination info ---- */}
      {total > 0 && (
        <div className="mt-3 text-xs text-slate-400 text-right">
          Showing {sortedFunds.length} of {total} funds
        </div>
      )}
    </div>
  );
}
