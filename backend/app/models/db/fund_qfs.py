"""
models/db/fund_qfs.py

Quantitative Fund Score (Layer 1) — backward-looking.
12 active metrics (batting_avg has 0 horizons) x 3 scoring horizons (1Y/3Y/5Y)
-> min-max normalised -> time-weighted -> QFS (0-100).

Data completeness is measured against 17 must-have metric x horizon data points.
10Y data is stored for reference but excluded from WFS scoring.

Recomputed monthly after JHV_RISK_MONTHLY ingestion.
Stores full metric breakdown for deep-dive UI transparency.
"""

from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FundQFS(Base):
    __tablename__ = "fund_qfs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mstar_id: Mapped[str] = mapped_column(String(20), nullable=False)
    computed_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Per-horizon raw scores (sum of normalised metric scores)
    score_1y: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    score_3y: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    score_5y: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    score_10y: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))

    # Weighted Fund Score = 1*score_1y + 2*score_3y + 3*score_5y (10Y excluded; weights 1/2/3)
    wfs_raw: Mapped[Optional[float]] = mapped_column(Numeric(12, 4))

    # Final normalised QFS (0-100)
    qfs: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)

    # Data quality
    data_completeness_pct: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), comment="% of 17 must-have metric x horizon data points available"
    )
    missing_metrics: Mapped[Optional[dict]] = mapped_column(
        JSONB, comment="List of null metrics + how handled"
    )
    available_horizons: Mapped[int] = mapped_column(
        Integer, default=4, comment="Count of horizons with data"
    )

    # Full metric breakdown for deep dive
    metric_scores: Mapped[Optional[dict]] = mapped_column(
        JSONB, comment="{metric: {horizon: {raw, normalised, rank}}}"
    )

    # Cross-validation with Morningstar Quartile Ranks
    quartile_consistency: Mapped[Optional[dict]] = mapped_column(
        JSONB, comment="{1y: Q1, 3y: Q1, 5y: Q2, 10y: Q1}"
    )
    cross_validation_flag: Mapped[Optional[str]] = mapped_column(
        String(50), comment="CONSISTENT / REVIEW_NEEDED / DATA_GAP"
    )

    # Traceability
    data_vintage: Mapped[Optional[date]] = mapped_column(
        Date, comment="Date of input data used"
    )
    input_hash: Mapped[Optional[str]] = mapped_column(
        String(64), comment="SHA-256 of input data"
    )
    engine_version: Mapped[str] = mapped_column(
        String(20), default="1.0.0"
    )
    category_universe_size: Mapped[Optional[int]] = mapped_column(
        Integer, comment="Funds in category at compute time"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("mstar_id", "computed_date", name="uq_qfs_mstar_date"),
        Index("idx_qfs_mstar_date", "mstar_id", computed_date.desc()),
    )
