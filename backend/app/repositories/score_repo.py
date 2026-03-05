"""
repositories/score_repo.py

Repository for fund_qfs, fund_fsas, fund_shortlist, fund_recommendation,
and score_audit_log tables. Handles upsert (INSERT ... ON CONFLICT) for
all score records and retrieval queries for the API layer.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.fund_fsas import FundFSAS
from app.models.db.fund_qfs import FundQFS
from app.models.db.fund_recommendation import FundRecommendation
from app.models.db.fund_shortlist import FundShortlist
from app.models.db.score_audit_log import ScoreAuditLog
from app.repositories.base import BaseRepository


class ScoreRepository(BaseRepository[FundQFS]):
    """Repository for QFS, FSAS, shortlist, and recommendation persistence."""

    model = FundQFS

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # ===================================================================
    # QFS methods
    # ===================================================================

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

    # ===================================================================
    # FSAS methods
    # ===================================================================

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

    # ===================================================================
    # Shortlist methods
    # ===================================================================

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
        from sqlalchemy import delete
        result = await self.session.execute(
            delete(FundShortlist).where(FundShortlist.computed_date == computed_date)
        )
        await self.session.flush()
        return result.rowcount

    # ===================================================================
    # Recommendation methods (replaces CRS)
    # ===================================================================

    async def bulk_upsert_recommendations(self, records: list[dict]) -> int:
        """Bulk upsert recommendation records. Returns the number of rows affected."""
        if not records:
            return 0

        update_keys = [
            k for k in records[0] if k not in ("mstar_id", "computed_date")
        ]
        stmt = pg_insert(FundRecommendation).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_recommendation_mstar_date",
            set_={key: stmt.excluded[key] for key in update_keys},
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def get_latest_recommendation(
        self, mstar_id: str
    ) -> Optional[FundRecommendation]:
        """Get the most recent recommendation for a specific fund."""
        result = await self.session.execute(
            select(FundRecommendation)
            .where(FundRecommendation.mstar_id == mstar_id)
            .order_by(FundRecommendation.computed_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_recommendations_by_mstar_ids(
        self, mstar_ids: list[str]
    ) -> list[FundRecommendation]:
        """Get the latest recommendation for each fund in the list."""
        if not mstar_ids:
            return []

        latest_date_subq = (
            select(
                FundRecommendation.mstar_id,
                func.max(FundRecommendation.computed_date).label("max_date"),
            )
            .where(FundRecommendation.mstar_id.in_(mstar_ids))
            .group_by(FundRecommendation.mstar_id)
            .subquery()
        )

        result = await self.session.execute(
            select(FundRecommendation).join(
                latest_date_subq,
                (FundRecommendation.mstar_id == latest_date_subq.c.mstar_id)
                & (FundRecommendation.computed_date == latest_date_subq.c.max_date),
            )
        )
        return list(result.scalars().all())

    async def get_latest_shortlisted_recommendations(
        self,
    ) -> list[FundRecommendation]:
        """Get recommendations for all currently shortlisted funds."""
        latest_date_subq = (
            select(
                FundRecommendation.mstar_id,
                func.max(FundRecommendation.computed_date).label("max_date"),
            )
            .where(FundRecommendation.is_shortlisted.is_(True))
            .group_by(FundRecommendation.mstar_id)
            .subquery()
        )

        result = await self.session.execute(
            select(FundRecommendation)
            .join(
                latest_date_subq,
                (FundRecommendation.mstar_id == latest_date_subq.c.mstar_id)
                & (FundRecommendation.computed_date == latest_date_subq.c.max_date),
            )
            .order_by(FundRecommendation.tier, FundRecommendation.qfs.desc())
        )
        return list(result.scalars().all())

    # ===================================================================
    # Audit log
    # ===================================================================

    async def create_audit_log(self, audit_data: dict) -> ScoreAuditLog:
        """Create a score audit log entry for traceability."""
        log_entry = ScoreAuditLog(**audit_data)
        self.session.add(log_entry)
        await self.session.flush()
        return log_entry
