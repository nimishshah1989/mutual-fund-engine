"""
repositories/qfs_repo.py

Repository for the fund_qfs table. Handles upsert (INSERT ... ON CONFLICT)
and retrieval queries for Quantitative Fund Scores.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.fund_qfs import FundQFS
from app.repositories.base import BaseRepository


class QFSRepository(BaseRepository[FundQFS]):
    """Repository for QFS score persistence and retrieval."""

    model = FundQFS

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def upsert_qfs(self, record: dict) -> FundQFS:
        """Insert a QFS record, or update if (mstar_id, computed_date) already exists."""
        stmt = pg_insert(FundQFS).values(**record)
        update_keys = [
            k for k in record if k not in ("mstar_id", "computed_date")
        ]
        stmt = stmt.on_conflict_do_update(
            constraint="uq_qfs_mstar_date",
            set_={key: stmt.excluded[key] for key in update_keys},
        )
        stmt = stmt.returning(FundQFS)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()

    async def bulk_upsert_qfs(self, records: list[dict]) -> int:
        """Bulk upsert QFS records. Returns the number of rows affected."""
        if not records:
            return 0

        update_keys = [
            k for k in records[0] if k not in ("mstar_id", "computed_date")
        ]
        stmt = pg_insert(FundQFS).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_qfs_mstar_date",
            set_={key: stmt.excluded[key] for key in update_keys},
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def get_latest_qfs(self, mstar_id: str) -> Optional[FundQFS]:
        """Get the most recent QFS record for a specific fund."""
        result = await self.session.execute(
            select(FundQFS)
            .where(FundQFS.mstar_id == mstar_id)
            .order_by(FundQFS.computed_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_qfs_by_mstar_ids(
        self, mstar_ids: list[str]
    ) -> list[FundQFS]:
        """Get the latest QFS record for each fund in the provided list."""
        if not mstar_ids:
            return []

        latest_date_subq = (
            select(
                FundQFS.mstar_id,
                func.max(FundQFS.computed_date).label("max_date"),
            )
            .where(FundQFS.mstar_id.in_(mstar_ids))
            .group_by(FundQFS.mstar_id)
            .subquery()
        )

        result = await self.session.execute(
            select(FundQFS).join(
                latest_date_subq,
                (FundQFS.mstar_id == latest_date_subq.c.mstar_id)
                & (FundQFS.computed_date == latest_date_subq.c.max_date),
            )
        )
        return list(result.scalars().all())

    async def get_latest_qfs_by_category(
        self,
        category_name: str,
        mstar_ids: list[str],
        sort_by: str = "qfs",
        sort_desc: bool = True,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[FundQFS], int]:
        """Get the latest QFS scores for all funds in a category (paginated)."""
        if not mstar_ids:
            return [], 0

        latest_date_subq = (
            select(
                FundQFS.mstar_id,
                func.max(FundQFS.computed_date).label("max_date"),
            )
            .where(FundQFS.mstar_id.in_(mstar_ids))
            .group_by(FundQFS.mstar_id)
            .subquery()
        )

        base_query = (
            select(FundQFS)
            .join(
                latest_date_subq,
                (FundQFS.mstar_id == latest_date_subq.c.mstar_id)
                & (FundQFS.computed_date == latest_date_subq.c.max_date),
            )
        )

        count_query = (
            select(func.count())
            .select_from(FundQFS)
            .join(
                latest_date_subq,
                (FundQFS.mstar_id == latest_date_subq.c.mstar_id)
                & (FundQFS.computed_date == latest_date_subq.c.max_date),
            )
        )
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        sort_column = getattr(FundQFS, sort_by, FundQFS.qfs)
        if sort_desc:
            base_query = base_query.order_by(sort_column.desc())
        else:
            base_query = base_query.order_by(sort_column.asc())

        offset = (page - 1) * limit
        base_query = base_query.offset(offset).limit(limit)

        result = await self.session.execute(base_query)
        rows = list(result.scalars().all())

        return rows, total

    async def get_qfs_history(
        self, mstar_id: str, limit: int = 12
    ) -> list[FundQFS]:
        """Get historical QFS records for a fund, most recent first."""
        result = await self.session.execute(
            select(FundQFS)
            .where(FundQFS.mstar_id == mstar_id)
            .order_by(FundQFS.computed_date.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
