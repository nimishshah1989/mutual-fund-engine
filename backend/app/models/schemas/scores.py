"""
models/schemas/scores.py

Pydantic schemas for the QFS, FSAS, and CRS scoring API endpoints.
Covers request bodies, response models, and score detail breakdowns.
"""

from __future__ import annotations

import enum
from datetime import date, datetime
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
    CRS = "crs"
    ALL = "all"


class ScoreComputeRequest(BaseModel):
    """Request body for triggering score computation."""
    category_name: Optional[str] = Field(
        default=None,
        description="SEBI category to compute. None = all categories.",
    )
    layer: ComputeLayer = Field(
        default=ComputeLayer.QFS,
        description="Which scoring layer to run. 'all' runs QFS -> FSAS -> CRS.",
    )
    trigger_event: str = Field(
        default="manual_compute",
        max_length=100,
        description="What triggered this computation (for audit trail).",
    )


# ---------------------------------------------------------------------------
# QFS Response schemas
# ---------------------------------------------------------------------------

class MetricHorizonDetail(BaseModel):
    """Single metric value at one horizon — raw and normalised."""
    raw: Optional[float] = Field(None, description="Raw metric value from data source")
    normalised: Optional[float] = Field(None, description="Min-max normalised score (0-100)")


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
    qfs: float = Field(..., description="Final Quantitative Fund Score (0-100)")
    wfs_raw: Optional[float] = Field(None, description="Weighted Fund Score before final normalization")
    score_1y: Optional[float] = Field(None, description="Average normalised score for 1-year horizon")
    score_3y: Optional[float] = Field(None, description="Average normalised score for 3-year horizon")
    score_5y: Optional[float] = Field(None, description="Average normalised score for 5-year horizon")
    score_10y: Optional[float] = Field(None, description="Average normalised score for 10-year horizon")
    data_completeness_pct: Optional[float] = Field(
        None, description="Percentage of 52 possible data points available"
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
    """Breakdown of one sector's contribution to the FSAS score."""
    exposure_pct: float = Field(..., description="Fund's allocation to this sector (%)")
    signal: str = Field(..., description="FM signal for this sector")
    signal_weight: float = Field(..., description="Numeric weight of the signal")
    confidence: str = Field(..., description="FM confidence level")
    confidence_multiplier: float = Field(..., description="Numeric multiplier for confidence")
    contribution: float = Field(..., description="Sector contribution to raw FSAS")


class FSASDetail(BaseModel):
    """Complete FSAS score detail for one fund."""
    mstar_id: str
    fm_signal_date: date = Field(..., description="Date of the FM signal set used")
    holdings_date: date = Field(..., description="Date of the holdings data used")
    raw_fsas: Optional[float] = Field(None, description="Raw FSAS before normalization")
    fsas: float = Field(..., description="Normalised FSAS (0-100)")
    sector_contributions: Optional[dict[str, Any]] = Field(
        None,
        description="Per-sector breakdown: {sector: {exposure_pct, signal, contribution, ...}}",
    )
    stale_holdings_flag: bool = Field(False, description="True if holdings > 45 days old")
    avoid_exposure_pct: float = Field(0.0, description="Total % in AVOID sectors")
    engine_version: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# CRS Response schemas
# ---------------------------------------------------------------------------

class CRSDetail(BaseModel):
    """Complete CRS detail for one fund — tier, action, and breakdown."""
    mstar_id: str
    computed_date: date
    qfs: float = Field(..., description="QFS component (0-100)")
    fsas: float = Field(..., description="FSAS component (0-100)")
    qfs_weight: float = Field(0.60, description="Weight applied to QFS")
    fsas_weight: float = Field(0.40, description="Weight applied to FSAS")
    crs: float = Field(..., description="Composite Recommendation Score (0-100)")
    tier: str = Field(..., description="CORE / QUALITY / WATCH / CAUTION / EXIT")
    action: str = Field(..., description="BUY / SIP / HOLD / REDUCE / EXIT")
    override_applied: bool = Field(False, description="Whether a hard override was applied")
    override_reason: Optional[str] = Field(None, description="Human-readable override reason")
    original_tier: Optional[str] = Field(None, description="Tier before override")
    action_rationale: Optional[str] = Field(None, description="Auto-generated rationale text")
    qfs_id: Optional[UUID] = Field(None, description="FK to the QFS record used")
    fsas_id: Optional[UUID] = Field(None, description="FK to the FSAS record used")
    engine_version: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Combined fund score detail (all layers)
# ---------------------------------------------------------------------------

class FundScoreDetail(BaseModel):
    """
    Full score detail for a single fund — combines QFS, FSAS, and CRS.
    Used on the fund deep-dive page to show all scoring layers.
    """
    mstar_id: str

    # QFS (Layer 1)
    qfs: Optional[ScoreDetail] = None

    # FSAS (Layer 2)
    fsas: Optional[FSASDetail] = None

    # CRS (Layer 3)
    crs: Optional[CRSDetail] = None


# ---------------------------------------------------------------------------
# Overview list items
# ---------------------------------------------------------------------------

class ScoreOverviewItem(BaseModel):
    """Summary QFS record for the overview list endpoint."""
    mstar_id: str
    fund_name: Optional[str] = Field(None, description="Fund name from master data")
    category_name: Optional[str] = Field(None, description="SEBI category name")
    computed_date: date
    qfs: float
    wfs_raw: Optional[float] = None
    score_1y: Optional[float] = None
    score_3y: Optional[float] = None
    score_5y: Optional[float] = None
    score_10y: Optional[float] = None
    data_completeness_pct: Optional[float] = None
    available_horizons: int = 4
    category_universe_size: Optional[int] = None
    engine_version: Optional[str] = None

    # CRS fields (populated when CRS data is available)
    crs: Optional[float] = Field(None, description="Composite Recommendation Score")
    tier: Optional[str] = Field(None, description="CORE / QUALITY / WATCH / CAUTION / EXIT")
    action: Optional[str] = Field(None, description="BUY / SIP / HOLD / REDUCE / EXIT")
    fsas: Optional[float] = Field(None, description="FM Sector Alignment Score")

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
    error: Optional[str] = None


class PipelineComputeResponse(BaseModel):
    """Response wrapper for full pipeline computation."""
    results: list[PipelineComputeResult]
    total_categories: int
    total_funds_computed: int
