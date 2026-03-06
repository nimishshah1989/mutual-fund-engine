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
import ShortlistTable from "./ShortlistTable";
import {
  groupByCategory,
  computeShortlistStats,
} from "./shortlist-helpers";

/* ------------------------------------------------------------------ */
/*  Page header constants                                              */
/* ------------------------------------------------------------------ */
const PAGE_EMOJI = "\u2B50";
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

  /* ----- derived data ----- */
  const stats = useMemo(() => computeShortlistStats(funds), [funds]);
  const categoryGroups = useMemo(() => groupByCategory(funds), [funds]);

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
          emoji={PAGE_EMOJI}
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
          emoji={PAGE_EMOJI}
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
          emoji={PAGE_EMOJI}
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
        emoji={PAGE_EMOJI}
        title={PAGE_TITLE}
        subtitle={subtitle}
      />

      <ShortlistStatCards stats={stats} />

      <ShortlistTable categoryGroups={categoryGroups} />

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
