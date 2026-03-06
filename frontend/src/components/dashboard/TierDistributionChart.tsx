"use client";

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";
import type { TierCount } from "./types";
import { TIER_COLORS } from "./types";

interface TierDistributionChartProps {
  tierCounts: TierCount[];
}

export default function TierDistributionChart({
  tierCounts,
}: TierDistributionChartProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="text-base font-semibold text-slate-800 mb-4">
        Tier Distribution
      </h3>
      {tierCounts.length === 0 ? (
        <p className="text-sm text-slate-400 text-center py-8">
          No scored funds yet
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={tierCounts}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={3}
              dataKey="value"
              nameKey="name"
            >
              {tierCounts.map((entry) => (
                <Cell
                  key={entry.name}
                  fill={TIER_COLORS[entry.name] ?? "#94a3b8"}
                />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                borderRadius: "8px",
                border: "1px solid #e2e8f0",
                fontSize: "12px",
              }}
            />
            <Legend
              verticalAlign="middle"
              align="right"
              layout="vertical"
              iconType="circle"
              iconSize={10}
              formatter={(value: string) => (
                <span className="text-xs text-slate-600">{value}</span>
              )}
            />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
