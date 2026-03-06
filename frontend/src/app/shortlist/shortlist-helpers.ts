/* ------------------------------------------------------------------ */
/*  Pure helper functions for the Shortlist page                       */
/*  No React — safe to import from any module                          */
/* ------------------------------------------------------------------ */

import type { ShortlistItem, AlignmentSummary } from "@/types/api";

/* ------------------------------------------------------------------ */
/*  CategoryGroup — used by groupByCategory                            */
/* ------------------------------------------------------------------ */
export interface CategoryGroup {
  category: string;
  funds: ShortlistItem[];
}

/* ------------------------------------------------------------------ */
/*  Shortlist summary stats                                            */
/* ------------------------------------------------------------------ */
export interface ShortlistStats {
  totalFunds: number;
  categoriesCovered: number;
  avgQfs: number;
  fundsWithFsas: number;
}

/* ------------------------------------------------------------------ */
/*  Sort field type for sortable numeric columns                       */
/* ------------------------------------------------------------------ */
export type ShortlistSortField = "qfs_score" | "fsas" | "avoid_exposure_pct";

/* ------------------------------------------------------------------ */
/*  Score color class based on threshold                                */
/* ------------------------------------------------------------------ */
export function scoreColorClass(score: number | null): string {
  if (score === null || score === undefined) return "text-slate-400";
  if (score >= 70) return "text-emerald-600";
  if (score >= 40) return "text-slate-600";
  return "text-red-600";
}

/* ------------------------------------------------------------------ */
/*  Avoid exposure color class                                         */
/* ------------------------------------------------------------------ */
export function avoidExposureClass(pct: number | null): string {
  if (pct === null || pct === undefined) return "text-slate-400";
  if (pct >= 15) return "text-red-600 font-semibold";
  return "text-slate-500";
}

/* ------------------------------------------------------------------ */
/*  Filter shortlist by search text, category, and tier                */
/* ------------------------------------------------------------------ */
export function filterShortlist(
  funds: ShortlistItem[],
  search: string,
  categoryFilter: string,
  tierFilter: string,
): ShortlistItem[] {
  let filtered = funds;

  // Search by fund name or mstar_id (case-insensitive partial match)
  if (search.trim() !== "") {
    const needle = search.trim().toLowerCase();
    filtered = filtered.filter((f) => {
      const nameMatch = f.fund_name
        ? f.fund_name.toLowerCase().includes(needle)
        : false;
      const idMatch = f.mstar_id.toLowerCase().includes(needle);
      return nameMatch || idMatch;
    });
  }

  // Filter by exact category match
  if (categoryFilter !== "") {
    filtered = filtered.filter((f) => f.category_name === categoryFilter);
  }

  // Filter by tier (case-insensitive exact match)
  if (tierFilter !== "") {
    const tierUpper = tierFilter.toUpperCase();
    filtered = filtered.filter(
      (f) => f.tier !== null && f.tier.toUpperCase() === tierUpper,
    );
  }

  return filtered;
}

/* ------------------------------------------------------------------ */
/*  Sort shortlist by a numeric field; null values placed last         */
/* ------------------------------------------------------------------ */
export function sortShortlist(
  funds: ShortlistItem[],
  sortField: ShortlistSortField | null,
  sortDesc: boolean,
): ShortlistItem[] {
  if (sortField === null) return funds;

  return [...funds].sort((a, b) => {
    const aVal = a[sortField];
    const bVal = b[sortField];

    // Nulls always last regardless of sort direction
    if (aVal === null || aVal === undefined) return 1;
    if (bVal === null || bVal === undefined) return -1;

    const diff = aVal - bVal;
    return sortDesc ? -diff : diff;
  });
}

/* ------------------------------------------------------------------ */
/*  Group funds by category, sorted alphabetically;                    */
/*  within each group, preserve the incoming order (caller controls    */
/*  sort before calling this)                                          */
/* ------------------------------------------------------------------ */
export function groupByCategory(funds: ShortlistItem[]): CategoryGroup[] {
  const map = new Map<string, ShortlistItem[]>();
  for (const fund of funds) {
    const cat = fund.category_name || "Uncategorized";
    if (!map.has(cat)) {
      map.set(cat, []);
    }
    map.get(cat)!.push(fund);
  }

  const groups: CategoryGroup[] = [];
  const sortedKeys = Array.from(map.keys()).sort((a, b) =>
    a.localeCompare(b),
  );
  for (const key of sortedKeys) {
    const catFunds = map.get(key)!;
    // Only apply default QFS sort when no explicit sort is active;
    // the caller should sort before grouping if a sort field is set.
    // We keep original order here to respect pre-applied sorting.
    groups.push({ category: key, funds: catFunds });
  }
  return groups;
}

/* ------------------------------------------------------------------ */
/*  Extract top aligned sector names for display                       */
/* ------------------------------------------------------------------ */
export function topAlignedSectorNames(
  summary: AlignmentSummary | null,
): string {
  if (!summary || !summary.top_aligned || summary.top_aligned.length === 0) {
    return "--";
  }
  return summary.top_aligned
    .slice(0, 3)
    .map((s) => s.sector)
    .join(", ");
}

/* ------------------------------------------------------------------ */
/*  Compute derived stats from the fund list                           */
/* ------------------------------------------------------------------ */
export function computeShortlistStats(
  funds: ShortlistItem[],
): ShortlistStats {
  const totalFunds = funds.length;

  const categoriesSet = new Set(funds.map((f) => f.category_name));
  const categoriesCovered = categoriesSet.size;

  const qfsScores = funds
    .map((f) => f.qfs_score)
    .filter((s): s is number => s !== null && s !== undefined);
  const avgQfs =
    qfsScores.length > 0
      ? qfsScores.reduce((sum, s) => sum + s, 0) / qfsScores.length
      : 0;

  const fundsWithFsas = funds.filter(
    (f) => f.fsas !== null && f.fsas !== undefined,
  ).length;

  return { totalFunds, categoriesCovered, avgQfs, fundsWithFsas };
}
