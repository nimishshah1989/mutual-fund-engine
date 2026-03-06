"use client";

import { formatScore } from "@/lib/formatters";
import TierBadge from "@/components/TierBadge";
import ActionBadge from "@/components/ActionBadge";
import type { RecommendationDetail } from "@/types/api";

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
          {/* Tier and action badges */}
          <div className="flex items-center justify-center gap-3 mb-4">
            <TierBadge tier={rec.tier} />
            <ActionBadge action={rec.action} />
          </div>

          {/* Key metrics */}
          <div className="space-y-3">
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
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600">Shortlisted</span>
              <span
                className={`text-xs font-bold uppercase px-2.5 py-0.5 rounded ${
                  rec.is_shortlisted
                    ? "bg-amber-100 text-amber-700"
                    : "bg-slate-100 text-slate-500"
                }`}
              >
                {rec.is_shortlisted ? "Yes" : "No"}
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
