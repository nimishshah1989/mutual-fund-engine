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

export interface ActionDistributionRow {
  action: string;
  count: number;
  pct: number;
}

/** Chart colours aligned with tier badges */
export const TIER_COLORS: Record<string, string> = {
  CORE: "#059669",
  QUALITY: "#2563eb",
  WATCH: "#f59e0b",
  CAUTION: "#f97316",
  EXIT: "#dc2626",
};

/** Colours aligned with ActionBadge component */
export const ACTION_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  ACCUMULATE: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-600" },
  HOLD: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500" },
  REDUCE: { bg: "bg-orange-50", text: "text-orange-700", dot: "bg-orange-500" },
  EXIT: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-600" },
};
