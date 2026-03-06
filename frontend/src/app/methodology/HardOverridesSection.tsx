// Hard Overrides section. Lists the automatic tier downgrade rules
// that fire regardless of QFS percentile rank.

import { HARD_OVERRIDES } from "./constants";

export default function HardOverridesSection() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
      <h3 className="text-base font-semibold text-slate-800 mb-1">
        Hard Overrides
      </h3>
      <p className="text-sm text-slate-500 mb-4">
        Certain conditions trigger automatic tier downgrades regardless of the
        QFS percentile rank. Overrides can only downgrade a tier &mdash; never
        upgrade.
      </p>
      <div className="space-y-3">
        {HARD_OVERRIDES.map((o) => (
          <div
            key={o.rule}
            className="flex items-start gap-4 bg-red-50 rounded-lg p-4 border border-red-100"
          >
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
  );
}
