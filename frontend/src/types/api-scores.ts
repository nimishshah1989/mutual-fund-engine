/* ------------------------------------------------------------------ */
/*  Score, shortlist, and recommendation types                         */
/* ------------------------------------------------------------------ */

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
  tier: string | null;
  action: string | null;
  qfs_rank: number | null;
  category_rank_pct: number | null;
}

/* ---------- /api/v1/scores/{mstar_id} ---------- */
export interface FundScoreDetail {
  mstar_id: string;
  fund_name: string | null;
  category_name: string | null;
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

/* ---------- Shortlist ---------- */
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
