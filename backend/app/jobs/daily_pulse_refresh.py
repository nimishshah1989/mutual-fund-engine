"""
jobs/daily_pulse_refresh.py

Scheduled job: refreshes benchmark prices, fund NAVs (latest only),
and recomputes all MF Pulse ratio return snapshots.

Schedule: 2:30 AM IST daily (after Morningstar refresh at 2:00 AM).

Daily efficiency:
  - Benchmark: yfinance downloads only last 10 days (~7 rows) — efficient.
  - Fund NAVs: Single AMFI bulk file (~2MB) gives latest NAV for ALL funds.
    No per-fund API calls. Inserts ~535 rows (1 per fund).
  - Snapshots: Recomputes 535 × 6 = 3,210 rows via 16 DB queries.
  - Total daily load: ~2 HTTP requests + ~20 DB queries. Runs in <30 seconds.

Skips weekends (Saturday/Sunday) since no new NAV data is published.
"""

from __future__ import annotations

import time
from datetime import date

import structlog

from app.core.database import get_standalone_session
from app.services.nav_fetcher_service import NavFetcherService
from app.services.pulse_data_service import PulseDataService

logger = structlog.get_logger(__name__)


async def run_daily_pulse_refresh() -> None:
    """
    Daily pulse refresh pipeline:
      1. Skip if weekend (no new NAV data on Sat/Sun)
      2. Refresh Nifty 50 benchmark prices (last 10 days via yfinance)
      3. Refresh fund NAVs (latest NAV via single AMFI bulk file)
      4. Recompute all pulse snapshots (535 funds × 6 periods)

    Runs inside a standalone DB session (background job, not request context).
    """
    today = date.today()

    # Skip weekends — Indian markets closed, no new NAV data
    if today.weekday() >= 5:  # Saturday=5, Sunday=6
        logger.info(
            "daily_pulse_refresh_skipped",
            reason="weekend",
            day=today.strftime("%A"),
        )
        return

    start = time.monotonic()
    logger.info("daily_pulse_refresh_start", date=str(today))

    try:
        async with get_standalone_session() as session:
            fetcher = NavFetcherService(session)
            service = PulseDataService(session)

            # Step 1: Refresh benchmark (yfinance, ~10 rows, <5 seconds)
            bench_result = await fetcher.refresh_benchmark(days=10)
            logger.info("daily_pulse_benchmark_done", result=bench_result)

            if bench_result.get("status") == "error":
                logger.error(
                    "daily_pulse_benchmark_failed",
                    error=bench_result.get("error"),
                )
                # Continue anyway — stale benchmark data within tolerance is acceptable

            # Step 2: Refresh fund NAVs (single AMFI bulk file, ~535 rows, <10 seconds)
            nav_result = await fetcher.refresh_fund_navs(days=5)
            logger.info("daily_pulse_navs_done", result=nav_result)

            # Step 3: Compute snapshots (535 × 6 periods, ~16 DB queries, <15 seconds)
            snapshot_result = await service.compute_all_snapshots()
            logger.info("daily_pulse_snapshots_done", result=snapshot_result)

        elapsed = round(time.monotonic() - start, 2)
        logger.info(
            "daily_pulse_refresh_complete",
            duration_seconds=elapsed,
            benchmark=bench_result.get("status"),
            navs=nav_result.get("status"),
            snapshots=snapshot_result.get("status"),
        )

    except Exception as exc:
        elapsed = round(time.monotonic() - start, 2)
        logger.error(
            "daily_pulse_refresh_failed",
            duration_seconds=elapsed,
            error=str(exc),
        )
        raise
