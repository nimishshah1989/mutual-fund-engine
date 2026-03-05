/* ------------------------------------------------------------------ */
/*  Indian number formatting + financial display helpers               */
/* ------------------------------------------------------------------ */

/**
 * Format a number in full Indian notation: 1,23,45,678
 * Uses the en-IN locale for the correct lakh/crore grouping.
 */
export function formatIndianNumber(value: number): string {
  return new Intl.NumberFormat("en-IN").format(value);
}

/**
 * Format a monetary value in INR.
 * - Values >= 1 Crore  -> "1.23 Cr"
 * - Values >= 1 Lakh   -> "1.23L"
 * - Smaller values      -> full Indian notation with rupee sign
 */
export function formatINR(amount: number): string {
  const abs = Math.abs(amount);
  const sign = amount < 0 ? "-" : "";

  if (abs >= 1_00_00_000) {
    const crores = abs / 1_00_00_000;
    return `${sign}\u20B9${crores.toFixed(2)} Cr`;
  }
  if (abs >= 1_00_000) {
    const lakhs = abs / 1_00_000;
    return `${sign}\u20B9${lakhs.toFixed(2)}L`;
  }
  return `${sign}\u20B9${formatIndianNumber(Math.round(abs))}`;
}

/**
 * Format a percentage with explicit +/- sign and 2 decimal places.
 */
export function formatPercent(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

/**
 * Format a score to 1 decimal place.
 */
export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return "--";
  return score.toFixed(1);
}

/**
 * Format an ISO date string to a short human-readable form.
 */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "--";
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/**
 * Format an ISO date string to a relative "time ago" string.
 */
export function formatTimeAgo(iso: string | null | undefined): string {
  if (!iso) return "--";
  const now = Date.now();
  const then = new Date(iso).getTime();
  const diffSec = Math.floor((now - then) / 1000);

  if (diffSec < 60) return "just now";
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
}
