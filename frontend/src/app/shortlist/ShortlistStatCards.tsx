"use client";

import type { ShortlistStats } from "./shortlist-helpers";

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */
interface ShortlistStatCardsProps {
  stats: ShortlistStats;
}

/* ------------------------------------------------------------------ */
/*  Stat card items — defined once, rendered in a loop                 */
/* ------------------------------------------------------------------ */
interface StatCardItem {
  label: string;
  value: string;
  subtitle: string;
  valueColor: string;
}

function buildStatCards(stats: ShortlistStats): StatCardItem[] {
  return [
    {
      label: "Total Shortlisted",
      value: String(stats.totalFunds),
      subtitle: "Funds recommended",
      valueColor: "text-teal-600",
    },
    {
      label: "Categories Covered",
      value: String(stats.categoriesCovered),
      subtitle: "SEBI categories",
      valueColor: "text-slate-800",
    },
    {
      label: "Average Fund Score",
      value: stats.avgQfs.toFixed(1),
      subtitle: "Across shortlisted funds",
      valueColor: "text-teal-600",
    },
    {
      label: "Funds with Alignment",
      value: String(stats.fundsWithFsas),
      subtitle: "Sector alignment scored",
      valueColor: "text-slate-800",
    },
  ];
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */
export default function ShortlistStatCards({
  stats,
}: ShortlistStatCardsProps) {
  const cards = buildStatCards(stats);

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      {cards.map((card) => (
        <div
          key={card.label}
          className="bg-white rounded-xl border border-slate-200 p-5"
        >
          <p className="text-sm text-slate-500">{card.label}</p>
          <p
            className={`text-2xl font-bold font-mono mt-1 ${card.valueColor}`}
          >
            {card.value}
          </p>
          <p className="text-xs text-slate-400 mt-1">{card.subtitle}</p>
        </div>
      ))}
    </div>
  );
}
