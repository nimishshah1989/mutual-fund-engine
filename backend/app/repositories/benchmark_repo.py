"""
repositories/benchmark_repo.py

Repository for the benchmark_sector_weights table. Handles upsert
and retrieval of benchmark sector weights (NIFTY 50 allocations).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.benchmark_sector_weights import BenchmarkSectorWeight
from app.repositories.base import BaseRepository

logger = structlog.get_logger(__name__)


class BenchmarkRepository(BaseRepository[BenchmarkSectorWeight]):
    """Repository for benchmark sector weight persistence and retrieval."""

    model = BenchmarkSectorWeight

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def upsert_weights(self, records: list[dict]) -> int:
        """
        Bulk upsert benchmark sector weights.
        On conflict (same benchmark + sector + date), update the weight.
        Returns the number of rows affected.
        """
        if not records:
            return 0

        stmt = pg_insert(BenchmarkSectorWeight).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_benchmark_sector_date",
            set_={
                "weight_pct": stmt.excluded.weight_pct,
                "source": stmt.excluded.source,
                "fetched_at": stmt.excluded.fetched_at,
            },
        )
        result = await self.session.execute(stmt)
        await self.session.flush()

        logger.info(
            "benchmark_weights_upserted",
            rows=result.rowcount,
            benchmark=records[0].get("benchmark_name") if records else "unknown",
        )
        return result.rowcount

    async def get_latest_weights(
        self, benchmark_name: str,
    ) -> list[BenchmarkSectorWeight]:
        """
        Get the most recent set of sector weights for a benchmark.
        Returns all sector rows for the latest effective_date.
        """
        # Find the latest effective_date for this benchmark
        latest_date_subq = (
            select(func.max(BenchmarkSectorWeight.effective_date))
            .where(
                BenchmarkSectorWeight.benchmark_name == benchmark_name,
                BenchmarkSectorWeight.deleted_at.is_(None),
            )
            .scalar_subquery()
        )

        result = await self.session.execute(
            select(BenchmarkSectorWeight)
            .where(
                BenchmarkSectorWeight.benchmark_name == benchmark_name,
                BenchmarkSectorWeight.effective_date == latest_date_subq,
                BenchmarkSectorWeight.deleted_at.is_(None),
            )
            .order_by(BenchmarkSectorWeight.weight_pct.desc())
        )
        return list(result.scalars().all())

    async def get_weights_age_days(self, benchmark_name: str) -> Optional[int]:
        """
        Return the age in days of the most recent benchmark weights.
        Returns None if no weights exist at all.
        """
        result = await self.session.execute(
            select(func.max(BenchmarkSectorWeight.fetched_at))
            .where(
                BenchmarkSectorWeight.benchmark_name == benchmark_name,
                BenchmarkSectorWeight.deleted_at.is_(None),
            )
        )
        latest_fetched = result.scalar_one_or_none()
        if latest_fetched is None:
            return None

        now = datetime.now(timezone.utc)
        return (now - latest_fetched).days

    async def get_weights_as_dict(
        self, benchmark_name: str,
    ) -> dict[str, Decimal]:
        """
        Get latest weights as a simple {sector_name: weight_pct} dict.
        Used by the FMS engine for active weight calculations.
        """
        rows = await self.get_latest_weights(benchmark_name)
        return {
            row.sector_name: row.weight_pct
            for row in rows
        }
