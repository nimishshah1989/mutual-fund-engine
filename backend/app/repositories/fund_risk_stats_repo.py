"""Repository for fund_risk_stats table."""

from __future__ import annotations
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.fund_risk_stats import FundRiskStats
from app.repositories.base import BaseRepository


class FundRiskStatsRepository(BaseRepository[FundRiskStats]):
    model = FundRiskStats

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_latest_by_mstar_id(
        self, mstar_id: str
    ) -> FundRiskStats | None:
        result = await self.session.execute(
            select(FundRiskStats)
            .where(FundRiskStats.mstar_id == mstar_id)
            .order_by(FundRiskStats.month_end_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_mstar_id_and_month(
        self, mstar_id: str, month_end_date: date
    ) -> FundRiskStats | None:
        result = await self.session.execute(
            select(FundRiskStats).where(
                FundRiskStats.mstar_id == mstar_id,
                FundRiskStats.month_end_date == month_end_date,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(self, data: dict) -> FundRiskStats:
        stmt = pg_insert(FundRiskStats).values(**data)
        update_keys = [
            k for k in data if k not in ("mstar_id", "month_end_date")
        ]
        stmt = stmt.on_conflict_do_update(
            constraint="uq_risk_stats_mstar_date",
            set_={key: stmt.excluded[key] for key in update_keys},
        )
        stmt = stmt.returning(FundRiskStats)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()

    async def bulk_upsert(self, records: list[dict]) -> int:
        if not records:
            return 0
        update_keys = [
            k for k in records[0] if k not in ("mstar_id", "month_end_date")
        ]
        stmt = pg_insert(FundRiskStats).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_risk_stats_mstar_date",
            set_={key: stmt.excluded[key] for key in update_keys},
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
