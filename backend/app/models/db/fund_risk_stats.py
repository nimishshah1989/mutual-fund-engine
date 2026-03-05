"""
models/db/fund_risk_stats.py

Monthly risk statistics for each fund — Sharpe, Alpha, Beta, Sortino, Treynor,
Tracking Error, Information Ratio, Capture Ratios, Max Drawdown, Correlation,
R-Squared, Skewness, Kurtosis across 1yr, 3yr, 5yr, 10yr horizons.

Source: JHV_RISK_MONTHLY feed (2nd of each month, 3AM IST).
These metrics power Layer 1 (QFS) computation — metrics #1 through #11.
"""

from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FundRiskStats(Base):
    __tablename__ = "fund_risk_stats"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mstar_id: Mapped[str] = mapped_column(String(20), nullable=False)
    month_end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Metric #1: Sharpe Ratio (higher is better)
    sharpe_1y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    sharpe_3y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    sharpe_5y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))

    # Metric #2: Alpha (higher is better) — null if benchmark not in MS index list
    alpha_3y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    alpha_5y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    alpha_10y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))

    # Metric #3: Beta (lower is better)
    beta_3y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    beta_5y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    beta_10y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))

    # Metric #4: Standard Deviation (lower is better)
    std_dev_1y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    std_dev_3y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    std_dev_5y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))

    # Metric #5: Sortino Ratio (higher is better)
    sortino_1y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    sortino_3y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    sortino_5y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))

    # Metric #6: Treynor Ratio (higher is better)
    treynor_1y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    treynor_3y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    treynor_5y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    treynor_10y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))

    # Metric #7: Tracking Error (lower is better) — null if benchmark not in MS index list
    tracking_error_1y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    tracking_error_3y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    tracking_error_5y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    tracking_error_10y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))

    # Metric #8: Information Ratio (higher is better) — null if benchmark not in MS index list
    info_ratio_1y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    info_ratio_3y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    info_ratio_5y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    info_ratio_10y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))

    # Metric #9: Upside Capture Ratio (higher is better)
    capture_up_1y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    capture_up_3y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    capture_up_5y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    capture_up_10y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))

    # Metric #10: Downside Capture Ratio (lower is better)
    capture_down_1y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    capture_down_3y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    capture_down_5y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))

    # Supplementary: Max Drawdown
    max_drawdown_1y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    max_drawdown_3y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    max_drawdown_5y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))

    # Supplementary: Correlation (Beta null fallback)
    correlation_1y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    correlation_3y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    correlation_5y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))

    # Supplementary: R-Squared (Alpha reliability context)
    r_squared_1y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    r_squared_3y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    r_squared_5y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))

    # Supplementary: Skewness and Kurtosis
    skewness_1y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    skewness_3y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    kurtosis_1y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    kurtosis_3y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("mstar_id", "month_end_date", name="uq_risk_stats_mstar_date"),
        Index("idx_risk_stats_mstar_date", "mstar_id", month_end_date.desc()),
    )
