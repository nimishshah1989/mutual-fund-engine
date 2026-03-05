"use client";

import PageHeader from "@/components/PageHeader";

const TIER_THRESHOLDS = [
  { tier: "CORE", range: "72 - 100", color: "bg-emerald-600 text-white", action: "BUY", description: "Top-tier funds with strong quantitative performance and favorable sector alignment. High conviction for fresh deployment." },
  { tier: "QUALITY", range: "55 - 71.99", color: "bg-blue-600 text-white", action: "SIP", description: "Solid funds suitable for systematic investment. Good fundamentals with room for upside." },
  { tier: "WATCH", range: "38 - 54.99", color: "bg-amber-500 text-white", action: "HOLD", description: "Moderate performers under observation. Existing positions may be held but new investment is not recommended." },
  { tier: "CAUTION", range: "20 - 37.99", color: "bg-orange-500 text-white", action: "SWITCH", description: "Underperforming funds. Consider switching to better alternatives within the same category." },
  { tier: "EXIT", range: "0 - 19.99", color: "bg-red-600 text-white", action: "EXIT", description: "Poor performance across metrics. Redeem and reallocate capital to higher-tier funds." },
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

export default function MethodologyPage() {
  return (
    <div>
      <PageHeader
        emoji={"\uD83D\uDCD6"}
        title="Scoring Methodology"
        subtitle="How we evaluate and rank mutual funds"
      />

      {/* Introduction */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <h3 className="text-base font-semibold text-slate-800 mb-3">
          Overview
        </h3>
        <p className="text-sm text-slate-600 leading-relaxed">
          The JIP MF Recommendation Engine uses a three-layer scoring system to evaluate
          every mutual fund in the Indian equity universe. Each fund receives a{" "}
          <span className="font-semibold text-slate-800">Composite Recommendation Score</span>{" "}
          (0-100) that combines quantitative performance metrics with fund manager
          sector views. This score determines the fund&apos;s tier classification and
          recommended action.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-5">
          <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Layer 1</p>
            <p className="text-sm font-semibold text-slate-800 mt-1">Quantitative Fund Score</p>
            <p className="text-xs text-slate-500 mt-1">13 performance &amp; risk metrics across 4 time horizons</p>
            <p className="text-lg font-bold text-teal-600 font-mono mt-2">60% weight</p>
          </div>
          <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Layer 2</p>
            <p className="text-sm font-semibold text-slate-800 mt-1">Sector Alignment Score</p>
            <p className="text-xs text-slate-500 mt-1">Fund holdings vs. fund manager sector signals</p>
            <p className="text-lg font-bold text-teal-600 font-mono mt-2">40% weight</p>
          </div>
          <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Layer 3</p>
            <p className="text-sm font-semibold text-slate-800 mt-1">Composite Recommendation Score</p>
            <p className="text-xs text-slate-500 mt-1">Weighted combination with tier classification</p>
            <p className="text-lg font-bold text-teal-600 font-mono mt-2">Final Score</p>
          </div>
        </div>
      </div>

      {/* Layer 1: Quantitative Fund Score */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <h3 className="text-base font-semibold text-slate-800 mb-1">
          Layer 1: Quantitative Fund Score
        </h3>
        <p className="text-sm text-slate-500 mb-4">
          A data-driven score based on 13 performance and risk metrics, evaluated across up to 4 time horizons.
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
            How The Score Is Calculated
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
              <p><span className="font-semibold text-slate-800">Weighted combination</span> &mdash; Combine horizon scores using the weights above (1Y: 15%, 3Y: 30%, 5Y: 35%, 10Y: 20%) to produce the final Quantitative Fund Score.</p>
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
            with 10+ year track records will have higher completeness. A fund with 80%+ completeness
            has robust data for scoring. Low completeness does not mean the fund is bad &mdash; it
            simply means less historical data is available for evaluation.
          </p>
        </div>
      </div>

      {/* Layer 2: Sector Alignment Score */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <h3 className="text-base font-semibold text-slate-800 mb-1">
          Layer 2: Sector Alignment Score
        </h3>
        <p className="text-sm text-slate-500 mb-4">
          Measures how well a fund&apos;s portfolio holdings align with the fund manager&apos;s current sector views.
        </p>

        <div className="space-y-3 text-sm text-slate-600">
          <div className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold">1</span>
            <p><span className="font-semibold text-slate-800">Fund manager provides sector signals</span> &mdash; For each sector (Technology, Banking, Pharma, etc.), the fund manager sets a directional signal: OVERWEIGHT, ACCUMULATE, NEUTRAL, UNDERWEIGHT, or AVOID, along with a confidence level (HIGH, MEDIUM, LOW).</p>
          </div>
          <div className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold">2</span>
            <p><span className="font-semibold text-slate-800">Map fund holdings to sectors</span> &mdash; Using the fund&apos;s latest portfolio holdings data, calculate what percentage of the fund is allocated to each sector.</p>
          </div>
          <div className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold">3</span>
            <p><span className="font-semibold text-slate-800">Score alignment</span> &mdash; For each sector, multiply the fund&apos;s exposure by the signal weight and confidence multiplier. Sectors where the fund is aligned with favorable signals contribute positively; misaligned exposure (e.g., heavy in AVOID sectors) reduces the score.</p>
          </div>
          <div className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold">4</span>
            <p><span className="font-semibold text-slate-800">Normalise to 0-100</span> &mdash; The raw alignment score is normalised to a 0-100 scale for combination with the Quantitative Fund Score.</p>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-5 gap-2">
          {[
            { signal: "OVERWEIGHT", weight: "+1.0", color: "bg-emerald-100 text-emerald-700" },
            { signal: "ACCUMULATE", weight: "+0.5", color: "bg-emerald-50 text-emerald-600" },
            { signal: "NEUTRAL", weight: "0.0", color: "bg-slate-100 text-slate-600" },
            { signal: "UNDERWEIGHT", weight: "-0.5", color: "bg-amber-100 text-amber-700" },
            { signal: "AVOID", weight: "-1.0", color: "bg-red-100 text-red-700" },
          ].map((s) => (
            <div key={s.signal} className={`rounded-lg p-3 text-center ${s.color}`}>
              <p className="text-xs font-bold">{s.signal}</p>
              <p className="text-sm font-mono font-semibold mt-1">{s.weight}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Layer 3: Composite Recommendation Score */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <h3 className="text-base font-semibold text-slate-800 mb-1">
          Layer 3: Composite Recommendation Score
        </h3>
        <p className="text-sm text-slate-500 mb-4">
          The final score that determines a fund&apos;s tier and recommended action.
        </p>

        <div className="bg-slate-50 rounded-lg p-5 border border-slate-100 mb-5">
          <p className="text-center text-sm text-slate-500 mb-2">Formula</p>
          <p className="text-center text-lg font-mono font-semibold text-slate-800">
            Composite Score = (Quantitative Score x 0.60) + (Sector Alignment x 0.40)
          </p>
        </div>

        <p className="text-sm text-slate-600 leading-relaxed mb-4">
          The composite score ranges from 0 to 100 and places each fund into one of five tiers.
          Each tier has a default recommended action, though hard overrides can be applied for
          funds with specific risk flags (e.g., heavy exposure to AVOID sectors, stale holdings data).
        </p>

        {/* Tier table */}
        <div className="overflow-hidden rounded-lg border border-slate-200">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">Tier</th>
                <th className="text-center px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">Score Range</th>
                <th className="text-center px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">Default Action</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">Description</th>
              </tr>
            </thead>
            <tbody>
              {TIER_THRESHOLDS.map((t) => (
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
      </div>

      {/* Hard Overrides */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <h3 className="text-base font-semibold text-slate-800 mb-1">
          Hard Overrides
        </h3>
        <p className="text-sm text-slate-500 mb-4">
          Certain conditions trigger automatic tier downgrades regardless of the calculated score.
        </p>
        <div className="space-y-3">
          {[
            { rule: "AVOID Sector Exposure > 15%", effect: "Downgrade to CAUTION or EXIT tier", reason: "Fund has significant exposure to sectors the fund manager wants to avoid" },
            { rule: "Stale Holdings (> 45 days old)", effect: "Cap at WATCH tier maximum", reason: "Portfolio data too old for reliable alignment scoring" },
            { rule: "Data Completeness < 25%", effect: "Cap at QUALITY tier maximum", reason: "Insufficient historical data for high-conviction recommendation" },
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
              Fund master data, daily NAVs, trailing returns, risk statistics (Sharpe, Alpha, Beta, etc.),
              and category benchmarks. Refreshed daily at 2:00 AM IST.
            </p>
          </div>
          <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
            <p className="text-sm font-semibold text-slate-800">Fund Manager Signals</p>
            <p className="text-xs text-slate-500 mt-1">
              Sector-level directional views (OVERWEIGHT to AVOID) set manually by the fund manager
              through the FM Signals page. Updated as market views change.
            </p>
          </div>
          <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
            <p className="text-sm font-semibold text-slate-800">Portfolio Holdings</p>
            <p className="text-xs text-slate-500 mt-1">
              Fund portfolio composition from Morningstar, showing sector-wise allocation percentages.
              Used to calculate alignment between holdings and fund manager signals.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
