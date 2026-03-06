"use client";

import { formatScore, formatDate } from "@/lib/formatters";
import { useDashboardData } from "@/hooks/useDashboardData";
import PageHeader from "@/components/PageHeader";
import StatCard from "@/components/StatCard";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import ErrorState from "@/components/ErrorState";
import {
  TierDistributionChart,
  SystemHealthPanel,
  TierActionTable,
} from "@/components/dashboard";

export default function DashboardPage() {
  const {
    health,
    loading,
    error,
    refetch,
    totalFunds,
    avgQFS,
    coreCount,
    qualityCount,
    shortlistedCount,
    lastScoredDate,
    dataFreshness,
    morningstarFreshness,
    tierCounts,
    tierActionRows,
  } = useDashboardData();

  if (loading) {
    return (
      <div>
        <PageHeader
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
          title="Dashboard"
          subtitle="MF Recommendation Engine"
        />
        <ErrorState message={error} onRetry={refetch} />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
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
          label="Avg Fund Score"
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
        <TierDistributionChart tierCounts={tierCounts} />
        <SystemHealthPanel
          health={health}
          totalFundsScored={totalFunds}
          morningstarFreshness={morningstarFreshness}
        />
      </div>

      {/* Tier x Action breakdown table */}
      <TierActionTable rows={tierActionRows} />
    </div>
  );
}
