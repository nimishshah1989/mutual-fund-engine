"""
jobs/monthly_risk_recompute.py

Scheduled on the 2nd of every month at 3:00 AM IST.
Performs a full data refresh + complete scoring pipeline recompute:
  Step 1: Ingest all funds (fresh data from Morningstar)
  Step 2: Run full pipeline (QFS -> Shortlist -> FSAS -> Recommend) for all categories
  Step 3: Log tier changes for audit trail

Runs outside FastAPI request context — creates its own DB session.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import get_standalone_session
from app.core.logging import get_logger
from app.models.db.fund_master import FundMaster
from app.services.ingestion_service import IngestionService
from app.services.scoring_service import ScoringService

logger = get_logger(__name__)


async def run_monthly_risk_recompute() -> dict:
    """
    Full monthly recompute: ingestion + full scoring pipeline.

    Steps:
      1. Ingest all eligible funds from Morningstar (fresh risk data)
      2. Run full scoring pipeline (QFS -> Shortlist -> FSAS -> Recommend) for all categories
      3. Summarise tier changes across all categories

    Returns:
        Summary dict with ingestion and scoring results.
    """
    job_start = datetime.now(timezone.utc)
    logger.info("monthly_risk_recompute_start", started_at=job_start.isoformat())

    ingestion_summary = None
    scoring_results = None

    try:
        # ============================================================
        # Step 1: Ingest all funds (fresh data from Morningstar)
        # ============================================================
        async with get_standalone_session() as session:
            result = await session.execute(
                select(FundMaster.mstar_id).where(
                    FundMaster.is_eligible.is_(True),
                    FundMaster.deleted_at.is_(None),
                )
            )
            mstar_ids = list(result.scalars().all())

            if not mstar_ids:
                logger.warning(
                    "monthly_risk_recompute_no_funds",
                    message="No eligible funds found",
                )
                return {
                    "job": "monthly_risk_recompute",
                    "status": "skipped",
                    "reason": "no_eligible_funds",
                }

            logger.info(
                "monthly_risk_recompute_ingestion_start",
                fund_count=len(mstar_ids),
            )

            service = IngestionService(session)
            ingestion_summary = await service.ingest_all_funds(mstar_ids)

        logger.info(
            "monthly_risk_recompute_ingestion_done",
            total=ingestion_summary["total"],
            succeeded=ingestion_summary["succeeded"],
            failed=ingestion_summary["failed"],
        )

        # ============================================================
        # Step 2: Run full scoring pipeline (QFS -> Shortlist -> FSAS -> Recommend)
        # ============================================================
        async with get_standalone_session() as session:
            logger.info("monthly_risk_recompute_scoring_start")

            scoring_service = ScoringService(session)
            scoring_results = await scoring_service.compute_full_pipeline_all_categories(
                trigger_event="monthly_risk_recompute",
            )

        # ============================================================
        # Step 3: Summarise tier changes
        # ============================================================
        total_funds_scored = 0
        total_tier_distribution: dict[str, int] = {}
        categories_completed = 0
        categories_failed = 0

        for cat_result in scoring_results:
            if cat_result.get("status") == "completed":
                categories_completed += 1
                total_funds_scored += cat_result.get("fund_count", 0)

                # Aggregate tier distribution across categories
                tier_dist = cat_result.get("tier_distribution", {})
                for tier, count in tier_dist.items():
                    total_tier_distribution[tier] = (
                        total_tier_distribution.get(tier, 0) + count
                    )
            else:
                categories_failed += 1

        job_end = datetime.now(timezone.utc)
        duration = (job_end - job_start).total_seconds()

        logger.info(
            "monthly_risk_recompute_complete",
            duration_seconds=duration,
            ingestion_total=ingestion_summary["total"],
            ingestion_succeeded=ingestion_summary["succeeded"],
            ingestion_failed=ingestion_summary["failed"],
            categories_scored=categories_completed,
            categories_failed=categories_failed,
            total_funds_scored=total_funds_scored,
            tier_distribution=total_tier_distribution,
        )

        return {
            "job": "monthly_risk_recompute",
            "status": "completed",
            "ingestion": {
                "total": ingestion_summary["total"],
                "succeeded": ingestion_summary["succeeded"],
                "failed": ingestion_summary["failed"],
            },
            "scoring": {
                "categories_completed": categories_completed,
                "categories_failed": categories_failed,
                "total_funds_scored": total_funds_scored,
                "tier_distribution": total_tier_distribution,
            },
            "duration_seconds": duration,
        }

    except Exception as exc:
        logger.error(
            "monthly_risk_recompute_failed",
            error=str(exc),
            error_type=type(exc).__name__,
            ingestion_completed=ingestion_summary is not None,
            scoring_completed=scoring_results is not None,
        )
        return {
            "job": "monthly_risk_recompute",
            "status": "failed",
            "error": str(exc),
        }
