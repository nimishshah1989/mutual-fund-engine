"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { formatScore } from "@/lib/formatters";
import type { FSASDetail } from "@/types/api";

interface FSASScoreCardProps {
  fsas: FSASDetail | null;
}

/** Flat sector row derived from the FSAS sector_contributions object */
interface SectorChartEntry {
  sector: string;
  contribution: number;
}

export default function FSASScoreCard({ fsas }: FSASScoreCardProps) {
  /* Convert sector contributions object to sorted array for the chart */
  const sectorChartData: SectorChartEntry[] = fsas?.sector_contributions
    ? Object.entries(fsas.sector_contributions)
        .map(([sector, sc]) => ({ sector, contribution: sc.contribution }))
        .sort((a, b) => b.contribution - a.contribution)
    : [];

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="text-base font-semibold text-slate-800 mb-4">
        Layer 2: Sector Alignment Score
      </h3>
      {fsas ? (
        <>
          <div className="text-center mb-4">
            <span className="text-4xl font-bold font-mono text-teal-600">
              {formatScore(fsas.fsas)}
            </span>
            <span className="text-lg text-slate-400 font-mono">/100</span>
          </div>

          {/* Avoid exposure & stale holdings flags */}
          <div className="mb-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-500">Avoid Exposure</span>
              <span className="text-xs font-mono font-semibold text-red-600">
                {fsas.avoid_exposure_pct.toFixed(1)}%
              </span>
            </div>
            <div className="flex items-center justify-between mt-1">
              <span className="text-xs text-slate-500">Stale Holdings</span>
              <span
                className={`text-xs font-bold uppercase px-2.5 py-0.5 rounded ${
                  fsas.stale_holdings_flag
                    ? "bg-amber-100 text-amber-700"
                    : "bg-slate-100 text-slate-500"
                }`}
              >
                {fsas.stale_holdings_flag ? "Yes" : "No"}
              </span>
            </div>
          </div>

          {/* Sector contribution horizontal bar chart */}
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Sector Contributions
          </p>
          {sectorChartData.length > 0 ? (
            <ResponsiveContainer
              width="100%"
              height={Math.max(180, sectorChartData.length * 28)}
            >
              <BarChart
                data={sectorChartData}
                layout="vertical"
                margin={{ left: 0, right: 10, top: 5, bottom: 5 }}
              >
                <XAxis type="number" hide />
                <YAxis
                  type="category"
                  dataKey="sector"
                  tick={{ fontSize: 10, fill: "#94a3b8" }}
                  width={90}
                />
                <Tooltip
                  contentStyle={{
                    borderRadius: "8px",
                    border: "1px solid #e2e8f0",
                    fontSize: "12px",
                  }}
                  formatter={(value) => [
                    typeof value === "number"
                      ? value.toFixed(2)
                      : String(value),
                    "Contribution",
                  ]}
                />
                <Bar dataKey="contribution" radius={[0, 4, 4, 0]}>
                  {sectorChartData.map((entry, idx) => (
                    <Cell
                      key={idx}
                      fill={entry.contribution >= 0 ? "#059669" : "#dc2626"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-slate-400 text-center py-6">
              No sector data available
            </p>
          )}
        </>
      ) : (
        <div className="text-center py-8">
          <p className="text-sm text-slate-400">
            Sector alignment not computed for this fund
          </p>
          <p className="text-xs text-slate-400 mt-1">
            Only shortlisted funds receive sector alignment scoring
          </p>
        </div>
      )}
    </div>
  );
}
