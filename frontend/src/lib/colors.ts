/**
 * Shared color maps for Morningstar sectors and SEBI category groups.
 * Provides consistent color coding across all tables, charts, and badges.
 */

/* ------------------------------------------------------------------ */
/*  Morningstar Sector Colors (11 sectors)                             */
/* ------------------------------------------------------------------ */
export const SECTOR_COLORS: Record<string, string> = {
  "Basic Materials": "bg-amber-500",
  "Communication Services": "bg-violet-500",
  "Consumer Cyclical": "bg-pink-500",
  "Consumer Defensive": "bg-lime-600",
  Energy: "bg-orange-500",
  "Financial Services": "bg-blue-500",
  Healthcare: "bg-emerald-500",
  Industrials: "bg-slate-500",
  "Real Estate": "bg-cyan-500",
  Technology: "bg-indigo-500",
  Utilities: "bg-yellow-500",
};

export const SECTOR_TEXT_COLORS: Record<string, string> = {
  "Basic Materials": "text-amber-500",
  "Communication Services": "text-violet-500",
  "Consumer Cyclical": "text-pink-500",
  "Consumer Defensive": "text-lime-600",
  Energy: "text-orange-500",
  "Financial Services": "text-blue-500",
  Healthcare: "text-emerald-500",
  Industrials: "text-slate-500",
  "Real Estate": "text-cyan-500",
  Technology: "text-indigo-500",
  Utilities: "text-yellow-500",
};

/* ------------------------------------------------------------------ */
/*  SEBI Category Group Colors                                         */
/* ------------------------------------------------------------------ */
export const CATEGORY_GROUP_COLORS: Record<string, string> = {
  "Large Cap": "bg-blue-600",
  "Large & Mid Cap": "bg-blue-600",
  "Mid Cap": "bg-purple-600",
  "Small Cap": "bg-purple-600",
  "Flexi Cap": "bg-teal-600",
  "Multi Cap": "bg-teal-600",
  Focused: "bg-teal-600",
  ELSS: "bg-emerald-600",
  Contra: "bg-emerald-600",
  Value: "bg-emerald-600",
  ESG: "bg-emerald-600",
  Sector: "bg-orange-500",
  Index: "bg-slate-500",
  Global: "bg-indigo-500",
};

/* ------------------------------------------------------------------ */
/*  Helper functions                                                   */
/* ------------------------------------------------------------------ */

/**
 * Returns the Tailwind bg-color class for a Morningstar sector name.
 * Falls back to slate-400 for unknown sectors.
 */
export function sectorBgColor(sector: string): string {
  return SECTOR_COLORS[sector] ?? "bg-slate-400";
}

/**
 * Returns the Tailwind text-color class for a Morningstar sector name.
 * Falls back to text-slate-400 for unknown sectors.
 */
export function sectorTextColor(sector: string): string {
  return SECTOR_TEXT_COLORS[sector] ?? "text-slate-400";
}

/**
 * Matches a SEBI category name to a category group color.
 * Checks for keyword matches (e.g., "Large Cap Fund" matches "Large Cap").
 * Falls back to slate-500 for unmatched categories.
 */
export function categoryGroupColor(categoryName: string): string {
  const lower = categoryName.toLowerCase();

  if (lower.includes("large") && lower.includes("mid")) return CATEGORY_GROUP_COLORS["Large & Mid Cap"];
  if (lower.includes("large")) return CATEGORY_GROUP_COLORS["Large Cap"];
  if (lower.includes("small")) return CATEGORY_GROUP_COLORS["Small Cap"];
  if (lower.includes("mid")) return CATEGORY_GROUP_COLORS["Mid Cap"];
  if (lower.includes("flexi")) return CATEGORY_GROUP_COLORS["Flexi Cap"];
  if (lower.includes("multi")) return CATEGORY_GROUP_COLORS["Multi Cap"];
  if (lower.includes("focused")) return CATEGORY_GROUP_COLORS["Focused"];
  if (lower.includes("elss")) return CATEGORY_GROUP_COLORS["ELSS"];
  if (lower.includes("contra")) return CATEGORY_GROUP_COLORS["Contra"];
  if (lower.includes("value")) return CATEGORY_GROUP_COLORS["Value"];
  if (lower.includes("esg")) return CATEGORY_GROUP_COLORS["ESG"];
  if (lower.includes("sector") || lower.includes("thematic")) return CATEGORY_GROUP_COLORS["Sector"];
  if (lower.includes("index") || lower.includes("etf")) return CATEGORY_GROUP_COLORS["Index"];
  if (lower.includes("global") || lower.includes("international")) return CATEGORY_GROUP_COLORS["Global"];

  return "bg-slate-500";
}
