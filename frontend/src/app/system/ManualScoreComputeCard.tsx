"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import type { ApiResponse, ScoreComputeResult, ScoreComputePayload } from "@/types/api";
import { LAYER_OPTIONS, type LayerValue } from "./utils";

interface ManualScoreComputeCardProps {
  /** Called after a successful compute to refresh parent data */
  onComputeComplete: () => Promise<void>;
}

/**
 * Card with a form to trigger manual score computation.
 * Supports layer selection (QFS / FSAS / Full Pipeline),
 * optional category name filtering, and top N per category for shortlisting.
 */
export default function ManualScoreComputeCard({
  onComputeComplete,
}: ManualScoreComputeCardProps) {
  const [selectedLayer, setSelectedLayer] = useState<LayerValue>("all");
  const [categoryName, setCategoryName] = useState("");
  const [shortlistN, setShortlistN] = useState(5);
  const [computing, setComputing] = useState(false);
  const [computeResult, setComputeResult] = useState<ScoreComputeResult | null>(null);
  const [computeError, setComputeError] = useState<string | null>(null);

  const showShortlistN = selectedLayer === "all";

  async function handleCompute(e: React.FormEvent) {
    e.preventDefault();
    setComputeError(null);
    setComputeResult(null);

    setComputing(true);
    try {
      const payload: ScoreComputePayload = {
        layer: selectedLayer,
        trigger_event: "manual_compute",
      };
      const trimmedCategory = categoryName.trim();
      if (trimmedCategory) {
        payload.category_name = trimmedCategory;
      }
      if (showShortlistN) {
        payload.shortlist_n = shortlistN;
      }

      const res = await apiFetch<ApiResponse<ScoreComputeResult>>(
        "/api/v1/scores/compute",
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
      );
      setComputeResult(res.data ?? null);
      setCategoryName("");
      await onComputeComplete();
    } catch (err) {
      setComputeError(
        err instanceof Error ? err.message : "Compute failed",
      );
    } finally {
      setComputing(false);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="text-base font-semibold text-slate-800 mb-2">
        Manual Score Compute
      </h3>
      <p className="text-xs text-slate-400 mb-4">
        Select a scoring layer to run. Optionally filter by category name.
      </p>
      <form onSubmit={handleCompute}>
        {/* Layer radio buttons */}
        <div className="mb-3">
          <label className="text-xs text-slate-500 mb-2 block">
            Layer
          </label>
          <div className="space-y-2">
            {LAYER_OPTIONS.map((opt) => (
              <label
                key={opt.value}
                className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer"
              >
                <input
                  type="radio"
                  name="compute-layer"
                  value={opt.value}
                  checked={selectedLayer === opt.value}
                  onChange={() => setSelectedLayer(opt.value)}
                  className="border-slate-300 text-teal-600 focus:ring-teal-500"
                />
                {opt.label}
              </label>
            ))}
          </div>
        </div>

        <div className="mb-3">
          <label className="text-xs text-slate-500 mb-1 block">
            Category Name (optional)
          </label>
          <input
            type="text"
            value={categoryName}
            onChange={(e) => setCategoryName(e.target.value)}
            placeholder="e.g. ELSS (Tax Savings) — leave blank for all"
            aria-label="Category name filter for score computation"
            className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
          />
        </div>

        {/* Top N per category — only visible when running full pipeline */}
        {showShortlistN && (
          <div className="mb-3">
            <label className="text-xs text-slate-500 mb-1 block">
              Funds to Shortlist per Category
            </label>
            <div className="flex items-center gap-3">
              <input
                type="number"
                min={1}
                max={20}
                value={shortlistN}
                onChange={(e) => setShortlistN(Math.max(1, Math.min(20, Number(e.target.value) || 1)))}
                aria-label="Number of funds to shortlist per category"
                className="w-20 bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 font-mono text-center focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
              />
              <span className="text-xs text-slate-400">
                Top N funds per SEBI category (1-20)
              </span>
            </div>
          </div>
        )}

        {computeError && (
          <p className="text-xs text-red-600 mt-2">{computeError}</p>
        )}
        {computeResult && <ComputeResultSummary result={computeResult} />}

        <button
          type="submit"
          disabled={computing}
          className="mt-3 bg-teal-600 text-white font-medium px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm disabled:opacity-50"
        >
          {computing ? "Computing..." : "Run Score Compute"}
        </button>
      </form>
    </div>
  );
}

/* ---- Internal sub-component for compute result display ---- */

interface ComputeResultSummaryProps {
  result: ScoreComputeResult;
}

function ComputeResultSummary({ result }: ComputeResultSummaryProps) {
  return (
    <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 mt-2">
      <p className="text-xs text-emerald-700 font-medium">
        Computed {result.total_funds_computed} funds across{" "}
        {result.total_categories} categories
      </p>
      {result.results.length > 0 && (
        <div className="mt-2 space-y-1">
          {result.results.map((cat, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between text-xs"
            >
              <span className="text-emerald-700">{cat.category}</span>
              <div className="flex items-center gap-2">
                <span className="font-mono text-emerald-600">
                  {cat.fund_count} funds
                </span>
                <span
                  className={`inline-block rounded px-1.5 py-0.5 font-bold uppercase ${
                    cat.status === "completed"
                      ? "bg-emerald-100 text-emerald-700"
                      : "bg-red-100 text-red-700"
                  }`}
                >
                  {cat.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
