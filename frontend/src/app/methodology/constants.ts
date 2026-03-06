// Methodology page data constants and TypeScript interfaces.
// All scoring methodology configuration lives here so section
// components stay focused on presentation.

export interface TierPercentile {
  tier: string;
  range: string;
  action: string;
  color: string;
  description: string;
}

export interface Metric {
  name: string;
  description: string;
  horizons: string;
}

export interface ScoringHorizon {
  period: string;
  weight: string;
  rawWeight: string;
  description: string;
}

export interface ActionDefinition {
  action: string;
  tier: string;
  description: string;
}

export interface SignalWeight {
  signal: string;
  weight: string;
  color: string;
}

export interface HardOverride {
  rule: string;
  effect: string;
  reason: string;
}

export const TIER_PERCENTILES: TierPercentile[] = [
  {
    tier: "CORE",
    range: "90th - 100th",
    action: "BUY",
    color: "bg-emerald-600 text-white",
    description:
      "Top 10% of category by QFS. High conviction for fresh deployment. Shortlisted funds with strong FSAS may get BUY action.",
  },
  {
    tier: "QUALITY",
    range: "70th - 89th",
    action: "SIP",
    color: "bg-blue-600 text-white",
    description:
      "Solid funds in the top 30%. Suitable for systematic investment. Shortlisted funds with high sector alignment may be upgraded to BUY.",
  },
  {
    tier: "WATCH",
    range: "40th - 69th",
    action: "HOLD",
    color: "bg-amber-500 text-white",
    description:
      "Middle of the pack. Existing positions may be held but new investment is not recommended. High FSAS may upgrade to HOLD+.",
  },
  {
    tier: "CAUTION",
    range: "20th - 39th",
    action: "REDUCE",
    color: "bg-orange-500 text-white",
    description:
      "Below-average performers. Consider reducing exposure and reallocating to higher-tier funds.",
  },
  {
    tier: "EXIT",
    range: "0th - 19th",
    action: "EXIT",
    color: "bg-red-600 text-white",
    description:
      "Bottom 20% of category. Redeem and reallocate capital to higher-tier funds.",
  },
];

export const MUST_HAVE_METRICS: Metric[] = [
  {
    name: "Total Return",
    description:
      "Absolute trailing returns \u2014 what investors see first. The most fundamental measure of fund performance.",
    horizons: "1Y, 3Y, 5Y",
  },
  {
    name: "Sharpe Ratio",
    description:
      "Gold standard risk-adjusted return. Measures excess return per unit of total volatility.",
    horizons: "1Y, 3Y, 5Y",
  },
  {
    name: "Alpha",
    description:
      "Fund manager\u2019s value addition above what the benchmark delivers. The core purpose of active management.",
    horizons: "3Y, 5Y",
  },
  {
    name: "Standard Deviation",
    description:
      "Core risk measure \u2014 total volatility of the fund\u2019s returns. Essential for risk assessment.",
    horizons: "1Y, 3Y, 5Y",
  },
  {
    name: "Sortino Ratio",
    description:
      "Downside risk-adjusted return. Only penalises harmful volatility, not total volatility.",
    horizons: "1Y, 3Y, 5Y",
  },
  {
    name: "Category Alpha",
    description:
      "Excess return over the SEBI category average. Always computable when returns exist.",
    horizons: "1Y, 3Y, 5Y",
  },
];

export const GOOD_TO_HAVE_METRICS: Metric[] = [
  {
    name: "Beta",
    description:
      "Systematic risk measure. Useful but often ~1.0 for diversified equity funds.",
    horizons: "3Y, 5Y",
  },
  {
    name: "Treynor Ratio",
    description:
      "Excess return per unit of systematic (market) risk. Partially redundant with Sharpe.",
    horizons: "1Y, 3Y, 5Y",
  },
  {
    name: "Tracking Error",
    description:
      "Deviation from benchmark returns. More relevant for index-tracking funds.",
    horizons: "1Y, 3Y, 5Y",
  },
  {
    name: "Information Ratio",
    description:
      "Consistency of outperformance relative to tracking error. Derivative measure.",
    horizons: "1Y, 3Y, 5Y",
  },
  {
    name: "Up Capture Ratio",
    description:
      "How much of the market\u2019s upside the fund captures during rallies.",
    horizons: "1Y, 3Y, 5Y",
  },
  {
    name: "Down Capture Ratio",
    description:
      "How much of the market\u2019s downside the fund absorbs during declines.",
    horizons: "1Y, 3Y, 5Y",
  },
];

export const SCORING_HORIZONS: ScoringHorizon[] = [
  {
    period: "1 Year",
    weight: "~17%",
    rawWeight: "1",
    description: "Recent performance signal",
  },
  {
    period: "3 Years",
    weight: "~33%",
    rawWeight: "2",
    description: "Medium-term consistency",
  },
  {
    period: "5 Years",
    weight: "50%",
    rawWeight: "3",
    description: "Core evaluation window",
  },
];

export const V2_ACTIONS: ActionDefinition[] = [
  {
    action: "BUY",
    tier: "CORE",
    description:
      "Deploy fresh capital. Highest conviction based on quantitative strength and sector alignment.",
  },
  {
    action: "SIP",
    tier: "QUALITY",
    description:
      "Systematic investment. Consistent performer suitable for periodic allocation.",
  },
  {
    action: "HOLD+",
    tier: "WATCH (with FSAS)",
    description:
      "Hold with added conviction. WATCH-tier fund with strong sector alignment warrants keeping the position.",
  },
  {
    action: "HOLD",
    tier: "WATCH",
    description: "Maintain existing position. No new investment recommended.",
  },
  {
    action: "REDUCE",
    tier: "CAUTION",
    description:
      "Reduce exposure. Below-average performer \u2014 shift capital to better alternatives.",
  },
  {
    action: "EXIT",
    tier: "EXIT",
    description:
      "Full redemption. Bottom of category with no sector alignment support.",
  },
];

export const SIGNAL_WEIGHTS: SignalWeight[] = [
  {
    signal: "OVERWEIGHT",
    weight: "+1.0",
    color: "bg-emerald-100 text-emerald-700",
  },
  {
    signal: "ACCUMULATE",
    weight: "+0.6",
    color: "bg-emerald-50 text-emerald-600",
  },
  {
    signal: "NEUTRAL",
    weight: "+0.1",
    color: "bg-slate-100 text-slate-600",
  },
  {
    signal: "UNDERWEIGHT",
    weight: "-0.5",
    color: "bg-amber-100 text-amber-700",
  },
  { signal: "AVOID", weight: "-1.0", color: "bg-red-100 text-red-700" },
];

export const MORNINGSTAR_SECTORS: string[] = [
  "Basic Materials",
  "Communication Services",
  "Consumer Cyclical",
  "Consumer Defensive",
  "Energy",
  "Financial Services",
  "Healthcare",
  "Industrials",
  "Real Estate",
  "Technology",
  "Utilities",
];

export const HARD_OVERRIDES: HardOverride[] = [
  {
    rule: "AVOID Sector Exposure > 25%",
    effect: "Force to CAUTION tier minimum",
    reason:
      "Fund has significant portfolio exposure to sectors the fund manager wants to avoid",
  },
  {
    rule: "Manager Tenure < 12 months",
    effect: "Cap at WATCH tier maximum",
    reason:
      "New fund manager \u2014 insufficient track record under current leadership",
  },
  {
    rule: "Data Completeness < 60%",
    effect: "Cap at WATCH tier maximum + INSUFFICIENT_DATA flag",
    reason:
      "Not enough must-have data points (need at least ~10 of 17) for reliable scoring",
  },
  {
    rule: "Emerging Fund (< 36 months old)",
    effect: "Cap at WATCH tier maximum + EMERGING_FUND flag",
    reason:
      "Fund too young to have multi-horizon track record, regardless of short-term performance",
  },
];
