"""
models/db/fund_fsas.py

FM Sector Alignment Score (Layer 2) — forward-looking.
Computed as weighted sum of FM signal weights x fund sector exposure.
Recomputed whenever FM updates signals OR new CAMS holdings arrive.
"""

from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FundFSAS(Base):
    __tablename__ = "fund_fsas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mstar_id: Mapped[str] = mapped_column(String(20), nullable=False)
    fm_signal_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="Which signal version drove this"
    )
    holdings_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="Which holdings data was used"
    )

    # Raw and normalised
    raw_fsas: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    fsas: Mapped[float] = mapped_column(
        Numeric(8, 4), nullable=False, comment="Normalised 0-100"
    )

    # Sector-by-sector breakdown
    sector_contributions: Mapped[dict] = mapped_column(
        JSONB, nullable=False,
        comment="{sector: {exposure_pct, signal, signal_weight, contribution}}"
    )

    # Flags
    stale_holdings_flag: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Holdings > 45 days old"
    )
    sector_drift_alerts: Mapped[Optional[dict]] = mapped_column(
        JSONB, comment="[{sector, prev_pct, curr_pct, change}]"
    )
    avoid_exposure_pct: Mapped[float] = mapped_column(
        Numeric(5, 2), default=0, comment="Total exposure to AVOID sectors"
    )

    engine_version: Mapped[str] = mapped_column(
        String(20), default="1.0.0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("mstar_id", "fm_signal_date", name="uq_fsas_mstar_signal"),
        Index("idx_fsas_mstar_date", "mstar_id", fm_signal_date.desc()),
    )
