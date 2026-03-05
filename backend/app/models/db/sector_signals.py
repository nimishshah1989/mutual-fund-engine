"""
models/db/sector_signals.py

FM Sector Signal Table — the forward-looking input from the Fund Manager.
Updated every 2-4 weeks. Each signal has an ENUM value and optional confidence.
Previous signals are archived (is_active=False), never deleted.

Signal weights map to numeric values:
  OVERWEIGHT: +1.0, ACCUMULATE: +0.6, NEUTRAL: +0.1,
  UNDERWEIGHT: -0.5, AVOID: -1.0
"""

from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# Signal → weight mapping (used by FSAS engine, stored here for reference)
SIGNAL_WEIGHTS: dict[str, float] = {
    "OVERWEIGHT": 1.0,
    "ACCUMULATE": 0.6,
    "NEUTRAL": 0.1,
    "UNDERWEIGHT": -0.5,
    "AVOID": -1.0,
}


class SectorSignal(Base):
    __tablename__ = "sector_signals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sector_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="FM sector taxonomy name"
    )
    signal: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="OVERWEIGHT / ACCUMULATE / NEUTRAL / UNDERWEIGHT / AVOID"
    )
    confidence: Mapped[str] = mapped_column(
        String(10), nullable=False, default="MEDIUM",
        comment="HIGH / MEDIUM / LOW"
    )
    signal_weight: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False,
        comment="Numeric weight derived from signal"
    )
    effective_date: Mapped[date] = mapped_column(
        Date, nullable=False
    )
    updated_by: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="FM name"
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="FALSE when superseded by newer signal"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_signals_active", "is_active", "sector_name",
              postgresql_where=is_active.is_(True)),
        Index("idx_signals_date", effective_date.desc()),
    )
