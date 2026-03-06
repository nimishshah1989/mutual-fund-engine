// Step 1: Quantitative Fund Score (QFS) section.
// Explains the 12-metric, 3-horizon scoring system including
// two-tier weighting, calculation steps, and data completeness rules.

import {
  MUST_HAVE_METRICS,
  GOOD_TO_HAVE_METRICS,
  SCORING_HORIZONS,
} from "./constants";
import MetricsTable from "./MetricsTable";

export default function QFSScoringSection() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
      <h3 className="text-base font-semibold text-slate-800 mb-1">
        Step 1: Quantitative Fund Score (QFS)
      </h3>
      <p className="text-sm text-slate-500 mb-4">
        A data-driven score based on 12 performance and risk metrics, classified
        into two tiers and evaluated across 3 scoring horizons (1Y, 3Y, 5Y).
        Computed for all funds in the universe. 10Y data is still extracted and
        displayed for reference but does not contribute to the QFS.
      </p>

      {/* Two-tier weighting explanation */}
      <div className="bg-teal-50 border border-teal-200 rounded-lg p-4 mb-5">
        <p className="text-sm font-semibold text-teal-800">
          Two-Tier Metric Weighting
        </p>
        <p className="text-sm text-teal-700 mt-1">
          Metrics are classified into{" "}
          <span className="font-semibold">Must-Have (75% weight)</span> and{" "}
          <span className="font-semibold">Good-to-Have (25% weight)</span>{" "}
          within each horizon. Must-have metrics are the core quality indicators
          that most define a fund&apos;s quality. Good-to-have metrics add
          supplementary nuance but don&apos;t carry equal importance.
        </p>
      </div>

      {/* Must-Have metrics */}
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
        Must-Have Metrics{" "}
        <span className="text-teal-600">(75% weight)</span> &mdash; 6 Metrics,
        17 Data Points
      </p>
      <div className="mb-5">
        <MetricsTable
          metrics={MUST_HAVE_METRICS}
          descriptionHeader="Why It Matters"
        />
      </div>

      {/* Good-to-Have metrics */}
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
        Good-to-Have Metrics{" "}
        <span className="text-slate-500">(25% weight)</span> &mdash; 6 Metrics,
        17 Data Points
      </p>
      <MetricsTable
        metrics={GOOD_TO_HAVE_METRICS}
        descriptionHeader="Why It's Supplementary"
      />

      {/* Horizons */}
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mt-6 mb-2">
        Scoring Horizons &amp; Weights
      </p>
      <div className="grid grid-cols-3 gap-3">
        {SCORING_HORIZONS.map((h) => (
          <div
            key={h.period}
            className="bg-slate-50 rounded-lg p-3 border border-slate-100 text-center"
          >
            <p className="text-sm font-semibold text-slate-800">{h.period}</p>
            <p className="text-lg font-bold text-teal-600 font-mono">
              {h.weight}
            </p>
            <p className="text-xs text-slate-400">{h.description}</p>
            <p className="text-xs text-slate-300 mt-1">
              Weight: {h.rawWeight}
            </p>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400 mt-2">
        10Y data is extracted and displayed on the fund detail page but does not
        contribute to the WFS or QFS score. Very few Indian MFs have a 10-year
        track record, and including 10Y artificially narrows the qualified pool.
      </p>

      {/* Scoring process */}
      <CalculationSteps />

      {/* Data Completeness */}
      <div className="mt-6 bg-amber-50 border border-amber-200 rounded-lg p-4">
        <p className="text-sm font-semibold text-amber-800">
          What is Data Completeness?
        </p>
        <p className="text-sm text-amber-700 mt-1">
          Data completeness is measured against{" "}
          <span className="font-semibold">must-have metrics only</span> across
          the 3 scoring horizons (1Y, 3Y, 5Y) &mdash; a total of{" "}
          <span className="font-mono font-semibold">17</span> data points. A
          fund with all must-have data present across 1Y, 3Y, and 5Y = 100%
          complete, even if all good-to-have metrics are missing. A fund with
          only 1Y data has ~29% completeness (5/17). Funds with less than 60%
          must-have completeness receive a proportional QFS penalty (see Hard
          Overrides below).
        </p>
      </div>
    </div>
  );
}

function CalculationSteps() {
  return (
    <div className="mt-6 space-y-3">
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
        How The QFS Is Calculated
      </p>
      <div className="space-y-2 text-sm text-slate-600">
        <StepItem number={1}>
          <span className="font-semibold text-slate-800">
            Collect raw data
          </span>{" "}
          &mdash; Pull the latest performance, risk, and return metrics from
          Morningstar for each fund across all available horizons (1Y through
          10Y).
        </StepItem>
        <StepItem number={2}>
          <span className="font-semibold text-slate-800">
            Normalise within category
          </span>{" "}
          &mdash; For each metric-horizon combination, apply min-max
          normalisation against all funds in the same SEBI category. This
          produces a 0-100 score where 100 = best in category.
        </StepItem>
        <StepItem number={3}>
          <span className="font-semibold text-slate-800">
            Two-tier weighted blend per horizon
          </span>{" "}
          &mdash; For each horizon (1Y, 3Y, 5Y), compute separate averages for
          must-have and good-to-have metrics, then blend:
          <div className="bg-slate-50 rounded-lg p-3 mt-2 font-mono text-xs space-y-1">
            <p>must_avg = mean(must-have normalised scores)</p>
            <p>good_avg = mean(good-to-have normalised scores)</p>
            <p className="pt-1 border-t border-slate-200">
              If both present:{" "}
              <span className="text-teal-700 font-semibold">
                horizon_score = 0.75 &times; must_avg + 0.25 &times; good_avg
              </span>
            </p>
            <p>
              If only must-have:{" "}
              <span className="text-teal-700">
                horizon_score = must_avg
              </span>{" "}
              (no penalty)
            </p>
            <p>
              If only good-to-have:{" "}
              <span className="text-amber-700">
                horizon_score = good_avg &times; 0.5
              </span>{" "}
              (capped)
            </p>
          </div>
        </StepItem>
        <StepItem number={4}>
          <span className="font-semibold text-slate-800">
            Weighted combination (1Y-5Y only)
          </span>{" "}
          &mdash; Combine horizon scores using weights (1Y: 1, 3Y: 2, 5Y: 3)
          to produce the Weighted Fund Score (WFS). 10Y is excluded from this
          computation.
        </StepItem>
        <StepItem number={5}>
          <span className="font-semibold text-slate-800">
            Final normalisation
          </span>{" "}
          &mdash; Normalise WFS across all funds in the category to produce the
          final QFS (0-100). Apply completeness penalty for funds below 60%
          must-have data coverage.
        </StepItem>
      </div>
    </div>
  );
}

interface StepItemProps {
  number: number;
  children: React.ReactNode;
}

function StepItem({ number, children }: StepItemProps) {
  return (
    <div className="flex items-start gap-3">
      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center text-xs font-bold">
        {number}
      </span>
      <p>{children}</p>
    </div>
  );
}
