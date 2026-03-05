"""
jobs/weekly_master_refresh.py

Scheduled every Monday at 6:00 AM IST.
Same as daily NAV refresh but also detects new funds and funds that
went inactive since the last run.

Runs outside FastAPI request context — creates its own DB session.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import get_standalone_session
from app.core.logging import get_logger
from app.models.db.fund_master import FundMaster
from app.services.ingestion_service import IngestionService

logger = get_logger(__name__)


async def run_weekly_master_refresh() -> dict:
    """
    Refresh all fund data and detect master-level changes.

    Steps:
      1. Snapshot current eligible fund mstar_ids (before ingestion)
      2. Run full ingestion for all eligible funds
      3. Re-query fund_master to detect new or deactivated funds
      4. Log changes summary

    Returns:
        Summary dict with ingestion results and change detection.
    """
    job_start = datetime.now(timezone.utc)
    logger.info("weekly_master_refresh_start", started_at=job_start.isoformat())

    try:
        async with get_standalone_session() as session:
            # Step 1: Snapshot current eligible fund IDs before ingestion
            result = await session.execute(
                select(FundMaster.mstar_id).where(
                    FundMaster.is_eligible.is_(True),
                    FundMaster.deleted_at.is_(None),
                )
            )
            pre_ingestion_ids = set(result.scalars().all())

            if not pre_ingestion_ids:
                logger.warning(
                    "weekly_master_refresh_no_funds",
                    message="No eligible funds found before ingestion",
                )
                return {
                    "job": "weekly_master_refresh",
                    "status": "skipped",
                    "reason": "no_eligible_funds",
                }

            logger.info(
                "weekly_master_refresh_pre_count",
                fund_count=len(pre_ingestion_ids),
            )

            # Step 2: Run ingestion
            service = IngestionService(session)
            summary = await service.ingest_all_funds(list(pre_ingestion_ids))

        # Step 3: Re-query to detect new/inactive funds in a fresh session
        async with get_standalone_session() as session:
            result = await session.execute(
                select(FundMaster.mstar_id).where(
                    FundMaster.is_eligible.is_(True),
                    FundMaster.deleted_at.is_(None),
                )
            )
            post_ingestion_ids = set(result.scalars().all())

            # Detect changes
            new_funds = post_ingestion_ids - pre_ingestion_ids
            gone_inactive = pre_ingestion_ids - post_ingestion_ids

        # Step 4: Log change summary
        job_end = datetime.now(timezone.utc)
        duration = (job_end - job_start).total_seconds()

        if new_funds:
            logger.info(
                "weekly_master_new_funds_detected",
                count=len(new_funds),
                mstar_ids=list(new_funds),
            )

        if gone_inactive:
            logger.warning(
                "weekly_master_funds_went_inactive",
                count=len(gone_inactive),
                mstar_ids=list(gone_inactive),
            )

        logger.info(
            "weekly_master_refresh_complete",
            total=summary["total"],
            succeeded=summary["succeeded"],
            failed=summary["failed"],
            new_funds=len(new_funds),
            gone_inactive=len(gone_inactive),
            duration_seconds=duration,
            log_id=summary.get("log_id"),
        )

        return {
            "job": "weekly_master_refresh",
            "status": "completed",
            "total": summary["total"],
            "succeeded": summary["succeeded"],
            "failed": summary["failed"],
            "new_funds": list(new_funds),
            "gone_inactive": list(gone_inactive),
            "duration_seconds": duration,
        }

    except Exception as exc:
        logger.error(
            "weekly_master_refresh_failed",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return {
            "job": "weekly_master_refresh",
            "status": "failed",
            "error": str(exc),
        }
