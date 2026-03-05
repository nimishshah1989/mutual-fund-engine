"""
models/db/ingestion_log.py

Tracks every data ingestion run — which feed, how many records,
success/failure, errors encountered.
"""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IngestionLog(Base):
    __tablename__ = "ingestion_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    feed_name: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="JHV_MASTER / JHV_PERFORMANCE_DAILY / JHV_RISK_MONTHLY / JHV_CALENDAR_ANNUAL / CAMS_HOLDINGS"
    )
    file_name: Mapped[Optional[str]] = mapped_column(String(300))
    records_total: Mapped[Optional[int]] = mapped_column(Integer)
    records_inserted: Mapped[Optional[int]] = mapped_column(Integer)
    records_updated: Mapped[Optional[int]] = mapped_column(Integer)
    records_failed: Mapped[Optional[int]] = mapped_column(Integer)
    errors: Mapped[Optional[dict]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(
        String(20), default="SUCCESS",
        comment="SUCCESS / PARTIAL / FAILED"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
