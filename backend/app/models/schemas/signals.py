"""
models/schemas/signals.py

Pydantic schemas for Fund Manager sector signal operations.
v2: Added bulk update schemas and signal change history.
"""

from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.schemas.common import ConfidenceEnum, SignalEnum


# ---------------------------------------------------------------------------
# Single signal CRUD
# ---------------------------------------------------------------------------

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
    notes: Optional[str] = Field(
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
    notes: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SignalListResponse(BaseModel):
    """Wrapper for returning a list of sector signals."""
    signals: list[SignalResponse]


# ---------------------------------------------------------------------------
# Bulk signal update
# ---------------------------------------------------------------------------

class BulkSignalEntry(BaseModel):
    """One sector's signal data in a bulk update request."""
    sector_name: str = Field(..., min_length=1, max_length=100)
    signal: SignalEnum
    confidence: ConfidenceEnum = ConfidenceEnum.MEDIUM
    notes: Optional[str] = Field(default=None, max_length=2000)


class BulkSignalUpdateRequest(BaseModel):
    """Request body for bulk signal update — all sectors at once."""
    signals: list[BulkSignalEntry] = Field(
        ..., min_length=1, max_length=20,
        description="List of sector signals to update",
    )
    updated_by: str = Field(
        ..., min_length=1, max_length=100,
        description="Name of the fund manager submitting changes",
    )
    effective_date: date = Field(
        default_factory=date.today,
        description="Effective date for all changes",
    )
    change_reason: Optional[str] = Field(
        default=None, max_length=500,
        description="Reason for this batch of changes",
    )


class BulkSignalUpdateResponse(BaseModel):
    """Response for bulk signal update."""
    updated_count: int = Field(..., description="Number of signals that actually changed")
    unchanged_count: int = Field(..., description="Number of signals that were unchanged")
    changes: list[SignalResponse] = Field(
        default_factory=list,
        description="The newly created signal records",
    )


# ---------------------------------------------------------------------------
# Sector list (all 11 GICS sectors with current signal)
# ---------------------------------------------------------------------------

class SectorWithSignal(BaseModel):
    """A GICS sector with its current active signal (or null if no signal)."""
    sector_name: str
    signal: Optional[str] = None
    confidence: Optional[str] = None
    signal_weight: Optional[float] = None
    notes: Optional[str] = None
    effective_date: Optional[date] = None
    updated_by: Optional[str] = None
    last_updated: Optional[datetime] = None


class SectorListResponse(BaseModel):
    """All GICS sectors with their current signals."""
    sectors: list[SectorWithSignal]


# ---------------------------------------------------------------------------
# Signal change history
# ---------------------------------------------------------------------------

class SignalChangeLogEntry(BaseModel):
    """One entry in the signal change audit trail."""
    id: UUID
    sector_name: str
    old_signal: Optional[str] = None
    new_signal: str
    old_confidence: Optional[str] = None
    new_confidence: str
    old_notes: Optional[str] = None
    new_notes: Optional[str] = None
    changed_by: str
    change_reason: Optional[str] = None
    changed_at: datetime

    model_config = {"from_attributes": True}
