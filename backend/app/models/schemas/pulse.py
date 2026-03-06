"""
models/schemas/pulse.py

Pydantic schemas for MF Pulse API endpoints.
Defines request/response shapes for ratio return data, category summaries,
and data coverage stats.
"""

from __future__ import annotations

import enum
from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PulsePeriod(str, enum.Enum):
    """Ratio return observation periods."""
    ONE_MONTH = "1m"
    THREE_MONTHS = "3m"
    SIX_MONTHS = "6m"
    ONE_YEAR = "1y"
    TWO_YEARS = "2y"
    THREE_YEARS = "3y"


class PulseSignal(str, enum.Enum):
    """Signal classification based on ratio return."""
    STRONG_OW = "STRONG_OW"
    OVERWEIGHT = "OVERWEIGHT"
    NEUTRAL = "NEUTRAL"
    UNDERWEIGHT = "UNDERWEIGHT"
    STRONG_UW = "STRONG_UW"


# ---------------------------------------------------------------------------
# Response items
# ---------------------------------------------------------------------------

class PulseFundItem(BaseModel):
    """Single fund row in the pulse table."""
    mstar_id: str
    fund_name: Optional[str] = None
    category_name: Optional[str] = None
    period: str
    snapshot_date: Optional[date] = None

    # Ratio return data
    ratio_return: Optional[float] = Field(None, description="Ratio return %")
    fund_return: Optional[float] = Field(None, description="Fund absolute return %")
    nifty_return: Optional[float] = Field(None, description="Nifty 50 return %")
    excess_return: Optional[float] = Field(None, description="Fund - Nifty return %")
    signal: Optional[str] = Field(None, description="STRONG_OW / OVERWEIGHT / NEUTRAL / UNDERWEIGHT / STRONG_UW")

    # Score context (enriched from QFS/recommendation tables)
    qfs: Optional[float] = Field(None, description="QFS score 0-100")
    fm_score: Optional[float] = Field(None, description="FM alignment score 0-100")
    qfs_quadrant: Optional[str] = Field(None, description="HIGH / MID / LOW")
    fm_quadrant: Optional[str] = Field(None, description="HIGH / MID / LOW")
    tier: Optional[str] = Field(None, description="CORE / QUALITY / WATCH / CAUTION / EXIT")
    action: Optional[str] = Field(None, description="ACCUMULATE / HOLD / REDUCE / EXIT")


class PulseCategorySummary(BaseModel):
    """Signal distribution for one SEBI category."""
    category_name: str
    fund_count: int = 0
    avg_ratio_return: float = 0.0
    signals: dict[str, int] = Field(default_factory=dict, description="Signal -> count mapping")


class PulseCoverageStats(BaseModel):
    """Data coverage stats for NAV and benchmark data."""
    nav_fund_count: int = 0
    nav_earliest_date: Optional[date] = None
    nav_latest_date: Optional[date] = None
    nav_total_rows: int = 0
    benchmark_earliest_date: Optional[date] = None
    benchmark_latest_date: Optional[date] = None
    benchmark_total_rows: int = 0
    snapshot_date: Optional[date] = None


# ---------------------------------------------------------------------------
# Response wrappers
# ---------------------------------------------------------------------------

class PulseDataResponse(BaseModel):
    """Response for GET /api/v1/pulse."""
    funds: list[PulseFundItem]
    period: str
    snapshot_date: Optional[date] = None
    total_funds: int = 0


class PulseCategoryResponse(BaseModel):
    """Response for GET /api/v1/pulse/categories."""
    categories: list[PulseCategorySummary]
    period: str
    total_categories: int = 0
