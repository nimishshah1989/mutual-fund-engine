"use client";

/* ------------------------------------------------------------------ */
/*  Data Completeness bar -- percentage bar with color coding          */
/* ------------------------------------------------------------------ */

interface DataCompletenessBarProps {
  value: number | null;
}

export default function DataCompletenessBar({
  value,
}: DataCompletenessBarProps) {
  if (value === null || value === undefined) {
    return <span className="text-xs text-slate-400">--</span>;
  }

  const pct = Math.round(value);
  let barColor = "bg-emerald-500";
  if (pct < 60) barColor = "bg-red-500";
  else if (pct < 80) barColor = "bg-amber-500";

  return (
    <div className="flex items-center justify-end gap-2">
      <span className="text-xs font-mono text-slate-600">{pct}%</span>
      <div className="w-16 bg-slate-100 rounded-full h-1.5">
        <div
          className={`${barColor} h-1.5 rounded-full`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
