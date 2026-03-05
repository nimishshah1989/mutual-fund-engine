"""
models/db/fund_ranks.py

Monthly Morningstar ranks — quartile ranks (Q1-Q4) and absolute ranks
within SEBI category for multiple time periods.
Used for QFS cross-validation and displayed in fund views.

Source: JHV_RISK_MONTHLY feed (ranks section) + JHV_CALENDAR_ANNUAL.
"""

from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FundRanks(Base):
    __tablename__ = "fund_ranks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mstar_id: Mapped[str] = mapped_column(String(20), nullable=False)
    month_end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Quartile Ranks (1=top quartile, 4=bottom)
    rank_1m_quartile: Mapped[Optional[int]] = mapped_column(Integer)
    rank_3m_quartile: Mapped[Optional[int]] = mapped_column(Integer)
    rank_6m_quartile: Mapped[Optional[int]] = mapped_column(Integer)
    rank_1y_quartile: Mapped[Optional[int]] = mapped_column(Integer)
    rank_2y_quartile: Mapped[Optional[int]] = mapped_column(Integer)
    rank_3y_quartile: Mapped[Optional[int]] = mapped_column(Integer)
    rank_5y_quartile: Mapped[Optional[int]] = mapped_column(Integer)
    rank_7y_quartile: Mapped[Optional[int]] = mapped_column(Integer)
    rank_10y_quartile: Mapped[Optional[int]] = mapped_column(Integer)

    # Absolute Ranks (position within category, e.g. 4th of 32)
    abs_rank_1m: Mapped[Optional[int]] = mapped_column(Integer)
    abs_rank_3m: Mapped[Optional[int]] = mapped_column(Integer)
    abs_rank_6m: Mapped[Optional[int]] = mapped_column(Integer)
    abs_rank_1y: Mapped[Optional[int]] = mapped_column(Integer)
    abs_rank_2y: Mapped[Optional[int]] = mapped_column(Integer)
    abs_rank_3y: Mapped[Optional[int]] = mapped_column(Integer)
    abs_rank_5y: Mapped[Optional[int]] = mapped_column(Integer)
    abs_rank_7y: Mapped[Optional[int]] = mapped_column(Integer)
    abs_rank_10y: Mapped[Optional[int]] = mapped_column(Integer)

    # Calendar Year Percentile Ranks (from JHV_CALENDAR_ANNUAL)
    rank_yr1: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    rank_yr2: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    rank_yr3: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    rank_yr4: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    rank_yr5: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    rank_yr6: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    rank_yr7: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    rank_yr8: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    rank_yr9: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    rank_yr10: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("mstar_id", "month_end_date", name="uq_ranks_mstar_date"),
        Index("idx_ranks_mstar_date", "mstar_id", month_end_date.desc()),
    )
