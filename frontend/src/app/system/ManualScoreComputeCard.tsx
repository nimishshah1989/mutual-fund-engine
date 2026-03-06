"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import type { ApiResponse } from "@/types/api";
import { LAYER_OPTIONS, type LayerValue } from "./utils";

/** Shape returned by the full pipeline (layer=all) */
interface PipelineResult {
  results: PipelineCategoryResult[];
  total_categories: number;
  total_funds_computed: number;
  total_shortlisted: number;
  warnings: string[];
}

interface PipelineCategoryResult {
  category: string;
  status: string;
  computed_date: string;
  fund_count: number;
  layers?: Record<string, LayerSummary>;
  tier_distribution?: Record<string, number>;
  warnings?: string[];
  error?: string;
}

interface LayerSummary {
  status?: string;
  fund_count?: number;
  reason?: string;
  error?: string;
  [key: string]: unknown;
}

interface ManualScoreComputeCardProps {
  onComputeComplete: () => Promise<void>;
}

/**
 * Card for triggering manual score computation with live status feedback.
 * Shows pipeline progress steps, warnings, and action distribution.
 */
export default function ManualScoreComputeCard({
  onComputeComplete,
}: ManualScoreComputeCardProps) {
  const [selectedLayer, setSelectedLayer] = useState<LayerValue>("all");
  const [categoryName, setCategoryName] = useState("");
  const [computing, setComputing] = useState(false);
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [computeResult, setComputeResult] = useState<PipelineResult | null>(null);
  const [computeError, setComputeError] = useState<string | null>(null);

  async function handleCompute(e: React.FormEvent) {
    e.preventDefault();
    setComputeError(null);
    setComputeResult(null);
    setComputing(true);

    // Show step-by-step status for full pipeline
    if (selectedLayer === "all") {
      setCurrentStep("Seeding benchmark weights (NIFTY 50)...");
      await delay(300);
      setCurrentStep("Computing QFS for all categories...");
    } else if (selectedLayer === "qfs") {
      setCurrentStep("Computing Quantitative Fund Scores...");
    } else {
      setCurrentStep("Computing FM Alignment Scores...");
    }

    try {
      const payload: Record<string, unknown> = {
        layer: selectedLayer,
        trigger_event: "manual_compute",
      };
      const trimmedCategory = categoryName.trim();
      if (trimmedCategory) {
        payload.category_name = trimmedCategory;
      }

      const res = await apiFetch<ApiResponse<PipelineResult>>(
        "/api/v1/scores/compute",
        { method: "POST", body: JSON.stringify(payload) },
      );

      setComputeResult(res.data ?? null);
      setCurrentStep(null);
      setCategoryName("");
      await onComputeComplete();
    } catch (err) {
      setComputeError(err instanceof Error ? err.message : "Compute failed");
      setCurrentStep(null);
    } finally {
      setComputing(false);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="text-base font-semibold text-slate-800 mb-2">
        Run Scoring Pipeline
      </h3>
      <p className="text-xs text-slate-400 mb-4">
        Computes fund scores, FM alignment, matrix classification, and
        action recommendations.
      </p>

      <form onSubmit={handleCompute}>
        {/* Layer selection */}
        <div className="mb-3">
          <label className="text-xs text-slate-500 mb-2 block">Pipeline</label>
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

        {/* Category filter */}
        <div className="mb-4">
          <label className="text-xs text-slate-500 mb-1 block">
            Category (optional)
          </label>
          <input
            type="text"
            value={categoryName}
            onChange={(e) => setCategoryName(e.target.value)}
            placeholder="Leave blank to run all categories"
            aria-label="Category name filter"
            className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
          />
        </div>

        {/* Live status during computation */}
        {computing && currentStep && (
          <div className="flex items-center gap-2 mb-3 px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg">
            <span className="inline-block w-3 h-3 rounded-full bg-blue-500 animate-pulse flex-shrink-0" />
            <span className="text-xs text-blue-700 font-medium">
              {currentStep}
            </span>
          </div>
        )}

        {/* Error display */}
        {computeError && (
          <div className="mb-3 px-3 py-2 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-xs text-red-700 font-medium">{computeError}</p>
          </div>
        )}

        {/* Result display */}
        {computeResult && <PipelineResultDisplay result={computeResult} />}

        <button
          type="submit"
          disabled={computing}
          className="mt-3 bg-teal-600 text-white font-medium px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm disabled:opacity-50"
        >
          {computing ? "Running Pipeline..." : "Run Scoring Pipeline"}
        </button>
      </form>
    </div>
  );
}

/* ---- Detailed result display ---- */

function PipelineResultDisplay({ result }: { result: PipelineResult }) {
  const cat = result.results[0];
  if (!cat) return null;

  const isError = cat.status === "error" || cat.status === "partial_failure";
  const layers = cat.layers ?? {};
  const tierDist = cat.tier_distribution ?? {};
  const warnings = result.warnings ?? cat.warnings ?? [];

  return (
    <div className="space-y-2 mb-3">
      {/* Summary */}
      <div
        className={`px-3 py-2 rounded-lg border ${
          isError
            ? "bg-red-50 border-red-200"
            : "bg-emerald-50 border-emerald-200"
        }`}
      >
        <p
          className={`text-xs font-semibold ${
            isError ? "text-red-700" : "text-emerald-700"
          }`}
        >
          {isError ? "Pipeline completed with issues" : "Pipeline completed"}{" "}
          &mdash; {result.total_funds_computed} funds scored
        </p>
      </div>

      {/* Layer status */}
      {Object.keys(layers).length > 0 && (
        <div className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg">
          <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold mb-1.5">
            Pipeline Steps
          </p>
          <div className="space-y-1">
            {Object.entries(layers).map(([layerName, summary]) => {
              const layerStatus =
                typeof summary === "object" && summary !== null
                  ? (summary as LayerSummary).status ?? "done"
                  : "done";
              const layerFunds =
                typeof summary === "object" && summary !== null
                  ? (summary as LayerSummary).fund_count
                  : null;
              const layerOk =
                layerStatus === "completed" || layerStatus === "done";

              return (
                <div
                  key={layerName}
                  className="flex items-center justify-between text-xs"
                >
                  <span className="text-slate-600 capitalize">
                    {layerName === "qfs"
                      ? "Quantitative Fund Score"
                      : layerName === "fms"
                      ? "FM Alignment Score"
                      : layerName === "recommendation"
                      ? "Matrix Classification"
                      : layerName}
                  </span>
                  <span
                    className={`font-mono font-semibold ${
                      layerOk ? "text-emerald-600" : "text-amber-600"
                    }`}
                  >
                    {layerOk ? "OK" : layerStatus}
                    {layerFunds != null && ` (${layerFunds})`}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Action distribution */}
      {Object.keys(tierDist).length > 0 && (
        <div className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg">
          <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold mb-1.5">
            Action Distribution
          </p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(tierDist).map(([tier, count]) => (
              <span
                key={tier}
                className="inline-flex items-center gap-1 text-xs bg-white border border-slate-200 rounded px-2 py-0.5"
              >
                <span className="font-medium text-slate-700">{tier}</span>
                <span className="font-mono text-slate-500">{count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg">
          <p className="text-[10px] text-amber-600 uppercase tracking-wider font-semibold mb-1">
            Warnings
          </p>
          <ul className="space-y-0.5">
            {warnings.map((w, i) => (
              <li key={i} className="text-xs text-amber-700">
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
