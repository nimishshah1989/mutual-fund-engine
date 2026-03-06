"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { ApiResponse, FundScoreDetail } from "@/types/api";
import PageHeader from "@/components/PageHeader";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import ErrorState from "@/components/ErrorState";
import FundHeaderCard from "./FundHeaderCard";
import QFSScoreCard from "./QFSScoreCard";
import FSASScoreCard from "./FSASScoreCard";
import RecommendationCard from "./RecommendationCard";
import MetricBreakdownTable from "./MetricBreakdownTable";
import SectorContributionTable from "./SectorContributionTable";

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

  /* ---------- Success state ---------- */
  return (
    <div>
      <PageHeader
        title={fund.fund_name ?? "Fund Detail"}
        subtitle={
          fund.category_name
            ? `${fund.mstar_id} \u00b7 ${fund.category_name}`
            : fund.mstar_id
        }
      />

      {/* Back link */}
      <Link
        href="/funds"
        className="text-sm text-teal-600 hover:text-teal-700 mb-4 inline-block"
      >
        &larr; Back to Fund Universe
      </Link>

      {/* Fund header card with QFS as primary score */}
      <FundHeaderCard
        fundName={fund.fund_name}
        mstarId={fund.mstar_id}
        categoryName={fund.category_name}
        qfs={fund.qfs}
        recommendation={fund.recommendation}
      />

      {/* Three score cards in a row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <QFSScoreCard qfs={fund.qfs} />
        <FSASScoreCard fsas={fund.fsas} />
        <RecommendationCard recommendation={fund.recommendation} />
      </div>

      {/* Metric breakdown table (rows = metrics, columns = horizons) */}
      <MetricBreakdownTable qfs={fund.qfs} />

      {/* Sector contribution detail table */}
      <SectorContributionTable fsas={fund.fsas} />
    </div>
  );
}
