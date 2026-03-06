"use client";

/* ------------------------------------------------------------------ */
/*  Bulk-edit table for sector signals                                 */
/* ------------------------------------------------------------------ */

import { formatDate, formatTimeAgo } from "@/lib/formatters";
import type { SectorWithSignal } from "@/types/api";
import { SIGNAL_OPTIONS, CONFIDENCE_OPTIONS } from "./constants";
import type { SectorEditState } from "./constants";

interface SignalTableProps {
  sectors: SectorWithSignal[];
  edits: Record<string, SectorEditState>;
  changedSectors: Set<string>;
  onUpdateEdit: (
    sectorName: string,
    field: keyof SectorEditState,
    value: string,
  ) => void;
  onRetry: () => void;
}

export default function SignalTable({
  sectors,
  edits,
  changedSectors,
  onUpdateEdit,
  onRetry,
}: SignalTableProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider w-[200px]">
                Sector
              </th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider w-[180px]">
                Signal
              </th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider w-[140px]">
                Confidence
              </th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Notes
              </th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider w-[160px]">
                Last Updated
              </th>
            </tr>
          </thead>
          <tbody>
            {sectors.map((sector) => {
              const edit = edits[sector.sector_name];
              const isChanged = changedSectors.has(sector.sector_name);

              return (
                <tr
                  key={sector.sector_name}
                  className={`border-b border-slate-100 hover:bg-slate-50 transition-colors ${
                    isChanged
                      ? "border-l-4 border-l-teal-500"
                      : "border-l-4 border-l-transparent"
                  }`}
                >
                  {/* Sector name */}
                  <td className="px-4 py-3 text-sm font-medium text-slate-800">
                    {sector.sector_name}
                  </td>

                  {/* Signal dropdown */}
                  <td className="px-4 py-3">
                    <select
                      value={edit?.signal ?? "NEUTRAL"}
                      onChange={(e) =>
                        onUpdateEdit(
                          sector.sector_name,
                          "signal",
                          e.target.value,
                        )
                      }
                      aria-label={`Signal for ${sector.sector_name}`}
                      className="border border-slate-200 rounded px-3 py-1.5 text-sm bg-white focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none w-full"
                    >
                      {SIGNAL_OPTIONS.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </td>

                  {/* Confidence dropdown */}
                  <td className="px-4 py-3">
                    <select
                      value={edit?.confidence ?? "MEDIUM"}
                      onChange={(e) =>
                        onUpdateEdit(
                          sector.sector_name,
                          "confidence",
                          e.target.value,
                        )
                      }
                      aria-label={`Confidence for ${sector.sector_name}`}
                      className="border border-slate-200 rounded px-3 py-1.5 text-sm bg-white focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none w-full"
                    >
                      {CONFIDENCE_OPTIONS.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  </td>

                  {/* Notes text input */}
                  <td className="px-4 py-3">
                    <input
                      type="text"
                      value={edit?.notes ?? ""}
                      onChange={(e) =>
                        onUpdateEdit(
                          sector.sector_name,
                          "notes",
                          e.target.value,
                        )
                      }
                      placeholder="Optional notes..."
                      aria-label={`Notes for ${sector.sector_name}`}
                      className="border border-slate-200 rounded px-3 py-1.5 text-sm bg-white focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none w-full placeholder:text-slate-400"
                    />
                  </td>

                  {/* Last updated */}
                  <td className="px-4 py-3 text-sm text-slate-500">
                    {sector.last_updated ? (
                      <div>
                        <span>{formatDate(sector.last_updated)}</span>
                        <span className="block text-xs text-slate-400">
                          {formatTimeAgo(sector.last_updated)}
                          {sector.updated_by && (
                            <> &middot; {sector.updated_by}</>
                          )}
                        </span>
                      </div>
                    ) : (
                      <span className="text-slate-400">No signal set</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Empty state if no sectors returned */}
      {sectors.length === 0 && (
        <div className="text-center py-12">
          <p className="text-sm font-medium text-slate-600">
            No sectors returned from the server
          </p>
          <p className="text-xs text-slate-400 mt-1">
            Ensure the backend has the 11 GICS sectors configured.
          </p>
          <button
            onClick={onRetry}
            aria-label="Retry loading sectors"
            className="mt-4 bg-teal-600 text-white font-medium px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
}
