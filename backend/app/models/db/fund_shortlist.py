"""
models/db/fund_shortlist.py

Shortlisted funds — top N per SEBI category by QFS rank.
Only shortlisted funds proceed to FSAS scoring (Layer 2).
Recomputed whenever QFS scores are refreshed.
"""

from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FundShortlist(Base):
    __tablename__ = "fund_shortlist"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mstar_id: Mapped[str] = mapped_column(String(20), nullable=False)
    category_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="SEBI category"
    )
    qfs_score: Mapped[float] = mapped_column(
        Numeric(8, 4), nullable=False, comment="QFS at time of shortlisting"
    )
    qfs_rank: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Rank within category (1 = best)"
    )
    total_in_category: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Total eligible funds in category"
    )
    shortlist_reason: Mapped[str] = mapped_column(
        String(200), nullable=False, default="top_n_by_qfs",
        comment="Why this fund was shortlisted"
    )
    computed_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("mstar_id", "computed_date", name="uq_shortlist_mstar_date"),
        Index("idx_shortlist_category_date", "category_name", computed_date.desc()),
        Index("idx_shortlist_mstar_date", "mstar_id", computed_date.desc()),
    )
