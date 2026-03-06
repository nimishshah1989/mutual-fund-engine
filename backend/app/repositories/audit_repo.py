"""
repositories/audit_repo.py

Repository for the score_audit_log table. Handles creation
of audit trail entries for score computation traceability.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.score_audit_log import ScoreAuditLog
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[ScoreAuditLog]):
    """Repository for score audit log persistence."""

    model = ScoreAuditLog

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create_audit_log(self, audit_data: dict) -> ScoreAuditLog:
        """Create a score audit log entry for traceability."""
        log_entry = ScoreAuditLog(**audit_data)
        self.session.add(log_entry)
        await self.session.flush()
        return log_entry
