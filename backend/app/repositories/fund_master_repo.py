"""Repository for fund_master table."""

from __future__ import annotations
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.fund_master import FundMaster
from app.repositories.base import BaseRepository


class FundMasterRepository(BaseRepository[FundMaster]):
    model = FundMaster

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_mstar_id(self, mstar_id: str) -> FundMaster | None:
        result = await self.session.execute(
            select(FundMaster).where(FundMaster.mstar_id == mstar_id)
        )
        return result.scalar_one_or_none()

    async def get_by_isin(self, isin: str) -> FundMaster | None:
        result = await self.session.execute(
            select(FundMaster).where(FundMaster.isin == isin)
        )
        return result.scalar_one_or_none()

    async def get_by_amfi_code(self, amfi_code: str) -> FundMaster | None:
        result = await self.session.execute(
            select(FundMaster).where(FundMaster.amfi_code == amfi_code)
        )
        return result.scalar_one_or_none()

    async def get_eligible_funds(
        self, category: str | None = None
    ) -> list[FundMaster]:
        stmt = select(FundMaster).where(
            FundMaster.is_eligible.is_(True),
            FundMaster.deleted_at.is_(None),
        )
        if category is not None:
            stmt = stmt.where(FundMaster.category_name == category)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_from_morningstar(self, data: dict) -> FundMaster:
        stmt = pg_insert(FundMaster).values(**data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["mstar_id"],
            set_={
                key: stmt.excluded[key]
                for key in data
                if key != "mstar_id"
            } | {"updated_at": datetime.now()},
        )
        stmt = stmt.returning(FundMaster)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()

    async def bulk_upsert(self, records: list[dict]) -> int:
        if not records:
            return 0
        # Determine which columns to update from the first record
        update_keys = [k for k in records[0] if k != "mstar_id"]
        stmt = pg_insert(FundMaster).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["mstar_id"],
            set_={key: stmt.excluded[key] for key in update_keys}
            | {"updated_at": datetime.now()},
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
