"""
repositories/pulse_snapshot_repo.py

Data access for the mf_pulse_snapshot table.
Provides bulk upsert, filtered queries, and category signal aggregation.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional

import structlog
from sqlalchemy import func as sa_func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.mf_pulse_snapshot import MFPulseSnapshot
from app.repositories.base import BaseRepository

logger = structlog.get_logger(__name__)


class PulseSnapshotRepository(BaseRepository[MFPulseSnapshot]):
    model = MFPulseSnapshot

    async def bulk_upsert(self, records: list[dict[str, Any]]) -> int:
        """
        Insert snapshot records, updating all fields on conflict.
        Uses PostgreSQL ON CONFLICT (mstar_id, snapshot_date, period) DO UPDATE.
        """
        if not records:
            return 0

        # Process in batches to avoid parameter limit
        batch_size = 500
        total_rows = 0
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            stmt = pg_insert(MFPulseSnapshot).values(batch)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_pulse_snapshot_fund_date_period",
                set_={
                    "nav_current": stmt.excluded.nav_current,
                    "nav_old": stmt.excluded.nav_old,
                    "fund_return": stmt.excluded.fund_return,
                    "nifty_current": stmt.excluded.nifty_current,
                    "nifty_old": stmt.excluded.nifty_old,
                    "nifty_return": stmt.excluded.nifty_return,
                    "ratio_current": stmt.excluded.ratio_current,
                    "ratio_old": stmt.excluded.ratio_old,
                    "ratio_return": stmt.excluded.ratio_return,
                    "signal": stmt.excluded.signal,
                    "excess_return": stmt.excluded.excess_return,
                },
            )
            result = await self.session.execute(stmt)
            total_rows += result.rowcount

        await self.session.flush()
        return total_rows

    async def get_latest_for_period(
        self,
        period: str,
        category_name: Optional[str] = None,
        signal: Optional[str] = None,
        sort_by: str = "ratio_return",
        sort_desc: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[MFPulseSnapshot], int]:
        """
        Get latest snapshots for a period with optional filters.
        Returns (rows, total_count) for pagination.
        """
        # Base query: latest snapshot_date for this period
        latest_date_subq = (
            select(sa_func.max(MFPulseSnapshot.snapshot_date))
            .where(MFPulseSnapshot.period == period)
            .scalar_subquery()
        )

        base_where = [
            MFPulseSnapshot.period == period,
            MFPulseSnapshot.snapshot_date == latest_date_subq,
        ]

        if signal:
            base_where.append(MFPulseSnapshot.signal == signal)

        # Count query
        count_q = select(sa_func.count()).select_from(MFPulseSnapshot).where(*base_where)

        # If filtering by category, join fund_master
        if category_name:
            from app.models.db.fund_master import FundMaster
            count_q = (
                select(sa_func.count())
                .select_from(MFPulseSnapshot)
                .join(FundMaster, FundMaster.mstar_id == MFPulseSnapshot.mstar_id)
                .where(*base_where, FundMaster.category_name == category_name)
            )

        count_result = await self.session.execute(count_q)
        total = count_result.scalar_one()

        # Data query
        allowed_sorts = {"ratio_return", "fund_return", "nifty_return", "excess_return", "signal"}
        sort_col_name = sort_by if sort_by in allowed_sorts else "ratio_return"
        sort_col = getattr(MFPulseSnapshot, sort_col_name, MFPulseSnapshot.ratio_return)
        order = sort_col.desc() if sort_desc else sort_col.asc()

        data_q = (
            select(MFPulseSnapshot)
            .where(*base_where)
            .order_by(order.nulls_last())
            .limit(limit)
            .offset(offset)
        )

        if category_name:
            from app.models.db.fund_master import FundMaster
            data_q = (
                select(MFPulseSnapshot)
                .join(FundMaster, FundMaster.mstar_id == MFPulseSnapshot.mstar_id)
                .where(*base_where, FundMaster.category_name == category_name)
                .order_by(order.nulls_last())
                .limit(limit)
                .offset(offset)
            )

        result = await self.session.execute(data_q)
        rows = list(result.scalars().all())
        return rows, total

    async def get_category_summary(self, period: str) -> list[dict[str, Any]]:
        """
        Aggregate signal counts per SEBI category for a given period.
        Returns list of dicts: {category_name, fund_count, avg_ratio_return, signals: {...}}
        """
        from app.models.db.fund_master import FundMaster

        latest_date_subq = (
            select(sa_func.max(MFPulseSnapshot.snapshot_date))
            .where(MFPulseSnapshot.period == period)
            .scalar_subquery()
        )

        result = await self.session.execute(
            select(
                FundMaster.category_name,
                MFPulseSnapshot.signal,
                sa_func.count().label("cnt"),
                sa_func.avg(MFPulseSnapshot.ratio_return).label("avg_rr"),
            )
            .join(FundMaster, FundMaster.mstar_id == MFPulseSnapshot.mstar_id)
            .where(
                MFPulseSnapshot.period == period,
                MFPulseSnapshot.snapshot_date == latest_date_subq,
                FundMaster.is_eligible.is_(True),
                FundMaster.deleted_at.is_(None),
            )
            .group_by(FundMaster.category_name, MFPulseSnapshot.signal)
            .order_by(FundMaster.category_name)
        )

        # Aggregate into per-category summaries
        categories: dict[str, dict[str, Any]] = {}
        for row in result.all():
            cat = row.category_name
            if cat not in categories:
                categories[cat] = {
                    "category_name": cat,
                    "fund_count": 0,
                    "avg_ratio_return": Decimal("0"),
                    "signals": {},
                    "_rr_sum": Decimal("0"),
                }
            entry = categories[cat]
            entry["signals"][row.signal or "UNKNOWN"] = row.cnt
            entry["fund_count"] += row.cnt
            entry["_rr_sum"] += (row.avg_rr or Decimal("0")) * row.cnt

        # Compute weighted average ratio return
        summaries: list[dict[str, Any]] = []
        for cat_data in categories.values():
            fc = cat_data["fund_count"]
            cat_data["avg_ratio_return"] = (cat_data["_rr_sum"] / fc).quantize(Decimal("0.0001")) if fc > 0 else Decimal("0")
            del cat_data["_rr_sum"]
            summaries.append(cat_data)

        return sorted(summaries, key=lambda x: x["category_name"])
