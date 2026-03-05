"""Repository for ingestion_log table."""

from __future__ import annotations
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.ingestion_log import IngestionLog
from app.repositories.base import BaseRepository


class IngestionLogRepository(BaseRepository[IngestionLog]):
    model = IngestionLog

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create_log(self, data: dict) -> IngestionLog:
        log = IngestionLog(**data)
        self.session.add(log)
        await self.session.flush()
        return log

    async def update_log(self, log_id: UUID, data: dict) -> IngestionLog:
        log = await self.session.get(IngestionLog, log_id)
        if log is None:
            raise ValueError(f"IngestionLog {log_id} not found")
        for key, value in data.items():
            setattr(log, key, value)
        await self.session.flush()
        return log

    async def get_latest_by_feed(
        self, feed_name: str
    ) -> IngestionLog | None:
        result = await self.session.execute(
            select(IngestionLog)
            .where(IngestionLog.feed_name == feed_name)
            .order_by(IngestionLog.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_recent(self, limit: int = 20) -> list[IngestionLog]:
        result = await self.session.execute(
            select(IngestionLog)
            .order_by(IngestionLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
