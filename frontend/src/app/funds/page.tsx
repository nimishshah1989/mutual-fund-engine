"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { apiFetch } from "@/lib/api";
import { formatDate } from "@/lib/formatters";
import type { ApiResponse, FundScoreOverview } from "@/types/api";
import PageHeader from "@/components/PageHeader";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import FundFilterBar from "./FundFilterBar";
import FundTable from "./FundTable";
import type { SortField } from "./types";

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

  const [sortField, setSortField] = useState<SortField>("qfs_rank");
  const [sortDesc, setSortDesc] = useState(false);

  /* ---- Data fetching ---- */
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

  /* ---- Filtering and sorting ---- */
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

  /* ---- Sort handler ---- */
  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortDesc((d) => !d);
    } else {
      setSortField(field);
      setSortDesc(true);
    }
  }

  /* ---- Loading state ---- */
  if (loading) {
    return (
      <div>
        <PageHeader

          title="Fund Universe"
          subtitle="Master fund scoreboard"
        />
        <LoadingSkeleton variant="table" />
      </div>
    );
  }

  /* ---- Error state ---- */
  if (error) {
    return (
      <div>
        <PageHeader

          title="Fund Universe"
          subtitle="Master fund scoreboard"
        />
        <ErrorState message={error} onRetry={fetchData} />
      </div>
    );
  }

  /* ---- Empty state ---- */
  if (funds.length === 0) {
    return (
      <div>
        <PageHeader

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

  /* ---- Build subtitle with scored date ---- */
  const scoredDateSuffix =
    funds.length > 0 && funds[0].computed_date
      ? ` · Scored: ${formatDate(funds[0].computed_date)}`
      : "";

  /* ---- Success state ---- */
  return (
    <div>
      <PageHeader
        title="Fund Universe"
        subtitle={`All ${totalFunds} funds with scores and tier classification${scoredDateSuffix}`}
      />

      <FundFilterBar
        search={search}
        onSearchChange={setSearch}
        categoryFilter={categoryFilter}
        onCategoryChange={setCategoryFilter}
        tierFilter={tierFilter}
        onTierChange={setTierFilter}
        actionFilter={actionFilter}
        onActionChange={setActionFilter}
        categories={categories}
        displayCount={displayFunds.length}
        totalCount={totalFunds}
      />

      <FundTable
        funds={displayFunds}
        sortField={sortField}
        sortDesc={sortDesc}
        onSort={handleSort}
      />
    </div>
  );
}
