"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { apiFetch } from "@/lib/api";
import { formatDate } from "@/lib/formatters";
import type { ApiResponse, ShortlistItem } from "@/types/api";
import PageHeader from "@/components/PageHeader";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import ShortlistStatCards from "./ShortlistStatCards";
import ShortlistFilterBar from "./ShortlistFilterBar";
import ShortlistTable from "./ShortlistTable";
import {
  type ShortlistSortField,
  groupByCategory,
  computeShortlistStats,
  filterShortlist,
  sortShortlist,
} from "./shortlist-helpers";

/* ------------------------------------------------------------------ */
/*  Page header constants                                              */
/* ------------------------------------------------------------------ */
const PAGE_TITLE = "Shortlisted Funds";
const PAGE_SUBTITLE_BASE =
  "Top funds per category \u2014 FM recommendation output";

/* ------------------------------------------------------------------ */
/*  Page component                                                     */
/* ------------------------------------------------------------------ */
export default function ShortlistPage() {
  /* ----- data state ----- */
  const [funds, setFunds] = useState<ShortlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* ----- filter state ----- */
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [tierFilter, setTierFilter] = useState("");

  /* ----- sort state ----- */
  const [sortField, setSortField] = useState<ShortlistSortField | null>(null);
  const [sortDesc, setSortDesc] = useState(true);

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

  /* ----- sort toggle handler ----- */
  const handleSort = useCallback(
    (field: ShortlistSortField) => {
      if (sortField === field) {
        // Toggle direction; if already ascending, clear sort
        if (!sortDesc) {
          setSortField(null);
          setSortDesc(true);
        } else {
          setSortDesc(false);
        }
      } else {
        setSortField(field);
        setSortDesc(true);
      }
    },
    [sortField, sortDesc],
  );

  /* ----- derived: unique sorted categories from ALL funds ----- */
  const categories = useMemo(() => {
    const catSet = new Set(funds.map((f) => f.category_name));
    return Array.from(catSet).sort((a, b) => a.localeCompare(b));
  }, [funds]);

  /* ----- derived: filtered -> sorted -> grouped ----- */
  const filteredFunds = useMemo(
    () => filterShortlist(funds, search, categoryFilter, tierFilter),
    [funds, search, categoryFilter, tierFilter],
  );

  const sortedFunds = useMemo(
    () => sortShortlist(filteredFunds, sortField, sortDesc),
    [filteredFunds, sortField, sortDesc],
  );

  const categoryGroups = useMemo(
    () => groupByCategory(sortedFunds),
    [sortedFunds],
  );

  /* ----- stats computed from filtered funds ----- */
  const stats = useMemo(
    () => computeShortlistStats(filteredFunds),
    [filteredFunds],
  );

  /* ----- subtitle with scored date ----- */
  const subtitle = useMemo(() => {
    if (funds.length > 0 && funds[0].computed_date) {
      return `${PAGE_SUBTITLE_BASE} \u00B7 Scored: ${formatDate(funds[0].computed_date)}`;
    }
    return PAGE_SUBTITLE_BASE;
  }, [funds]);

  /* ----- loading state ----- */
  if (loading) {
    return (
      <div>
        <PageHeader
          title={PAGE_TITLE}
          subtitle={PAGE_SUBTITLE_BASE}
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
          title={PAGE_TITLE}
          subtitle={PAGE_SUBTITLE_BASE}
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
          title={PAGE_TITLE}
          subtitle={PAGE_SUBTITLE_BASE}
        />
        <EmptyState
          title="No shortlisted funds yet"
          description="Run the scoring engine with FM signals to generate shortlisted fund recommendations."
        />
      </div>
    );
  }

  /* ----- success state ----- */
  return (
    <div>
      <PageHeader
        title={PAGE_TITLE}
        subtitle={subtitle}
      />

      <ShortlistStatCards stats={stats} />

      <ShortlistFilterBar
        search={search}
        onSearchChange={setSearch}
        categoryFilter={categoryFilter}
        onCategoryChange={setCategoryFilter}
        tierFilter={tierFilter}
        onTierChange={setTierFilter}
        categories={categories}
        displayCount={filteredFunds.length}
        totalCount={funds.length}
      />

      <ShortlistTable
        categoryGroups={categoryGroups}
        sortField={sortField}
        sortDesc={sortDesc}
        onSort={handleSort}
      />

      {/* Footer metadata */}
      <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
        <p>
          Showing {filteredFunds.length} shortlisted funds across{" "}
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
