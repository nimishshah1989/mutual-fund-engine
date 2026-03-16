"""
models/schemas/scores.py

Pydantic schemas for the QFS, FSAS, shortlist, and recommendation API endpoints.
Covers request bodies, response models, and score detail breakdowns.

v2: Removed CRS-related schemas. Added shortlist and recommendation schemas.
"""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ComputeLayer(str, enum.Enum):
    """Which scoring layer to compute."""
    QFS = "qfs"
    FSAS = "fsas"
    ALL = "all"


class ScoreComputeRequest(BaseModel):
    """Request body for triggering score computation."""
    category_name: Optional[str] = Field(
        default=None,
        description="SEBI category to compute. None = all categories.",
    )
    layer: ComputeLayer = Field(
        default=ComputeLayer.QFS,
        description="Which scoring layer to run. 'all' runs QFS -> shortlist -> FSAS -> recommend.",
    )
    trigger_event: str = Field(
        default="manual_compute",
        max_length=100,
        description="What triggered this computation (for audit trail).",
    )
    shortlist_n: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description="Top N funds per category to shortlist. Default 5 if not specified.",
    )


# ---------------------------------------------------------------------------
# QFS Response schemas
# ---------------------------------------------------------------------------

class MetricHorizonDetail(BaseModel):
    """Single metric value at one horizon — raw and normalised."""
    raw: Optional[Decimal] = Field(None, description="Raw metric value from data source")
    normalised: Optional[Decimal] = Field(None, description="Min-max normalised score (0-100)")


class MetricBreakdown(BaseModel):
    """Full breakdown for one metric across all horizons."""
    metric_name: str
    higher_is_better: bool
    horizons: dict[str, MetricHorizonDetail] = Field(
        default_factory=dict,
        description="Per-horizon raw and normalised values",
    )


class ScoreDetail(BaseModel):
    """Complete QFS score detail for one fund — used on the deep-dive page."""
    mstar_id: str
    computed_date: date
    qfs: Decimal = Field(..., description="Final Quantitative Fund Score (0-100)")
    wfs_raw: Optional[Decimal] = Field(None, description="Weighted Fund Score before final normalization")
    score_1y: Optional[Decimal] = Field(None, description="Average normalised score for 1-year horizon")
    score_3y: Optional[Decimal] = Field(None, description="Average normalised score for 3-year horizon")
    score_5y: Optional[Decimal] = Field(None, description="Average normalised score for 5-year horizon")
    score_10y: Optional[Decimal] = Field(None, description="Average normalised score for 10-year horizon")
    data_completeness_pct: Optional[Decimal] = Field(
        None, description="Percentage of scorable data points available (dynamic from METRIC_CONFIG)"
    )
    available_horizons: int = Field(4, description="Number of horizons with data")
    metric_scores: Optional[dict[str, Any]] = Field(
        None, description="Full metric breakdown: {metric: {horizon: {raw, normalised}}}"
    )
    missing_metrics: Optional[list[dict[str, Any]]] = Field(
        None, description="List of missing data points"
    )
    category_universe_size: Optional[int] = Field(
        None, description="Number of funds in category at compute time"
    )
    data_vintage: Optional[date] = Field(None, description="Date of input data used")
    engine_version: Optional[str] = Field(None, description="Engine algorithm version")
    input_hash: Optional[str] = Field(None, description="SHA-256 hash of input data")
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# FSAS Response schemas
# ---------------------------------------------------------------------------

class SectorContributionDetail(BaseModel):
    """Breakdown of one sector's contribution to the FMS score."""
    exposure_pct: Decimal = Field(..., description="Fund's allocation to this sector (%)")
    benchmark_weight_pct: Decimal = Field(Decimal("0"), description="Benchmark allocation to this sector (%)")
    active_weight: Decimal = Field(Decimal("0"), description="Fund exposure - benchmark weight")
    signal: str = Field(..., description="FM signal for this sector")
    signal_weight: Decimal = Field(..., description="Numeric weight of the signal")
    confidence: str = Field(..., description="FM confidence level")
    confidence_multiplier: Decimal = Field(..., description="Numeric multiplier for confidence")
    contribution: Decimal = Field(..., description="Sector contribution to raw FMS")


class FSASDetail(BaseModel):
    """Complete FSAS score detail for one fund."""
    mstar_id: str
    fm_signal_date: date = Field(..., description="Date of the FM signal set used")
    holdings_date: date = Field(..., description="Date of the holdings data used")
    raw_fsas: Optional[Decimal] = Field(None, description="Raw FSAS before normalization")
    fsas: Decimal = Field(..., description="Normalised FSAS (0-100)")
    sector_contributions: Optional[dict[str, Any]] = Field(
        None,
        description="Per-sector breakdown: {sector: {exposure_pct, signal, contribution, ...}}",
    )
    stale_holdings_flag: bool = Field(False, description="True if holdings > 45 days old")
    avoid_exposure_pct: Decimal = Field(Decimal("0"), description="Total % in AVOID sectors")
    engine_version: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Recommendation Response schemas (replaces CRS)
# ---------------------------------------------------------------------------

class RecommendationDetail(BaseModel):
    """Fund recommendation detail — v3: tier/action from 3x3 decision matrix."""
    mstar_id: str
    computed_date: date
    qfs: Decimal = Field(..., description="QFS score (0-100)")
    fsas: Optional[Decimal] = Field(None, description="FM Alignment Score (0-100)")
    qfs_rank: int = Field(..., description="Rank within category (1 = best)")
    category_rank_pct: Decimal = Field(..., description="QFS percentile rank (0-100, 100 = best)")
    is_shortlisted: bool = Field(False, description="Legacy — always False in v3")
    tier: str = Field(..., description="CORE / QUALITY / WATCH / CAUTION / EXIT")
    action: str = Field(..., description="ACCUMULATE / HOLD / REDUCE / EXIT")
    override_applied: bool = Field(False, description="Whether a hard override was applied")
    override_reason: Optional[str] = Field(None, description="Human-readable override reason")
    original_tier: Optional[str] = Field(None, description="Tier before override")
    action_rationale: Optional[str] = Field(None, description="Auto-generated rationale text")

    # v3 Decision Matrix fields
    fm_score: Optional[Decimal] = Field(None, description="FM Alignment Score (0-100)")
    fm_score_percentile: Optional[Decimal] = Field(None, description="FMS percentile in category")
    qfs_percentile: Optional[Decimal] = Field(None, description="QFS percentile in category")
    matrix_row: Optional[str] = Field(None, description="QFS band: HIGH / MID / LOW")
    matrix_col: Optional[str] = Field(None, description="FMS band: HIGH / MID / LOW")
    matrix_position: Optional[str] = Field(None, description="e.g. HIGH_HIGH, MID_LOW")

    qfs_id: Optional[UUID] = None
    fsas_id: Optional[UUID] = None
    engine_version: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Shortlist schemas
# ---------------------------------------------------------------------------

class ShortlistItem(BaseModel):
    """A shortlisted fund with its QFS rank and optional FSAS data."""
    mstar_id: str
    fund_name: Optional[str] = None
    category_name: str
    qfs_score: Decimal
    qfs_rank: int
    total_in_category: int
    shortlist_reason: str = "top_n_by_qfs"
    computed_date: date

    # Enriched from recommendation table
    fsas: Optional[Decimal] = None
    tier: Optional[str] = None
    action: Optional[str] = None
    avoid_exposure_pct: Optional[Decimal] = None

    # Enriched from FSAS detail
    alignment_summary: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Combined fund score detail (all layers)
# ---------------------------------------------------------------------------

class FundScoreDetail(BaseModel):
    """
    Full score detail for a single fund — combines QFS, FSAS, and recommendation.
    Used on the fund deep-dive page to show all scoring layers.
    """
    mstar_id: str
    fund_name: Optional[str] = Field(None, description="Fund name from master data")
    category_name: Optional[str] = Field(None, description="SEBI category name")
    qfs: Optional[ScoreDetail] = None
    fsas: Optional[FSASDetail] = None
    recommendation: Optional[RecommendationDetail] = None


# ---------------------------------------------------------------------------
# Overview list items
# ---------------------------------------------------------------------------

class ScoreOverviewItem(BaseModel):
    """Summary record for the overview list endpoint."""
    mstar_id: str
    fund_name: Optional[str] = Field(None, description="Fund name from master data")
    category_name: Optional[str] = Field(None, description="SEBI category name")
    computed_date: date
    qfs: Decimal
    wfs_raw: Optional[Decimal] = None
    score_1y: Optional[Decimal] = None
    score_3y: Optional[Decimal] = None
    score_5y: Optional[Decimal] = None
    score_10y: Optional[Decimal] = None
    data_completeness_pct: Optional[Decimal] = None
    available_horizons: int = 4
    category_universe_size: Optional[int] = None
    engine_version: Optional[str] = None

    # Recommendation fields (populated from fund_recommendation)
    tier: Optional[str] = Field(None, description="CORE / QUALITY / WATCH / CAUTION / EXIT")
    action: Optional[str] = Field(None, description="ACCUMULATE / HOLD / REDUCE / EXIT")
    qfs_rank: Optional[int] = Field(None, description="Rank within category")
    category_rank_pct: Optional[Decimal] = Field(None, description="Percentile rank in category")

    # v3 Decision Matrix fields
    fm_score: Optional[Decimal] = Field(None, description="FM Alignment Score (0-100)")
    fm_score_percentile: Optional[Decimal] = Field(None, description="FMS percentile in category")
    qfs_percentile: Optional[Decimal] = Field(None, description="QFS percentile in category")
    matrix_position: Optional[str] = Field(None, description="e.g. HIGH_HIGH, MID_LOW")

    # Override visibility
    override_applied: Optional[bool] = Field(None, description="Whether a hard override was applied")
    override_reason: Optional[str] = Field(None, description="Human-readable override reason")

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Compute response schemas
# ---------------------------------------------------------------------------

class ScoreComputeResult(BaseModel):
    """Result of a score computation for one category."""
    category: str
    fund_count: int = 0
    computed_date: str = ""
    status: str = "unknown"
    rows_upserted: Optional[int] = None
    audits_created: Optional[int] = None
    reason: Optional[str] = None
    error: Optional[str] = None
    tier_distribution: Optional[dict[str, int]] = None
    override_count: Optional[int] = None


class ScoreComputeResponse(BaseModel):
    """Response wrapper for score computation — can be single or multi-category."""
    results: list[ScoreComputeResult]
    total_categories: int
    total_funds_computed: int
    layer: str = Field("qfs", description="Which layer was computed")


class PipelineComputeResult(BaseModel):
    """Result of a full pipeline computation for one category."""
    category: str
    status: str
    computed_date: str = ""
    fund_count: int = 0
    trigger_event: Optional[str] = None
    layers: Optional[dict[str, Any]] = None
    tier_distribution: Optional[dict[str, int]] = None
    shortlisted_count: Optional[int] = None
    error: Optional[str] = None
    warnings: Optional[list[str]] = Field(
        default=None,
        description="Actionable warnings about missing data or skipped steps",
    )


class PipelineComputeResponse(BaseModel):
    """Response wrapper for full pipeline computation."""
    results: list[PipelineComputeResult]
    total_categories: int
    total_funds_computed: int
    total_shortlisted: int = 0
    warnings: list[str] = Field(
        default_factory=list,
        description="Pipeline-level warnings about data availability",
    )
