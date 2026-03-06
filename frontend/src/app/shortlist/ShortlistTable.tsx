"use client";

import { useState } from "react";
import { formatScore } from "@/lib/formatters";
import type { ShortlistItem } from "@/types/api";
import TierBadge from "@/components/TierBadge";
import ActionBadge from "@/components/ActionBadge";
import AlignmentDetail from "./AlignmentDetail";
import { categoryGroupColor } from "@/lib/colors";
import {
  type CategoryGroup,
  type ShortlistSortField,
  scoreColorClass,
  avoidExposureClass,
  topAlignedSectorNames,
} from "./shortlist-helpers";

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */
interface ShortlistTableProps {
  categoryGroups: CategoryGroup[];
  sortField: ShortlistSortField | null;
  sortDesc: boolean;
  onSort: (field: ShortlistSortField) => void;
}

/* ------------------------------------------------------------------ */
/*  Single fund row component                                          */
/* ------------------------------------------------------------------ */
interface FundRowProps {
  fund: ShortlistItem;
  rowIndex: number;
  isExpanded: boolean;
  onToggle: (mstarId: string) => void;
}

function FundRow({ fund, rowIndex, isExpanded, onToggle }: FundRowProps) {
  const hasAlignment = fund.alignment_summary !== null;

  return (
    <>
      <tr
        onClick={hasAlignment ? () => onToggle(fund.mstar_id) : undefined}
        className={`border-b border-slate-100 transition-colors ${
          hasAlignment ? "cursor-pointer hover:bg-slate-50" : ""
        } ${isExpanded ? "bg-teal-50/40" : ""}`}
      >
        {/* Row number */}
        <td className="px-4 py-3 text-sm text-slate-400 font-mono tabular-nums">
          {rowIndex}
        </td>

        {/* Fund Name */}
        <td className="px-4 py-3 text-sm font-medium text-slate-800">
          <div className="flex items-center gap-2">
            {fund.fund_name ?? fund.mstar_id}
            {hasAlignment && (
              <span
                className={`text-slate-400 text-xs transition-transform ${
                  isExpanded ? "rotate-90" : ""
                }`}
              >
                &#9654;
              </span>
            )}
          </div>
        </td>

        {/* Category */}
        <td className="px-4 py-3 text-sm text-slate-500">
          {fund.category_name}
        </td>

        {/* QFS */}
        <td
          className={`px-4 py-3 text-right text-sm font-mono tabular-nums font-semibold ${scoreColorClass(
            fund.qfs_score,
          )}`}
        >
          {formatScore(fund.qfs_score)}
        </td>

        {/* QFS Rank */}
        <td className="px-4 py-3 text-right text-sm font-mono tabular-nums text-slate-600">
          {fund.qfs_rank}/{fund.total_in_category}
        </td>

        {/* FSAS */}
        <td
          className={`px-4 py-3 text-right text-sm font-mono tabular-nums font-semibold ${scoreColorClass(
            fund.fsas,
          )}`}
        >
          {formatScore(fund.fsas)}
        </td>

        {/* Tier */}
        <td className="px-4 py-3 text-center">
          {fund.tier ? (
            <TierBadge tier={fund.tier} />
          ) : (
            <span className="text-xs text-slate-400">--</span>
          )}
        </td>

        {/* Action */}
        <td className="px-4 py-3 text-center">
          {fund.action ? (
            <ActionBadge action={fund.action} />
          ) : (
            <span className="text-xs text-slate-400">--</span>
          )}
        </td>

        {/* Top Aligned Sectors */}
        <td className="px-4 py-3 text-sm text-slate-500 max-w-[200px] truncate">
          {topAlignedSectorNames(fund.alignment_summary)}
        </td>

        {/* Avoid Exposure % */}
        <td
          className={`px-4 py-3 text-right text-sm font-mono tabular-nums ${avoidExposureClass(
            fund.avoid_exposure_pct,
          )}`}
        >
          {fund.avoid_exposure_pct !== null &&
          fund.avoid_exposure_pct !== undefined
            ? `${fund.avoid_exposure_pct.toFixed(1)}%`
            : "--"}
        </td>
      </tr>

      {/* Expanded detail row */}
      {isExpanded && fund.alignment_summary && (
        <AlignmentDetail summary={fund.alignment_summary} rationale={null} />
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Sort indicator arrow                                               */
/* ------------------------------------------------------------------ */
function SortIndicator({
  field,
  activeField,
  desc,
}: {
  field: ShortlistSortField;
  activeField: ShortlistSortField | null;
  desc: boolean;
}) {
  if (activeField !== field) {
    // Show a subtle indicator that the column is sortable
    return (
      <span className="ml-1 text-slate-300 text-[10px]">&#9650;&#9660;</span>
    );
  }
  return (
    <span className="ml-1 text-teal-600 text-xs">
      {desc ? "\u25BC" : "\u25B2"}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Column definitions                                                 */
/* ------------------------------------------------------------------ */
interface ColumnDef {
  label: string;
  align: string;
  width: string;
  sortField?: ShortlistSortField;
}

const COLUMNS: readonly ColumnDef[] = [
  { label: "#", align: "text-left", width: "w-10" },
  { label: "Fund Name", align: "text-left", width: "" },
  { label: "Category", align: "text-left", width: "" },
  { label: "Fund Score", align: "text-right", width: "", sortField: "qfs_score" },
  { label: "Score Rank", align: "text-right", width: "" },
  { label: "Alignment", align: "text-right", width: "", sortField: "fsas" },
  { label: "Tier", align: "text-center", width: "" },
  { label: "Action", align: "text-center", width: "" },
  { label: "Top Aligned Sectors", align: "text-left", width: "" },
  { label: "Avoid Exposure %", align: "text-right", width: "", sortField: "avoid_exposure_pct" },
] as const;

/* ------------------------------------------------------------------ */
/*  Main table component                                               */
/* ------------------------------------------------------------------ */
export default function ShortlistTable({
  categoryGroups,
  sortField,
  sortDesc,
  onSort,
}: ShortlistTableProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  function toggleExpand(mstarId: string) {
    setExpandedId((prev) => (prev === mstarId ? null : mstarId));
  }

  /* Build a running global index across all groups */
  let globalIndex = 0;

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-200">
              {COLUMNS.map((col) => {
                const isSortable = col.sortField !== undefined;
                const isActive = sortField === col.sortField;

                return (
                  <th
                    key={col.label}
                    onClick={
                      isSortable && col.sortField
                        ? () => onSort(col.sortField!)
                        : undefined
                    }
                    className={`px-4 py-3 ${col.align} text-xs font-semibold text-slate-400 uppercase tracking-wider ${col.width} ${
                      isSortable
                        ? "cursor-pointer select-none hover:text-slate-600 transition-colors"
                        : ""
                    } ${isActive ? "text-teal-600" : ""}`}
                  >
                    <span className="inline-flex items-center">
                      {col.label}
                      {isSortable && col.sortField && (
                        <SortIndicator
                          field={col.sortField}
                          activeField={sortField}
                          desc={sortDesc}
                        />
                      )}
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {categoryGroups.map((group) => {
              const rows: React.ReactNode[] = [];

              {/* Category separator row */}
              rows.push(
                <tr key={`cat-${group.category}`}>
                  <td
                    colSpan={10}
                    className="bg-slate-50 px-4 py-2.5 font-semibold text-slate-600 text-sm border-b border-slate-200"
                  >
                    <span className="inline-flex items-center gap-2">
                      <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${categoryGroupColor(group.category)}`} />
                      {group.category}
                    <span className="ml-2 text-xs font-normal text-slate-400">
                      ({group.funds.length}{" "}
                      {group.funds.length === 1 ? "fund" : "funds"})
                    </span>
                    </span>
                  </td>
                </tr>,
              );

              {/* Fund rows within this category */}
              for (const fund of group.funds) {
                globalIndex += 1;
                rows.push(
                  <FundRow
                    key={fund.mstar_id}
                    fund={fund}
                    rowIndex={globalIndex}
                    isExpanded={expandedId === fund.mstar_id}
                    onToggle={toggleExpand}
                  />,
                );
              }

              return rows;
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
