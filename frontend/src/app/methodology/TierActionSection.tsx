// 3x3 Decision Matrix section. Shows how QFS percentile (Y-axis)
// and FMS percentile (X-axis) combine to determine tier and action.

export default function TierActionSection() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
      <h3 className="text-base font-semibold text-slate-800 mb-1">
        3&times;3 Decision Matrix
      </h3>
      <p className="text-sm text-slate-500 mb-4">
        Each fund is placed into a matrix cell based on two independent
        percentile axes: QFS (quantitative quality) and FMS (sector alignment
        with FM views). The matrix cell determines both the tier classification
        and the recommended action.
      </p>

      {/* Axis explanation */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
        <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
            Y-Axis: QFS Percentile
          </p>
          <p className="text-sm text-slate-600">
            Quantitative Fund Score percentile rank within the fund&apos;s SEBI
            category. Measures the fund&apos;s data-driven quality based on 12
            performance and risk metrics.
          </p>
        </div>
        <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
            X-Axis: FMS Percentile
          </p>
          <p className="text-sm text-slate-600">
            FM Alignment Score percentile rank within the fund&apos;s SEBI
            category. Measures how well the fund&apos;s active sector bets align
            with the fund manager&apos;s views.
          </p>
        </div>
      </div>

      {/* Tercile thresholds */}
      <div className="bg-teal-50 border border-teal-200 rounded-lg p-4 mb-5">
        <p className="text-sm font-semibold text-teal-800">
          Tercile Thresholds
        </p>
        <p className="text-sm text-teal-700 mt-1">
          Each axis is divided into three terciles:{" "}
          <span className="font-mono font-semibold">LOW (&lt;33.33)</span>,{" "}
          <span className="font-mono font-semibold">MID (33.33&ndash;66.67)</span>
          , and{" "}
          <span className="font-mono font-semibold">HIGH (&gt;66.67)</span>.
          The combination of QFS tercile and FMS tercile places each fund into
          one of 9 matrix cells.
        </p>
      </div>

      {/* Decision Matrix table */}
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
        Decision Matrix
      </p>
      <div className="overflow-hidden rounded-lg border border-slate-200">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider w-36">
                QFS \ FMS
              </th>
              <th className="text-center px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                LOW FMS
                <span className="block text-slate-300 normal-case font-normal">
                  &lt;33.33
                </span>
              </th>
              <th className="text-center px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                MID FMS
                <span className="block text-slate-300 normal-case font-normal">
                  33.33&ndash;66.67
                </span>
              </th>
              <th className="text-center px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                HIGH FMS
                <span className="block text-slate-300 normal-case font-normal">
                  &gt;66.67
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            {/* HIGH QFS row */}
            <tr className="border-b border-slate-100">
              <td className="px-4 py-3">
                <span className="text-xs font-bold text-slate-800 uppercase">
                  HIGH QFS
                </span>
                <span className="block text-xs text-slate-400">
                  &gt;66.67
                </span>
              </td>
              <MatrixCell
                action="HOLD"
                tier="WATCH"
                bg="bg-amber-50"
                actionColor="text-amber-700"
                tierColor="bg-amber-500 text-white"
              />
              <MatrixCell
                action="ACCUMULATE"
                tier="QUALITY"
                bg="bg-blue-50"
                actionColor="text-blue-700"
                tierColor="bg-blue-600 text-white"
              />
              <MatrixCell
                action="ACCUMULATE"
                tier="CORE"
                bg="bg-emerald-50"
                actionColor="text-emerald-700"
                tierColor="bg-emerald-600 text-white"
                star
              />
            </tr>
            {/* MID QFS row */}
            <tr className="border-b border-slate-100">
              <td className="px-4 py-3">
                <span className="text-xs font-bold text-slate-800 uppercase">
                  MID QFS
                </span>
                <span className="block text-xs text-slate-400">
                  33.33&ndash;66.67
                </span>
              </td>
              <MatrixCell
                action="REDUCE"
                tier="CAUTION"
                bg="bg-orange-50"
                actionColor="text-orange-700"
                tierColor="bg-orange-500 text-white"
              />
              <MatrixCell
                action="HOLD"
                tier="WATCH"
                bg="bg-amber-50"
                actionColor="text-amber-700"
                tierColor="bg-amber-500 text-white"
              />
              <MatrixCell
                action="ACCUMULATE"
                tier="QUALITY"
                bg="bg-blue-50"
                actionColor="text-blue-700"
                tierColor="bg-blue-600 text-white"
              />
            </tr>
            {/* LOW QFS row */}
            <tr>
              <td className="px-4 py-3">
                <span className="text-xs font-bold text-slate-800 uppercase">
                  LOW QFS
                </span>
                <span className="block text-xs text-slate-400">
                  &lt;33.33
                </span>
              </td>
              <MatrixCell
                action="EXIT"
                tier="EXIT"
                bg="bg-red-50"
                actionColor="text-red-700"
                tierColor="bg-red-600 text-white"
              />
              <MatrixCell
                action="REDUCE"
                tier="CAUTION"
                bg="bg-orange-50"
                actionColor="text-orange-700"
                tierColor="bg-orange-500 text-white"
              />
              <MatrixCell
                action="HOLD"
                tier="WATCH"
                bg="bg-amber-50"
                actionColor="text-amber-700"
                tierColor="bg-amber-500 text-white"
              />
            </tr>
          </tbody>
        </table>
      </div>

      {/* Cell rationale */}
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mt-6 mb-2">
        Cell Rationale
      </p>
      <div className="space-y-2">
        <RationaleItem
          cell="HIGH QFS + HIGH FMS"
          tier="CORE"
          rationale="Top-quality fund with strong FM alignment. Highest conviction for fresh deployment. Marked with a star."
          color="bg-emerald-50 border-emerald-200"
        />
        <RationaleItem
          cell="HIGH QFS + MID FMS / MID QFS + HIGH FMS"
          tier="QUALITY"
          rationale="Either quantitatively excellent with moderate alignment, or moderately scored with strong alignment. Good candidates for portfolio building."
          color="bg-blue-50 border-blue-200"
        />
        <RationaleItem
          cell="HIGH QFS + LOW FMS / MID QFS + MID FMS / LOW QFS + HIGH FMS"
          tier="WATCH"
          rationale="Imbalanced profile. The fund excels on one dimension but is weak on the other, or is middling on both. Hold existing positions but do not add."
          color="bg-amber-50 border-amber-200"
        />
        <RationaleItem
          cell="MID QFS + LOW FMS / LOW QFS + MID FMS"
          tier="CAUTION"
          rationale="Below-average on both dimensions or weak on one with nothing to compensate. Reduce exposure and reallocate to higher-tier alternatives."
          color="bg-orange-50 border-orange-200"
        />
        <RationaleItem
          cell="LOW QFS + LOW FMS"
          tier="EXIT"
          rationale="Bottom tercile on both axes. The fund is quantitatively weak and misaligned with FM views. Full redemption recommended."
          color="bg-red-50 border-red-200"
        />
      </div>

      {/* How to read the matrix */}
      <div className="mt-5 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm font-semibold text-blue-800">
          Reading the Matrix
        </p>
        <p className="text-sm text-blue-700 mt-1">
          The matrix is symmetric in structure &mdash; the diagonal from
          bottom-left (EXIT) to top-right (CORE) represents increasing quality.
          Moving up improves QFS (fund quality). Moving right improves FMS (FM
          alignment). Both must be strong for the highest conviction. Hard
          overrides (next section) can only downgrade a cell&apos;s
          classification, never upgrade it.
        </p>
      </div>
    </div>
  );
}

interface MatrixCellProps {
  action: string;
  tier: string;
  bg: string;
  actionColor: string;
  tierColor: string;
  star?: boolean;
}

function MatrixCell({
  action,
  tier,
  bg,
  actionColor,
  tierColor,
  star,
}: MatrixCellProps) {
  return (
    <td className={`px-4 py-3 text-center ${bg}`}>
      <span
        className={`inline-block rounded px-2 py-0.5 text-xs font-bold ${tierColor}`}
      >
        {tier}
        {star && " \u2605"}
      </span>
      <p className={`text-sm font-semibold mt-1 ${actionColor}`}>{action}</p>
    </td>
  );
}

interface RationaleItemProps {
  cell: string;
  tier: string;
  rationale: string;
  color: string;
}

function RationaleItem({ cell, tier, rationale, color }: RationaleItemProps) {
  return (
    <div className={`rounded-lg p-3 border ${color}`}>
      <p className="text-xs font-semibold text-slate-700">
        {cell} &rarr;{" "}
        <span className="font-bold">{tier}</span>
      </p>
      <p className="text-xs text-slate-500 mt-0.5">{rationale}</p>
    </div>
  );
}
