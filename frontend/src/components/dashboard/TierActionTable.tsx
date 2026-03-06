"use client";

import TierBadge from "@/components/TierBadge";
import type { TierActionRow } from "./types";

interface TierActionTableProps {
  rows: TierActionRow[];
}

/** Format a cell value: show "--" for zero, otherwise the number */
function cellValue(count: number): string {
  return count === 0 ? "--" : String(count);
}

const ACTION_HEADERS = [
  "ACCUMULATE",
  "HOLD",
  "REDUCE",
  "EXIT",
  "Total",
] as const;

export default function TierActionTable({ rows }: TierActionTableProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 mt-6">
      <h3 className="text-base font-semibold text-slate-800 mb-4">
        Tier &times; Action Breakdown
      </h3>
      {rows.length === 0 ? (
        <p className="text-sm text-slate-400 text-center py-8">
          No scored funds yet
        </p>
      ) : (
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Tier
              </th>
              {ACTION_HEADERS.map((header) => (
                <th
                  key={header}
                  className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.tier}
                className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
              >
                <td className="px-4 py-3">
                  <TierBadge tier={row.tier} />
                </td>
                <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                  {cellValue(row.accumulate)}
                </td>
                <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                  {cellValue(row.hold)}
                </td>
                <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                  {cellValue(row.reduce)}
                </td>
                <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                  {cellValue(row.exit)}
                </td>
                <td className="px-4 py-3 text-right text-sm font-mono font-semibold text-slate-800">
                  {row.total}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
