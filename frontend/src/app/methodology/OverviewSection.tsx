// Overview section: introduces the v3 Decision Matrix pipeline and shows
// the 6-step process (QFS → FMS → Percentiles → 3x3 Matrix → Overrides → Action).

export default function OverviewSection() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
      <h3 className="text-base font-semibold text-slate-800 mb-3">Overview</h3>
      <p className="text-sm text-slate-600 leading-relaxed">
        The Recommendation Engine v3 uses a{" "}
        <span className="font-semibold text-slate-800">
          dual-axis Decision Matrix
        </span>{" "}
        to evaluate every mutual fund in the Indian equity universe. First, the{" "}
        <span className="font-semibold text-slate-800">
          Quantitative Fund Score (QFS)
        </span>{" "}
        ranks all funds within their SEBI category using 12 performance and risk
        metrics. Then, the{" "}
        <span className="font-semibold text-slate-800">
          FM Alignment Score (FMS)
        </span>{" "}
        evaluates every fund&apos;s sector exposure against the fund
        manager&apos;s active views, using active weights relative to the NIFTY
        50 benchmark. Both scores are computed for{" "}
        <span className="font-semibold text-slate-800">all funds</span> &mdash;
        there is no shortlist filter. Each fund&apos;s QFS and FMS percentile
        ranks form two independent axes that place the fund into a{" "}
        <span className="font-semibold text-slate-800">3&times;3 matrix</span>,
        which determines its tier and action.
      </p>

      {/* Key change callout */}
      <div className="mt-4 bg-teal-50 border border-teal-200 rounded-lg p-4">
        <p className="text-sm font-semibold text-teal-800">
          What Changed in v3
        </p>
        <ul className="text-sm text-teal-700 mt-1 space-y-1 list-disc list-inside">
          <li>
            No shortlist concept &mdash; FMS is computed for{" "}
            <span className="font-semibold">all</span> funds, not just the top N
          </li>
          <li>
            Two independent axes (QFS percentile + FMS percentile) instead of a
            single-axis tier assignment
          </li>
          <li>
            A 3&times;3 Decision Matrix determines tier and action based on both
            axes
          </li>
          <li>
            FMS uses active weights relative to NIFTY 50, not raw portfolio
            exposure
          </li>
        </ul>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 mt-5">
        <PipelineStep
          step="1"
          title="Fund Scoring (QFS)"
          description="Score all funds on 12 metrics across 3 scoring horizons (1Y-5Y)"
          label="All Funds"
        />
        <PipelineStep
          step="2"
          title="FM Alignment (FMS)"
          description="Score all funds on active sector weights vs FM signals"
          label="All Funds"
        />
        <PipelineStep
          step="3"
          title="Percentile Ranks"
          description="Compute QFS and FMS percentile within SEBI category"
          label="Two Axes"
        />
        <PipelineStep
          step="4"
          title="3x3 Matrix"
          description="Place fund in matrix cell based on QFS + FMS terciles"
          label="9 Cells"
        />
        <PipelineStep
          step="5"
          title="Hard Overrides"
          description="Apply automatic tier caps for data quality, tenure, exposure"
          label="Guard Rails"
        />
        <PipelineStep
          step="6"
          title="Action"
          description="Map final matrix cell to tier and action recommendation"
          label="Tier + Action"
        />
      </div>
    </div>
  );
}

interface PipelineStepProps {
  step: string;
  title: string;
  description: string;
  label: string;
}

function PipelineStep({ step, title, description, label }: PipelineStepProps) {
  return (
    <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
        Step {step}
      </p>
      <p className="text-sm font-semibold text-slate-800 mt-1">{title}</p>
      <p className="text-xs text-slate-500 mt-1">{description}</p>
      <p className="text-lg font-bold text-teal-600 font-mono mt-2">{label}</p>
    </div>
  );
}
