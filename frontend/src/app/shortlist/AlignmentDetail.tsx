"use client";

import type { AlignmentSummary, SectorAlignmentEntry } from "@/types/api";
import SignalBadge from "@/components/SignalBadge";
import { sectorBgColor } from "@/lib/colors";

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */
interface AlignmentDetailProps {
  summary: AlignmentSummary;
  rationale: string | null;
}

/* ------------------------------------------------------------------ */
/*  Reusable sub-table for aligned / misaligned sectors                */
/* ------------------------------------------------------------------ */
interface SectorTableProps {
  entries: SectorAlignmentEntry[];
  emptyMessage: string;
  contributionColor: string;
  /** If true, prefix contribution with "+" */
  showPlusSign: boolean;
}

function SectorTable({
  entries,
  emptyMessage,
  contributionColor,
  showPlusSign,
}: SectorTableProps) {
  if (entries.length === 0) {
    return <p className="text-xs text-slate-400">{emptyMessage}</p>;
  }

  return (
    <table className="w-full">
      <thead>
        <tr className="border-b border-slate-200">
          <th className="text-left px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Sector
          </th>
          <th className="text-center px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Signal
          </th>
          <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Exposure
          </th>
          <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Contribution
          </th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry) => (
          <tr key={entry.sector} className="border-b border-slate-100">
            <td className="px-3 py-2 text-sm text-slate-700">
              <span className="inline-flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${sectorBgColor(entry.sector)}`} />
                {entry.sector}
              </span>
            </td>
            <td className="px-3 py-2 text-center">
              <SignalBadge signal={entry.signal} />
            </td>
            <td className="px-3 py-2 text-right text-sm font-mono text-slate-600">
              {entry.exposure_pct.toFixed(1)}%
            </td>
            <td
              className={`px-3 py-2 text-right text-sm font-mono ${contributionColor}`}
            >
              {showPlusSign ? "+" : ""}
              {entry.contribution.toFixed(2)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/* ------------------------------------------------------------------ */
/*  Main expanded-row component                                        */
/* ------------------------------------------------------------------ */
export default function AlignmentDetail({
  summary,
  rationale,
}: AlignmentDetailProps) {
  return (
    <tr>
      <td colSpan={10} className="p-0">
        <div className="bg-slate-50 border-l-4 border-l-teal-500 p-6">
          {/* Action rationale */}
          {rationale && (
            <p className="text-sm text-slate-600 mb-4 italic">{rationale}</p>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Aligned sectors */}
            <div>
              <h4 className="text-sm font-semibold text-emerald-700 mb-3 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                Aligned Sectors
              </h4>
              <SectorTable
                entries={summary.aligned_sectors}
                emptyMessage="No aligned sectors for this fund."
                contributionColor="text-emerald-600"
                showPlusSign
              />
            </div>

            {/* Misaligned sectors */}
            <div>
              <h4 className="text-sm font-semibold text-red-600 mb-3 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-red-500" />
                Misaligned Sectors
              </h4>
              <SectorTable
                entries={summary.misaligned_sectors}
                emptyMessage="No misaligned sectors for this fund."
                contributionColor="text-red-600"
                showPlusSign={false}
              />
            </div>
          </div>

          {/* Neutral sectors (if any) */}
          {summary.neutral_sectors.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-200">
              <p className="text-xs text-slate-400">
                <span className="font-semibold text-slate-500">
                  Neutral sectors:{" "}
                </span>
                {summary.neutral_sectors.join(", ")}
              </p>
            </div>
          )}
        </div>
      </td>
    </tr>
  );
}
