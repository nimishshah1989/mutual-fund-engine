"""
models/db/signal_change_log.py

Audit trail for FM sector signal changes. Every time a signal is updated
via the bulk endpoint, a row is created here capturing the before/after
values for full traceability.
"""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SignalChangeLog(Base):
    __tablename__ = "signal_change_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sector_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="GICS sector name"
    )

    # Before values (None if this is the first signal for the sector)
    old_signal: Mapped[Optional[str]] = mapped_column(String(20))
    old_confidence: Mapped[Optional[str]] = mapped_column(String(10))
    old_notes: Mapped[Optional[str]] = mapped_column(Text)

    # After values
    new_signal: Mapped[str] = mapped_column(String(20), nullable=False)
    new_confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    new_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Who and why
    changed_by: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Name of person who made the change"
    )
    change_reason: Mapped[Optional[str]] = mapped_column(
        String(500), comment="Optional reason for the change"
    )

    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
