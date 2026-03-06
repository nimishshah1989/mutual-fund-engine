// Action Reference section. Lists all 6 possible recommendation
// actions from strongest conviction (BUY) to exit.

import { V2_ACTIONS } from "./constants";

export default function ActionReferenceSection() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
      <h3 className="text-base font-semibold text-slate-800 mb-1">
        Action Reference
      </h3>
      <p className="text-sm text-slate-500 mb-4">
        Four possible actions, from strongest conviction (ACCUMULATE) to exit
        recommendation.
      </p>
      <div className="overflow-hidden rounded-lg border border-slate-200">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Action
              </th>
              <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Typical Tier
              </th>
              <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Description
              </th>
            </tr>
          </thead>
          <tbody>
            {V2_ACTIONS.map((a) => (
              <tr
                key={a.action}
                className="border-b border-slate-100 last:border-0"
              >
                <td className="px-4 py-3">
                  <span className="text-sm font-bold text-slate-800">
                    {a.action}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-slate-600">{a.tier}</td>
                <td className="px-4 py-3 text-sm text-slate-500">
                  {a.description}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
