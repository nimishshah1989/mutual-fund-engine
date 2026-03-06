// Reusable table component for displaying must-have and good-to-have
// metric lists with their descriptions and applicable horizons.

import { Metric } from "./constants";

interface MetricsTableProps {
  metrics: Metric[];
  descriptionHeader: string;
}

export default function MetricsTable({
  metrics,
  descriptionHeader,
}: MetricsTableProps) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200">
      <table className="w-full">
        <thead>
          <tr className="bg-slate-50 border-b border-slate-200">
            <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider w-8">
              #
            </th>
            <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Metric
            </th>
            <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              {descriptionHeader}
            </th>
            <th className="text-center px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Horizons
            </th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((metric, idx) => (
            <tr
              key={metric.name}
              className="border-b border-slate-100 last:border-0"
            >
              <td className="px-4 py-2.5 text-xs font-mono text-slate-400">
                {idx + 1}
              </td>
              <td className="px-4 py-2.5 text-sm font-medium text-slate-800">
                {metric.name}
              </td>
              <td className="px-4 py-2.5 text-sm text-slate-500">
                {metric.description}
              </td>
              <td className="px-4 py-2.5 text-xs font-mono text-center text-slate-600">
                {metric.horizons}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
