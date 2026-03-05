"""
models/db/score_audit_log.py

Audit trail for all score changes — every QFS, FSAS, CRS computation
is logged with old/new values, trigger event, and timestamp.
Enables backtesting and regulatory compliance.
"""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ScoreAuditLog(Base):
    __tablename__ = "score_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mstar_id: Mapped[str] = mapped_column(String(20), nullable=False)
    computation_type: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="QFS / FSAS / CRS"
    )
    old_value: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    new_value: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    old_tier: Mapped[Optional[str]] = mapped_column(String(10))
    new_tier: Mapped[Optional[str]] = mapped_column(String(10))
    trigger_event: Mapped[Optional[str]] = mapped_column(
        String(100), comment="monthly_recompute / fm_signal_update / manual_override"
    )
    computed_by: Mapped[str] = mapped_column(
        String(100), default="system"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
