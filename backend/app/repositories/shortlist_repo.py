"""
repositories/shortlist_repo.py

Repository for the fund_shortlist table. Handles upsert, retrieval,
and clearing of shortlist records per computed date.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.fund_shortlist import FundShortlist
from app.repositories.base import BaseRepository


class ShortlistRepository(BaseRepository[FundShortlist]):
    """Repository for shortlist persistence and retrieval."""

    model = FundShortlist

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def bulk_upsert_shortlist(self, records: list[dict]) -> int:
        """Bulk upsert shortlist records. Returns the number of rows affected."""
        if not records:
            return 0

        update_keys = [
            k for k in records[0] if k not in ("mstar_id", "computed_date")
        ]
        stmt = pg_insert(FundShortlist).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_shortlist_mstar_date",
            set_={key: stmt.excluded[key] for key in update_keys},
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def get_latest_shortlist(self) -> list[FundShortlist]:
        """Get the latest shortlist (most recent computed_date across all categories)."""
        # Find the most recent computed_date
        max_date_result = await self.session.execute(
            select(func.max(FundShortlist.computed_date))
        )
        max_date = max_date_result.scalar_one_or_none()
        if max_date is None:
            return []

        result = await self.session.execute(
            select(FundShortlist)
            .where(FundShortlist.computed_date == max_date)
            .order_by(FundShortlist.category_name, FundShortlist.qfs_rank)
        )
        return list(result.scalars().all())

    async def get_shortlisted_mstar_ids(self) -> list[str]:
        """Get the mstar_ids of the latest shortlisted funds."""
        max_date_result = await self.session.execute(
            select(func.max(FundShortlist.computed_date))
        )
        max_date = max_date_result.scalar_one_or_none()
        if max_date is None:
            return []

        result = await self.session.execute(
            select(FundShortlist.mstar_id)
            .where(FundShortlist.computed_date == max_date)
        )
        return list(result.scalars().all())

    async def clear_shortlist_for_date(self, computed_date: date) -> int:
        """Delete all shortlist entries for a specific date (before rebuild)."""
        result = await self.session.execute(
            delete(FundShortlist).where(FundShortlist.computed_date == computed_date)
        )
        await self.session.flush()
        return result.rowcount
