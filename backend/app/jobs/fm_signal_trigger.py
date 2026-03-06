"""
jobs/fm_signal_trigger.py

Triggered on-demand via API when the Fund Manager updates sector signals.

v3 (Decision Matrix): Runs FMS for ALL funds -> reassigns matrix recommendations.
QFS is NOT recomputed (FM signal changes don't affect quantitative fundamentals).
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
    Recompute FMS for ALL funds and reassign matrix recommendations
    after FM signal changes.

    v3 Steps:
      1. Ensure benchmark weights are fresh
      2. Run FMS for ALL funds (picks up new signal weights)
      3. Reassign matrix recommendations (uses updated FMS + existing QFS)

    Returns:
        Summary dict with results and action distribution.
    """
    job_start = datetime.now(timezone.utc)
    logger.info(
        "fm_signal_recompute_start",
        triggered_by=triggered_by,
        started_at=job_start.isoformat(),
        pipeline_version="v3_matrix",
    )

    try:
        async with get_standalone_session() as session:
            scoring_service = ScoringService(session)

            # Step 1: Ensure benchmark weights are available
            logger.info("fm_signal_recompute_benchmark_check")
            benchmark_weights = await scoring_service.ensure_benchmark_weights()

            # Step 2: Recompute FMS for ALL funds
            logger.info("fm_signal_recompute_fms_start")
            fms_result = await scoring_service.compute_fms_for_all_funds(
                benchmark_weights=benchmark_weights,
                trigger_event=triggered_by,
            )

            # Step 3: Reassign matrix recommendations
            logger.info("fm_signal_recompute_recommendations_start")
            rec_result = await scoring_service.assign_recommendations(
                trigger_event=triggered_by,
            )

        job_end = datetime.now(timezone.utc)
        duration = (job_end - job_start).total_seconds()

        tier_distribution = rec_result.get("tier_distribution", {})
        action_distribution = rec_result.get("action_distribution", {})
        total_funds = rec_result.get("fund_count", 0)

        logger.info(
            "fm_signal_recompute_complete",
            triggered_by=triggered_by,
            duration_seconds=duration,
            total_funds=total_funds,
            action_distribution=action_distribution,
            tier_distribution=tier_distribution,
        )

        return {
            "job": "fm_signal_recompute",
            "status": "completed",
            "triggered_by": triggered_by,
            "pipeline_version": "v3_matrix",
            "fms": fms_result,
            "recommendation": rec_result,
            "summary": {
                "total_funds_rescored": total_funds,
                "tier_distribution": tier_distribution,
                "action_distribution": action_distribution,
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
