"""
models/schemas/ingestion.py

Pydantic request/response schemas for the data ingestion endpoints.
Covers the trigger request, batch result summary, and ingestion log history.

from __future__ import annotations is required for Python 3.9 compat with X | None syntax.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class IngestionRequest(BaseModel):
    """Request body to trigger Morningstar data ingestion for a batch of funds."""
    mstar_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="List of Morningstar fund IDs to ingest (max 200 per batch)",
    )


class IngestionResponse(BaseModel):
    """Summary returned after a batch ingestion run completes."""
    total: int = Field(..., description="Total funds in the batch")
    succeeded: int = Field(..., description="Funds ingested successfully")
    failed: int = Field(..., description="Funds that failed ingestion")
    errors: list[dict[str, str]] = Field(
        default_factory=list,
        description="Per-fund error details [{mstar_id, error}]",
    )
    log_id: UUID = Field(..., description="ID of the IngestionLog record tracking this run")
    duration_seconds: float = Field(..., description="Wall-clock duration of the batch in seconds")


class IngestionLogResponse(BaseModel):
    """Single ingestion log entry for history / audit views."""
    id: UUID
    feed_name: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    records_total: int | None = None
    records_inserted: int | None = None
    records_updated: int | None = None
    records_failed: int | None = None
    error_details: dict | None = Field(
        default=None,
        description="JSON blob with error context from the run",
    )
    created_at: datetime

    model_config = {"from_attributes": True}
