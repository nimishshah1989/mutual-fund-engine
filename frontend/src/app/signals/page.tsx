"use client";

import { useEffect, useState, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { formatDate } from "@/lib/formatters";
import type {
  ApiResponse,
  FMSignal,
  SignalCreatePayload,
  SignalsResponse,
  RecomputeResult,
} from "@/types/api";
import PageHeader from "@/components/PageHeader";
import SignalBadge from "@/components/SignalBadge";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";

const SIGNAL_OPTIONS = [
  "OVERWEIGHT",
  "ACCUMULATE",
  "NEUTRAL",
  "UNDERWEIGHT",
  "AVOID",
];

const CONFIDENCE_OPTIONS = ["HIGH", "MEDIUM", "LOW"];

/** Color map for confidence text badges */
const CONFIDENCE_STYLES: Record<string, string> = {
  HIGH: "bg-emerald-100 text-emerald-700",
  MEDIUM: "bg-amber-100 text-amber-700",
  LOW: "bg-red-100 text-red-700",
};

export default function SignalsPage() {
  const [signals, setSignals] = useState<FMSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* New signal form */
  const [showForm, setShowForm] = useState(false);
  const [formSectorName, setFormSectorName] = useState("");
  const [formSignal, setFormSignal] = useState("NEUTRAL");
  const [formConfidence, setFormConfidence] = useState("MEDIUM");
  const [formUpdatedBy, setFormUpdatedBy] = useState("");
  const [formNotes, setFormNotes] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  /* Recompute */
  const [recomputing, setRecomputing] = useState(false);
  const [recomputeResult, setRecomputeResult] =
    useState<RecomputeResult | null>(null);
  const [recomputeError, setRecomputeError] = useState<string | null>(null);

  /* ---- Fetch signals (response is { signals: [...] }) ---- */
  const fetchSignals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<ApiResponse<SignalsResponse>>(
        "/api/v1/signals",
      );
      setSignals(res.data?.signals ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load signals");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSignals();
  }, [fetchSignals]);

  /* ---- Create new signal ---- */
  async function handleCreateSignal(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);

    if (!formSectorName.trim()) {
      setFormError("Sector name is required");
      return;
    }
    if (!formUpdatedBy.trim()) {
      setFormError("Updated By is required");
      return;
    }

    setSubmitting(true);
    try {
      const payload: SignalCreatePayload = {
        sector_name: formSectorName.trim(),
        signal: formSignal,
        confidence: formConfidence,
        updated_by: formUpdatedBy.trim(),
        notes: formNotes.trim() || undefined,
      };

      await apiFetch<ApiResponse<FMSignal>>("/api/v1/signals", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      /* Reset form and refresh list */
      setFormSectorName("");
      setFormSignal("NEUTRAL");
      setFormConfidence("MEDIUM");
      setFormUpdatedBy("");
      setFormNotes("");
      setShowForm(false);
      await fetchSignals();
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : "Failed to create signal",
      );
    } finally {
      setSubmitting(false);
    }
  }

  /* ---- Recompute scores ---- */
  async function handleRecompute() {
    setRecomputing(true);
    setRecomputeResult(null);
    setRecomputeError(null);
    try {
      const res = await apiFetch<ApiResponse<RecomputeResult>>(
        "/api/v1/jobs/fm-signal-recompute",
        { method: "POST" },
      );
      setRecomputeResult(res.data ?? null);
    } catch (err) {
      setRecomputeError(
        err instanceof Error ? err.message : "Recompute failed",
      );
    } finally {
      setRecomputing(false);
    }
  }

  /* ---- Loading state ---- */
  if (loading) {
    return (
      <div>
        <PageHeader
          emoji="\uD83D\uDCC8"
          title="FM Signals"
          subtitle="Fund Manager sector signals"
        />
        <LoadingSkeleton variant="table" />
      </div>
    );
  }

  /* ---- Error state ---- */
  if (error) {
    return (
      <div>
        <PageHeader
          emoji="\uD83D\uDCC8"
          title="FM Signals"
          subtitle="Fund Manager sector signals"
        />
        <ErrorState message={error} onRetry={fetchSignals} />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        emoji="\uD83D\uDCC8"
        title="FM Signals"
        subtitle="Fund Manager sector signals"
      />

      {/* Action buttons */}
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => setShowForm((s) => !s)}
          className="bg-teal-600 text-white font-medium px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm flex items-center gap-1"
        >
          <span>+</span> Add / Update Signal
        </button>
        <button
          onClick={handleRecompute}
          disabled={recomputing}
          className="bg-white text-slate-600 font-medium px-4 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors text-sm disabled:opacity-50"
        >
          {recomputing ? "Recomputing..." : "Recompute Scores"}
        </button>
      </div>

      {/* Recompute result */}
      {recomputeResult && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 mb-6">
          <p className="text-sm font-medium text-emerald-800">
            Recompute Complete &mdash; {recomputeResult.status}
          </p>
          <p className="text-xs text-emerald-600 mt-1">
            {recomputeResult.summary.total_funds_rescored} funds rescored in{" "}
            {recomputeResult.duration_seconds.toFixed(2)}s
          </p>

          {/* Tier distribution breakdown */}
          {recomputeResult.summary.tier_distribution &&
            Object.keys(recomputeResult.summary.tier_distribution).length >
              0 && (
              <div className="flex items-center gap-3 mt-2">
                <span className="text-xs text-emerald-700 font-medium">
                  Tier Distribution:
                </span>
                {Object.entries(
                  recomputeResult.summary.tier_distribution,
                ).map(([tier, count]) => (
                  <span
                    key={tier}
                    className="inline-flex items-center gap-1 bg-white border border-emerald-200 rounded px-2 py-0.5 text-xs text-slate-700"
                  >
                    <span className="font-medium">{tier}</span>
                    <span className="font-mono">{count}</span>
                  </span>
                ))}
              </div>
            )}

          {/* Sector Alignment / Composite Score category summary */}
          <div className="flex items-center gap-4 mt-2 text-xs text-emerald-600">
            <span>
              Sector Alignment: {recomputeResult.fsas.categories_completed} completed
              {recomputeResult.fsas.categories_failed > 0 && (
                <span className="text-red-600">
                  , {recomputeResult.fsas.categories_failed} failed
                </span>
              )}
            </span>
            <span>
              Composite Score: {recomputeResult.crs.categories_completed} completed
              {recomputeResult.crs.categories_failed > 0 && (
                <span className="text-red-600">
                  , {recomputeResult.crs.categories_failed} failed
                </span>
              )}
            </span>
          </div>
        </div>
      )}
      {recomputeError && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
          <p className="text-sm font-medium text-red-800">Recompute Failed</p>
          <p className="text-xs text-red-600 mt-1">{recomputeError}</p>
        </div>
      )}

      {/* Add / Update signal form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
          <h3 className="text-base font-semibold text-slate-800 mb-4">
            Add / Update Signal
          </h3>
          <form onSubmit={handleCreateSignal}>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
              <div>
                <label className="text-xs text-slate-500 mb-1 block">
                  Sector Name
                </label>
                <input
                  type="text"
                  value={formSectorName}
                  onChange={(e) => setFormSectorName(e.target.value)}
                  placeholder="e.g. Technology"
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                />
              </div>
              <div>
                <label className="text-xs text-slate-500 mb-1 block">
                  Signal
                </label>
                <select
                  value={formSignal}
                  onChange={(e) => setFormSignal(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                >
                  {SIGNAL_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-500 mb-1 block">
                  Confidence
                </label>
                <select
                  value={formConfidence}
                  onChange={(e) => setFormConfidence(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                >
                  {CONFIDENCE_OPTIONS.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-500 mb-1 block">
                  Updated By
                </label>
                <input
                  type="text"
                  value={formUpdatedBy}
                  onChange={(e) => setFormUpdatedBy(e.target.value)}
                  placeholder="Your name"
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                />
              </div>
            </div>

            {/* Notes field */}
            <div className="mt-4">
              <label className="text-xs text-slate-500 mb-1 block">
                Notes (optional)
              </label>
              <textarea
                value={formNotes}
                onChange={(e) => setFormNotes(e.target.value)}
                placeholder="e.g. Infra push beneficiary"
                rows={2}
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none resize-none"
              />
            </div>

            {formError && (
              <p className="text-xs text-red-600 mt-2">{formError}</p>
            )}
            <div className="flex items-center gap-3 mt-4">
              <button
                type="submit"
                disabled={submitting}
                className="bg-teal-600 text-white font-medium px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors text-sm disabled:opacity-50"
              >
                {submitting ? "Saving..." : "Save Signal"}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="bg-white text-slate-600 font-medium px-4 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors text-sm"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Signals table */}
      {signals.length === 0 ? (
        <EmptyState
          title="No signals configured"
          description="Add sector signals to influence fund scoring via the Sector Alignment layer."
          actionLabel="Add Signal"
          onAction={() => setShowForm(true)}
        />
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Sector
                  </th>
                  <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Signal
                  </th>
                  <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Confidence
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Signal Weight
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Notes
                  </th>
                  <th className="text-center px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Active
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Updated By
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Effective Date
                  </th>
                </tr>
              </thead>
              <tbody>
                {signals.map((sig) => (
                  <tr
                    key={sig.id}
                    className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
                  >
                    <td className="px-4 py-3 text-sm font-medium text-slate-800">
                      {sig.sector_name}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <SignalBadge signal={sig.signal} />
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          CONFIDENCE_STYLES[sig.confidence] ??
                          "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {sig.confidence}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-mono text-slate-700">
                      {sig.signal_weight.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-500 max-w-[200px] truncate">
                      {sig.notes ?? "\u2014"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {sig.is_active ? (
                        <span className="inline-block w-2 h-2 rounded-full bg-emerald-500" title="Active" />
                      ) : (
                        <span className="inline-block w-2 h-2 rounded-full bg-slate-300" title="Inactive" />
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600">
                      {sig.updated_by}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-500">
                      {formatDate(sig.effective_date)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
