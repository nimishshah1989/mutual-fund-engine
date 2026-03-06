"use client";

import { formatDate, formatTimeAgo } from "@/lib/formatters";
import type { DataFreshnessEntry } from "@/types/api";
import { feedDisplayName } from "./utils";

interface DataFreshnessCardProps {
  dataFeeds: [string, DataFreshnessEntry][];
}

/**
 * Card showing the freshness status of each data feed
 * (Morningstar API, JHV Master, Monthly Recompute, etc.).
 */
export default function DataFreshnessCard({ dataFeeds }: DataFreshnessCardProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="text-base font-semibold text-slate-800 mb-4">
        Data Freshness
      </h3>
      {dataFeeds.length === 0 ? (
        <p className="text-sm text-slate-400 text-center py-4">
          No data feeds configured
        </p>
      ) : (
        <div className="space-y-1">
          {dataFeeds.map(([feedKey, feed]) => (
            <DataFeedRow key={feedKey} feedKey={feedKey} feed={feed} />
          ))}
        </div>
      )}
    </div>
  );
}

/* ---- Internal sub-component for a single feed row ---- */

interface DataFeedRowProps {
  feedKey: string;
  feed: DataFreshnessEntry;
}

function DataFeedRow({ feedKey, feed }: DataFeedRowProps) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-slate-100 last:border-0">
      <div className="min-w-0">
        <p className="text-sm font-medium text-slate-800">
          {feedDisplayName(feedKey)}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          {/* Status badge */}
          <span
            className={`inline-block rounded px-2 py-0.5 text-xs font-bold uppercase ${
              feed.last_status === "SUCCESS" ||
              feed.status === undefined
                ? feed.is_stale
                  ? "bg-amber-100 text-amber-700"
                  : "bg-emerald-100 text-emerald-700"
                : feed.status === "never_run"
                  ? "bg-slate-100 text-slate-500"
                  : "bg-red-100 text-red-700"
            }`}
          >
            {feed.last_status ??
              feed.status ??
              (feed.is_stale ? "STALE" : "OK")}
          </span>
          {feed.is_stale && feed.last_status === "SUCCESS" && (
            <span className="text-xs text-amber-600 font-medium">
              Stale
            </span>
          )}
        </div>
      </div>
      <div className="text-right shrink-0 ml-4">
        {feed.last_run ? (
          <>
            <p className="text-sm text-slate-700">
              {formatDate(feed.last_run)}
            </p>
            <p className="text-xs text-slate-400">
              {formatTimeAgo(feed.last_run)}
              {feed.age_hours !== undefined && (
                <span>
                  {" "}
                  &middot; {feed.age_hours.toFixed(1)}h old
                </span>
              )}
            </p>
            {feed.records_total !== undefined && (
              <p className="text-xs text-slate-400 font-mono">
                {feed.records_succeeded ?? 0}/
                {feed.records_total} succeeded
              </p>
            )}
          </>
        ) : (
          <p className="text-sm text-slate-400 italic">
            Never run
          </p>
        )}
        <p className="text-xs text-slate-300 mt-0.5">
          Threshold: {feed.threshold_hours}h
        </p>
      </div>
    </div>
  );
}
