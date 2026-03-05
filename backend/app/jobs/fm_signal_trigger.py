"""
jobs/fm_signal_trigger.py

Triggered on-demand via API when the Fund Manager updates sector signals.

v2: Runs FSAS for shortlisted funds -> reassigns recommendations.
QFS and shortlist are NOT recomputed (FM signal changes don't affect
quantitative fundamentals or the shortlist).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.database import get_standalone_session
from app.core.logging import get_logger
from app.services.scoring_service import ScoringService

logger = get_logger(__name__)


async def run_fm_signal_recompute(
    triggered_by: str = "fm_signal_update",
) -> dict[str, Any]:
    """
    Recompute FSAS for shortlisted funds and reassign recommendations
    after FM signal changes.

    Steps:
      1. Run FSAS for shortlisted funds (picks up new signal weights)
      2. Reassign tiers and actions (uses updated FSAS + existing QFS percentiles)

    Returns:
        Summary dict with results and tier change summary.
    """
    job_start = datetime.now(timezone.utc)
    logger.info(
        "fm_signal_recompute_start",
        triggered_by=triggered_by,
        started_at=job_start.isoformat(),
    )

    try:
        async with get_standalone_session() as session:
            scoring_service = ScoringService(session)

            # Step 1: Recompute FSAS for shortlisted funds
            logger.info("fm_signal_recompute_fsas_start")
            fsas_result = await scoring_service.compute_fsas_for_shortlisted(
                trigger_event=triggered_by,
            )

            # Step 2: Reassign recommendations (tiers + actions)
            logger.info("fm_signal_recompute_recommendations_start")
            rec_result = await scoring_service.assign_recommendations(
                trigger_event=triggered_by,
            )

        job_end = datetime.now(timezone.utc)
        duration = (job_end - job_start).total_seconds()

        tier_distribution = rec_result.get("tier_distribution", {})
        total_funds = rec_result.get("fund_count", 0)
        shortlisted_count = rec_result.get("shortlisted_count", 0)

        logger.info(
            "fm_signal_recompute_complete",
            triggered_by=triggered_by,
            duration_seconds=duration,
            total_funds=total_funds,
            shortlisted_count=shortlisted_count,
            tier_distribution=tier_distribution,
        )

        return {
            "job": "fm_signal_recompute",
            "status": "completed",
            "triggered_by": triggered_by,
            "fsas": fsas_result,
            "recommendation": rec_result,
            "summary": {
                "total_funds_rescored": total_funds,
                "shortlisted_count": shortlisted_count,
                "tier_distribution": tier_distribution,
                "override_count": rec_result.get("override_count", 0),
            },
            "duration_seconds": duration,
        }

    except Exception as exc:
        logger.error(
            "fm_signal_recompute_failed",
            triggered_by=triggered_by,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return {
            "job": "fm_signal_recompute",
            "status": "failed",
            "error": str(exc),
        }
