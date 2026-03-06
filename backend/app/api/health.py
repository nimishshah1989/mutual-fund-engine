"""
api/health.py

Health check endpoints for monitoring and deployment pipelines.

- GET /health         — lightweight liveness probe
- GET /health/ready   — deep readiness check with DB, scheduler, data freshness
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import get_db
from app.core.dependencies import get_settings
from app.core.rate_limit import RATE_HEALTH, limiter
from app.models.db.ingestion_log import IngestionLog

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Health"])

# Staleness thresholds — data older than these is flagged as stale.
# Only real data feeds are tracked. JHV_MASTER and MONTHLY_RECOMPUTE were
# placeholder checks that caused false warnings on fresh deploys.
STALENESS_THRESHOLDS = {
    "MORNINGSTAR_API": timedelta(hours=24),       # Daily refresh expected
}


@router.get("/health")
@limiter.limit(RATE_HEALTH)
async def health_check(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """
    Lightweight health check — confirms the API is reachable and responsive.
    Does not verify database connectivity (use /health/ready for deep checks).
    """
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.app_env,
    }


@router.get("/health/ready")
@limiter.limit(RATE_HEALTH)
async def readiness_check(
    request: Request,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Deep readiness check that verifies:
      1. Database connectivity (SELECT 1)
      2. Data freshness per feed (with staleness warnings)
      3. Scheduler status (running/stopped, next run times)
    """
    result: dict[str, Any] = {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.app_env,
        "checks": {},
    }

    warnings: list[str] = []

    # -- 1. Database connectivity --
    db_status = await _check_database(db)
    result["checks"]["database"] = db_status
    if db_status["status"] != "ok":
        result["status"] = "degraded"
        warnings.append("Database connectivity check failed")

    # -- 2. Data freshness --
    freshness = await _check_data_freshness(db)
    result["checks"]["data_freshness"] = freshness
    for feed_name, feed_info in freshness.items():
        if feed_info.get("is_stale"):
            warnings.append(f"Data feed '{feed_name}' is stale")
            result["status"] = "degraded"

    # -- 3. Scheduler status --
    scheduler_info = _check_scheduler_status()
    result["checks"]["scheduler"] = scheduler_info
    if scheduler_info["status"] == "stopped" and settings.scheduler_enabled:
        warnings.append("Scheduler is enabled but not running")
        result["status"] = "degraded"

    if warnings:
        result["warnings"] = warnings

    return result


async def _check_database(db: AsyncSession) -> dict[str, Any]:
    """Verify database connectivity with a simple SELECT 1 query."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        logger.error("health_db_check_failed", error=str(exc))
        return {
            "status": "error",
            "error": "database_check_failed",
        }


async def _check_data_freshness(db: AsyncSession) -> dict[str, Any]:
    """
    Query ingestion_log for the latest completed run per feed.
    Flag feeds as stale if they exceed the staleness threshold.
    """
    freshness: dict[str, Any] = {}
    now = datetime.now(timezone.utc)

    for feed_name, threshold in STALENESS_THRESHOLDS.items():
        try:
            row = await db.execute(
                select(IngestionLog)
                .where(
                    IngestionLog.feed_name == feed_name,
                    IngestionLog.status.in_(["SUCCESS", "PARTIAL"]),
                )
                .order_by(IngestionLog.completed_at.desc())
                .limit(1)
            )
            latest_log: Optional[IngestionLog] = row.scalar_one_or_none()

            if latest_log is None:
                freshness[feed_name] = {
                    "last_run": None,
                    "status": "never_run",
                    "is_stale": True,
                    "threshold_hours": threshold.total_seconds() / 3600,
                }
            else:
                completed_at = latest_log.completed_at
                # Handle timezone-naive datetimes from DB
                if completed_at is not None and completed_at.tzinfo is None:
                    completed_at = completed_at.replace(tzinfo=timezone.utc)

                age = now - completed_at if completed_at else None
                is_stale = age > threshold if age else True

                freshness[feed_name] = {
                    "last_run": completed_at.isoformat() if completed_at else None,
                    "last_status": latest_log.status,
                    "records_total": latest_log.records_total,
                    "records_succeeded": latest_log.records_inserted,
                    "records_failed": latest_log.records_failed,
                    "age_hours": round(age.total_seconds() / 3600, 1) if age else None,
                    "is_stale": is_stale,
                    "threshold_hours": threshold.total_seconds() / 3600,
                }

        except Exception as exc:
            logger.error(
                "health_freshness_check_failed",
                feed=feed_name,
                error=str(exc),
            )
            freshness[feed_name] = {
                "status": "error",
                "error": "freshness_check_failed",
                "is_stale": True,
            }

    return freshness


def _check_scheduler_status() -> dict[str, Any]:
    """
    Check whether the APScheduler instance is running
    and report next run times for all registered jobs.
    """
    # Lazy import to avoid circular dependency
    from app.jobs.scheduler import get_scheduler

    scheduler = get_scheduler()

    if scheduler is None:
        return {
            "status": "stopped",
            "jobs": [],
        }

    if not scheduler.running:
        return {
            "status": "stopped",
            "jobs": [],
        }

    jobs_info: list[dict[str, Any]] = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        jobs_info.append({
            "id": job.id,
            "name": job.name,
            "next_run": next_run.isoformat() if next_run else None,
            "pending": job.pending,
        })

    return {
        "status": "running",
        "job_count": len(jobs_info),
        "jobs": jobs_info,
    }
