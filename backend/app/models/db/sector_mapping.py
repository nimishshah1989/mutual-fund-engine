"""
models/db/sector_mapping.py

ISIN → Sector mapping table.
Maps individual stock ISINs to the FM sector taxonomy.
Populated from NSE equities master file + manual overrides.
"""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SectorMapping(Base):
    __tablename__ = "sector_mapping"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    isin: Mapped[str] = mapped_column(
        String(12), unique=True, nullable=False
    )
    company_name: Mapped[Optional[str]] = mapped_column(String(300))
    nse_symbol: Mapped[Optional[str]] = mapped_column(String(20))
    bse_code: Mapped[Optional[str]] = mapped_column(String(10))
    sector_name: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Maps to FM signal taxonomy"
    )
    sub_sector: Mapped[Optional[str]] = mapped_column(
        String(100), comment="For future v2 sub-sector support"
    )
    nifty_index: Mapped[Optional[str]] = mapped_column(
        String(200), comment="Aligned Nifty/BSE index"
    )
    source: Mapped[str] = mapped_column(
        String(50), default="nse_master"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_sector_mapping_sector", "sector_name"),
    )
