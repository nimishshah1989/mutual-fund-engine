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
        Tiers are assigned based on QFS percentile rank within each fund&apos;s
        SEBI category. Actions are determined by tier, then optionally refined
        by FSAS for shortlisted funds.
      </p>

      {/* Formula callout */}
      <div className="bg-slate-50 rounded-lg p-5 border border-slate-100 mb-5">
        <p className="text-center text-sm text-slate-500 mb-2">
          Tier Assignment Rule
        </p>
        <p className="text-center text-lg font-mono font-semibold text-slate-800">
          Tier = f(QFS Percentile Rank within SEBI Category)
        </p>
        <p className="text-center text-xs text-slate-400 mt-2">
          No blended score. QFS filters first, FSAS refines the action for
          shortlisted funds.
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

      {/* FSAS Action Refinement */}
      <FSASRefinement />
    </div>
  );
}

function FSASRefinement() {
  return (
    <>
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mt-6 mb-2">
        FSAS Action Refinement (Shortlisted Funds Only)
      </p>
      <p className="text-sm text-slate-600 mb-3">
        For shortlisted funds, the FSAS score can refine the action within the
        fund&apos;s tier:
      </p>
      <div className="space-y-2 text-sm text-slate-600">
        <div className="flex items-start gap-3 bg-emerald-50 rounded-lg p-3 border border-emerald-100">
          <span className="text-xs font-bold text-emerald-700 bg-emerald-200 rounded px-2 py-0.5 flex-shrink-0">
            UPGRADE
          </span>
          <p>
            QUALITY tier + FSAS &ge; 75 &rarr; action upgraded from SIP to{" "}
            <span className="font-semibold">BUY</span>
          </p>
        </div>
        <div className="flex items-start gap-3 bg-blue-50 rounded-lg p-3 border border-blue-100">
          <span className="text-xs font-bold text-blue-700 bg-blue-200 rounded px-2 py-0.5 flex-shrink-0">
            UPGRADE
          </span>
          <p>
            WATCH tier + FSAS &ge; 70 &rarr; action upgraded from HOLD to{" "}
            <span className="font-semibold">HOLD+</span>
          </p>
        </div>
        <div className="flex items-start gap-3 bg-amber-50 rounded-lg p-3 border border-amber-100">
          <span className="text-xs font-bold text-amber-700 bg-amber-200 rounded px-2 py-0.5 flex-shrink-0">
            DOWNGRADE
          </span>
          <p>
            CORE tier + FSAS &lt; 30 &rarr; action downgraded from BUY to{" "}
            <span className="font-semibold">SIP</span>
          </p>
        </div>
        <div className="flex items-start gap-3 bg-red-50 rounded-lg p-3 border border-red-100">
          <span className="text-xs font-bold text-red-700 bg-red-200 rounded px-2 py-0.5 flex-shrink-0">
            CAP
          </span>
          <p>
            AVOID exposure &gt; 15% &rarr; action capped at{" "}
            <span className="font-semibold">HOLD</span> regardless of tier
          </p>
        </div>
      </div>
    </>
  );
}
