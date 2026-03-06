"use client";

import { useEffect, useState, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { formatTimeAgo } from "@/lib/formatters";
import type {
  ApiResponse,
  HealthReady,
  DataFreshnessEntry,
  IngestionLog,
} from "@/types/api";
import PageHeader from "@/components/PageHeader";
import StatCard from "@/components/StatCard";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import ErrorState from "@/components/ErrorState";

import WarningsBanner from "./WarningsBanner";
import SystemStatusBadge from "./SystemStatusBadge";
import DataFreshnessCard from "./DataFreshnessCard";
import ScheduledJobsCard from "./ScheduledJobsCard";
import ManualIngestionCard from "./ManualIngestionCard";
import ManualScoreComputeCard from "./ManualScoreComputeCard";
import IngestionLogsTable from "./IngestionLogsTable";

export default function SystemPage() {
  const [health, setHealth] = useState<HealthReady | null>(null);
  const [logs, setLogs] = useState<IngestionLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthRes, logsRes] = await Promise.all([
        apiFetch<HealthReady>("/health/ready"),
        apiFetch<ApiResponse<IngestionLog[]>>("/api/v1/ingest/logs"),
      ]);
      setHealth(healthRes);
      setLogs(logsRes.data ?? []);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load system data",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /* Derived values from health */
  const dbOk = health?.checks.database.status === "ok";
  const schedulerRunning = health?.checks.scheduler.status === "running";
  const schedulerJobs = health?.checks.scheduler.jobs ?? [];
  const dataFeeds: [string, DataFreshnessEntry][] = health?.checks.data_freshness
    ? Object.entries(health.checks.data_freshness)
    : [];
  const morningstarFeed = health?.checks.data_freshness?.MORNINGSTAR_API;
  const warnings = health?.warnings ?? [];

  if (loading) {
    return (
      <div>
        <PageHeader
          emoji="&#x2699;&#xFE0F;"
          title="System"
          subtitle="Administration & monitoring"
        />
        <LoadingSkeleton variant="card" cardCount={4} />
        <div className="mt-6">
          <LoadingSkeleton variant="table" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <PageHeader
          emoji="&#x2699;&#xFE0F;"
          title="System"
          subtitle="Administration & monitoring"
        />
        <ErrorState message={error} onRetry={fetchData} />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        emoji="&#x2699;&#xFE0F;"
        title="System"
        subtitle="Administration & monitoring"
      />

      {/* Warnings banner */}
      <WarningsBanner warnings={warnings} />

      {/* Overall status badge */}
      {health && <SystemStatusBadge health={health} />}

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Database"
          value={dbOk ? "OK" : "Error"}
          colored={dbOk}
          alert={!dbOk}
        />
        <StatCard
          label="Scheduler"
          value={schedulerRunning ? "Running" : "Stopped"}
          subtext={
            schedulerRunning
              ? `${health?.checks.scheduler.job_count ?? 0} jobs`
              : undefined
          }
          colored={schedulerRunning}
          alert={!schedulerRunning}
        />
        <StatCard
          label="Funds Ingested"
          value={String(morningstarFeed?.records_total ?? 0)}
          subtext={
            morningstarFeed?.last_run
              ? `Last: ${formatTimeAgo(morningstarFeed.last_run)}`
              : "Never run"
          }
          colored
        />
        <StatCard
          label="Data Feeds"
          value={`${dataFeeds.length}`}
          subtext={`${dataFeeds.filter(([, f]) => f.is_stale).length} stale`}
          colored={dataFeeds.every(([, f]) => !f.is_stale)}
          alert={dataFeeds.some(([, f]) => f.is_stale)}
        />
      </div>

      {/* Data Freshness + Scheduler */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <DataFreshnessCard dataFeeds={dataFeeds} />
        <ScheduledJobsCard jobs={schedulerJobs} />
      </div>

      {/* Manual operations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <ManualIngestionCard onIngestionComplete={fetchData} />
        <ManualScoreComputeCard onComputeComplete={fetchData} />
      </div>

      {/* Ingestion logs */}
      <IngestionLogsTable logs={logs} />
    </div>
  );
}
