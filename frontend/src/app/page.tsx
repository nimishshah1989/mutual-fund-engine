"use client";

import { formatScore, formatDate } from "@/lib/formatters";
import { useDashboardData } from "@/hooks/useDashboardData";
import PageHeader from "@/components/PageHeader";
import StatCard from "@/components/StatCard";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import ErrorState from "@/components/ErrorState";
import {
  SystemHealthPanel,
  TierActionTable,
} from "@/components/dashboard";
import DecisionMatrix from "@/app/funds/DecisionMatrix";

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
    accumulateCount,
    matrixCoverageCount,
    lastScoredDate,
    dataFreshness,
    morningstarFreshness,
    matrixCells,
    actionDistribution,
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
          label="Accumulate"
          value={String(accumulateCount)}
          subtext="Funds recommended to accumulate"
        />
        <StatCard
          label="Core Tier"
          value={String(coreCount)}
          subtext={`${totalFunds > 0 ? ((coreCount / totalFunds) * 100).toFixed(0) : 0}% of total`}
        />
        <StatCard
          label="Matrix Coverage"
          value={String(matrixCoverageCount)}
          subtext={`${totalFunds > 0 ? ((matrixCoverageCount / totalFunds) * 100).toFixed(0) : 0}% of scored funds`}
        />
        <StatCard
          label="Last Scored"
          value={lastScoredDate ? formatDate(lastScoredDate) : "--"}
          subtext={`Data: ${dataFreshness}`}
        />
      </div>

      {/* Two-column section: decision matrix + system health */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <DecisionMatrix
          cells={matrixCells}
          selectedPosition={null}
          onCellClick={() => {}}
        />
        <SystemHealthPanel
          health={health}
          totalFundsScored={totalFunds}
          morningstarFreshness={morningstarFreshness}
        />
      </div>

      {/* Action distribution table */}
      <TierActionTable rows={actionDistribution} />
    </div>
  );
}
