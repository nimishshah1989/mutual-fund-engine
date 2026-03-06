"use client";

import type { ActionDistributionRow } from "./types";
import { ACTION_COLORS } from "./types";

interface TierActionTableProps {
  rows: ActionDistributionRow[];
}

/** Format a cell value: show "--" for zero, otherwise the number */
function cellValue(count: number): string {
  return count === 0 ? "--" : String(count);
}

/** Format percentage to 1 decimal place */
function formatPct(pct: number): string {
  if (pct === 0) return "--";
  return `${pct.toFixed(1)}%`;
}

const COLUMN_HEADERS = ["Action", "Fund Count", "% of Total"] as const;

export default function TierActionTable({ rows }: TierActionTableProps) {
  const totalFunds = rows.reduce((sum, r) => sum + r.count, 0);

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 mt-6">
      <h3 className="text-base font-semibold text-slate-800 mb-4">
        Action Distribution
      </h3>
      {rows.length === 0 || totalFunds === 0 ? (
        <p className="text-sm text-slate-400 text-center py-8">
          No scored funds yet
        </p>
      ) : (
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-200">
              {COLUMN_HEADERS.map((header, idx) => (
                <th
                  key={header}
                  className={`${idx === 0 ? "text-left" : "text-right"} px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider`}
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const colors = ACTION_COLORS[row.action] ?? {
                bg: "bg-slate-50",
                text: "text-slate-600",
                dot: "bg-slate-400",
              };

              return (
                <tr
                  key={row.action}
                  className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-2.5 h-2.5 rounded-full ${colors.dot}`}
                      />
                      <span className="text-sm font-semibold text-slate-700">
                        {row.action}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                    {cellValue(row.count)}
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                    {formatPct(row.pct)}
                  </td>
                </tr>
              );
            })}
            {/* Totals row */}
            <tr className="border-t border-slate-200 bg-slate-50">
              <td className="px-4 py-3 text-sm font-semibold text-slate-800">
                Total
              </td>
              <td className="px-4 py-3 text-right text-sm font-mono font-semibold text-slate-800">
                {totalFunds}
              </td>
              <td className="px-4 py-3 text-right text-sm font-mono font-semibold text-slate-800">
                100%
              </td>
            </tr>
          </tbody>
        </table>
      )}
    </div>
  );
}
