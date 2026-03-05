/* ------------------------------------------------------------------ */
/*  API response types — v2: QFS-rank tiers, shortlist, no CRS        */
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
  // v2: QFS-rank based tiers (no CRS)
  tier: string | null;
  action: string | null;
  qfs_rank: number | null;
  category_rank_pct: number | null;
}

/* ---------- /api/v1/scores/{mstar_id} ---------- */
export interface FundScoreDetail {
  mstar_id: string;
  qfs: QFSDetail | null;
  fsas: FSASDetail | null;
  recommendation: RecommendationDetail | null;
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

/* v2: Replaces CRSDetail */
export interface RecommendationDetail {
  mstar_id: string;
  computed_date: string;
  qfs: number;
  fsas: number | null;
  qfs_rank: number;
  category_rank_pct: number;
  is_shortlisted: boolean;
  tier: string;
  action: string;
  override_applied: boolean;
  override_reason: string | null;
  original_tier: string | null;
  action_rationale: string | null;
  qfs_id: string | null;
  fsas_id: string | null;
  engine_version: string;
  created_at: string;
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

/* v2: Sector list with current signal */
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

/* v2: Bulk signal update */
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

/* v2: Signal change history */
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

/* v2: Shortlist */
export interface ShortlistItem {
  mstar_id: string;
  fund_name: string | null;
  category_name: string;
  qfs_score: number;
  qfs_rank: number;
  total_in_category: number;
  shortlist_reason: string;
  computed_date: string;
  fsas: number | null;
  tier: string | null;
  action: string | null;
  avoid_exposure_pct: number | null;
  alignment_summary: AlignmentSummary | null;
}

export interface AlignmentSummary {
  aligned_sectors: SectorAlignmentEntry[];
  misaligned_sectors: SectorAlignmentEntry[];
  neutral_sectors: string[];
  avoid_exposure_pct: number;
  top_aligned: SectorAlignmentEntry[];
  top_misaligned: SectorAlignmentEntry[];
}

export interface SectorAlignmentEntry {
  sector: string;
  signal: string;
  exposure_pct: number;
  contribution: number;
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

/* ---------- /api/v1/jobs/fm-signal-recompute (v2) ---------- */
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
