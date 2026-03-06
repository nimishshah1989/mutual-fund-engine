// Step 3: FM Sector Alignment Score (FSAS) section. Explains how
// shortlisted funds are scored against the fund manager's sector signals
// across 11 Morningstar sectors.

import { SIGNAL_WEIGHTS, MORNINGSTAR_SECTORS } from "./constants";

export default function FSASSection() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
      <h3 className="text-base font-semibold text-slate-800 mb-1">
        Step 3: FM Sector Alignment Score (FSAS)
      </h3>
      <p className="text-sm text-slate-500 mb-4">
        Computed only for shortlisted funds. Measures how well a fund&apos;s
        portfolio holdings align with the fund manager&apos;s current sector
        views across 11 Morningstar sectors.
      </p>

      <div className="space-y-3 text-sm text-slate-600">
        <StepItem number={1}>
          <span className="font-semibold text-slate-800">
            FM provides sector signals
          </span>{" "}
          &mdash; For each of the 11 Morningstar sectors, the fund manager sets
          a directional signal: OVERWEIGHT, ACCUMULATE, NEUTRAL, UNDERWEIGHT, or
          AVOID, along with a confidence level (HIGH, MEDIUM, LOW).
        </StepItem>
        <StepItem number={2}>
          <span className="font-semibold text-slate-800">
            Map fund holdings to sectors
          </span>{" "}
          &mdash; Using the fund&apos;s latest portfolio holdings data from
          Morningstar, calculate what percentage of the fund is allocated to each
          sector.
        </StepItem>
        <StepItem number={3}>
          <span className="font-semibold text-slate-800">Score alignment</span>{" "}
          &mdash; For each sector, multiply the fund&apos;s exposure by the
          signal weight and confidence multiplier. Sectors where the fund is
          aligned with favorable signals contribute positively; misaligned
          exposure (e.g., heavy in AVOID sectors) reduces the score.
        </StepItem>
        <StepItem number={4}>
          <span className="font-semibold text-slate-800">
            Normalise to 0-100
          </span>{" "}
          &mdash; The raw alignment score is normalised across all shortlisted
          funds to a 0-100 scale.
        </StepItem>
      </div>

      {/* Signal weight badges */}
      <div className="mt-5 grid grid-cols-5 gap-2">
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

      {/* Sector list */}
      <div className="mt-4 bg-slate-50 border border-slate-200 rounded-lg p-4">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
          11 Morningstar Sectors
        </p>
        <div className="flex flex-wrap gap-2">
          {MORNINGSTAR_SECTORS.map((sector) => (
            <span
              key={sector}
              className="text-xs bg-white border border-slate-200 rounded px-2 py-1 text-slate-600"
            >
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
      <p>{children}</p>
    </div>
  );
}
