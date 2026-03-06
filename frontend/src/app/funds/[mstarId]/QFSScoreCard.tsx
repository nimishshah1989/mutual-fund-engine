"use client";

import { formatScore } from "@/lib/formatters";
import type { QFSDetail } from "@/types/api";

interface QFSScoreCardProps {
  qfs: QFSDetail | null;
}

/** Horizon score entry for display */
interface HorizonScore {
  label: string;
  value: number | null;
}

export default function QFSScoreCard({ qfs }: QFSScoreCardProps) {
  const horizonScores: HorizonScore[] = [
    { label: "1Y", value: qfs?.score_1y ?? null },
    { label: "3Y", value: qfs?.score_3y ?? null },
    { label: "5Y", value: qfs?.score_5y ?? null },
    { label: "10Y", value: qfs?.score_10y ?? null },
  ];

  /* Data completeness is already 0-100, no multiplication needed */
  const dataCompleteness = qfs?.data_completeness_pct ?? 0;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="text-base font-semibold text-slate-800 mb-4">
        Layer 1: Quantitative Fund Score
      </h3>
      <div className="text-center mb-4">
        <span className="text-4xl font-bold font-mono text-teal-600">
          {formatScore(qfs?.qfs)}
        </span>
        <span className="text-lg text-slate-400 font-mono">/100</span>
      </div>

      {/* Horizon scores */}
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
        Horizon Scores
      </p>
      <div className="space-y-2">
        {horizonScores.map((hs) => (
          <div key={hs.label} className="flex items-center justify-between">
            <span className="text-sm text-slate-600">{hs.label}</span>
            <span className="text-sm font-mono font-semibold text-slate-800">
              {formatScore(hs.value)}
            </span>
          </div>
        ))}
      </div>

      {/* Data completeness bar */}
      <div className="mt-4">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-slate-500">Data Completeness</span>
          <span className="text-xs font-mono font-semibold text-slate-700">
            {Math.round(dataCompleteness)}%
          </span>
        </div>
        <div className="w-full bg-slate-100 rounded-full h-2">
          <div
            className={`h-2 rounded-full ${
              dataCompleteness >= 80
                ? "bg-emerald-500"
                : dataCompleteness >= 60
                  ? "bg-amber-500"
                  : "bg-red-500"
            }`}
            style={{
              width: `${Math.min(Math.round(dataCompleteness), 100)}%`,
            }}
          />
        </div>
      </div>
    </div>
  );
}
