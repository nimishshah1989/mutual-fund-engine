"""Repository for fund_sector_exposure table."""

from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.fund_sector_exposure import FundSectorExposure
from app.repositories.base import BaseRepository


class FundSectorExposureRepository(BaseRepository[FundSectorExposure]):
    model = FundSectorExposure

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_latest_by_mstar_id(
        self, mstar_id: str
    ) -> list[FundSectorExposure]:
        # Get the most recent month_end_date for this fund, then fetch all
        # sector rows for that date
        latest_date_result = await self.session.execute(
            select(FundSectorExposure.month_end_date)
            .where(FundSectorExposure.mstar_id == mstar_id)
            .order_by(FundSectorExposure.month_end_date.desc())
            .limit(1)
        )
        latest_date = latest_date_result.scalar_one_or_none()
        if latest_date is None:
            return []

        result = await self.session.execute(
            select(FundSectorExposure).where(
                FundSectorExposure.mstar_id == mstar_id,
                FundSectorExposure.month_end_date == latest_date,
            )
        )
        return list(result.scalars().all())

    async def bulk_upsert(self, records: list[dict]) -> int:
        if not records:
            return 0
        update_keys = [
            k
            for k in records[0]
            if k not in ("mstar_id", "month_end_date", "sector_name")
        ]
        stmt = pg_insert(FundSectorExposure).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_exposure_fund_date_sector",
            set_={key: stmt.excluded[key] for key in update_keys},
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
