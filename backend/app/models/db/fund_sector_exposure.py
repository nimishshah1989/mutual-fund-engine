"""
models/db/fund_sector_exposure.py

Monthly fund portfolio allocation by sector.
Derived from CAMS/KFintech holdings → ISIN → sector mapping.
Used by FSAS engine to compute sector alignment with FM signals.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FundSectorExposure(Base):
    __tablename__ = "fund_sector_exposure"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mstar_id: Mapped[str] = mapped_column(String(20), nullable=False)
    month_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    sector_name: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Same taxonomy as sector_signals"
    )
    exposure_pct: Mapped[float] = mapped_column(
        Numeric(8, 4), nullable=False,
        comment="Percentage allocation 0-100"
    )
    source: Mapped[str] = mapped_column(
        String(20), default="cams",
        comment="cams / kfintech / morningstar"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("mstar_id", "month_end_date", "sector_name",
                         name="uq_exposure_fund_date_sector"),
        Index("idx_exposure_fund_date", "mstar_id", month_end_date.desc()),
    )
