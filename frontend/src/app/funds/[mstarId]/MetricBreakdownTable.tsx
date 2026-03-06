"use client";

import { Fragment } from "react";
import type { QFSDetail, MetricValue } from "@/types/api";

/** Horizons displayed in the metric breakdown table */
const HORIZONS = ["1y", "3y", "5y", "10y"] as const;

/** Pretty-print a metric key: "capture_down" -> "Capture Down" */
function formatMetricName(key: string): string {
  return key
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

interface MetricBreakdownTableProps {
  qfs: QFSDetail | null;
}

export default function MetricBreakdownTable({
  qfs,
}: MetricBreakdownTableProps) {
  const metricNames = qfs?.metric_scores
    ? Object.keys(qfs.metric_scores)
    : [];

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
      <h3 className="text-base font-semibold text-slate-800 mb-4">
        Metric Breakdown
      </h3>
      {metricNames.length === 0 ? (
        <p className="text-sm text-slate-400 text-center py-8">
          No metric data available
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200">
                <th
                  rowSpan={2}
                  className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider align-bottom"
                >
                  Metric
                </th>
                {HORIZONS.map((h) => (
                  <th
                    key={h}
                    colSpan={2}
                    className="text-center px-2 py-2 text-xs font-semibold text-slate-800 uppercase tracking-wider border-b border-slate-100"
                  >
                    {h}
                  </th>
                ))}
              </tr>
              <tr className="border-b border-slate-200">
                {HORIZONS.map((h) => (
                  <Fragment key={h}>
                    <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400 tracking-wider">
                      Raw
                    </th>
                    <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400 tracking-wider">
                      Score
                    </th>
                  </Fragment>
                ))}
              </tr>
            </thead>
            <tbody>
              {metricNames.map((metricKey) => {
                const horizonData: Record<string, MetricValue> =
                  qfs?.metric_scores?.[metricKey] ?? {};

                return (
                  <tr
                    key={metricKey}
                    className="border-b border-slate-100 hover:bg-slate-50"
                  >
                    <td className="px-4 py-3 text-sm font-medium text-slate-800 whitespace-nowrap">
                      {formatMetricName(metricKey)}
                    </td>
                    {HORIZONS.map((h) => {
                      const cell = horizonData[h];
                      return (
                        <Fragment key={h}>
                          <td className="px-3 py-3 text-right text-sm font-mono text-slate-600">
                            {cell?.raw !== null && cell?.raw !== undefined
                              ? cell.raw.toFixed(2)
                              : "--"}
                          </td>
                          <td className="px-3 py-3 text-right text-sm font-mono text-slate-700">
                            {cell?.normalised !== null &&
                            cell?.normalised !== undefined
                              ? cell.normalised.toFixed(1)
                              : "--"}
                          </td>
                        </Fragment>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
