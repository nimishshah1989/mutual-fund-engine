"""
models/db/nav_history.py

Daily NAV history for all mutual funds.
Source: AMFI (via mftool) — one row per fund per trading day.
Used by MF Pulse engine for ratio return calculations and by QFS for excess returns.
"""

from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NavHistory(Base):
    __tablename__ = "nav_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mstar_id: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Morningstar SecId (FK to fund_master)"
    )
    nav_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="NAV publication date"
    )
    nav: Mapped[float] = mapped_column(
        Numeric(14, 4), nullable=False, comment="Net Asset Value"
    )
    source: Mapped[str] = mapped_column(
        String(30), default="amfi", comment="Data source (amfi, morningstar)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("mstar_id", "nav_date", name="uq_nav_history_fund_date"),
        Index("idx_nav_history_fund_date_desc", "mstar_id", nav_date.desc()),
        Index("idx_nav_history_date_desc", nav_date.desc()),
    )
