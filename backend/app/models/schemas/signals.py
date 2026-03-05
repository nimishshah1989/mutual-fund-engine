"""
models/schemas/signals.py

Pydantic schemas for Fund Manager sector signal CRUD operations.
Signals represent the FM's forward-looking view on each sector
(OVERWEIGHT / ACCUMULATE / NEUTRAL / UNDERWEIGHT / AVOID).
"""

from __future__ import annotations
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.schemas.common import ConfidenceEnum, SignalEnum


class SignalCreate(BaseModel):
    """Request body to create (or replace) a sector signal."""
    sector_name: str = Field(
        ..., min_length=1, max_length=100,
        description="Sector taxonomy name, e.g. 'Technology', 'Healthcare'",
    )
    signal: SignalEnum = Field(
        ..., description="FM signal for the sector",
    )
    confidence: ConfidenceEnum = Field(
        default=ConfidenceEnum.MEDIUM,
        description="Confidence level of the signal",
    )
    effective_date: date = Field(
        default_factory=date.today,
        description="Date from which this signal is effective (defaults to today)",
    )
    updated_by: str = Field(
        ..., min_length=1, max_length=100,
        description="Name of the fund manager who set the signal",
    )
    notes: str | None = Field(
        default=None, max_length=2000,
        description="Optional rationale or commentary",
    )


class SignalResponse(BaseModel):
    """Single sector signal returned in API responses."""
    id: UUID
    sector_name: str
    signal: str
    confidence: str
    signal_weight: float
    effective_date: date
    updated_by: str
    notes: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SignalListResponse(BaseModel):
    """Wrapper for returning a list of sector signals."""
    signals: list[SignalResponse]
