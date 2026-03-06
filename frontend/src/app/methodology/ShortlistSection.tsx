// Step 2: Shortlist section. Explains how the top N funds per
// SEBI category are selected after QFS scoring for FSAS evaluation.

export default function ShortlistSection() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
      <h3 className="text-base font-semibold text-slate-800 mb-1">
        Step 2: Shortlist (Top N per Category)
      </h3>
      <p className="text-sm text-slate-500 mb-4">
        After QFS scoring, the top funds within each SEBI category are
        shortlisted for deeper analysis.
      </p>

      <div className="space-y-2 text-sm text-slate-600">
        <StepItem number={1}>
          <span className="font-semibold text-slate-800">
            Rank within category
          </span>{" "}
          &mdash; All funds are ranked by QFS score within their SEBI
          Morningstar category. Rank 1 = highest QFS in category.
        </StepItem>
        <StepItem number={2}>
          <span className="font-semibold text-slate-800">Select top N</span>{" "}
          &mdash; The top 5 funds per category (configurable) are shortlisted.
          Only shortlisted funds proceed to FSAS evaluation.
        </StepItem>
        <StepItem number={3}>
          <span className="font-semibold text-slate-800">
            Percentile rank computed
          </span>{" "}
          &mdash; Each fund&apos;s percentile rank within its category is
          calculated (0-100 scale, where 100 = best). This percentile determines
          the fund&apos;s tier classification.
        </StepItem>
      </div>

      <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm font-semibold text-blue-800">Why shortlist?</p>
        <p className="text-sm text-blue-700 mt-1">
          FSAS scoring requires comparing fund sector exposure against FM
          signals &mdash; a more nuanced analysis. By first filtering through
          QFS, we focus this deeper analysis on only the highest-quality funds.
          Non-shortlisted funds still receive QFS-based tier and action
          recommendations &mdash; they just don&apos;t get FSAS-refined actions.
        </p>
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
