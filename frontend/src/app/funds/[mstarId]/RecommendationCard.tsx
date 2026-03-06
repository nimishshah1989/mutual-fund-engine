"use client";

import { formatScore } from "@/lib/formatters";
import TierBadge from "@/components/TierBadge";
import ActionBadge from "@/components/ActionBadge";
import type { RecommendationDetail } from "@/types/api";

/** Color style for matrix_position badges */
const MATRIX_BADGE_STYLES: Record<string, string> = {
  HIGH_HIGH: "bg-emerald-100 text-emerald-700",
  HIGH_MID: "bg-emerald-100 text-emerald-700",
  HIGH_LOW: "bg-amber-100 text-amber-700",
  MID_HIGH: "bg-blue-100 text-blue-700",
  MID_MID: "bg-blue-100 text-blue-700",
  MID_LOW: "bg-amber-100 text-amber-700",
  LOW_HIGH: "bg-amber-100 text-amber-700",
  LOW_MID: "bg-orange-100 text-orange-700",
  LOW_LOW: "bg-red-100 text-red-700",
};

/** Human-readable label for matrix_position */
function matrixLabel(position: string): string {
  const parts = position.split("_");
  if (parts.length >= 2) {
    return `QFS ${parts[0]} / FMS ${parts[1]}`;
  }
  return position;
}

interface RecommendationCardProps {
  recommendation: RecommendationDetail | null;
}

export default function RecommendationCard({
  recommendation,
}: RecommendationCardProps) {
  const rec = recommendation;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="text-base font-semibold text-slate-800 mb-4">
        Recommendation
      </h3>
      {rec ? (
        <>
          {/* Matrix position badge */}
          {rec.matrix_position != null && (
            <div className="flex justify-center mb-3">
              <span
                className={`inline-block rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wide ${
                  MATRIX_BADGE_STYLES[rec.matrix_position] ??
                  "bg-slate-100 text-slate-600"
                }`}
              >
                {matrixLabel(rec.matrix_position)}
              </span>
            </div>
          )}

          {/* Tier and action badges */}
          <div className="flex items-center justify-center gap-3 mb-4">
            <TierBadge tier={rec.tier} />
            <ActionBadge action={rec.action} />
          </div>

          {/* QFS and FM Score percentiles — 2-column layout */}
          {(rec.qfs_percentile != null || rec.fm_score_percentile != null) && (
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="bg-slate-50 rounded-lg p-3 text-center">
                <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">
                  QFS Percentile
                </p>
                <p className="text-lg font-bold font-mono text-slate-800">
                  {rec.qfs_percentile != null
                    ? `${Math.round(rec.qfs_percentile)}th`
                    : "--"}
                </p>
              </div>
              <div className="bg-slate-50 rounded-lg p-3 text-center">
                <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">
                  FMS Percentile
                </p>
                <p className="text-lg font-bold font-mono text-slate-800">
                  {rec.fm_score_percentile != null
                    ? `${Math.round(rec.fm_score_percentile)}th`
                    : "--"}
                </p>
              </div>
            </div>
          )}

          {/* Key metrics */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600">QFS</span>
              <span className="text-sm font-mono font-semibold text-teal-600">
                {formatScore(rec.qfs)}
              </span>
            </div>
            {rec.fm_score != null && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">FM Score</span>
                <span className="text-sm font-mono font-semibold text-teal-600">
                  {formatScore(rec.fm_score)}
                </span>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600">Score Rank</span>
              <span className="text-sm font-mono font-semibold text-slate-800">
                #{rec.qfs_rank}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600">Category Percentile</span>
              <span className="text-sm font-mono font-semibold text-slate-800">
                {rec.category_rank_pct != null
                  ? `${Math.round(rec.category_rank_pct)}th`
                  : "--"}
              </span>
            </div>
            {rec.fsas != null && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">Sector Alignment</span>
                <span className="text-sm font-mono font-semibold text-teal-600">
                  {formatScore(rec.fsas)}
                </span>
              </div>
            )}
          </div>

          {/* Override info */}
          <div className="mt-4 pt-4 border-t border-slate-100">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600">Override Applied</span>
              <span
                className={`text-xs font-bold uppercase px-2.5 py-0.5 rounded ${
                  rec.override_applied
                    ? "bg-amber-100 text-amber-700"
                    : "bg-slate-100 text-slate-500"
                }`}
              >
                {rec.override_applied ? "Yes" : "No"}
              </span>
            </div>
            {rec.override_reason && (
              <p className="text-xs text-slate-400 mt-1">
                {rec.override_reason}
              </p>
            )}
            {rec.original_tier && rec.override_applied && (
              <p className="text-xs text-slate-400 mt-1">
                Original tier: {rec.original_tier}
              </p>
            )}
          </div>

          {/* Action rationale */}
          {rec.action_rationale && (
            <div className="mt-4 pt-4 border-t border-slate-100">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                Action Rationale
              </p>
              <p className="text-xs text-slate-600 leading-relaxed">
                {rec.action_rationale}
              </p>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-8">
          <p className="text-sm text-slate-400">
            No recommendation data yet
          </p>
          <p className="text-xs text-slate-400 mt-1">
            Run the scoring pipeline to generate recommendations
          </p>
        </div>
      )}
    </div>
  );
}
