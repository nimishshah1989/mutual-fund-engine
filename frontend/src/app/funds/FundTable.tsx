"use client";

import Link from "next/link";
import type { FundScoreOverview } from "@/types/api";
import TierBadge from "@/components/TierBadge";
import ActionBadge from "@/components/ActionBadge";
import ScoreCell from "./ScoreCell";
import DataCompletenessBar from "./DataCompletenessBar";
import type { SortField } from "./types";

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
                QFS{sortIndicator("qfs", sortField, sortDesc)}
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Tier / Action
              </th>
              <th
                onClick={() => onSort("qfs_rank")}
                className={sortableHeaderClasses}
              >
                QFS Rank{sortIndicator("qfs_rank", sortField, sortDesc)}
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
                  {fund.category_name ?? "--"}
                </td>
                <td className="px-4 py-3 text-right">
                  <ScoreCell value={fund.qfs} />
                </td>
                <td className="px-4 py-3 text-center">
                  <div className="flex items-center justify-center gap-1.5">
                    <TierBadge tier={fund.tier ?? "--"} />
                    <ActionBadge action={fund.action ?? "--"} />
                  </div>
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
