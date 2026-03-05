"""
repositories/score_repo.py

Repository for the fund_qfs, fund_fsas, and fund_crs tables.
Handles upsert (INSERT ... ON CONFLICT) for all score records
and retrieval queries for the API layer.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.fund_crs import FundCRS
from app.models.db.fund_fsas import FundFSAS
from app.models.db.fund_qfs import FundQFS
from app.models.db.score_audit_log import ScoreAuditLog
from app.repositories.base import BaseRepository


class ScoreRepository(BaseRepository[FundQFS]):
    """Repository for QFS, FSAS, and CRS score persistence and retrieval."""

    model = FundQFS

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # ===================================================================
    # QFS methods
    # ===================================================================

    async def upsert_qfs(self, record: dict) -> FundQFS:
        """
        Insert a QFS record, or update if (mstar_id, computed_date) already exists.
        Returns the upserted row.
        """
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
        """
        Bulk upsert QFS records. Uses INSERT ... ON CONFLICT for idempotency.
        Returns the number of rows affected.
        """
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
        """
        Get the latest QFS record for each fund in the provided list.
        Returns one row per fund (the most recent computed_date).
        """
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
        """
        Get the latest QFS scores for all funds in a category.

        Uses a subquery to find the most recent computed_date per fund,
        then filters to only those rows.

        Args:
            category_name: Used for logging; actual filtering is by mstar_ids.
            mstar_ids: List of fund mstar_ids in the category.
            sort_by: Column to sort by (qfs, wfs_raw, data_completeness_pct).
            sort_desc: Sort descending if True.
            page: 1-indexed page number.
            limit: Number of results per page.

        Returns:
            Tuple of (list of FundQFS records, total count).
        """
        if not mstar_ids:
            return [], 0

        # Subquery: latest computed_date per mstar_id
        latest_date_subq = (
            select(
                FundQFS.mstar_id,
                func.max(FundQFS.computed_date).label("max_date"),
            )
            .where(FundQFS.mstar_id.in_(mstar_ids))
            .group_by(FundQFS.mstar_id)
            .subquery()
        )

        # Main query: join with subquery to get only latest rows
        base_query = (
            select(FundQFS)
            .join(
                latest_date_subq,
                (FundQFS.mstar_id == latest_date_subq.c.mstar_id)
                & (FundQFS.computed_date == latest_date_subq.c.max_date),
            )
        )

        # Count total
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

        # Sort
        sort_column = getattr(FundQFS, sort_by, FundQFS.qfs)
        if sort_desc:
            base_query = base_query.order_by(sort_column.desc())
        else:
            base_query = base_query.order_by(sort_column.asc())

        # Paginate
        offset = (page - 1) * limit
        base_query = base_query.offset(offset).limit(limit)

        result = await self.session.execute(base_query)
        rows = list(result.scalars().all())

        return rows, total

    async def get_qfs_history(
        self,
        mstar_id: str,
        limit: int = 12,
    ) -> list[FundQFS]:
        """Get historical QFS records for a fund, ordered by most recent first."""
        result = await self.session.execute(
            select(FundQFS)
            .where(FundQFS.mstar_id == mstar_id)
            .order_by(FundQFS.computed_date.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # ===================================================================
    # FSAS methods
    # ===================================================================

    async def upsert_fsas(self, record: dict) -> FundFSAS:
        """
        Insert an FSAS record, or update if (mstar_id, fm_signal_date) already exists.
        Returns the upserted row.
        """
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
        """
        Bulk upsert FSAS records. Uses INSERT ... ON CONFLICT for idempotency.
        Returns the number of rows affected.
        """
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
        """
        Get the latest FSAS record for each fund in the provided list.
        Returns one row per fund (the most recent fm_signal_date).
        """
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

    # ===================================================================
    # CRS methods
    # ===================================================================

    async def upsert_crs(self, record: dict) -> FundCRS:
        """
        Insert a CRS record, or update if (mstar_id, computed_date) already exists.
        Returns the upserted row.
        """
        stmt = pg_insert(FundCRS).values(**record)
        update_keys = [
            k for k in record if k not in ("mstar_id", "computed_date")
        ]
        stmt = stmt.on_conflict_do_update(
            constraint="uq_crs_mstar_date",
            set_={key: stmt.excluded[key] for key in update_keys},
        )
        stmt = stmt.returning(FundCRS)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one()

    async def bulk_upsert_crs(self, records: list[dict]) -> int:
        """
        Bulk upsert CRS records. Uses INSERT ... ON CONFLICT for idempotency.
        Returns the number of rows affected.
        """
        if not records:
            return 0

        update_keys = [
            k for k in records[0] if k not in ("mstar_id", "computed_date")
        ]
        stmt = pg_insert(FundCRS).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_crs_mstar_date",
            set_={key: stmt.excluded[key] for key in update_keys},
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def get_latest_crs(self, mstar_id: str) -> Optional[FundCRS]:
        """Get the most recent CRS record for a specific fund."""
        result = await self.session.execute(
            select(FundCRS)
            .where(FundCRS.mstar_id == mstar_id)
            .order_by(FundCRS.computed_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_crs_by_mstar_ids(
        self, mstar_ids: list[str]
    ) -> list[FundCRS]:
        """
        Get the latest CRS record for each fund in the provided list.
        Returns one row per fund (the most recent computed_date).
        """
        if not mstar_ids:
            return []

        latest_date_subq = (
            select(
                FundCRS.mstar_id,
                func.max(FundCRS.computed_date).label("max_date"),
            )
            .where(FundCRS.mstar_id.in_(mstar_ids))
            .group_by(FundCRS.mstar_id)
            .subquery()
        )

        result = await self.session.execute(
            select(FundCRS).join(
                latest_date_subq,
                (FundCRS.mstar_id == latest_date_subq.c.mstar_id)
                & (FundCRS.computed_date == latest_date_subq.c.max_date),
            )
        )
        return list(result.scalars().all())

    async def get_latest_crs_by_category(
        self,
        category_name: str,
        mstar_ids: list[str],
        sort_by: str = "crs",
        sort_desc: bool = True,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[FundCRS], int]:
        """
        Get the latest CRS scores for all funds in a category.

        Args:
            category_name: Used for logging; actual filtering is by mstar_ids.
            mstar_ids: List of fund mstar_ids in the category.
            sort_by: Column to sort by (crs, qfs, fsas, tier).
            sort_desc: Sort descending if True.
            page: 1-indexed page number.
            limit: Number of results per page.

        Returns:
            Tuple of (list of FundCRS records, total count).
        """
        if not mstar_ids:
            return [], 0

        latest_date_subq = (
            select(
                FundCRS.mstar_id,
                func.max(FundCRS.computed_date).label("max_date"),
            )
            .where(FundCRS.mstar_id.in_(mstar_ids))
            .group_by(FundCRS.mstar_id)
            .subquery()
        )

        base_query = (
            select(FundCRS)
            .join(
                latest_date_subq,
                (FundCRS.mstar_id == latest_date_subq.c.mstar_id)
                & (FundCRS.computed_date == latest_date_subq.c.max_date),
            )
        )

        # Count total
        count_query = (
            select(func.count())
            .select_from(FundCRS)
            .join(
                latest_date_subq,
                (FundCRS.mstar_id == latest_date_subq.c.mstar_id)
                & (FundCRS.computed_date == latest_date_subq.c.max_date),
            )
        )
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        # Sort
        sort_column = getattr(FundCRS, sort_by, FundCRS.crs)
        if sort_desc:
            base_query = base_query.order_by(sort_column.desc())
        else:
            base_query = base_query.order_by(sort_column.asc())

        # Paginate
        offset = (page - 1) * limit
        base_query = base_query.offset(offset).limit(limit)

        result = await self.session.execute(base_query)
        rows = list(result.scalars().all())

        return rows, total

    # ===================================================================
    # Audit log
    # ===================================================================

    async def create_audit_log(self, audit_data: dict) -> ScoreAuditLog:
        """Create a score audit log entry for traceability."""
        log_entry = ScoreAuditLog(**audit_data)
        self.session.add(log_entry)
        await self.session.flush()
        return log_entry
