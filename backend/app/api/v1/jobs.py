"""
api/v1/jobs.py

API endpoints for triggering background jobs on-demand.
These are NOT scheduled — they are invoked by the FM (Fund Manager)
or admin when manual recomputation is needed.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks

from app.jobs.fm_signal_trigger import run_fm_signal_recompute
from app.models.schemas.common import ApiResponse

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post(
    "/fm-signal-recompute",
    response_model=ApiResponse[dict[str, Any]],
    status_code=200,
    summary="Trigger FSAS + recommendation recompute after FM signal update",
)
async def trigger_fm_signal_recompute(
    background_tasks: BackgroundTasks,
) -> ApiResponse[dict[str, Any]]:
    """
    Trigger FSAS recompute for shortlisted funds and reassign recommendations.
    Typically called after the FM updates sector signals.

    QFS and shortlist are NOT recomputed (FM signal changes don't affect
    quantitative fundamentals or the shortlist).
    """
    try:
        logger.info("fm_signal_recompute_api_triggered")

        # Run synchronously (not in background) so we can return results
        # This is intentional — the FM wants to see tier change impact immediately
        result = await run_fm_signal_recompute(
            triggered_by="api_fm_signal_recompute",
        )

        return ApiResponse.ok(data=result)

    except Exception as exc:
        logger.error(
            "fm_signal_recompute_api_failed",
            error=str(exc),
        )
        return ApiResponse.fail(
            code="FM_RECOMPUTE_ERROR",
            message=f"Failed to trigger FM signal recompute: {exc}",
        )


@router.post(
    "/fm-signal-recompute/async",
    response_model=ApiResponse[dict[str, str]],
    status_code=202,
    summary="Trigger FSAS + recommendation recompute in background",
)
async def trigger_fm_signal_recompute_async(
    background_tasks: BackgroundTasks,
) -> ApiResponse[dict[str, str]]:
    """
    Trigger FSAS + recommendation recompute in the background.
    Returns immediately with a 202 Accepted. Use the health endpoint
    to monitor progress.
    """
    try:
        logger.info("fm_signal_recompute_async_api_triggered")

        background_tasks.add_task(
            run_fm_signal_recompute,
            triggered_by="api_fm_signal_recompute_async",
        )

        return ApiResponse.ok(
            data={"message": "FM signal recompute queued for background execution"},
        )

    except Exception as exc:
        logger.error(
            "fm_signal_recompute_async_api_failed",
            error=str(exc),
        )
        return ApiResponse.fail(
            code="FM_RECOMPUTE_QUEUE_ERROR",
            message=f"Failed to queue FM signal recompute: {exc}",
        )
