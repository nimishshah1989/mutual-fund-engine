"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import type { ApiResponse } from "@/types/api";

interface ManualIngestionCardProps {
  /** Called after a successful ingestion to refresh parent data */
  onIngestionComplete: () => Promise<void>;
}

/**
 * Card with a form to trigger manual Morningstar data ingestion
 * by entering comma-separated Morningstar IDs.
 */
export default function ManualIngestionCard({
  onIngestionComplete,
}: ManualIngestionCardProps) {
  const [ingestIds, setIngestIds] = useState("");
  const [ingesting, setIngesting] = useState(false);
  const [ingestResult, setIngestResult] = useState<string | null>(null);
  const [ingestError, setIngestError] = useState<string | null>(null);

  async function handleIngest(e: React.FormEvent) {
    e.preventDefault();
    setIngestError(null);
    setIngestResult(null);

    const ids = ingestIds
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    if (ids.length === 0) {
      setIngestError("Enter at least one Morningstar ID");
      return;
    }

    setIngesting(true);
    try {
      const res = await apiFetch<ApiResponse<{ message: string }>>(
        "/api/v1/ingest/morningstar",
        {
          method: "POST",
          body: JSON.stringify({ mstar_ids: ids }),
        },
      );
      setIngestResult(
        res.data?.message ?? `Ingestion triggered for ${ids.length} fund(s)`,
      );
      setIngestIds("");
      await onIngestionComplete();
    } catch (err) {
      setIngestError(
        err instanceof Error ? err.message : "Ingestion failed",
      );
    } finally {
      setIngesting(false);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="text-base font-semibold text-slate-800 mb-2">
        Manual Ingestion
      </h3>
      <p className="text-xs text-slate-400 mb-4">
        Enter Morningstar IDs (comma-separated) to trigger data ingestion
      </p>
      <form onSubmit={handleIngest}>
        <div>
          <label className="text-xs text-slate-500 mb-1 block">
            Morningstar IDs
          </label>
          <input
            type="text"
            value={ingestIds}
            onChange={(e) => setIngestIds(e.target.value)}
            placeholder="e.g. F00000XYZR, F00000ABCD"
            aria-label="Morningstar fund IDs, comma-separated"
            className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
          />
        </div>
        {ingestError && (
          <p className="text-xs text-red-600 mt-2">{ingestError}</p>
        )}
        {ingestResult && (
          <p className="text-xs text-emerald-600 mt-2">{ingestResult}</p>
        )}
        <button
          type="submit"
          disabled={ingesting}
          className="mt-3 bg-teal-600 text-white font-medium px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm disabled:opacity-50"
        >
          {ingesting ? "Ingesting..." : "Trigger Ingestion"}
        </button>
      </form>
    </div>
  );
}
