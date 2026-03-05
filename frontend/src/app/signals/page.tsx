"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { apiFetch } from "@/lib/api";
import { formatDate, formatTimeAgo } from "@/lib/formatters";
import type {
  ApiResponse,
  SectorWithSignal,
  SectorListResponse,
  BulkSignalUpdatePayload,
  BulkSignalUpdateResponse,
  SignalChangeLogEntry,
} from "@/types/api";
import PageHeader from "@/components/PageHeader";
import SignalBadge from "@/components/SignalBadge";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import ErrorState from "@/components/ErrorState";

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const SIGNAL_OPTIONS = [
  "OVERWEIGHT",
  "ACCUMULATE",
  "NEUTRAL",
  "UNDERWEIGHT",
  "AVOID",
] as const;

const CONFIDENCE_OPTIONS = ["HIGH", "MEDIUM", "LOW"] as const;

const CONFIDENCE_STYLES: Record<string, string> = {
  HIGH: "bg-emerald-100 text-emerald-700",
  MEDIUM: "bg-amber-100 text-amber-700",
  LOW: "bg-red-100 text-red-700",
};

const UPDATED_BY_STORAGE_KEY = "jip_fm_signals_updated_by";

/* ------------------------------------------------------------------ */
/*  Per-row edit state                                                 */
/* ------------------------------------------------------------------ */

interface SectorEditState {
  signal: string;
  confidence: string;
  notes: string;
}

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function SignalsPage() {
  /* ---------- Sector data ---------- */
  const [sectors, setSectors] = useState<SectorWithSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* ---------- Edit state (map: sector_name -> edits) ---------- */
  const [edits, setEdits] = useState<Record<string, SectorEditState>>({});
  const [originals, setOriginals] = useState<Record<string, SectorEditState>>(
    {},
  );

  /* ---------- Updated By ---------- */
  const [updatedBy, setUpdatedBy] = useState<string>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem(UPDATED_BY_STORAGE_KEY) ?? "";
    }
    return "";
  });

  /* ---------- Save state ---------- */
  const [saving, setSaving] = useState(false);
  const [saveResult, setSaveResult] = useState<{
    message: string;
    type: "success" | "error";
  } | null>(null);

  /* ---------- Change history ---------- */
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyEntries, setHistoryEntries] = useState<SignalChangeLogEntry[]>(
    [],
  );
  const [historyTotal, setHistoryTotal] = useState(0);

  /* ---------------------------------------------------------------- */
  /*  Fetch sectors                                                    */
  /* ---------------------------------------------------------------- */

  const fetchSectors = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<ApiResponse<SectorListResponse>>(
        "/api/v1/signals/sectors",
      );
      const sectorList = res.data?.sectors ?? [];
      setSectors(sectorList);

      // Build original + edit maps
      const origMap: Record<string, SectorEditState> = {};
      const editMap: Record<string, SectorEditState> = {};
      for (const s of sectorList) {
        const state: SectorEditState = {
          signal: s.signal ?? "NEUTRAL",
          confidence: s.confidence ?? "MEDIUM",
          notes: s.notes ?? "",
        };
        origMap[s.sector_name] = { ...state };
        editMap[s.sector_name] = { ...state };
      }
      setOriginals(origMap);
      setEdits(editMap);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load sector signals",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSectors();
  }, [fetchSectors]);

  /* ---------------------------------------------------------------- */
  /*  Detect changed rows                                              */
  /* ---------------------------------------------------------------- */

  const changedSectors = useMemo(() => {
    const changed: string[] = [];
    for (const sectorName of Object.keys(edits)) {
      const orig = originals[sectorName];
      const edit = edits[sectorName];
      if (!orig || !edit) continue;
      if (
        orig.signal !== edit.signal ||
        orig.confidence !== edit.confidence ||
        orig.notes !== edit.notes
      ) {
        changed.push(sectorName);
      }
    }
    return new Set(changed);
  }, [edits, originals]);

  const hasChanges = changedSectors.size > 0;
  const canSave = hasChanges && updatedBy.trim().length > 0 && !saving;

  /* ---------------------------------------------------------------- */
  /*  Edit handlers                                                    */
  /* ---------------------------------------------------------------- */

  function updateEdit(
    sectorName: string,
    field: keyof SectorEditState,
    value: string,
  ) {
    setEdits((prev) => ({
      ...prev,
      [sectorName]: {
        ...prev[sectorName],
        [field]: value,
      },
    }));
    // Clear any previous save result when user makes new edits
    setSaveResult(null);
  }

  /* ---------------------------------------------------------------- */
  /*  Save bulk changes                                                */
  /* ---------------------------------------------------------------- */

  async function handleSave() {
    if (!canSave) return;

    // Persist updatedBy for next session
    localStorage.setItem(UPDATED_BY_STORAGE_KEY, updatedBy.trim());

    const changedSignals = Array.from(changedSectors).map((sectorName) => ({
      sector_name: sectorName,
      signal: edits[sectorName].signal,
      confidence: edits[sectorName].confidence,
      notes: edits[sectorName].notes.trim() || null,
    }));

    const payload: BulkSignalUpdatePayload = {
      signals: changedSignals,
      updated_by: updatedBy.trim(),
    };

    setSaving(true);
    setSaveResult(null);

    try {
      const res = await apiFetch<ApiResponse<BulkSignalUpdateResponse>>(
        "/api/v1/signals/bulk",
        {
          method: "PUT",
          body: JSON.stringify(payload),
        },
      );

      const updatedCount = res.data?.updated_count ?? changedSignals.length;
      setSaveResult({
        message: `${updatedCount} sector signal${updatedCount !== 1 ? "s" : ""} updated successfully.`,
        type: "success",
      });

      // Refresh data to sync originals
      await fetchSectors();

      // If history is open, refresh it too
      if (historyOpen) {
        fetchHistory();
      }
    } catch (err) {
      setSaveResult({
        message:
          err instanceof Error ? err.message : "Failed to save signal changes",
        type: "error",
      });
    } finally {
      setSaving(false);
    }
  }

  /* ---------------------------------------------------------------- */
  /*  Fetch change history                                             */
  /* ---------------------------------------------------------------- */

  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const res = await apiFetch<ApiResponse<SignalChangeLogEntry[]>>(
        "/api/v1/signals/history?page=1&limit=20",
      );
      setHistoryEntries(res.data ?? []);
      setHistoryTotal(res.meta?.total ?? 0);
    } catch (err) {
      setHistoryError(
        err instanceof Error ? err.message : "Failed to load change history",
      );
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  function handleToggleHistory() {
    const willOpen = !historyOpen;
    setHistoryOpen(willOpen);
    if (willOpen && historyEntries.length === 0) {
      fetchHistory();
    }
  }

  /* ---------------------------------------------------------------- */
  /*  Auto-dismiss save result toast after 5 seconds                   */
  /* ---------------------------------------------------------------- */

  useEffect(() => {
    if (!saveResult) return;
    const timer = setTimeout(() => setSaveResult(null), 5000);
    return () => clearTimeout(timer);
  }, [saveResult]);

  /* ---------------------------------------------------------------- */
  /*  Loading state                                                    */
  /* ---------------------------------------------------------------- */

  if (loading) {
    return (
      <div>
        <PageHeader
          emoji="📈"
          title="FM Sector Signals"
          subtitle="Manage sector views — bulk edit all sectors at once"
        />
        <LoadingSkeleton variant="table" />
      </div>
    );
  }

  /* ---------------------------------------------------------------- */
  /*  Error state                                                      */
  /* ---------------------------------------------------------------- */

  if (error) {
    return (
      <div>
        <PageHeader
          emoji="📈"
          title="FM Sector Signals"
          subtitle="Manage sector views — bulk edit all sectors at once"
        />
        <ErrorState message={error} onRetry={fetchSectors} />
      </div>
    );
  }

  /* ---------------------------------------------------------------- */
  /*  Main render                                                      */
  /* ---------------------------------------------------------------- */

  return (
    <div>
      <PageHeader
        emoji="📈"
        title="FM Sector Signals"
        subtitle="Manage sector views — bulk edit all sectors at once"
      />

      {/* Updated By + Save button bar */}
      <div className="flex items-end justify-between gap-4 mb-6">
        <div className="flex items-end gap-4">
          <div>
            <label className="text-xs text-slate-500 mb-1 block">
              Updated By <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={updatedBy}
              onChange={(e) => setUpdatedBy(e.target.value)}
              placeholder="Your name (e.g. Nimish Shah)"
              className="w-64 bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
            />
          </div>
          {hasChanges && (
            <p className="text-xs text-teal-600 font-medium pb-2">
              {changedSectors.size} sector
              {changedSectors.size !== 1 ? "s" : ""} modified
            </p>
          )}
        </div>
        <button
          onClick={handleSave}
          disabled={!canSave}
          className="bg-teal-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-teal-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors text-sm"
        >
          {saving ? "Saving..." : "Save All Changes"}
        </button>
      </div>

      {/* Save result toast */}
      {saveResult && (
        <div
          className={`rounded-xl border p-4 mb-6 ${
            saveResult.type === "success"
              ? "bg-emerald-50 border-emerald-200"
              : "bg-red-50 border-red-200"
          }`}
        >
          <div className="flex items-center justify-between">
            <p
              className={`text-sm font-medium ${
                saveResult.type === "success"
                  ? "text-emerald-800"
                  : "text-red-800"
              }`}
            >
              {saveResult.type === "success" ? "Changes Saved" : "Save Failed"}
            </p>
            <button
              onClick={() => setSaveResult(null)}
              className="text-slate-400 hover:text-slate-600 text-sm"
            >
              Dismiss
            </button>
          </div>
          <p
            className={`text-xs mt-1 ${
              saveResult.type === "success"
                ? "text-emerald-600"
                : "text-red-600"
            }`}
          >
            {saveResult.message}
          </p>
        </div>
      )}

      {/* Sector signals bulk edit table */}
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
                      isChanged ? "border-l-4 border-l-teal-500" : "border-l-4 border-l-transparent"
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
                          updateEdit(
                            sector.sector_name,
                            "signal",
                            e.target.value,
                          )
                        }
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
                          updateEdit(
                            sector.sector_name,
                            "confidence",
                            e.target.value,
                          )
                        }
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
                          updateEdit(
                            sector.sector_name,
                            "notes",
                            e.target.value,
                          )
                        }
                        placeholder="Optional notes..."
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

        {/* Empty state inside the card if somehow no sectors come back */}
        {sectors.length === 0 && (
          <div className="text-center py-12">
            <p className="text-sm font-medium text-slate-600">
              No sectors returned from the server
            </p>
            <p className="text-xs text-slate-400 mt-1">
              Ensure the backend has the 11 GICS sectors configured.
            </p>
            <button
              onClick={fetchSectors}
              className="mt-4 bg-teal-600 text-white font-medium px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm"
            >
              Retry
            </button>
          </div>
        )}
      </div>

      {/* Current signal preview strip */}
      {sectors.length > 0 && (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-400 font-medium mr-1">
            Current signals:
          </span>
          {sectors.map((sector) => {
            const currentSignal = edits[sector.sector_name]?.signal ?? "NEUTRAL";
            return (
              <div
                key={sector.sector_name}
                className="flex items-center gap-1.5"
              >
                <span className="text-xs text-slate-500">
                  {sector.sector_name}
                </span>
                <SignalBadge signal={currentSignal} />
              </div>
            );
          })}
        </div>
      )}

      {/* ---- Change History (collapsible) ---- */}
      <div className="mt-8">
        <button
          onClick={handleToggleHistory}
          className="flex items-center gap-2 text-sm font-semibold text-slate-700 hover:text-slate-900 transition-colors"
        >
          <svg
            className={`w-4 h-4 transition-transform ${historyOpen ? "rotate-90" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 5l7 7-7 7"
            />
          </svg>
          Change History
          {historyTotal > 0 && (
            <span className="text-xs text-slate-400 font-normal">
              ({historyTotal} entries)
            </span>
          )}
        </button>

        {historyOpen && (
          <div className="mt-4">
            {historyLoading && <LoadingSkeleton variant="table" />}

            {historyError && (
              <ErrorState message={historyError} onRetry={fetchHistory} />
            )}

            {!historyLoading && !historyError && historyEntries.length === 0 && (
              <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
                <p className="text-sm text-slate-500">
                  No change history found.
                </p>
              </div>
            )}

            {!historyLoading &&
              !historyError &&
              historyEntries.length > 0 && (
                <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse">
                      <thead>
                        <tr className="border-b border-slate-200 bg-slate-50">
                          <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                            Date
                          </th>
                          <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                            Sector
                          </th>
                          <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                            Signal Change
                          </th>
                          <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                            Confidence Change
                          </th>
                          <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                            Changed By
                          </th>
                          <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                            Reason
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {historyEntries.map((entry) => (
                          <tr
                            key={entry.id}
                            className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
                          >
                            <td className="px-4 py-3 text-sm text-slate-600">
                              <div>
                                {formatDate(entry.changed_at)}
                                <span className="block text-xs text-slate-400">
                                  {formatTimeAgo(entry.changed_at)}
                                </span>
                              </div>
                            </td>
                            <td className="px-4 py-3 text-sm font-medium text-slate-800">
                              {entry.sector_name}
                            </td>
                            <td className="px-4 py-3 text-sm">
                              <div className="flex items-center gap-1.5">
                                {entry.old_signal ? (
                                  <SignalBadge signal={entry.old_signal} />
                                ) : (
                                  <span className="text-xs text-slate-400">
                                    (none)
                                  </span>
                                )}
                                <span className="text-slate-400">&rarr;</span>
                                <SignalBadge signal={entry.new_signal} />
                              </div>
                            </td>
                            <td className="px-4 py-3 text-sm">
                              <div className="flex items-center gap-1.5">
                                <span
                                  className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                                    CONFIDENCE_STYLES[
                                      entry.old_confidence ?? ""
                                    ] ?? "bg-slate-100 text-slate-500"
                                  }`}
                                >
                                  {entry.old_confidence ?? "--"}
                                </span>
                                <span className="text-slate-400">&rarr;</span>
                                <span
                                  className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                                    CONFIDENCE_STYLES[entry.new_confidence] ??
                                    "bg-slate-100 text-slate-500"
                                  }`}
                                >
                                  {entry.new_confidence}
                                </span>
                              </div>
                            </td>
                            <td className="px-4 py-3 text-sm text-slate-600">
                              {entry.changed_by}
                            </td>
                            <td className="px-4 py-3 text-sm text-slate-500 max-w-[200px] truncate">
                              {entry.change_reason ?? "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
          </div>
        )}
      </div>
    </div>
  );
}
