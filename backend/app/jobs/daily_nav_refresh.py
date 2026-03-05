"""
jobs/daily_nav_refresh.py

Scheduled daily at 2:00 AM IST.
Refreshes NAV and performance data for all active funds from Morningstar API.

Runs outside FastAPI request context — creates its own DB session via
get_standalone_session().
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.database import get_standalone_session
from app.core.logging import get_logger
from app.models.db.fund_master import FundMaster
from app.services.ingestion_service import IngestionService

from sqlalchemy import select

logger = get_logger(__name__)


async def run_daily_nav_refresh() -> dict:
    """
    Fetch and update NAV/performance data for all eligible funds.

    Steps:
      1. Load all active, eligible mstar_ids from fund_master
      2. Call IngestionService.ingest_all_funds() to pull from Morningstar
      3. Log results summary

    Returns:
        Summary dict with total, succeeded, failed counts.
    """
    job_start = datetime.now(timezone.utc)
    logger.info("daily_nav_refresh_start", started_at=job_start.isoformat())

    try:
        async with get_standalone_session() as session:
            # Step 1: Load all eligible fund mstar_ids
            result = await session.execute(
                select(FundMaster.mstar_id).where(
                    FundMaster.is_eligible.is_(True),
                    FundMaster.deleted_at.is_(None),
                )
            )
            mstar_ids = list(result.scalars().all())

            if not mstar_ids:
                logger.warning("daily_nav_refresh_no_funds", message="No eligible funds found")
                return {
                    "job": "daily_nav_refresh",
                    "status": "skipped",
                    "reason": "no_eligible_funds",
                }

            logger.info("daily_nav_refresh_fund_count", fund_count=len(mstar_ids))

            # Step 2: Run ingestion for all funds
            service = IngestionService(session)
            summary = await service.ingest_all_funds(mstar_ids)

        # Step 3: Log results
        job_end = datetime.now(timezone.utc)
        duration = (job_end - job_start).total_seconds()

        logger.info(
            "daily_nav_refresh_complete",
            total=summary["total"],
            succeeded=summary["succeeded"],
            failed=summary["failed"],
            duration_seconds=duration,
            log_id=summary.get("log_id"),
        )

        if summary["failed"] > 0:
            logger.warning(
                "daily_nav_refresh_partial_failures",
                failed_count=summary["failed"],
                errors=summary.get("errors", []),
            )

        return {
            "job": "daily_nav_refresh",
            "status": "completed",
            "total": summary["total"],
            "succeeded": summary["succeeded"],
            "failed": summary["failed"],
            "duration_seconds": duration,
        }

    except Exception as exc:
        logger.error(
            "daily_nav_refresh_failed",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return {
            "job": "daily_nav_refresh",
            "status": "failed",
            "error": str(exc),
        }
