/* ------------------------------------------------------------------ */
/*  API response types — verified against actual backend responses     */
/* ------------------------------------------------------------------ */

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

/* ---------- /api/v1/scores/overview ---------- */
export interface FundScoreOverview {
  mstar_id: string;
  fund_name: string | null;
  category_name: string | null;
  computed_date: string;
  qfs: number | null;
  wfs_raw: number | null;
  score_1y: number | null;
  score_3y: number | null;
  score_5y: number | null;
  score_10y: number | null;
  data_completeness_pct: number | null;
  available_horizons: number;
  category_universe_size: number;
  engine_version: string;
  crs: number | null;
  tier: string | null;
  action: string | null;
  fsas: number | null;
}

/* ---------- /api/v1/scores/{mstar_id} ---------- */
export interface FundScoreDetail {
  mstar_id: string;
  qfs: QFSDetail | null;
  fsas: FSASDetail | null;
  crs: CRSDetail | null;
}

export interface QFSDetail {
  mstar_id: string;
  computed_date: string;
  qfs: number;
  wfs_raw: number;
  score_1y: number | null;
  score_3y: number | null;
  score_5y: number | null;
  score_10y: number | null;
  data_completeness_pct: number;
  available_horizons: number;
  metric_scores: Record<string, Record<string, MetricValue>>;
  missing_metrics: Array<{ metric: string; reason: string; horizon: string }>;
  category_universe_size: number;
  data_vintage: string | null;
  engine_version: string;
  input_hash: string;
  created_at: string;
}

export interface MetricValue {
  raw: number | null;
  normalised: number | null;
}

export interface FSASDetail {
  mstar_id: string;
  fsas: number;
  raw_fsas: number;
  sector_contributions: Record<string, SectorContribution>;
  stale_holdings_flag: boolean;
  avoid_exposure_pct: number;
  fm_signal_date: string;
  holdings_date: string;
  engine_version: string;
  created_at: string;
}

export interface SectorContribution {
  signal: string;
  confidence: string;
  contribution: number;
  exposure_pct: number;
  signal_weight: number;
  confidence_multiplier: number;
}

export interface CRSDetail {
  mstar_id: string;
  computed_date: string;
  qfs: number;
  fsas: number;
  qfs_weight: number;
  fsas_weight: number;
  crs: number;
  tier: string;
  action: string;
  override_applied: boolean;
  override_reason: string | null;
  original_tier: string | null;
  action_rationale: string | null;
  qfs_id: string;
  fsas_id: string;
  engine_version: string;
  created_at: string;
}

/* ---------- /api/v1/signals ---------- */
/* Response is: { success, data: { signals: FMSignal[] } } */
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
  fsas: { categories_completed: number; categories_failed: number };
  crs: { categories_completed: number; categories_failed: number };
  summary: {
    total_funds_rescored: number;
    tier_distribution: Record<string, number>;
    categories_with_overrides: string[];
  };
  duration_seconds: number;
}

/* ---------- /api/v1/ingest/morningstar ---------- */
export interface IngestPayload {
  mstar_ids: string[];
}

/* ---------- /api/v1/scores/compute ---------- */
export interface ScoreComputePayload {
  layer: "qfs" | "fsas" | "crs" | "all";
  category_name?: string;
  trigger_event?: string;
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
  error: string | null;
}
