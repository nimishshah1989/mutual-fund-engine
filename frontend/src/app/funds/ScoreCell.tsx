"use client";

import { formatScore } from "@/lib/formatters";

/* ------------------------------------------------------------------ */
/*  Score cell -- color-coded QFS score display                        */
/* ------------------------------------------------------------------ */

interface ScoreCellProps {
  value: number | null;
}

export default function ScoreCell({ value }: ScoreCellProps) {
  if (value === null || value === undefined) {
    return <span className="text-sm text-slate-400 font-mono">--</span>;
  }

  let colorClass = "text-slate-600";
  if (value >= 70) colorClass = "text-emerald-600";
  else if (value < 40) colorClass = "text-red-600";

  return (
    <span
      className={`text-sm font-mono tabular-nums font-semibold ${colorClass}`}
    >
      {formatScore(value)}
    </span>
  );
}
