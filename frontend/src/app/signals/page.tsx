"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { apiFetch } from "@/lib/api";
import type {
  ApiResponse,
  SectorWithSignal,
  SectorListResponse,
  BulkSignalUpdatePayload,
  BulkSignalUpdateResponse,
} from "@/types/api";
import PageHeader from "@/components/PageHeader";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import ErrorState from "@/components/ErrorState";

import { UPDATED_BY_STORAGE_KEY } from "./constants";
import type { SectorEditState } from "./constants";
import SignalToolbar from "./SignalToolbar";
import SignalTable from "./SignalTable";
import SignalPreviewStrip from "./SignalPreviewStrip";
import ChangeHistoryPanel from "./ChangeHistoryPanel";
import BenchmarkWeightsCard from "./BenchmarkWeightsCard";

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

  /* ---------- History refresh counter ---------- */
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);

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
  /*  Edit handler                                                     */
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

      // Signal history panel to refresh
      setHistoryRefreshKey((prev) => prev + 1);
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
        title="FM Sector Signals"
        subtitle="Manage sector views — bulk edit all sectors at once"
      />

      <SignalToolbar
        updatedBy={updatedBy}
        onUpdatedByChange={setUpdatedBy}
        changedCount={changedSectors.size}
        hasChanges={hasChanges}
        canSave={canSave}
        saving={saving}
        onSave={handleSave}
        saveResult={saveResult}
        onDismissResult={() => setSaveResult(null)}
      />

      <SignalTable
        sectors={sectors}
        edits={edits}
        changedSectors={changedSectors}
        onUpdateEdit={updateEdit}
        onRetry={fetchSectors}
      />

      <SignalPreviewStrip sectors={sectors} edits={edits} />

      <ChangeHistoryPanel refreshKey={historyRefreshKey} />

      {/* -------------------------------------------------------------- */}
      {/*  Benchmark Reference Data                                       */}
      {/* -------------------------------------------------------------- */}

      <div className="mt-6">
        <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2 mb-4">
          <span>📊</span> Benchmark Reference Data
        </h2>
        <BenchmarkWeightsCard />
      </div>
    </div>
  );
}
