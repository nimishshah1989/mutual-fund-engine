"""Repository for category_returns table."""

from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.category_returns import CategoryReturns
from app.repositories.base import BaseRepository


class CategoryReturnsRepository(BaseRepository[CategoryReturns]):
    model = CategoryReturns

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_latest_by_category(
        self, category_code: str
    ) -> CategoryReturns | None:
        result = await self.session.execute(
            select(CategoryReturns)
            .where(CategoryReturns.category_code == category_code)
            .order_by(CategoryReturns.as_of_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def upsert(self, data: dict) -> CategoryReturns:
        stmt = pg_insert(CategoryReturns).values(**data)
        update_keys = [
            k for k in data if k not in ("category_code", "as_of_date")
        ]
        stmt = stmt.on_conflict_do_update(
            constraint="uq_cat_returns_code_date",
            set_={key: stmt.excluded[key] for key in update_keys},
        )
        stmt = stmt.returning(CategoryReturns)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()

    async def bulk_upsert(self, records: list[dict]) -> int:
        if not records:
            return 0
        update_keys = [
            k for k in records[0] if k not in ("category_code", "as_of_date")
        ]
        stmt = pg_insert(CategoryReturns).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_cat_returns_code_date",
            set_={key: stmt.excluded[key] for key in update_keys},
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
