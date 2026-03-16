"""
repositories/nav_history_repo.py

Data access for the nav_history table.
Provides bulk upsert, date-tolerant lookups, and coverage stats.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

import structlog
from sqlalchemy import func as sa_func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.nav_history import NavHistory
from app.repositories.base import BaseRepository

logger = structlog.get_logger(__name__)


class NavHistoryRepository(BaseRepository[NavHistory]):
    model = NavHistory

    async def bulk_upsert(self, records: list[dict[str, Any]]) -> int:
        """
        Insert NAV records, updating nav/source on conflict.
        Uses PostgreSQL ON CONFLICT (mstar_id, nav_date) DO UPDATE.
        """
        if not records:
            return 0

        stmt = pg_insert(NavHistory).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_nav_history_fund_date",
            set_={
                "nav": stmt.excluded.nav,
                "source": stmt.excluded.source,
            },
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def get_nav_on_or_before(
        self, mstar_id: str, target_date: date, tolerance_days: int = 5,
    ) -> Optional[dict[str, Any]]:
        """
        Get the closest NAV on or before target_date, within tolerance.
        Returns dict with nav_date and nav, or None if no data within range.
        """
        earliest = target_date - timedelta(days=tolerance_days)
        result = await self.session.execute(
            select(NavHistory.nav_date, NavHistory.nav)
            .where(
                NavHistory.mstar_id == mstar_id,
                NavHistory.nav_date <= target_date,
                NavHistory.nav_date >= earliest,
            )
            .order_by(NavHistory.nav_date.desc())
            .limit(1)
        )
        row = result.first()
        if row is None:
            return None
        return {"nav_date": row.nav_date, "nav": row.nav}

    async def get_latest_navs_bulk(
        self, mstar_ids: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Get the most recent NAV for each fund in a single query."""
        if not mstar_ids:
            return {}

        latest_subq = (
            select(
                NavHistory.mstar_id,
                sa_func.max(NavHistory.nav_date).label("max_date"),
            )
            .where(NavHistory.mstar_id.in_(mstar_ids))
            .group_by(NavHistory.mstar_id)
            .subquery()
        )
        result = await self.session.execute(
            select(NavHistory.mstar_id, NavHistory.nav_date, NavHistory.nav)
            .join(
                latest_subq,
                (NavHistory.mstar_id == latest_subq.c.mstar_id)
                & (NavHistory.nav_date == latest_subq.c.max_date),
            )
        )
        return {
            row.mstar_id: {"nav_date": row.nav_date, "nav": row.nav}
            for row in result.all()
        }

    async def get_navs_on_or_before_bulk(
        self, mstar_ids: list[str], target_date: date, tolerance_days: int = 5,
    ) -> dict[str, dict[str, Any]]:
        """Get closest NAV on or before target_date for multiple funds at once."""
        if not mstar_ids:
            return {}

        earliest = target_date - timedelta(days=tolerance_days)

        # Use DISTINCT ON to get one row per fund (the latest nav_date <= target)
        result = await self.session.execute(
            text("""
                SELECT DISTINCT ON (mstar_id)
                    mstar_id, nav_date, nav
                FROM nav_history
                WHERE mstar_id = ANY(:ids)
                  AND nav_date <= :target
                  AND nav_date >= :earliest
                ORDER BY mstar_id, nav_date DESC
            """).bindparams(
                ids=mstar_ids,
                target=target_date,
                earliest=earliest,
            )
        )
        return {
            row.mstar_id: {"nav_date": row.nav_date, "nav": row.nav}
            for row in result.all()
        }

    async def get_data_coverage(self) -> dict[str, Any]:
        """Return coverage stats: fund count with data, date range."""
        result = await self.session.execute(
            select(
                sa_func.count(sa_func.distinct(NavHistory.mstar_id)).label("fund_count"),
                sa_func.min(NavHistory.nav_date).label("earliest_date"),
                sa_func.max(NavHistory.nav_date).label("latest_date"),
                sa_func.count().label("total_rows"),
            )
        )
        row = result.first()
        if row is None:
            return {"fund_count": 0, "earliest_date": None, "latest_date": None, "total_rows": 0}
        return {
            "fund_count": row.fund_count,
            "earliest_date": row.earliest_date,
            "latest_date": row.latest_date,
            "total_rows": row.total_rows,
        }
