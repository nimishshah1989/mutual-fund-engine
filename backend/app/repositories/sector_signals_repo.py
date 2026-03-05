"""Repository for sector_signals table."""

from __future__ import annotations
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.sector_signals import SectorSignal
from app.repositories.base import BaseRepository


class SectorSignalRepository(BaseRepository[SectorSignal]):
    model = SectorSignal

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_active_signals(self) -> list[SectorSignal]:
        result = await self.session.execute(
            select(SectorSignal)
            .where(SectorSignal.is_active.is_(True))
            .order_by(SectorSignal.sector_name)
        )
        return list(result.scalars().all())

    async def get_active_by_sector(
        self, sector_name: str
    ) -> SectorSignal | None:
        result = await self.session.execute(
            select(SectorSignal).where(
                SectorSignal.sector_name == sector_name,
                SectorSignal.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def create_signal(self, data: dict) -> SectorSignal:
        # Deactivate any existing active signal for the same sector
        await self.session.execute(
            update(SectorSignal)
            .where(
                SectorSignal.sector_name == data["sector_name"],
                SectorSignal.is_active.is_(True),
            )
            .values(is_active=False)
        )
        new_signal = SectorSignal(**data)
        self.session.add(new_signal)
        await self.session.flush()
        return new_signal

    async def deactivate_signal(self, signal_id: UUID) -> bool:
        result = await self.session.execute(
            update(SectorSignal)
            .where(SectorSignal.id == signal_id)
            .values(is_active=False)
        )
        await self.session.flush()
        return result.rowcount > 0
