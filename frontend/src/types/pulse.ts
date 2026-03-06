/* ------------------------------------------------------------------ */
/*  MF Pulse types — ratio returns relative to Nifty 50               */
/* ------------------------------------------------------------------ */

/** Signal classification based on ratio return */
export type PulseSignal =
  | "STRONG_OW"
  | "OVERWEIGHT"
  | "NEUTRAL"
  | "UNDERWEIGHT"
  | "STRONG_UW";

/** Valid pulse periods */
export type PulsePeriod = "1m" | "3m" | "6m" | "1y" | "2y" | "3y";

/** Single fund row in the pulse table */
export interface PulseFundItem {
  mstar_id: string;
  fund_name: string | null;
  category_name: string | null;
  period: string;
  snapshot_date: string | null;

  ratio_return: number | null;
  fund_return: number | null;
  nifty_return: number | null;
  excess_return: number | null;
  signal: PulseSignal | null;

  qfs: number | null;
  fm_score: number | null;
  qfs_quadrant: string | null;
  fm_quadrant: string | null;
  tier: string | null;
  action: string | null;
}

/** Signal distribution for one SEBI category */
export interface PulseCategorySummary {
  category_name: string;
  fund_count: number;
  avg_ratio_return: number;
  signals: Record<string, number>;
}

/** Response for GET /api/v1/pulse/categories */
export interface PulseCategoryResponse {
  categories: PulseCategorySummary[];
  period: string;
  total_categories: number;
}

/** Data coverage stats */
export interface PulseCoverageStats {
  nav_fund_count: number;
  nav_earliest_date: string | null;
  nav_latest_date: string | null;
  nav_total_rows: number;
  benchmark_earliest_date: string | null;
  benchmark_latest_date: string | null;
  benchmark_total_rows: number;
  snapshot_date: string | null;
}
