"""
models/db/mf_pulse_snapshot.py

Pre-computed ratio return snapshots for the MF Pulse engine.
One row per fund × period × snapshot date.

Ratio return formula:
  ratio_today = fund_nav / nifty_close
  ratio_old   = fund_nav_old / nifty_close_old
  ratio_return = ((ratio_today / ratio_old) - 1) × 100

Signal classification based on ratio_period = 1 + (ratio_return / 100):
  STRONG_OW:  ratio_period > strong_ow_threshold (default 1.05)
  OVERWEIGHT:  ratio_period > 1.00
  NEUTRAL:     ratio_period == 1.00
  UNDERWEIGHT: ratio_period >= strong_uw_threshold (default 0.95)
  STRONG_UW:   ratio_period < strong_uw_threshold
"""

from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MFPulseSnapshot(Base):
    __tablename__ = "mf_pulse_snapshot"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mstar_id: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Morningstar SecId (FK to fund_master)"
    )
    snapshot_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="Date of snapshot computation"
    )
    period: Mapped[str] = mapped_column(
        String(5), nullable=False, comment="1m, 3m, 6m, 1y, 2y, 3y"
    )

    # Fund NAV data points
    nav_current: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 4), comment="Fund NAV on snapshot date"
    )
    nav_old: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 4), comment="Fund NAV at period start"
    )
    fund_return: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), comment="Fund absolute return % over period"
    )

    # Nifty 50 data points
    nifty_current: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 4), comment="Nifty 50 close on snapshot date"
    )
    nifty_old: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 4), comment="Nifty 50 close at period start"
    )
    nifty_return: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), comment="Nifty 50 return % over period"
    )

    # Ratio return computation
    ratio_current: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 6), comment="fund_nav / nifty_close (current)"
    )
    ratio_old: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 6), comment="fund_nav / nifty_close (old)"
    )
    ratio_return: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), comment="((ratio_current / ratio_old) - 1) × 100"
    )

    # Signal classification
    signal: Mapped[Optional[str]] = mapped_column(
        String(15), comment="STRONG_OW / OVERWEIGHT / NEUTRAL / UNDERWEIGHT / STRONG_UW"
    )

    # Excess return (fund - nifty)
    excess_return: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4), comment="fund_return - nifty_return"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "mstar_id", "snapshot_date", "period",
            name="uq_pulse_snapshot_fund_date_period",
        ),
        Index("idx_pulse_snapshot_period_signal", "period", "signal"),
        Index("idx_pulse_snapshot_fund_date", "mstar_id", snapshot_date.desc()),
        Index("idx_pulse_snapshot_period_date", "period", snapshot_date.desc()),
    )
