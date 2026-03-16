// Layer 2: FM Alignment Score (FMS) section. Explains how all funds
// are scored against the fund manager's sector signals using active
// weights relative to the NIFTY 50 benchmark.

import { SIGNAL_WEIGHTS, MORNINGSTAR_SECTORS } from "./constants";
import { sectorBgColor } from "@/lib/colors";

/** Confidence multiplier data for the table */
const CONFIDENCE_MULTIPLIERS = [
  { level: "HIGH", multiplier: "1.3", color: "bg-emerald-100 text-emerald-700" },
  { level: "MEDIUM", multiplier: "1.0", color: "bg-slate-100 text-slate-600" },
  { level: "LOW", multiplier: "0.5", color: "bg-amber-100 text-amber-700" },
];

/** Worked examples demonstrating the FMS calculation */
const WORKED_EXAMPLES = [
  {
    label: "Aligned overweight (bullish)",
    sector: "Technology",
    fundExposure: "25.0%",
    benchmark: "13.5%",
    activeWeight: "+11.5%",
    signal: "OVERWEIGHT",
    signalWeight: "+1.0",
    confidence: "HIGH",
    confMultiplier: "1.3",
    contribution: "+14.95",
    interpretation:
      "Fund is overweight Tech vs NIFTY 50, and FM is also bullish on Tech with high confidence. Strong positive contribution.",
    color: "bg-emerald-50 border-emerald-200",
  },
  {
    label: "Misaligned underweight (bullish view, fund underweight)",
    sector: "Technology",
    fundExposure: "10.0%",
    benchmark: "13.5%",
    activeWeight: "-3.5%",
    signal: "OVERWEIGHT",
    signalWeight: "+1.0",
    confidence: "HIGH",
    confMultiplier: "1.3",
    contribution: "-4.55",
    interpretation:
      "FM wants more Tech, but fund is underweight vs benchmark. Active weight is negative, so even a positive signal produces a negative contribution.",
    color: "bg-amber-50 border-amber-200",
  },
  {
    label: "Misaligned overweight (bearish view, fund overweight)",
    sector: "Energy",
    fundExposure: "20.0%",
    benchmark: "12.0%",
    activeWeight: "+8.0%",
    signal: "AVOID",
    signalWeight: "-1.0",
    confidence: "HIGH",
    confMultiplier: "1.3",
    contribution: "-10.40",
    interpretation:
      "Fund is overweight Energy vs benchmark, but FM wants to avoid Energy entirely. Large negative contribution penalises this misalignment.",
    color: "bg-red-50 border-red-200",
  },
];

export default function FSASSection() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
      <h3 className="text-base font-semibold text-slate-800 mb-1">
        FM Alignment Score (FMS) &mdash; Layer 2
      </h3>
      <p className="text-sm text-slate-500 mb-4">
        Computed for <span className="font-semibold text-slate-700">all funds</span> in
        the universe. Measures how well a fund&apos;s sector positioning aligns
        with the fund manager&apos;s current sector views, using{" "}
        <span className="font-semibold text-slate-700">active weights</span>{" "}
        relative to the NIFTY 50 benchmark.
      </p>

      {/* Key change callout */}
      <div className="bg-teal-50 border border-teal-200 rounded-lg p-4 mb-5">
        <p className="text-sm font-semibold text-teal-800">
          Key Change from v2
        </p>
        <p className="text-sm text-teal-700 mt-1">
          The old FSAS used raw fund exposure percentages. The new FMS uses{" "}
          <span className="font-semibold">active weights</span> &mdash; the
          difference between the fund&apos;s sector exposure and the NIFTY 50
          benchmark weight. This means a fund is only rewarded (or penalised)
          for its{" "}
          <span className="font-semibold">deliberate sector bets</span>, not
          for holding benchmark-weight positions.
        </p>
      </div>

      {/* Calculation steps */}
      <div className="space-y-3 text-sm text-slate-600">
        <StepItem number={1}>
          <span className="font-semibold text-slate-800">
            FM provides sector signals
          </span>{" "}
          &mdash; For each of the 11 Morningstar sectors, the fund manager sets
          a directional signal (OVERWEIGHT, ACCUMULATE, NEUTRAL, UNDERWEIGHT,
          AVOID) and a confidence level (HIGH, MEDIUM, LOW).
        </StepItem>
        <StepItem number={2}>
          <span className="font-semibold text-slate-800">
            Compute active weights
          </span>{" "}
          &mdash; For each sector, calculate the fund&apos;s active weight as
          the difference between its portfolio exposure and the NIFTY 50
          benchmark weight for that sector.
        </StepItem>
        <StepItem number={3}>
          <span className="font-semibold text-slate-800">
            Score sector contributions
          </span>{" "}
          &mdash; For each sector, multiply the active weight by the signal
          weight and the confidence multiplier to produce a sector contribution.
          Positive active weight in a bullish sector = positive contribution.
          Positive active weight in a bearish sector = negative contribution.
        </StepItem>
        <StepItem number={4}>
          <span className="font-semibold text-slate-800">Sum contributions</span>{" "}
          &mdash; Sum all 11 sector contributions to produce the raw FMS for that
          fund.
        </StepItem>
        <StepItem number={5}>
          <span className="font-semibold text-slate-800">
            Normalise within category
          </span>{" "}
          &mdash; Apply min-max normalisation across all funds in the same SEBI
          category to produce a final FMS on a 0&ndash;100 scale.
        </StepItem>
      </div>

      {/* Formula callout */}
      <div className="bg-slate-50 rounded-lg p-5 border border-slate-100 mt-5 mb-5">
        <p className="text-center text-sm text-slate-500 mb-2">
          FMS Formula (per fund)
        </p>
        <div className="text-center font-mono text-sm text-slate-800 space-y-2">
          <p>
            For each sector:{" "}
            <span className="text-teal-700 font-semibold">
              active_weight = fund_exposure_pct &minus; benchmark_weight_pct
            </span>
          </p>
          <p>
            <span className="text-teal-700 font-semibold">
              contribution = active_weight &times; signal_weight &times;
              confidence_multiplier
            </span>
          </p>
          <p className="pt-2 border-t border-slate-200">
            <span className="text-teal-700 font-semibold">
              raw_fms = &Sigma; contributions (across 11 sectors)
            </span>
          </p>
          <p>
            <span className="text-teal-700 font-semibold">
              fms = min_max_normalise(raw_fms, within_category) &rarr; 0&ndash;100
            </span>
          </p>
        </div>
        <p className="text-center text-xs text-slate-400 mt-3">
          Benchmark: NIFTY 50 sector weights. Normalisation universe: all funds
          in the same SEBI Morningstar category.
        </p>
      </div>

      {/* Signal weight badges */}
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
        Signal Weights
      </p>
      <div className="grid grid-cols-5 gap-2">
        {SIGNAL_WEIGHTS.map((s) => (
          <div
            key={s.signal}
            className={`rounded-lg p-3 text-center ${s.color}`}
          >
            <p className="text-xs font-bold">{s.signal}</p>
            <p className="text-sm font-mono font-semibold mt-1">{s.weight}</p>
          </div>
        ))}
      </div>

      {/* Confidence multipliers */}
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mt-5 mb-2">
        Confidence Multipliers
      </p>
      <div className="grid grid-cols-3 gap-2">
        {CONFIDENCE_MULTIPLIERS.map((c) => (
          <div
            key={c.level}
            className={`rounded-lg p-3 text-center ${c.color}`}
          >
            <p className="text-xs font-bold">{c.level}</p>
            <p className="text-sm font-mono font-semibold mt-1">
              &times;{c.multiplier}
            </p>
          </div>
        ))}
      </div>

      {/* Worked examples */}
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mt-6 mb-2">
        Worked Examples
      </p>
      <div className="space-y-3">
        {WORKED_EXAMPLES.map((ex) => (
          <div
            key={ex.label}
            className={`rounded-lg p-4 border ${ex.color}`}
          >
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              {ex.label}
            </p>
            <div className="overflow-hidden rounded-lg border border-slate-200">
              <table className="w-full text-sm">
                <tbody>
                  <tr className="border-b border-slate-100">
                    <td className="px-3 py-1.5 text-xs text-slate-500 w-40">
                      Sector
                    </td>
                    <td className="px-3 py-1.5 text-xs font-semibold text-slate-800">
                      {ex.sector}
                    </td>
                  </tr>
                  <tr className="border-b border-slate-100">
                    <td className="px-3 py-1.5 text-xs text-slate-500">
                      Fund Exposure
                    </td>
                    <td className="px-3 py-1.5 text-xs font-mono text-slate-800">
                      {ex.fundExposure}
                    </td>
                  </tr>
                  <tr className="border-b border-slate-100">
                    <td className="px-3 py-1.5 text-xs text-slate-500">
                      Benchmark (NIFTY 50)
                    </td>
                    <td className="px-3 py-1.5 text-xs font-mono text-slate-800">
                      {ex.benchmark}
                    </td>
                  </tr>
                  <tr className="border-b border-slate-100 bg-slate-50">
                    <td className="px-3 py-1.5 text-xs text-slate-500 font-semibold">
                      Active Weight
                    </td>
                    <td className="px-3 py-1.5 text-xs font-mono font-semibold text-slate-800">
                      {ex.activeWeight}
                    </td>
                  </tr>
                  <tr className="border-b border-slate-100">
                    <td className="px-3 py-1.5 text-xs text-slate-500">
                      FM Signal
                    </td>
                    <td className="px-3 py-1.5 text-xs font-semibold text-slate-800">
                      {ex.signal} (weight: {ex.signalWeight})
                    </td>
                  </tr>
                  <tr className="border-b border-slate-100">
                    <td className="px-3 py-1.5 text-xs text-slate-500">
                      Confidence
                    </td>
                    <td className="px-3 py-1.5 text-xs text-slate-800">
                      {ex.confidence} (&times;{ex.confMultiplier})
                    </td>
                  </tr>
                  <tr className="bg-slate-50">
                    <td className="px-3 py-1.5 text-xs text-slate-500 font-semibold">
                      Contribution
                    </td>
                    <td className="px-3 py-1.5 text-xs font-mono font-bold text-slate-800">
                      {ex.contribution}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="text-xs text-slate-500 mt-2">{ex.interpretation}</p>
          </div>
        ))}
      </div>

      {/* Sector list */}
      <div className="mt-5 bg-slate-50 border border-slate-200 rounded-lg p-4">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
          11 Morningstar Sectors
        </p>
        <div className="flex flex-wrap gap-2">
          {MORNINGSTAR_SECTORS.map((sector) => (
            <span
              key={sector}
              className="text-xs bg-white border border-slate-200 rounded px-2 py-1 text-slate-600 inline-flex items-center gap-1.5"
            >
              <span
                className={`w-2 h-2 rounded-full flex-shrink-0 ${sectorBgColor(sector)}`}
              />
              {sector}
            </span>
          ))}
        </div>
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
      <div className="text-sm text-slate-600">{children}</div>
    </div>
  );
}
