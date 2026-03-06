"""
repositories/fsas_repo.py

Repository for the fund_fsas table. Handles upsert (INSERT ... ON CONFLICT)
and retrieval queries for FM Sector Alignment Scores.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.fund_fsas import FundFSAS
from app.repositories.base import BaseRepository


class FSASRepository(BaseRepository[FundFSAS]):
    """Repository for FSAS score persistence and retrieval."""

    model = FundFSAS

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def upsert_fsas(self, record: dict) -> FundFSAS:
        """Insert an FSAS record, or update if (mstar_id, fm_signal_date) exists."""
        stmt = pg_insert(FundFSAS).values(**record)
        update_keys = [
            k for k in record if k not in ("mstar_id", "fm_signal_date")
        ]
        stmt = stmt.on_conflict_do_update(
            constraint="uq_fsas_mstar_signal",
            set_={key: stmt.excluded[key] for key in update_keys},
        )
        stmt = stmt.returning(FundFSAS)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()

    async def bulk_upsert_fsas(self, records: list[dict]) -> int:
        """Bulk upsert FSAS records. Returns the number of rows affected."""
        if not records:
            return 0

        update_keys = [
            k for k in records[0] if k not in ("mstar_id", "fm_signal_date")
        ]
        stmt = pg_insert(FundFSAS).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_fsas_mstar_signal",
            set_={key: stmt.excluded[key] for key in update_keys},
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def get_latest_fsas(self, mstar_id: str) -> Optional[FundFSAS]:
        """Get the most recent FSAS record for a specific fund."""
        result = await self.session.execute(
            select(FundFSAS)
            .where(FundFSAS.mstar_id == mstar_id)
            .order_by(FundFSAS.fm_signal_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_fsas_by_mstar_ids(
        self, mstar_ids: list[str]
    ) -> list[FundFSAS]:
        """Get the latest FSAS record for each fund in the provided list."""
        if not mstar_ids:
            return []

        latest_date_subq = (
            select(
                FundFSAS.mstar_id,
                func.max(FundFSAS.fm_signal_date).label("max_date"),
            )
            .where(FundFSAS.mstar_id.in_(mstar_ids))
            .group_by(FundFSAS.mstar_id)
            .subquery()
        )

        result = await self.session.execute(
            select(FundFSAS).join(
                latest_date_subq,
                (FundFSAS.mstar_id == latest_date_subq.c.mstar_id)
                & (FundFSAS.fm_signal_date == latest_date_subq.c.max_date),
            )
        )
        return list(result.scalars().all())
