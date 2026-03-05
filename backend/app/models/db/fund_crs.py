"""
models/db/fund_crs.py

Composite Recommendation Score (Layer 3) — the final output.
CRS = QFS x qfs_weight + FSAS x fsas_weight (default 60/40).
Assigns tier (CORE/QUALITY/WATCH/CAUTION/EXIT) and action (BUY/SIP/HOLD/REDUCE/EXIT).
Applies hard override rules before final classification.
"""

from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FundCRS(Base):
    __tablename__ = "fund_crs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mstar_id: Mapped[str] = mapped_column(String(20), nullable=False)
    computed_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Component scores
    qfs: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    fsas: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    qfs_weight: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0.60)
    fsas_weight: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0.40)

    # Composite score
    crs: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)

    # Classification
    tier: Mapped[str] = mapped_column(
        String(10), nullable=False,
        comment="CORE / QUALITY / WATCH / CAUTION / EXIT"
    )
    action: Mapped[str] = mapped_column(
        String(10), nullable=False,
        comment="BUY / SIP / HOLD_PLUS / HOLD / REDUCE / REVIEW / EXIT"
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
    engine_version: Mapped[str] = mapped_column(String(20), default="1.0.0")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("mstar_id", "computed_date", name="uq_crs_mstar_date"),
        Index("idx_crs_mstar_date", "mstar_id", computed_date.desc()),
        Index("idx_crs_tier", "tier", crs.desc()),
    )
