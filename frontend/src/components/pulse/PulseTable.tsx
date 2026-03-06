"use client";

import Link from "next/link";
import type { PulseFundItem } from "@/types/pulse";
import PulseSignalBadge from "./PulseSignalBadge";

interface PulseTableProps {
  funds: PulseFundItem[];
  sortField: string;
  sortDesc: boolean;
  onSort: (field: string) => void;
}

/* ---- Quadrant badge (HIGH / MID / LOW) ---- */
function QuadrantBadge({ value }: { value: string | null }) {
  if (!value) return <span className="text-slate-300 text-xs">--</span>;

  const styles: Record<string, string> = {
    HIGH: "bg-emerald-50 text-emerald-700",
    MID: "bg-amber-50 text-amber-700",
    LOW: "bg-red-50 text-red-700",
  };
  const style = styles[value.toUpperCase()] ?? "bg-slate-50 text-slate-500";

  return (
    <span className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${style}`}>
      {value}
    </span>
  );
}

/* ---- Sort header ---- */
function SortHeader({
  label,
  field,
  currentSort,
  sortDesc,
  onSort,
  align = "right",
}: {
  label: string;
  field: string;
  currentSort: string;
  sortDesc: boolean;
  onSort: (field: string) => void;
  align?: "left" | "right";
}) {
  const isActive = currentSort === field;
  const arrow = isActive ? (sortDesc ? " \u25BC" : " \u25B2") : "";

  return (
    <th
      className={`px-3 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400 cursor-pointer hover:text-slate-600 select-none whitespace-nowrap ${
        align === "left" ? "text-left" : "text-right"
      }`}
      onClick={() => onSort(field)}
      aria-sort={isActive ? (sortDesc ? "descending" : "ascending") : "none"}
    >
      {label}
      {arrow}
    </th>
  );
}

/* ---- Format number with sign ---- */
function formatReturn(val: number | null): string {
  if (val === null || val === undefined) return "--";
  const sign = val >= 0 ? "+" : "";
  return `${sign}${val.toFixed(2)}%`;
}

function formatScore(val: number | null): string {
  if (val === null || val === undefined) return "--";
  return val.toFixed(1);
}

/* ---- Return color ---- */
function returnColor(val: number | null): string {
  if (val === null) return "text-slate-400";
  if (val > 0) return "text-emerald-600";
  if (val < 0) return "text-red-600";
  return "text-slate-500";
}

export default function PulseTable({
  funds,
  sortField,
  sortDesc,
  onSort,
}: PulseTableProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm" role="table">
          <thead className="border-b border-slate-200 bg-slate-50/50">
            <tr>
              <SortHeader label="Fund" field="fund_name" currentSort={sortField} sortDesc={sortDesc} onSort={onSort} align="left" />
              <SortHeader label="Category" field="category_name" currentSort={sortField} sortDesc={sortDesc} onSort={onSort} align="left" />
              <SortHeader label="QFS" field="qfs" currentSort={sortField} sortDesc={sortDesc} onSort={onSort} />
              <SortHeader label="FMS" field="fm_score" currentSort={sortField} sortDesc={sortDesc} onSort={onSort} />
              <th className="px-3 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400 text-center whitespace-nowrap">QFS Q</th>
              <th className="px-3 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400 text-center whitespace-nowrap">FM Q</th>
              <SortHeader label="Ratio Ret" field="ratio_return" currentSort={sortField} sortDesc={sortDesc} onSort={onSort} />
              <SortHeader label="Fund Ret" field="fund_return" currentSort={sortField} sortDesc={sortDesc} onSort={onSort} />
              <SortHeader label="Signal" field="signal" currentSort={sortField} sortDesc={sortDesc} onSort={onSort} align="left" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {funds.map((fund) => (
              <tr
                key={fund.mstar_id}
                className="hover:bg-slate-50/50 transition-colors"
              >
                {/* Fund name */}
                <td className="px-3 py-2.5 max-w-[220px]">
                  <Link
                    href={`/funds/${fund.mstar_id}`}
                    className="text-sm font-medium text-slate-700 hover:text-teal-600 truncate block"
                    title={fund.fund_name ?? fund.mstar_id}
                  >
                    {fund.fund_name ?? fund.mstar_id}
                  </Link>
                </td>

                {/* Category */}
                <td className="px-3 py-2.5 text-xs text-slate-500 max-w-[160px] truncate">
                  {fund.category_name ?? "--"}
                </td>

                {/* QFS Score */}
                <td className="px-3 py-2.5 text-right font-mono tabular-nums text-sm text-slate-700">
                  {formatScore(fund.qfs)}
                </td>

                {/* FM Score */}
                <td className="px-3 py-2.5 text-right font-mono tabular-nums text-sm text-slate-700">
                  {formatScore(fund.fm_score)}
                </td>

                {/* QFS Quadrant */}
                <td className="px-3 py-2.5 text-center">
                  <QuadrantBadge value={fund.qfs_quadrant} />
                </td>

                {/* FM Quadrant */}
                <td className="px-3 py-2.5 text-center">
                  <QuadrantBadge value={fund.fm_quadrant} />
                </td>

                {/* Ratio Return */}
                <td className={`px-3 py-2.5 text-right font-mono tabular-nums text-sm ${returnColor(fund.ratio_return)}`}>
                  {formatReturn(fund.ratio_return)}
                </td>

                {/* Fund Return */}
                <td className={`px-3 py-2.5 text-right font-mono tabular-nums text-sm ${returnColor(fund.fund_return)}`}>
                  {formatReturn(fund.fund_return)}
                </td>

                {/* Signal */}
                <td className="px-3 py-2.5">
                  <PulseSignalBadge signal={fund.signal} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
