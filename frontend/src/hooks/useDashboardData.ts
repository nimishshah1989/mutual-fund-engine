"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { apiFetch } from "@/lib/api";
import { formatTimeAgo } from "@/lib/formatters";
import type {
  ApiResponse,
  FundScoreOverview,
  HealthReady,
  DataFreshnessEntry,
  MatrixCellSummary,
  MatrixSummaryResponse,
} from "@/types/api";
import type { TierCount, TierActionRow, ActionDistributionRow } from "@/components/dashboard/types";

/** Canonical action order for display */
const ACTION_ORDER = ["ACCUMULATE", "HOLD", "REDUCE", "EXIT"] as const;

export interface DashboardData {
  /* Raw data */
  funds: FundScoreOverview[];
  health: HealthReady | null;
  matrixCells: MatrixCellSummary[];

  /* Loading / error state */
  loading: boolean;
  error: string | null;
  refetch: () => void;

  /* Derived summary metrics */
  totalFunds: number;
  avgQFS: number;
  coreCount: number;
  qualityCount: number;
  accumulateCount: number;
  matrixCoverageCount: number;
  lastScoredDate: string | null;
  dataFreshness: string;
  morningstarFreshness: DataFreshnessEntry | undefined;

  /* Chart / table data */
  tierCounts: TierCount[];
  tierActionRows: TierActionRow[];
  actionDistribution: ActionDistributionRow[];
}

export function useDashboardData(): DashboardData {
  const [funds, setFunds] = useState<FundScoreOverview[]>([]);
  const [health, setHealth] = useState<HealthReady | null>(null);
  const [matrixCells, setMatrixCells] = useState<MatrixCellSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [scoresRes, healthRes, matrixRes] = await Promise.all([
        apiFetch<ApiResponse<FundScoreOverview[]>>(
          "/api/v1/scores/overview?limit=1000",
        ),
        apiFetch<HealthReady>("/health/ready"),
        apiFetch<ApiResponse<MatrixSummaryResponse>>(
          "/api/v1/scores/matrix",
        ),
      ]);

      setFunds(scoresRes.data ?? []);
      setHealth(healthRes);
      setMatrixCells(matrixRes.data?.cells ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /* ---- Derived metrics (memoised to avoid recalc on every render) ---- */

  const totalFunds = funds.length;

  const avgQFS = useMemo(
    () =>
      funds.length > 0
        ? funds.reduce((sum, f) => sum + (f.qfs ?? 0), 0) / funds.length
        : 0,
    [funds],
  );

  const coreCount = useMemo(
    () =>
      funds.filter((f) => (f.tier ?? "").toUpperCase() === "CORE").length,
    [funds],
  );

  const qualityCount = useMemo(
    () =>
      funds.filter((f) => (f.tier ?? "").toUpperCase() === "QUALITY").length,
    [funds],
  );

  /* Count of funds with action = ACCUMULATE (replaces shortlistedCount) */
  const accumulateCount = useMemo(
    () =>
      funds.filter((f) => (f.action ?? "").toUpperCase() === "ACCUMULATE").length,
    [funds],
  );

  /* Count of funds that have a matrix_position assigned */
  const matrixCoverageCount = useMemo(
    () =>
      funds.filter((f) => f.matrix_position != null && f.matrix_position !== "").length,
    [funds],
  );

  /* Data freshness from health checks */
  const morningstarFreshness =
    health?.checks?.data_freshness?.MORNINGSTAR_API;

  const dataFreshness = morningstarFreshness?.last_run
    ? formatTimeAgo(morningstarFreshness.last_run)
    : "--";

  /* Last scored date -- most recent computed_date from funds */
  const lastScoredDate = useMemo(() => {
    if (funds.length === 0) return null;
    return funds.reduce((latest, f) => {
      if (!f.computed_date) return latest;
      return f.computed_date > latest ? f.computed_date : latest;
    }, "");
  }, [funds]);

  /* Tier distribution for donut chart */
  const tierCounts: TierCount[] = useMemo(() => {
    const map: Record<string, number> = {};
    funds.forEach((f) => {
      const t = (f.tier ?? "UNSCORED").toUpperCase();
      map[t] = (map[t] ?? 0) + 1;
    });
    return Object.entries(map).map(([name, value]) => ({ name, value }));
  }, [funds]);

  /* Tier x Action breakdown (kept for backward compatibility) */
  const tierActionRows: TierActionRow[] = useMemo(() => {
    const map: Record<string, TierActionRow> = {};
    funds.forEach((f) => {
      const t = (f.tier ?? "UNSCORED").toUpperCase();
      if (!map[t]) {
        map[t] = {
          tier: t,
          accumulate: 0,
          hold: 0,
          reduce: 0,
          exit: 0,
          total: 0,
        };
      }
      const a = (f.action ?? "").toUpperCase();
      if (a === "ACCUMULATE") map[t].accumulate++;
      else if (a === "HOLD") map[t].hold++;
      else if (a === "REDUCE") map[t].reduce++;
      else if (a === "EXIT") map[t].exit++;
      map[t].total++;
    });
    return Object.values(map);
  }, [funds]);

  /* Action distribution derived from matrixCells (or fallback to funds) */
  const actionDistribution: ActionDistributionRow[] = useMemo(() => {
    const countMap: Record<string, number> = {};

    if (matrixCells.length > 0) {
      /* Derive from matrix summary — authoritative source */
      matrixCells.forEach((cell) => {
        const a = (cell.action ?? "").toUpperCase();
        countMap[a] = (countMap[a] ?? 0) + cell.fund_count;
      });
    } else {
      /* Fallback: derive from fund-level overview data */
      funds.forEach((f) => {
        const a = (f.action ?? "").toUpperCase();
        if (a) {
          countMap[a] = (countMap[a] ?? 0) + 1;
        }
      });
    }

    const total = Object.values(countMap).reduce((s, c) => s + c, 0);

    return ACTION_ORDER.map((action) => ({
      action,
      count: countMap[action] ?? 0,
      pct: total > 0 ? ((countMap[action] ?? 0) / total) * 100 : 0,
    }));
  }, [matrixCells, funds]);

  return {
    funds,
    health,
    matrixCells,
    loading,
    error,
    refetch: fetchData,
    totalFunds,
    avgQFS,
    coreCount,
    qualityCount,
    accumulateCount,
    matrixCoverageCount,
    lastScoredDate,
    dataFreshness,
    morningstarFreshness,
    tierCounts,
    tierActionRows,
    actionDistribution,
  };
}
