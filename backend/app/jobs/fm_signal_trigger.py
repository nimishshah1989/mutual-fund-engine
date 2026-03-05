"""
jobs/fm_signal_trigger.py

NOT a scheduled job — triggered on-demand via API when the Fund Manager
updates sector signals.

Runs FSAS (Layer 2) -> CRS (Layer 3) recompute for all categories,
using the updated signals. QFS (Layer 1) is NOT recomputed because
FM signal changes do not affect quantitative fundamentals.

Returns a tier change summary so the FM sees immediate impact.
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
    Recompute FSAS and CRS for all categories after FM signal changes.

    Steps:
      1. Run FSAS for all categories (picks up new signal weights)
      2. Run CRS for all categories (uses updated FSAS + existing QFS)
      3. Build tier change summary

    Args:
        triggered_by: Identifier for who/what triggered this recompute.

    Returns:
        Summary dict with per-category results and tier change summary.
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

            # Step 1: Recompute FSAS for all categories
            logger.info("fm_signal_recompute_fsas_start")
            fsas_results = await scoring_service.compute_fsas_for_all_categories(
                trigger_event=triggered_by,
            )

            # Step 2: Recompute CRS for all categories
            logger.info("fm_signal_recompute_crs_start")
            crs_results = await scoring_service.compute_crs_for_all_categories(
                trigger_event=triggered_by,
            )

        # Step 3: Build tier change summary
        tier_changes: list[dict[str, Any]] = []
        total_funds_rescored = 0
        aggregate_tier_distribution: dict[str, int] = {}

        for cat_result in crs_results:
            if cat_result.get("status") == "completed":
                fund_count = cat_result.get("fund_count", 0)
                total_funds_rescored += fund_count

                tier_dist = cat_result.get("tier_distribution", {})
                for tier, count in tier_dist.items():
                    aggregate_tier_distribution[tier] = (
                        aggregate_tier_distribution.get(tier, 0) + count
                    )

                override_count = cat_result.get("override_count", 0)
                if override_count > 0:
                    tier_changes.append({
                        "category": cat_result["category"],
                        "fund_count": fund_count,
                        "overrides": override_count,
                        "tier_distribution": tier_dist,
                    })

        job_end = datetime.now(timezone.utc)
        duration = (job_end - job_start).total_seconds()

        # Summarise FSAS results
        fsas_categories_ok = sum(
            1 for r in fsas_results if r.get("status") == "completed"
        )
        fsas_categories_failed = sum(
            1 for r in fsas_results if r.get("status") == "error"
        )

        # Summarise CRS results
        crs_categories_ok = sum(
            1 for r in crs_results if r.get("status") == "completed"
        )
        crs_categories_failed = sum(
            1 for r in crs_results if r.get("status") == "error"
        )

        logger.info(
            "fm_signal_recompute_complete",
            triggered_by=triggered_by,
            duration_seconds=duration,
            total_funds_rescored=total_funds_rescored,
            fsas_categories_ok=fsas_categories_ok,
            fsas_categories_failed=fsas_categories_failed,
            crs_categories_ok=crs_categories_ok,
            crs_categories_failed=crs_categories_failed,
            tier_distribution=aggregate_tier_distribution,
        )

        return {
            "job": "fm_signal_recompute",
            "status": "completed",
            "triggered_by": triggered_by,
            "fsas": {
                "categories_completed": fsas_categories_ok,
                "categories_failed": fsas_categories_failed,
                "details": fsas_results,
            },
            "crs": {
                "categories_completed": crs_categories_ok,
                "categories_failed": crs_categories_failed,
                "details": crs_results,
            },
            "summary": {
                "total_funds_rescored": total_funds_rescored,
                "tier_distribution": aggregate_tier_distribution,
                "categories_with_overrides": tier_changes,
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
