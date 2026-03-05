"""
models/db/fund_performance.py

Daily fund performance data — NAV, returns across all periods, 52-week high/low.
Source: JHV_PERFORMANCE_DAILY feed (daily, 2AM IST).
Also stores calendar year returns as JSONB for Year1-Year10.
"""

from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FundPerformance(Base):
    __tablename__ = "fund_performance"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mstar_id: Mapped[str] = mapped_column(String(20), nullable=False)
    nav_date: Mapped[date] = mapped_column(Date, nullable=False)
    nav: Mapped[Optional[float]] = mapped_column(Numeric(19, 5))
    nav_change: Mapped[Optional[float]] = mapped_column(Numeric(19, 5))

    # Standard period returns (CAGR)
    return_1d: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    return_1w: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    return_1m: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    return_3m: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    return_6m: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    return_ytd: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    return_1y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    return_2y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    return_3y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    return_4y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    return_5y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    return_7y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    return_10y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    return_since_inception: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))

    # Cumulative returns
    cumulative_return_3y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    cumulative_return_5y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    cumulative_return_10y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))

    # 52-week range
    nav_52w_high: Mapped[Optional[float]] = mapped_column(Numeric(19, 5))
    nav_52w_high_date: Mapped[Optional[date]] = mapped_column(Date)
    nav_52w_low: Mapped[Optional[float]] = mapped_column(Numeric(19, 5))
    nav_52w_low_date: Mapped[Optional[date]] = mapped_column(Date)

    # Calendar year returns (Year1 through Year10 as JSON)
    calendar_year_returns: Mapped[Optional[dict]] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("mstar_id", "nav_date", name="uq_fund_perf_mstar_date"),
        Index("idx_fund_perf_mstar_date", "mstar_id", nav_date.desc()),
        Index("idx_fund_perf_date", nav_date.desc()),
    )
