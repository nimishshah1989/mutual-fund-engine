/* ------------------------------------------------------------------ */
/*  Dashboard-specific types shared across dashboard components       */
/* ------------------------------------------------------------------ */

export interface TierCount {
  name: string;
  value: number;
}

export interface TierActionRow {
  tier: string;
  accumulate: number;
  hold: number;
  reduce: number;
  exit: number;
  total: number;
}

/** Chart colours aligned with tier badges */
export const TIER_COLORS: Record<string, string> = {
  CORE: "#059669",
  QUALITY: "#2563eb",
  WATCH: "#f59e0b",
  CAUTION: "#f97316",
  EXIT: "#dc2626",
};
