"""
models/db/benchmark_sector_weights.py

NIFTY 50 (or other index) sector weights used as the benchmark
for active weight calculations in the FM Alignment Score (FMS).

Weights are auto-fetched from Morningstar GSSB API — not manually entered.
Each row represents one sector's weight in the benchmark on a given date.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BenchmarkSectorWeight(Base):
    __tablename__ = "benchmark_sector_weights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    benchmark_name: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Human-readable name, e.g. 'NIFTY 50'"
    )
    benchmark_mstar_id: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="Morningstar ID of the benchmark index fund/ETF"
    )
    sector_name: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Morningstar sector name, e.g. 'Financial Services'"
    )
    weight_pct: Mapped[float] = mapped_column(
        Numeric(8, 4), nullable=False,
        comment="Sector weight as percentage (0-100)"
    )
    effective_date: Mapped[date] = mapped_column(
        Date, nullable=False,
        comment="Date these weights are effective from"
    )
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="morningstar_gssb",
        comment="Data source identifier"
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        comment="When these weights were fetched from the API"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "benchmark_mstar_id", "sector_name", "effective_date",
            name="uq_benchmark_sector_date"
        ),
        Index("idx_benchmark_name_date", "benchmark_name", effective_date.desc()),
        Index("idx_benchmark_mstar_id", "benchmark_mstar_id"),
    )
