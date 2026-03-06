"""
models/db/benchmark_history.py

Daily closing prices for benchmark indices (primarily Nifty 50).
Source: yfinance (Yahoo Finance) — ^NSEI ticker.
Used by MF Pulse for ratio return calculations and QFS for excess return computation.
"""

from __future__ import annotations
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BenchmarkHistory(Base):
    __tablename__ = "benchmark_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    benchmark_name: Mapped[str] = mapped_column(
        String(50), nullable=False, default="NIFTY_50",
        comment="Benchmark identifier (NIFTY_50, SENSEX, etc.)"
    )
    price_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="Trading date"
    )
    close_price: Mapped[float] = mapped_column(
        Numeric(14, 4), nullable=False, comment="Closing price/index value"
    )
    source: Mapped[str] = mapped_column(
        String(30), default="yfinance", comment="Data source"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("benchmark_name", "price_date", name="uq_benchmark_history_name_date"),
        Index("idx_benchmark_history_name_date_desc", "benchmark_name", price_date.desc()),
    )
