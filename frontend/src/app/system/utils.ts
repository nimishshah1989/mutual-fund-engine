/* ------------------------------------------------------------------ */
/*  System page utilities — shared types, constants, helper functions  */
/* ------------------------------------------------------------------ */

export type LayerValue = "qfs" | "fsas" | "all";

export const LAYER_OPTIONS: { value: LayerValue; label: string }[] = [
  { value: "all", label: "Full Pipeline (Score \u2192 Shortlist \u2192 Alignment \u2192 Recommend)" },
  { value: "qfs", label: "Layer 1 \u2014 Quantitative Fund Score" },
  { value: "fsas", label: "Layer 2 \u2014 Sector Alignment Score (Shortlisted Only)" },
];

/**
 * Calculate duration in human-readable form from two ISO timestamps.
 */
export function formatDuration(
  startIso: string | null | undefined,
  endIso: string | null | undefined,
): string {
  if (!startIso || !endIso) return "--";
  const start = new Date(startIso).getTime();
  const end = new Date(endIso).getTime();
  const diffMs = end - start;
  if (diffMs < 0) return "--";
  if (diffMs < 1000) return `${diffMs}ms`;
  const seconds = diffMs / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainSec = Math.round(seconds % 60);
  return `${minutes}m ${remainSec}s`;
}

/**
 * Friendly display name for data feed keys.
 */
export function feedDisplayName(key: string): string {
  const map: Record<string, string> = {
    MORNINGSTAR_API: "Morningstar API",
    JHV_MASTER: "JHV Master Data",
    MONTHLY_RECOMPUTE: "Monthly Recompute",
  };
  return map[key] ?? key;
}
