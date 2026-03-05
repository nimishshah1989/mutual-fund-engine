"""
models/db/fund_recommendation.py

Fund Recommendation — the final output of the scoring pipeline.
Replaces the old fund_crs table. No more blended CRS score.

QFS and FSAS are displayed separately:
- tier comes from QFS percentile rank within category
- action comes from tier + FSAS alignment context
- FSAS is only populated for shortlisted funds
"""

from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FundRecommendation(Base):
    __tablename__ = "fund_recommendation"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mstar_id: Mapped[str] = mapped_column(String(20), nullable=False)
    computed_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Scores — QFS always present, FSAS only for shortlisted funds
    qfs: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    fsas: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 4), nullable=True,
        comment="Only populated for shortlisted funds"
    )

    # QFS ranking within category
    qfs_rank: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Rank within category by QFS (1 = best)"
    )
    category_rank_pct: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False,
        comment="Percentile rank within category (0-100, 100 = best)"
    )
    is_shortlisted: Mapped[bool] = mapped_column(
        Boolean, default=False,
        comment="True if fund was in top N for its category"
    )

    # Classification
    tier: Mapped[str] = mapped_column(
        String(10), nullable=False,
        comment="CORE / QUALITY / WATCH / CAUTION / EXIT — from QFS percentile"
    )
    action: Mapped[str] = mapped_column(
        String(10), nullable=False,
        comment="BUY / SIP / HOLD_PLUS / HOLD / REDUCE / EXIT"
    )

    # Override tracking
    override_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    override_reason: Mapped[Optional[str]] = mapped_column(String(200))
    original_tier: Mapped[Optional[str]] = mapped_column(String(10))

    # Auto-generated rationale
    action_rationale: Mapped[Optional[str]] = mapped_column(Text)

    # Traceability
    qfs_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    fsas_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    engine_version: Mapped[str] = mapped_column(String(20), default="2.0.0")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("mstar_id", "computed_date", name="uq_recommendation_mstar_date"),
        Index("idx_recommendation_mstar_date", "mstar_id", computed_date.desc()),
        Index("idx_recommendation_tier", "tier", qfs.desc()),
        Index("idx_recommendation_shortlisted", "is_shortlisted", "tier"),
    )
