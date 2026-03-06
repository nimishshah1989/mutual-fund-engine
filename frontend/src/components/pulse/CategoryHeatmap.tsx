"use client";

import type { PulseCategorySummary } from "@/types/pulse";

interface CategoryHeatmapProps {
  categories: PulseCategorySummary[];
  selectedCategory: string | null;
  onCategoryClick: (category: string | null) => void;
}

/** Color tint based on dominant signal direction */
function getCategoryTint(summary: PulseCategorySummary): string {
  const { signals } = summary;
  const ow = (signals.STRONG_OW ?? 0) + (signals.OVERWEIGHT ?? 0);
  const uw = (signals.STRONG_UW ?? 0) + (signals.UNDERWEIGHT ?? 0);
  const total = summary.fund_count || 1;
  const owRatio = ow / total;
  const uwRatio = uw / total;

  if (owRatio > 0.5) return "bg-emerald-50 border-emerald-200";
  if (uwRatio > 0.5) return "bg-red-50 border-red-200";
  return "bg-white border-slate-200";
}

/** Mini signal bar showing distribution */
function SignalBar({ signals, total }: { signals: Record<string, number>; total: number }) {
  if (total === 0) return null;

  const segments = [
    { key: "STRONG_OW", color: "bg-emerald-700" },
    { key: "OVERWEIGHT", color: "bg-emerald-300" },
    { key: "NEUTRAL", color: "bg-slate-300" },
    { key: "UNDERWEIGHT", color: "bg-red-300" },
    { key: "STRONG_UW", color: "bg-red-700" },
  ];

  return (
    <div className="flex h-1.5 rounded-full overflow-hidden mt-2" aria-label="Signal distribution">
      {segments.map(({ key, color }) => {
        const count = signals[key] ?? 0;
        if (count === 0) return null;
        const pct = (count / total) * 100;
        return (
          <div
            key={key}
            className={color}
            style={{ width: `${pct}%` }}
            title={`${key}: ${count}`}
          />
        );
      })}
    </div>
  );
}

export default function CategoryHeatmap({
  categories,
  selectedCategory,
  onCategoryClick,
}: CategoryHeatmapProps) {
  if (categories.length === 0) return null;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
      {categories.map((cat) => {
        const isSelected = selectedCategory === cat.category_name;
        const tint = getCategoryTint(cat);
        const ow = (cat.signals.STRONG_OW ?? 0) + (cat.signals.OVERWEIGHT ?? 0);
        const uw = (cat.signals.STRONG_UW ?? 0) + (cat.signals.UNDERWEIGHT ?? 0);

        return (
          <button
            key={cat.category_name}
            onClick={() =>
              onCategoryClick(isSelected ? null : cat.category_name)
            }
            className={`
              rounded-lg border p-3 text-left transition-all cursor-pointer
              ${tint}
              ${isSelected ? "ring-2 ring-teal-500 ring-offset-1" : "hover:shadow-sm"}
            `}
            aria-pressed={isSelected}
            aria-label={`${cat.category_name}: ${cat.fund_count} funds, avg ratio return ${cat.avg_ratio_return.toFixed(2)}%`}
          >
            <p className="text-xs font-semibold text-slate-700 truncate">
              {cat.category_name}
            </p>
            <p className="text-sm font-mono tabular-nums mt-1">
              <span
                className={
                  cat.avg_ratio_return > 0
                    ? "text-emerald-600"
                    : cat.avg_ratio_return < 0
                    ? "text-red-600"
                    : "text-slate-500"
                }
              >
                {cat.avg_ratio_return > 0 ? "+" : ""}
                {cat.avg_ratio_return.toFixed(2)}%
              </span>
            </p>
            <div className="flex items-center gap-2 mt-1.5 text-[10px] text-slate-500">
              <span>{cat.fund_count} funds</span>
              <span className="text-emerald-600">OW:{ow}</span>
              <span className="text-red-600">UW:{uw}</span>
            </div>
            <SignalBar signals={cat.signals} total={cat.fund_count} />
          </button>
        );
      })}
    </div>
  );
}
