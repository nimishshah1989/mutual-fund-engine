// Overview section: introduces the two-filter pipeline and shows
// the 4-step process (QFS -> Shortlist -> FSAS -> Recommendation).

export default function OverviewSection() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
      <h3 className="text-base font-semibold text-slate-800 mb-3">Overview</h3>
      <p className="text-sm text-slate-600 leading-relaxed">
        The MF Recommendation Engine uses a{" "}
        <span className="font-semibold text-slate-800">
          two-filter pipeline
        </span>{" "}
        to evaluate every mutual fund in the Indian equity universe. First, the{" "}
        <span className="font-semibold text-slate-800">
          Quantitative Fund Score (QFS)
        </span>{" "}
        ranks all funds within their SEBI category using 13 performance and risk
        metrics. Then, the top funds are shortlisted and evaluated against the
        fund manager&apos;s sector views via the{" "}
        <span className="font-semibold text-slate-800">
          FM Sector Alignment Score (FSAS)
        </span>
        . QFS and FSAS are never blended into a single composite score &mdash;
        they serve as independent layers that filter and refine recommendations.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-5">
        <PipelineStep
          step="1"
          title="QFS Scoring"
          description="Score all funds on 12 metrics across 3 scoring horizons (1Y-5Y)"
          label="All Funds"
        />
        <PipelineStep
          step="2"
          title="Shortlist"
          description="Select top 5 funds per SEBI category by QFS rank"
          label="Top N/Category"
        />
        <PipelineStep
          step="3"
          title="FSAS Scoring"
          description="Evaluate shortlisted funds against FM sector signals"
          label="Shortlisted Only"
        />
        <PipelineStep
          step="4"
          title="Recommendation"
          description="Assign tier from QFS percentile, refine action with FSAS"
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
