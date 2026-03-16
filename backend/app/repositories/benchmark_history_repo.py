"""
repositories/benchmark_history_repo.py

Data access for the benchmark_history table.
Provides bulk upsert, date-tolerant lookups, and time series queries.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

import structlog
from sqlalchemy import func as sa_func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.benchmark_history import BenchmarkHistory
from app.repositories.base import BaseRepository

logger = structlog.get_logger(__name__)


class BenchmarkHistoryRepository(BaseRepository[BenchmarkHistory]):
    model = BenchmarkHistory

    async def bulk_upsert(self, records: list[dict[str, Any]]) -> int:
        """
        Insert benchmark price records, updating close_price/source on conflict.
        Uses PostgreSQL ON CONFLICT (benchmark_name, price_date) DO UPDATE.
        """
        if not records:
            return 0

        stmt = pg_insert(BenchmarkHistory).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_benchmark_history_name_date",
            set_={
                "close_price": stmt.excluded.close_price,
                "source": stmt.excluded.source,
            },
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def get_price_on_or_before(
        self, benchmark: str, target_date: date, tolerance_days: int = 5,
    ) -> Optional[dict[str, Any]]:
        """
        Get the closest benchmark price on or before target_date, within tolerance.
        Returns dict with price_date and close_price, or None.
        """
        earliest = target_date - timedelta(days=tolerance_days)
        result = await self.session.execute(
            select(BenchmarkHistory.price_date, BenchmarkHistory.close_price)
            .where(
                BenchmarkHistory.benchmark_name == benchmark,
                BenchmarkHistory.price_date <= target_date,
                BenchmarkHistory.price_date >= earliest,
            )
            .order_by(BenchmarkHistory.price_date.desc())
            .limit(1)
        )
        row = result.first()
        if row is None:
            return None
        return {"price_date": row.price_date, "close_price": row.close_price}

    async def get_price_series(
        self, benchmark: str, from_date: date, to_date: date,
    ) -> list[dict[str, Any]]:
        """Get full time series of benchmark prices between two dates."""
        result = await self.session.execute(
            select(BenchmarkHistory.price_date, BenchmarkHistory.close_price)
            .where(
                BenchmarkHistory.benchmark_name == benchmark,
                BenchmarkHistory.price_date >= from_date,
                BenchmarkHistory.price_date <= to_date,
            )
            .order_by(BenchmarkHistory.price_date)
        )
        return [
            {"price_date": row.price_date, "close_price": row.close_price}
            for row in result.all()
        ]

    async def get_latest_price(self, benchmark: str) -> Optional[dict[str, Any]]:
        """Get the most recent price for a benchmark."""
        result = await self.session.execute(
            select(BenchmarkHistory.price_date, BenchmarkHistory.close_price)
            .where(BenchmarkHistory.benchmark_name == benchmark)
            .order_by(BenchmarkHistory.price_date.desc())
            .limit(1)
        )
        row = result.first()
        if row is None:
            return None
        return {"price_date": row.price_date, "close_price": row.close_price}

    async def get_data_coverage(self, benchmark: str = "NIFTY_50") -> dict[str, Any]:
        """Return coverage stats for a benchmark."""
        result = await self.session.execute(
            select(
                sa_func.min(BenchmarkHistory.price_date).label("earliest_date"),
                sa_func.max(BenchmarkHistory.price_date).label("latest_date"),
                sa_func.count().label("total_rows"),
            )
            .where(BenchmarkHistory.benchmark_name == benchmark)
        )
        row = result.first()
        if row is None:
            return {"earliest_date": None, "latest_date": None, "total_rows": 0}
        return {
            "earliest_date": row.earliest_date,
            "latest_date": row.latest_date,
            "total_rows": row.total_rows,
        }
