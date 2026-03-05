"""Repository for fund_performance table."""

from __future__ import annotations
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.fund_performance import FundPerformance
from app.repositories.base import BaseRepository


class FundPerformanceRepository(BaseRepository[FundPerformance]):
    model = FundPerformance

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_latest_by_mstar_id(
        self, mstar_id: str
    ) -> FundPerformance | None:
        result = await self.session.execute(
            select(FundPerformance)
            .where(FundPerformance.mstar_id == mstar_id)
            .order_by(FundPerformance.nav_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_mstar_id_and_date(
        self, mstar_id: str, nav_date: date
    ) -> FundPerformance | None:
        result = await self.session.execute(
            select(FundPerformance).where(
                FundPerformance.mstar_id == mstar_id,
                FundPerformance.nav_date == nav_date,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(self, data: dict) -> FundPerformance:
        stmt = pg_insert(FundPerformance).values(**data)
        update_keys = [k for k in data if k not in ("mstar_id", "nav_date")]
        stmt = stmt.on_conflict_do_update(
            constraint="uq_fund_perf_mstar_date",
            set_={key: stmt.excluded[key] for key in update_keys},
        )
        stmt = stmt.returning(FundPerformance)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()

    async def bulk_upsert(self, records: list[dict]) -> int:
        if not records:
            return 0
        update_keys = [
            k for k in records[0] if k not in ("mstar_id", "nav_date")
        ]
        stmt = pg_insert(FundPerformance).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_fund_perf_mstar_date",
            set_={key: stmt.excluded[key] for key in update_keys},
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
