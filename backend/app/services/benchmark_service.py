"""
services/benchmark_service.py

Manages benchmark sector weights (NIFTY 50 allocation data).

Fetches from Morningstar GSSB API using the same infrastructure as fund
sector data. Persists to benchmark_sector_weights table.

Responsibilities:
    - refresh_benchmark_weights(): fetch + parse + upsert from Morningstar
    - get_latest_weights(): read cached weights from DB
    - check_staleness(): determine if weights need refresh
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.benchmark_repo import BenchmarkRepository
from app.services.ingestion_mappers import SECTOR_FIELD_MAP
from app.services.morningstar_fetcher import MorningstarFetcher
from app.services.morningstar_parser import safe_float

logger = structlog.get_logger(__name__)


class BenchmarkService:
    """Manages benchmark sector weight data lifecycle."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = BenchmarkRepository(session)

    async def refresh_benchmark_weights(
        self,
        benchmark_mstar_id: str,
        benchmark_name: str = "NIFTY 50",
    ) -> dict[str, Any]:
        """
        Fetch sector weights from Morningstar GSSB API and persist.

        Uses the same fetch_sector_breakdown() method used for funds.
        Parses the XML response using SECTOR_FIELD_MAP for 11 sectors.

        Args:
            benchmark_mstar_id: Morningstar ID of the benchmark index fund/ETF.
            benchmark_name: Human-readable name (default "NIFTY 50").

        Returns:
            Summary dict with sector count, total weight, fetch timestamp.
        """
        logger.info(
            "benchmark_refresh_start",
            mstar_id=benchmark_mstar_id,
            benchmark=benchmark_name,
        )

        async with MorningstarFetcher() as fetcher:
            raw_data = await fetcher.fetch_sector_breakdown(benchmark_mstar_id)

        if not raw_data:
            logger.error(
                "benchmark_refresh_empty_response",
                mstar_id=benchmark_mstar_id,
            )
            return {
                "status": "error",
                "reason": "empty_response_from_morningstar",
                "benchmark_mstar_id": benchmark_mstar_id,
            }

        today = date.today()
        now = datetime.now(timezone.utc)
        records: list[dict[str, Any]] = []

        for xml_tag, sector_name in SECTOR_FIELD_MAP.items():
            weight = safe_float(raw_data.get(xml_tag))
            if weight is not None:
                records.append({
                    "benchmark_name": benchmark_name,
                    "benchmark_mstar_id": benchmark_mstar_id,
                    "sector_name": sector_name,
                    "weight_pct": weight,
                    "effective_date": today,
                    "source": "morningstar_gssb",
                    "fetched_at": now,
                })

        if not records:
            logger.warning(
                "benchmark_refresh_no_sectors_parsed",
                mstar_id=benchmark_mstar_id,
                raw_keys=list(raw_data.keys())[:20],
            )
            return {
                "status": "error",
                "reason": "no_sector_weights_parsed",
                "benchmark_mstar_id": benchmark_mstar_id,
            }

        rows_affected = await self.repo.upsert_weights(records)
        total_weight = sum(r["weight_pct"] for r in records)

        logger.info(
            "benchmark_refresh_complete",
            benchmark=benchmark_name,
            sectors=len(records),
            total_weight=round(total_weight, 2),
            rows_upserted=rows_affected,
        )

        return {
            "status": "completed",
            "benchmark_name": benchmark_name,
            "benchmark_mstar_id": benchmark_mstar_id,
            "sector_count": len(records),
            "total_weight_pct": round(total_weight, 2),
            "rows_upserted": rows_affected,
            "fetched_at": now.isoformat(),
        }

    async def get_latest_weights(
        self, benchmark_name: str = "NIFTY 50",
    ) -> dict[str, float]:
        """Get latest weights as {sector_name: weight_pct} dict."""
        return await self.repo.get_weights_as_dict(benchmark_name)

    async def get_latest_weights_detail(
        self, benchmark_name: str = "NIFTY 50",
    ) -> list[dict[str, Any]]:
        """Get latest weights with full detail (effective_date, fetched_at, etc.)."""
        rows = await self.repo.get_latest_weights(benchmark_name)
        return [
            {
                "sector_name": row.sector_name,
                "weight_pct": float(row.weight_pct),
                "effective_date": str(row.effective_date),
                "source": row.source,
                "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
            }
            for row in rows
        ]

    async def check_staleness(
        self,
        benchmark_name: str = "NIFTY 50",
        max_age_days: int = 45,
    ) -> tuple[bool, Optional[int]]:
        """
        Check if benchmark weights are stale.

        Returns:
            Tuple of (is_stale, age_in_days). age_in_days is None if no weights exist.
        """
        age = await self.repo.get_weights_age_days(benchmark_name)
        if age is None:
            return True, None
        return age > max_age_days, age

    async def ensure_fresh_weights(
        self,
        benchmark_mstar_id: str,
        benchmark_name: str = "NIFTY 50",
        max_age_days: int = 45,
    ) -> dict[str, float]:
        """
        Get benchmark weights, auto-refreshing if stale.
        Called by the pipeline before FMS computation.

        Returns:
            {sector_name: weight_pct} dict. Empty if both fetch and cache fail.
        """
        is_stale, age = await self.check_staleness(benchmark_name, max_age_days)

        if is_stale:
            reason = "no_cached_weights" if age is None else f"weights_stale_{age}_days"
            logger.info("benchmark_auto_refresh", reason=reason)
            try:
                await self.refresh_benchmark_weights(
                    benchmark_mstar_id=benchmark_mstar_id,
                    benchmark_name=benchmark_name,
                )
            except Exception as exc:
                logger.error(
                    "benchmark_auto_refresh_failed",
                    error=str(exc),
                    fallback="using_cached_weights" if age is not None else "no_fallback",
                )
                if age is None:
                    # First-time setup with no cache — cannot proceed
                    return {}

        return await self.get_latest_weights(benchmark_name)
