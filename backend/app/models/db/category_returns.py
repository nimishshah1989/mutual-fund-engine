"""
models/db/category_returns.py

Category average returns — used to compute Category Alpha (Metric #13).
Category Alpha = Fund Return - Category Return for same period.
Available for ALL funds regardless of benchmark availability.

Source: JHV_PERFORMANCE_DAILY feed (CategoryReturn fields).
"""

from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CategoryReturns(Base):
    __tablename__ = "category_returns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    category_code: Mapped[str] = mapped_column(String(20), nullable=False)
    category_name: Mapped[str] = mapped_column(String(200), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)

    return_2y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    return_3y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    return_5y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    return_10y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))

    cumulative_return_3y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    cumulative_return_5y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))
    cumulative_return_10y: Mapped[Optional[float]] = mapped_column(Numeric(12, 5))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("category_code", "as_of_date", name="uq_cat_returns_code_date"),
        Index("idx_cat_returns_code_date", "category_code", as_of_date.desc()),
    )
