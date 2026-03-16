"use client";

import { formatScore } from "@/lib/formatters";
import TierBadge from "@/components/TierBadge";
import ActionBadge from "@/components/ActionBadge";
import { categoryGroupColor } from "@/lib/colors";
import type { RecommendationDetail, QFSDetail } from "@/types/api";

interface FundHeaderCardProps {
  fundName: string | null;
  mstarId: string;
  categoryName: string | null;
  qfs: QFSDetail | null;
  recommendation: RecommendationDetail | null;
}

export default function FundHeaderCard({
  fundName,
  mstarId,
  categoryName,
  qfs,
  recommendation,
}: FundHeaderCardProps) {
  const rec = recommendation;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 md:p-6 mb-6 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-slate-800">
            {fundName ?? mstarId}
          </h2>
          <p className="text-sm text-slate-500 mt-0.5 inline-flex items-center gap-1.5">
            {mstarId}
            {categoryName && (
              <>
                {" \u00b7 "}
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${categoryGroupColor(categoryName)}`} />
                {categoryName}
              </>
            )}
            {" \u00b7 Computed "}
            {qfs?.computed_date ?? "--"}
          </p>
          <div className="flex items-center gap-3 mt-3">
            <TierBadge tier={rec?.tier ?? "--"} />
            <ActionBadge action={rec?.action ?? "--"} />
            {rec?.is_shortlisted && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-700">
                Shortlisted
              </span>
            )}
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-400">Quantitative Fund Score</p>
          <p className="text-4xl md:text-5xl font-bold font-mono text-teal-600">
            {formatScore(qfs?.qfs)}
          </p>
          <p className="text-sm text-slate-400 font-mono">/100</p>
          {rec?.qfs_rank != null && (
            <p className="text-sm text-slate-500 mt-1 font-mono">
              Rank #{rec.qfs_rank}
              {rec.category_rank_pct != null && (
                <span className="text-xs text-slate-400 ml-1">
                  ({Math.round(rec.category_rank_pct)}th pct)
                </span>
              )}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
