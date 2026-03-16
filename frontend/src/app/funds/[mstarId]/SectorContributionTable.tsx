"use client";

import SignalBadge from "@/components/SignalBadge";
import { sectorBgColor } from "@/lib/colors";
import type { FSASDetail, SectorContribution } from "@/types/api";

/** Confidence badge -- color-coded HIGH/MEDIUM/LOW */
function ConfidenceBadge({ confidence }: { confidence: string }) {
  const styles: Record<string, string> = {
    HIGH: "bg-emerald-100 text-emerald-700",
    MEDIUM: "bg-amber-100 text-amber-700",
    LOW: "bg-slate-100 text-slate-600",
  };
  const style =
    styles[confidence.toUpperCase()] ?? "bg-slate-100 text-slate-600";
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium uppercase ${style}`}
    >
      {confidence}
    </span>
  );
}

/** Flat sector row with the sector name merged in */
interface SectorRow extends SectorContribution {
  sector: string;
}

interface SectorContributionTableProps {
  fsas: FSASDetail | null;
}

export default function SectorContributionTable({
  fsas,
}: SectorContributionTableProps) {
  /* Convert sector contributions object to array */
  const sectorArray: SectorRow[] = fsas?.sector_contributions
    ? Object.entries(fsas.sector_contributions).map(([sector, sc]) => ({
        sector,
        ...sc,
      }))
    : [];

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 md:p-6">
      <h3 className="text-base font-semibold text-slate-800 mb-4">
        Sector Contribution Detail
      </h3>
      {sectorArray.length === 0 ? (
        <p className="text-sm text-slate-400 text-center py-8">
          {fsas
            ? "No sector contribution data available"
            : "Sector alignment not computed for this fund"}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Sector
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Fund %
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Benchmark %
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Active Wt
                </th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Signal
                </th>
                <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Confidence
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Contribution
                </th>
              </tr>
            </thead>
            <tbody>
              {sectorArray.map((sc) => (
                <tr
                  key={sc.sector}
                  className="border-b border-slate-100 hover:bg-slate-50"
                >
                  <td className="px-4 py-3 text-sm font-medium text-slate-800">
                    <span className="inline-flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${sectorBgColor(sc.sector)}`} />
                      {sc.sector}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                    {sc.exposure_pct.toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                    {sc.benchmark_weight_pct != null
                      ? `${sc.benchmark_weight_pct.toFixed(1)}%`
                      : "\u2014"}
                  </td>
                  <td
                    className={`px-4 py-3 text-right text-sm font-mono font-semibold ${
                      sc.active_weight != null
                        ? sc.active_weight >= 0
                          ? "text-emerald-600"
                          : "text-red-600"
                        : "text-slate-400"
                    }`}
                  >
                    {sc.active_weight != null
                      ? `${sc.active_weight > 0 ? "+" : ""}${sc.active_weight.toFixed(1)}%`
                      : "\u2014"}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <SignalBadge signal={sc.signal} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <ConfidenceBadge confidence={sc.confidence} />
                  </td>
                  <td
                    className={`px-4 py-3 text-right text-sm font-mono font-semibold ${
                      sc.contribution >= 0
                        ? "text-emerald-600"
                        : "text-red-600"
                    }`}
                  >
                    {sc.contribution >= 0 ? "+" : ""}
                    {sc.contribution.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
