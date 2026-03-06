"use client";

import Link from "next/link";
import type { FundScoreOverview } from "@/types/api";
import ActionBadge from "@/components/ActionBadge";
import ScoreCell from "./ScoreCell";
import DataCompletenessBar from "./DataCompletenessBar";
import { categoryGroupColor } from "@/lib/colors";
import type { SortField } from "./types";

/* ------------------------------------------------------------------ */
/*  Matrix position badge styling                                      */
/* ------------------------------------------------------------------ */

const MATRIX_BADGE_STYLES: Record<string, string> = {
  HIGH_HIGH: "bg-emerald-100 text-emerald-700",
  HIGH_MID: "bg-blue-100 text-blue-700",
  MID_HIGH: "bg-blue-100 text-blue-700",
  HIGH_LOW: "bg-amber-100 text-amber-700",
  MID_MID: "bg-amber-100 text-amber-700",
  LOW_HIGH: "bg-amber-100 text-amber-700",
  MID_LOW: "bg-orange-100 text-orange-700",
  LOW_MID: "bg-orange-100 text-orange-700",
  LOW_LOW: "bg-red-100 text-red-700",
};

/** Matrix position → action as defined by the 3x3 decision matrix */
const MATRIX_ACTIONS: Record<string, string> = {
  HIGH_HIGH: "ACCUMULATE",
  HIGH_MID: "ACCUMULATE",
  HIGH_LOW: "HOLD",
  MID_HIGH: "ACCUMULATE",
  MID_MID: "HOLD",
  MID_LOW: "REDUCE",
  LOW_HIGH: "HOLD",
  LOW_MID: "REDUCE",
  LOW_LOW: "EXIT",
};

function MatrixBadge({ position }: { position: string | null | undefined }) {
  if (!position) {
    return <span className="text-sm text-slate-400 font-mono">&mdash;</span>;
  }
  const colorClasses = MATRIX_BADGE_STYLES[position] ?? "bg-slate-100 text-slate-600";
  const matrixAction = MATRIX_ACTIONS[position];
  return (
    <span
      title={matrixAction ? `Matrix: ${matrixAction}` : undefined}
      className={`inline-block rounded-full px-2 py-0.5 text-[11px] font-medium whitespace-nowrap ${colorClasses}`}
    >
      {position.replace("_", "/")}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Fund Table -- sortable data table for the fund universe            */
/* ------------------------------------------------------------------ */

interface FundTableProps {
  funds: FundScoreOverview[];
  sortField: SortField;
  sortDesc: boolean;
  onSort: (field: SortField) => void;
}

/** Returns a sort direction indicator arrow or empty string */
function sortIndicator(
  field: SortField,
  activeField: SortField,
  desc: boolean,
): string {
  if (activeField !== field) return "";
  return desc ? " \u25BC" : " \u25B2";
}

const sortableHeaderClasses =
  "px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-600 select-none";

export default function FundTable({
  funds,
  sortField,
  sortDesc,
  onSort,
}: FundTableProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider w-10">
                #
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Fund Name
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Category
              </th>
              <th
                onClick={() => onSort("qfs")}
                className={sortableHeaderClasses}
              >
                Fund Score{sortIndicator("qfs", sortField, sortDesc)}
              </th>
              <th
                onClick={() => onSort("fm_score")}
                className={sortableHeaderClasses}
              >
                FM Score{sortIndicator("fm_score", sortField, sortDesc)}
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Matrix
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Action
              </th>
              <th
                onClick={() => onSort("qfs_rank")}
                className={sortableHeaderClasses}
              >
                Score Rank{sortIndicator("qfs_rank", sortField, sortDesc)}
              </th>
              <th
                onClick={() => onSort("data_completeness_pct")}
                className={sortableHeaderClasses}
              >
                Data Completeness
                {sortIndicator("data_completeness_pct", sortField, sortDesc)}
              </th>
            </tr>
          </thead>
          <tbody>
            {funds.map((fund, idx) => (
              <tr
                key={fund.mstar_id}
                className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
              >
                <td className="px-4 py-3 text-sm text-slate-400 font-mono">
                  {idx + 1}
                </td>
                <td className="px-4 py-3">
                  <Link
                    href={`/funds/${fund.mstar_id}`}
                    className="text-sm font-medium text-slate-800 hover:text-teal-600 transition-colors"
                  >
                    {fund.fund_name ?? fund.mstar_id}
                  </Link>
                  {fund.fund_name && (
                    <span className="block text-[11px] text-slate-400 font-mono">
                      {fund.mstar_id}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-slate-500 max-w-[200px] truncate">
                  <span className="inline-flex items-center gap-1.5">
                    {fund.category_name && (
                      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${categoryGroupColor(fund.category_name)}`} />
                    )}
                    {fund.category_name ?? "--"}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <ScoreCell value={fund.qfs} />
                </td>
                <td className="px-4 py-3 text-right">
                  {fund.fm_score != null ? (
                    <span
                      className={`text-sm font-mono tabular-nums font-semibold ${
                        fund.fm_score > 0
                          ? "text-emerald-600"
                          : fund.fm_score < 0
                          ? "text-red-600"
                          : "text-slate-600"
                      }`}
                    >
                      {fund.fm_score > 0 ? "+" : ""}
                      {fund.fm_score.toFixed(1)}
                    </span>
                  ) : (
                    <span className="text-sm text-slate-400 font-mono">--</span>
                  )}
                </td>
                <td className="px-4 py-3 text-center">
                  <MatrixBadge position={fund.matrix_position} />
                </td>
                <td className="px-4 py-3 text-center">
                  {(() => {
                    const matrixAction = fund.matrix_position
                      ? MATRIX_ACTIONS[fund.matrix_position]
                      : null;
                    const wasOverridden =
                      fund.override_applied && matrixAction && matrixAction !== fund.action;

                    return (
                      <div className="flex flex-col items-center gap-0.5">
                        <ActionBadge action={fund.action ?? "--"} />
                        {wasOverridden && (
                          <span
                            title={fund.override_reason ?? "Override applied"}
                            className="text-[10px] text-amber-600 cursor-help"
                          >
                            Matrix: {matrixAction} &rarr; {fund.action}
                          </span>
                        )}
                      </div>
                    );
                  })()}
                </td>
                <td className="px-4 py-3 text-right text-sm font-mono tabular-nums text-slate-600">
                  {fund.qfs_rank != null ? (
                    <span>
                      {fund.qfs_rank}
                      {fund.category_rank_pct != null && (
                        <span className="text-xs text-slate-400 ml-1">
                          ({Math.round(fund.category_rank_pct)}th pct)
                        </span>
                      )}
                    </span>
                  ) : (
                    "--"
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  <DataCompletenessBar value={fund.data_completeness_pct} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {funds.length === 0 && (
          <div className="py-12 text-center">
            <p className="text-sm font-medium text-slate-600">
              No funds match your filters
            </p>
            <p className="text-xs text-slate-400 mt-1">
              Try adjusting your search or filter criteria
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
