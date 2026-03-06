// Step 4: Tier and Action Assignment section. Shows the percentile-based
// tier thresholds table and the FSAS action refinement rules.

import { TIER_PERCENTILES } from "./constants";

export default function TierActionSection() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
      <h3 className="text-base font-semibold text-slate-800 mb-1">
        Step 4: Tier &amp; Action Assignment
      </h3>
      <p className="text-sm text-slate-500 mb-4">
        Tiers are assigned based on Fund Score percentile rank within each
        fund&apos;s SEBI category. Each tier maps directly to one action.
      </p>

      {/* Formula callout */}
      <div className="bg-slate-50 rounded-lg p-5 border border-slate-100 mb-5">
        <p className="text-center text-sm text-slate-500 mb-2">
          Tier Assignment Rule
        </p>
        <p className="text-center text-lg font-mono font-semibold text-slate-800">
          Tier = f(Fund Score Percentile Rank within SEBI Category)
        </p>
        <p className="text-center text-xs text-slate-400 mt-2">
          Each tier maps directly to one action. Sector Alignment Score provides
          context but does not modify the action.
        </p>
      </div>

      {/* Tier table */}
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
        Percentile-Based Tier Thresholds
      </p>
      <div className="overflow-hidden rounded-lg border border-slate-200">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Tier
              </th>
              <th className="text-center px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Percentile Range
              </th>
              <th className="text-center px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Default Action
              </th>
              <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Description
              </th>
            </tr>
          </thead>
          <tbody>
            {TIER_PERCENTILES.map((t) => (
              <tr
                key={t.tier}
                className="border-b border-slate-100 last:border-0"
              >
                <td className="px-4 py-3">
                  <span
                    className={`inline-block rounded px-2.5 py-0.5 text-xs font-bold ${t.color}`}
                  >
                    {t.tier}
                  </span>
                </td>
                <td className="px-4 py-3 text-center text-sm font-mono text-slate-700">
                  {t.range}
                </td>
                <td className="px-4 py-3 text-center text-sm font-semibold text-slate-700">
                  {t.action}
                </td>
                <td className="px-4 py-3 text-sm text-slate-500">
                  {t.description}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Sector Alignment context note */}
      <div className="mt-5 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm font-semibold text-blue-800">
          Role of Sector Alignment Score
        </p>
        <p className="text-sm text-blue-700 mt-1">
          The Sector Alignment Score is computed for shortlisted funds and
          displayed for context, but it does not modify the action. Actions are
          determined purely by tier classification.
        </p>
      </div>
    </div>
  );
}
