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
/*  Group funds by category, sorted alphabetically;                    */
/*  within each group, sorted by QFS descending                        */
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
    catFunds.sort((a, b) => (b.qfs_score ?? 0) - (a.qfs_score ?? 0));
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
