"use client";

import PageHeader from "@/components/PageHeader";

const TIER_PERCENTILES = [
  { tier: "CORE", range: "90th - 100th", action: "BUY", color: "bg-emerald-600 text-white", description: "Top 10% of category by QFS. High conviction for fresh deployment. Shortlisted funds with strong FSAS may get BUY action." },
  { tier: "QUALITY", range: "70th - 89th", action: "SIP", color: "bg-blue-600 text-white", description: "Solid funds in the top 30%. Suitable for systematic investment. Shortlisted funds with high sector alignment may be upgraded to BUY." },
  { tier: "WATCH", range: "40th - 69th", action: "HOLD", color: "bg-amber-500 text-white", description: "Middle of the pack. Existing positions may be held but new investment is not recommended. High FSAS may upgrade to HOLD+." },
  { tier: "CAUTION", range: "20th - 39th", action: "REDUCE", color: "bg-orange-500 text-white", description: "Below-average performers. Consider reducing exposure and reallocating to higher-tier funds." },
  { tier: "EXIT", range: "0th - 19th", action: "EXIT", color: "bg-red-600 text-white", description: "Bottom 20% of category. Redeem and reallocate capital to higher-tier funds." },
];

const QFS_METRICS = [
  { name: "Returns vs Category Average", description: "How the fund's trailing returns compare to the average of its SEBI category peers" },
  { name: "Returns vs Benchmark", description: "Fund's excess return (alpha) over its primary benchmark index" },
  { name: "Sharpe Ratio", description: "Risk-adjusted return measuring excess return per unit of volatility" },
  { name: "Sortino Ratio", description: "Similar to Sharpe but only penalises downside deviation, not total volatility" },
  { name: "Alpha", description: "Fund manager's value addition above what the benchmark delivers" },
  { name: "Beta", description: "Fund's sensitivity to market movements. Lower beta = less market risk" },
  { name: "R-Squared", description: "How closely the fund tracks its benchmark. Higher = more index-like" },
  { name: "Standard Deviation", description: "Total volatility of the fund's returns. Lower = more stable" },
  { name: "Max Drawdown", description: "Largest peak-to-trough decline. Measures worst-case loss scenario" },
  { name: "Information Ratio", description: "Consistency of outperformance relative to tracking error" },
  { name: "Treynor Ratio", description: "Excess return per unit of systematic (market) risk" },
  { name: "Up Capture Ratio", description: "How much of the market's upside the fund captures during rallies" },
  { name: "Down Capture Ratio", description: "How much of the market's downside the fund absorbs during declines" },
];

const HORIZONS = [
  { period: "1 Year", weight: "15%", description: "Recent performance signal" },
  { period: "3 Years", weight: "30%", description: "Medium-term consistency" },
  { period: "5 Years", weight: "35%", description: "Core evaluation window" },
  { period: "10 Years", weight: "20%", description: "Long-term track record" },
];

const V2_ACTIONS = [
  { action: "BUY", tier: "CORE", description: "Deploy fresh capital. Highest conviction based on quantitative strength and sector alignment." },
  { action: "SIP", tier: "QUALITY", description: "Systematic investment. Consistent performer suitable for periodic allocation." },
  { action: "HOLD+", tier: "WATCH (with FSAS)", description: "Hold with added conviction. WATCH-tier fund with strong sector alignment warrants keeping the position." },
  { action: "HOLD", tier: "WATCH", description: "Maintain existing position. No new investment recommended." },
  { action: "REDUCE", tier: "CAUTION", description: "Reduce exposure. Below-average performer — shift capital to better alternatives." },
  { action: "EXIT", tier: "EXIT", description: "Full redemption. Bottom of category with no sector alignment support." },
];

export default function MethodologyPage() {
  return (
    <div>
      <PageHeader
        emoji="📖"
        title="Scoring Methodology"
        subtitle="How the MF Recommendation Engine evaluates and ranks mutual funds"
      />

      {/* Introduction */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <h3 className="text-base font-semibold text-slate-800 mb-3">
          Overview
        </h3>
        <p className="text-sm text-slate-600 leading-relaxed">
          The MF Recommendation Engine uses a{" "}
          <span className="font-semibold text-slate-800">two-filter pipeline</span>{" "}
          to evaluate every mutual fund in the Indian equity universe. First, the{" "}
          <span className="font-semibold text-slate-800">Quantitative Fund Score (QFS)</span>{" "}
          ranks all funds within their SEBI category using 13 performance and risk metrics.
          Then, the top funds are shortlisted and evaluated against the fund manager&apos;s
          sector views via the{" "}
          <span className="font-semibold text-slate-800">FM Sector Alignment Score (FSAS)</span>.
          QFS and FSAS are never blended into a single composite score &mdash; they serve as
          independent layers that filter and refine recommendations.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-5">
          <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Step 1</p>
            <p className="text-sm font-semibold text-slate-800 mt-1">QFS Scoring</p>
            <p className="text-xs text-slate-500 mt-1">Score all 535 funds on 13 metrics across 4 time horizons</p>
            <p className="text-lg font-bold text-teal-600 font-mono mt-2">All Funds</p>
          </div>
          <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Step 2</p>
            <p className="text-sm font-semibold text-slate-800 mt-1">Shortlist</p>
            <p className="text-xs text-slate-500 mt-1">Select top 5 funds per SEBI category by QFS rank</p>
            <p className="text-lg font-bold text-teal-600 font-mono mt-2">Top N/Category</p>
          </div>
          <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Step 3</p>
            <p className="text-sm font-semibold text-slate-800 mt-1">FSAS Scoring</p>
            <p className="text-xs text-slate-500 mt-1">Evaluate shortlisted funds against FM sector signals</p>
            <p className="text-lg font-bold text-teal-600 font-mono mt-2">Shortlisted Only</p>
          </div>
          <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Step 4</p>
            <p className="text-sm font-semibold text-slate-800 mt-1">Recommendation</p>
            <p className="text-xs text-slate-500 mt-1">Assign tier from QFS percentile, refine action with FSAS</p>
            <p className="text-lg font-bold text-teal-600 font-mono mt-2">Tier + Action</p>
          </div>
        </div>
      </div>

      {/* Layer 1: Quantitative Fund Score */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <h3 className="text-base font-semibold text-slate-800 mb-1">
          Step 1: Quantitative Fund Score (QFS)
        </h3>
        <p className="text-sm text-slate-500 mb-4">
          A data-driven score based on 13 performance and risk metrics, evaluated across up to 4 time horizons.
          Computed for all funds in the universe.
        </p>

        {/* Metrics table */}
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
          13 Metrics Evaluated
        </p>
        <div className="overflow-hidden rounded-lg border border-slate-200">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider w-8">#</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">Metric</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">What It Measures</th>
              </tr>
            </thead>
            <tbody>
              {QFS_METRICS.map((metric, idx) => (
                <tr key={metric.name} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-2.5 text-xs font-mono text-slate-400">{idx + 1}</td>
                  <td className="px-4 py-2.5 text-sm font-medium text-slate-800">{metric.name}</td>
                  <td className="px-4 py-2.5 text-sm text-slate-500">{metric.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Horizons */}
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mt-6 mb-2">
          Time Horizons &amp; Weights
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {HORIZONS.map((h) => (
            <div key={h.period} className="bg-slate-50 rounded-lg p-3 border border-slate-100 text-center">
              <p className="text-sm font-semibold text-slate-800">{h.period}</p>
              <p className="text-lg font-bold text-teal-600 font-mono">{h.weight}</p>
              <p className="text-xs text-slate-400">{h.description}</p>
            </div>
          ))}
        </div>

        {/* Scoring process */}
        <div className="mt-6 space-y-3">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            How The QFS Is Calculated
          </p>
          <div className="space-y-2 text-sm text-slate-600">
            <div className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold">1</span>
              <p><span className="font-semibold text-slate-800">Collect raw data</span> &mdash; Pull the latest performance, risk, and return metrics from Morningstar for each fund across all available horizons.</p>
            </div>
            <div className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold">2</span>
              <p><span className="font-semibold text-slate-800">Normalise within category</span> &mdash; For each metric-horizon combination, apply min-max normalisation against all funds in the same SEBI category. This produces a 0-100 score where 100 = best in category.</p>
            </div>
            <div className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold">3</span>
              <p><span className="font-semibold text-slate-800">Average per horizon</span> &mdash; Average all normalised metric scores within each time horizon to get a horizon score (1Y, 3Y, 5Y, 10Y).</p>
            </div>
            <div className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold">4</span>
              <p><span className="font-semibold text-slate-800">Weighted combination</span> &mdash; Combine horizon scores using the weights above (1Y: 15%, 3Y: 30%, 5Y: 35%, 10Y: 20%) to produce the final Quantitative Fund Score (0-100).</p>
            </div>
          </div>
        </div>

        {/* Data Completeness */}
        <div className="mt-6 bg-amber-50 border border-amber-200 rounded-lg p-4">
          <p className="text-sm font-semibold text-amber-800">What is Data Completeness?</p>
          <p className="text-sm text-amber-700 mt-1">
            With 13 metrics across 4 horizons, each fund has up to 52 possible data points.
            Data Completeness shows the percentage of these 52 data points that are available.
            Newer funds may only have 1-year data (13 metrics = 25%), while established funds
            with 10+ year track records will have higher completeness. Funds with less than 60%
            data completeness are automatically capped at WATCH tier (see Hard Overrides below).
          </p>
        </div>
      </div>

      {/* Step 2: Shortlist */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <h3 className="text-base font-semibold text-slate-800 mb-1">
          Step 2: Shortlist (Top N per Category)
        </h3>
        <p className="text-sm text-slate-500 mb-4">
          After QFS scoring, the top funds within each SEBI category are shortlisted for deeper analysis.
        </p>

        <div className="space-y-2 text-sm text-slate-600">
          <div className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold">1</span>
            <p><span className="font-semibold text-slate-800">Rank within category</span> &mdash; All funds are ranked by QFS score within their SEBI Morningstar category. Rank 1 = highest QFS in category.</p>
          </div>
          <div className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold">2</span>
            <p><span className="font-semibold text-slate-800">Select top N</span> &mdash; The top 5 funds per category (configurable) are shortlisted. Only shortlisted funds proceed to FSAS evaluation.</p>
          </div>
          <div className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold">3</span>
            <p><span className="font-semibold text-slate-800">Percentile rank computed</span> &mdash; Each fund&apos;s percentile rank within its category is calculated (0-100 scale, where 100 = best). This percentile determines the fund&apos;s tier classification.</p>
          </div>
        </div>

        <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm font-semibold text-blue-800">Why shortlist?</p>
          <p className="text-sm text-blue-700 mt-1">
            FSAS scoring requires comparing fund sector exposure against FM signals &mdash; a more
            nuanced analysis. By first filtering through QFS, we focus this deeper analysis on
            only the highest-quality funds. Non-shortlisted funds still receive QFS-based tier
            and action recommendations &mdash; they just don&apos;t get FSAS-refined actions.
          </p>
        </div>
      </div>

      {/* Step 3: Sector Alignment Score */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <h3 className="text-base font-semibold text-slate-800 mb-1">
          Step 3: FM Sector Alignment Score (FSAS)
        </h3>
        <p className="text-sm text-slate-500 mb-4">
          Computed only for shortlisted funds. Measures how well a fund&apos;s portfolio holdings
          align with the fund manager&apos;s current sector views across 11 Morningstar sectors.
        </p>

        <div className="space-y-3 text-sm text-slate-600">
          <div className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold">1</span>
            <p><span className="font-semibold text-slate-800">FM provides sector signals</span> &mdash; For each of the 11 Morningstar sectors, the fund manager sets a directional signal: OVERWEIGHT, ACCUMULATE, NEUTRAL, UNDERWEIGHT, or AVOID, along with a confidence level (HIGH, MEDIUM, LOW).</p>
          </div>
          <div className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold">2</span>
            <p><span className="font-semibold text-slate-800">Map fund holdings to sectors</span> &mdash; Using the fund&apos;s latest portfolio holdings data from Morningstar, calculate what percentage of the fund is allocated to each sector.</p>
          </div>
          <div className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold">3</span>
            <p><span className="font-semibold text-slate-800">Score alignment</span> &mdash; For each sector, multiply the fund&apos;s exposure by the signal weight and confidence multiplier. Sectors where the fund is aligned with favorable signals contribute positively; misaligned exposure (e.g., heavy in AVOID sectors) reduces the score.</p>
          </div>
          <div className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold">4</span>
            <p><span className="font-semibold text-slate-800">Normalise to 0-100</span> &mdash; The raw alignment score is normalised across all shortlisted funds to a 0-100 scale.</p>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-5 gap-2">
          {[
            { signal: "OVERWEIGHT", weight: "+1.0", color: "bg-emerald-100 text-emerald-700" },
            { signal: "ACCUMULATE", weight: "+0.6", color: "bg-emerald-50 text-emerald-600" },
            { signal: "NEUTRAL", weight: "+0.1", color: "bg-slate-100 text-slate-600" },
            { signal: "UNDERWEIGHT", weight: "-0.5", color: "bg-amber-100 text-amber-700" },
            { signal: "AVOID", weight: "-1.0", color: "bg-red-100 text-red-700" },
          ].map((s) => (
            <div key={s.signal} className={`rounded-lg p-3 text-center ${s.color}`}>
              <p className="text-xs font-bold">{s.signal}</p>
              <p className="text-sm font-mono font-semibold mt-1">{s.weight}</p>
            </div>
          ))}
        </div>

        <div className="mt-4 bg-slate-50 border border-slate-200 rounded-lg p-4">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">11 Morningstar Sectors</p>
          <div className="flex flex-wrap gap-2">
            {[
              "Basic Materials", "Communication Services", "Consumer Cyclical",
              "Consumer Defensive", "Energy", "Financial Services", "Healthcare",
              "Industrials", "Real Estate", "Technology", "Utilities",
            ].map((sector) => (
              <span key={sector} className="text-xs bg-white border border-slate-200 rounded px-2 py-1 text-slate-600">
                {sector}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Step 4: Tier & Action Assignment */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <h3 className="text-base font-semibold text-slate-800 mb-1">
          Step 4: Tier &amp; Action Assignment
        </h3>
        <p className="text-sm text-slate-500 mb-4">
          Tiers are assigned based on QFS percentile rank within each fund&apos;s SEBI category.
          Actions are determined by tier, then optionally refined by FSAS for shortlisted funds.
        </p>

        <div className="bg-slate-50 rounded-lg p-5 border border-slate-100 mb-5">
          <p className="text-center text-sm text-slate-500 mb-2">Tier Assignment Rule</p>
          <p className="text-center text-lg font-mono font-semibold text-slate-800">
            Tier = f(QFS Percentile Rank within SEBI Category)
          </p>
          <p className="text-center text-xs text-slate-400 mt-2">
            No blended score. QFS filters first, FSAS refines the action for shortlisted funds.
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
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">Tier</th>
                <th className="text-center px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">Percentile Range</th>
                <th className="text-center px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">Default Action</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">Description</th>
              </tr>
            </thead>
            <tbody>
              {TIER_PERCENTILES.map((t) => (
                <tr key={t.tier} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-3">
                    <span className={`inline-block rounded px-2.5 py-0.5 text-xs font-bold ${t.color}`}>
                      {t.tier}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center text-sm font-mono text-slate-700">{t.range}</td>
                  <td className="px-4 py-3 text-center text-sm font-semibold text-slate-700">{t.action}</td>
                  <td className="px-4 py-3 text-sm text-slate-500">{t.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* FSAS Action Refinement */}
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mt-6 mb-2">
          FSAS Action Refinement (Shortlisted Funds Only)
        </p>
        <p className="text-sm text-slate-600 mb-3">
          For shortlisted funds, the FSAS score can refine the action within the fund&apos;s tier:
        </p>
        <div className="space-y-2 text-sm text-slate-600">
          <div className="flex items-start gap-3 bg-emerald-50 rounded-lg p-3 border border-emerald-100">
            <span className="text-xs font-bold text-emerald-700 bg-emerald-200 rounded px-2 py-0.5 flex-shrink-0">UPGRADE</span>
            <p>QUALITY tier + FSAS &ge; 75 &rarr; action upgraded from SIP to <span className="font-semibold">BUY</span></p>
          </div>
          <div className="flex items-start gap-3 bg-blue-50 rounded-lg p-3 border border-blue-100">
            <span className="text-xs font-bold text-blue-700 bg-blue-200 rounded px-2 py-0.5 flex-shrink-0">UPGRADE</span>
            <p>WATCH tier + FSAS &ge; 70 &rarr; action upgraded from HOLD to <span className="font-semibold">HOLD+</span></p>
          </div>
          <div className="flex items-start gap-3 bg-amber-50 rounded-lg p-3 border border-amber-100">
            <span className="text-xs font-bold text-amber-700 bg-amber-200 rounded px-2 py-0.5 flex-shrink-0">DOWNGRADE</span>
            <p>CORE tier + FSAS &lt; 30 &rarr; action downgraded from BUY to <span className="font-semibold">SIP</span></p>
          </div>
          <div className="flex items-start gap-3 bg-red-50 rounded-lg p-3 border border-red-100">
            <span className="text-xs font-bold text-red-700 bg-red-200 rounded px-2 py-0.5 flex-shrink-0">CAP</span>
            <p>AVOID exposure &gt; 15% &rarr; action capped at <span className="font-semibold">HOLD</span> regardless of tier</p>
          </div>
        </div>
      </div>

      {/* All 6 Actions */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <h3 className="text-base font-semibold text-slate-800 mb-1">
          Action Reference
        </h3>
        <p className="text-sm text-slate-500 mb-4">
          Six possible actions, from strongest conviction (BUY) to exit recommendation.
        </p>
        <div className="overflow-hidden rounded-lg border border-slate-200">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">Action</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">Typical Tier</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">Description</th>
              </tr>
            </thead>
            <tbody>
              {V2_ACTIONS.map((a) => (
                <tr key={a.action} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-3">
                    <span className="text-sm font-bold text-slate-800">{a.action}</span>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-600">{a.tier}</td>
                  <td className="px-4 py-3 text-sm text-slate-500">{a.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Hard Overrides */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <h3 className="text-base font-semibold text-slate-800 mb-1">
          Hard Overrides
        </h3>
        <p className="text-sm text-slate-500 mb-4">
          Certain conditions trigger automatic tier downgrades regardless of the QFS percentile rank.
          Overrides can only downgrade a tier &mdash; never upgrade.
        </p>
        <div className="space-y-3">
          {[
            { rule: "AVOID Sector Exposure > 25%", effect: "Force to CAUTION tier minimum", reason: "Fund has significant portfolio exposure to sectors the fund manager wants to avoid" },
            { rule: "Manager Tenure < 12 months", effect: "Cap at WATCH tier maximum", reason: "New fund manager — insufficient track record under current leadership" },
            { rule: "Data Completeness < 60%", effect: "Cap at WATCH tier maximum + INSUFFICIENT_DATA flag", reason: "Not enough historical data across the 52 possible data points for reliable scoring" },
            { rule: "Emerging Fund (< 36 months old)", effect: "Cap at WATCH tier maximum + EMERGING_FUND flag", reason: "Fund too young to have multi-horizon track record, regardless of short-term performance" },
          ].map((o) => (
            <div key={o.rule} className="flex items-start gap-4 bg-red-50 rounded-lg p-4 border border-red-100">
              <div className="flex-shrink-0 w-2 h-2 rounded-full bg-red-500 mt-1.5" />
              <div>
                <p className="text-sm font-semibold text-slate-800">{o.rule}</p>
                <p className="text-xs text-red-700 mt-0.5">{o.effect}</p>
                <p className="text-xs text-slate-500 mt-0.5">{o.reason}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Data Sources */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="text-base font-semibold text-slate-800 mb-3">
          Data Sources
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
            <p className="text-sm font-semibold text-slate-800">Morningstar API</p>
            <p className="text-xs text-slate-500 mt-1">
              Fund master data, trailing returns, risk statistics (Sharpe, Alpha, Beta, etc.),
              sector exposure breakdowns, and category benchmarks. 7 API endpoints per fund
              fetched concurrently during ingestion.
            </p>
          </div>
          <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
            <p className="text-sm font-semibold text-slate-800">Fund Manager Signals</p>
            <p className="text-xs text-slate-500 mt-1">
              Sector-level directional views (OVERWEIGHT to AVOID) across 11 Morningstar sectors,
              set by the fund manager through the FM Signals page. All changes are logged
              in the signal change audit trail.
            </p>
          </div>
          <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
            <p className="text-sm font-semibold text-slate-800">Portfolio Holdings</p>
            <p className="text-xs text-slate-500 mt-1">
              Fund portfolio composition from Morningstar Global Stock Sector Breakdown API,
              showing sector-wise allocation percentages across 11 sectors. Used for FSAS
              alignment scoring on shortlisted funds only.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
