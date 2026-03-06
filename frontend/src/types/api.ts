/* ------------------------------------------------------------------ */
/*  API response types — v2: QFS-rank tiers, shortlist, no CRS        */
/* ------------------------------------------------------------------ */

// Re-export score/shortlist types so existing imports from '@/types/api' still work
export type {
  FundScoreOverview, FundScoreDetail, QFSDetail, MetricValue,
  FSASDetail, SectorContribution, RecommendationDetail,
  ShortlistItem, AlignmentSummary, SectorAlignmentEntry,
  MatrixCellSummary, MatrixSummaryResponse,
  BenchmarkWeightItem, BenchmarkWeightsResponse,
} from "./api-scores";

/** Standard envelope returned by most endpoints */
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta?: {
    page?: number;
    limit?: number;
    total?: number;
    total_pages?: number;
  } | null;
  error?: string | null;
}

/* ---------- /health/ready (NOT wrapped in ApiResponse) ---------- */
export interface HealthReady {
  status: string;
  version: string;
  environment: string;
  checks: {
    database: { status: string };
    data_freshness: Record<string, DataFreshnessEntry>;
    scheduler: SchedulerHealth;
  };
  warnings: string[];
}

export interface DataFreshnessEntry {
  last_run: string | null;
  last_status?: string;
  status?: string;
  records_total?: number;
  records_succeeded?: number;
  records_failed?: number;
  age_hours?: number;
  is_stale: boolean;
  threshold_hours: number;
}

export interface SchedulerHealth {
  status: string;
  job_count: number;
  jobs: SchedulerJob[];
}

export interface SchedulerJob {
  id: string;
  name: string;
  next_run: string;
  pending: boolean;
}

/* ---------- /api/v1/signals ---------- */
export interface SignalsResponse {
  signals: FMSignal[];
}

export interface FMSignal {
  id: string;
  sector_name: string;
  signal: string;
  confidence: string;
  signal_weight: number;
  effective_date: string;
  updated_by: string;
  notes: string | null;
  is_active: boolean;
  created_at: string;
}

export interface SignalCreatePayload {
  sector_name: string;
  signal: string;
  confidence: string;
  updated_by: string;
  notes?: string;
}

export interface SectorWithSignal {
  sector_name: string;
  signal: string | null;
  confidence: string | null;
  signal_weight: number | null;
  notes: string | null;
  effective_date: string | null;
  updated_by: string | null;
  last_updated: string | null;
}

export interface SectorListResponse {
  sectors: SectorWithSignal[];
}

export interface BulkSignalEntry {
  sector_name: string;
  signal: string;
  confidence: string;
  notes: string | null;
}

export interface BulkSignalUpdatePayload {
  signals: BulkSignalEntry[];
  updated_by: string;
  effective_date?: string;
  change_reason?: string;
}

export interface BulkSignalUpdateResponse {
  updated_count: number;
  unchanged_count: number;
  changes: FMSignal[];
}

export interface SignalChangeLogEntry {
  id: string;
  sector_name: string;
  old_signal: string | null;
  new_signal: string;
  old_confidence: string | null;
  new_confidence: string;
  old_notes: string | null;
  new_notes: string | null;
  changed_by: string;
  change_reason: string | null;
  changed_at: string;
}

/* ---------- /api/v1/ingest/logs ---------- */
export interface IngestionLog {
  id: string;
  feed_name: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  records_total: number;
  records_inserted: number;
  records_updated: number;
  records_failed: number;
  error_details: string | null;
  created_at: string;
}

/* ---------- /api/v1/jobs/fm-signal-recompute ---------- */
export interface RecomputeResult {
  job: string;
  status: string;
  triggered_by: string;
  fsas: { fund_count: number; status: string };
  recommendation: {
    fund_count: number;
    tier_distribution: Record<string, number>;
    shortlisted_count: number;
    override_count: number;
  };
  summary: {
    total_funds_rescored: number;
    shortlisted_count: number;
    tier_distribution: Record<string, number>;
    override_count: number;
  };
  duration_seconds: number;
}

/* ---------- /api/v1/ingest/morningstar ---------- */
export interface IngestPayload {
  mstar_ids: string[];
}

/* ---------- /api/v1/scores/compute ---------- */
export interface ScoreComputePayload {
  layer: "qfs" | "fsas" | "all";
  category_name?: string;
  trigger_event?: string;
  shortlist_n?: number;
}

export interface ScoreComputeResult {
  results: ScoreComputeCategoryResult[];
  total_categories: number;
  total_funds_computed: number;
}

export interface ScoreComputeCategoryResult {
  category: string;
  status: string;
  computed_date: string;
  fund_count: number;
  trigger_event: string;
  layers: Record<string, unknown>;
  tier_distribution: Record<string, number>;
  shortlisted_count?: number;
  error: string | null;
}

/* ---------- /api/v1/benchmarks ---------- */
export interface BenchmarkRefreshResponse {
  status: string;
  benchmark_name?: string;
  benchmark_mstar_id?: string;
  sector_count: number;
  total_weight_pct: number;
  rows_upserted: number;
  fetched_at?: string;
  reason?: string;
  source?: string;
}
