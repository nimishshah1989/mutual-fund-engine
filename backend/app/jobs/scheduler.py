"""
jobs/scheduler.py

APScheduler (v3) configuration with AsyncIOScheduler.
Registers all recurring background jobs (daily, weekly, monthly)
and provides start/stop lifecycle functions for FastAPI integration.

Timezone: Asia/Kolkata for all scheduled jobs (Indian market hours).
Job defaults: coalesce=True (skip missed runs), max_instances=1 (no overlap).
"""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Module-level scheduler instance — accessible for health checks
_scheduler: AsyncIOScheduler | None = None

IST_TIMEZONE = "Asia/Kolkata"


def get_scheduler() -> AsyncIOScheduler | None:
    """Return the current scheduler instance (or None if not started)."""
    return _scheduler


async def start_scheduler(settings: Settings) -> None:
    """
    Create, configure, and start the APScheduler instance.
    Called during FastAPI lifespan startup, AFTER init_db().

    Skipped entirely when scheduler_enabled=False (e.g., in tests).
    """
    global _scheduler

    if not settings.scheduler_enabled:
        logger.info("scheduler_disabled", reason="SCHEDULER_ENABLED=false")
        return

    _scheduler = AsyncIOScheduler(
        timezone=IST_TIMEZONE,
        job_defaults={
            "coalesce": True,       # If multiple runs were missed, only fire once
            "max_instances": 1,     # Never run overlapping instances of the same job
            "misfire_grace_time": 3600,  # Allow up to 1 hour late execution
        },
    )

    # -- Register scheduled jobs --
    _register_jobs(_scheduler)

    _scheduler.start()
    logger.info(
        "scheduler_started",
        timezone=IST_TIMEZONE,
        job_count=len(_scheduler.get_jobs()),
    )

    # Log all registered jobs and their next run times
    for job in _scheduler.get_jobs():
        logger.info(
            "scheduler_job_registered",
            job_id=job.id,
            job_name=job.name,
            next_run=str(job.next_run_time),
        )


async def stop_scheduler() -> None:
    """
    Gracefully shut down the scheduler.
    Called during FastAPI lifespan shutdown.
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")
        _scheduler = None


def _register_jobs(scheduler: AsyncIOScheduler) -> None:
    """
    Register all recurring background jobs.

    Schedule:
      - daily_nav_refresh: Every day at 2:00 AM IST
      - weekly_master_refresh: Monday at 6:00 AM IST
      - monthly_risk_recompute: 2nd of every month at 3:00 AM IST
    """
    # Lazy imports to avoid circular dependencies at module load time
    from app.jobs.daily_nav_refresh import run_daily_nav_refresh
    from app.jobs.weekly_master_refresh import run_weekly_master_refresh
    from app.jobs.monthly_risk_recompute import run_monthly_risk_recompute
    from app.jobs.daily_pulse_refresh import run_daily_pulse_refresh

    # -- Daily NAV Refresh: 2:00 AM IST every day --
    scheduler.add_job(
        func=run_daily_nav_refresh,
        trigger=CronTrigger(hour=2, minute=0, timezone=IST_TIMEZONE),
        id="daily_nav_refresh",
        name="Daily NAV Refresh (Morningstar)",
        replace_existing=True,
    )

    # -- Weekly Master Refresh: Monday 6:00 AM IST --
    scheduler.add_job(
        func=run_weekly_master_refresh,
        trigger=CronTrigger(day_of_week="mon", hour=6, minute=0, timezone=IST_TIMEZONE),
        id="weekly_master_refresh",
        name="Weekly Master Data Refresh",
        replace_existing=True,
    )

    # -- Monthly Risk Recompute: 2nd of month, 3:00 AM IST --
    scheduler.add_job(
        func=run_monthly_risk_recompute,
        trigger=CronTrigger(day=2, hour=3, minute=0, timezone=IST_TIMEZONE),
        id="monthly_risk_recompute",
        name="Monthly Full Pipeline Recompute",
        replace_existing=True,
    )

    # -- Daily Pulse Refresh: 2:30 AM IST every day --
    scheduler.add_job(
        func=run_daily_pulse_refresh,
        trigger=CronTrigger(hour=2, minute=30, timezone=IST_TIMEZONE),
        id="daily_pulse_refresh",
        name="Daily MF Pulse Refresh (NAV + Ratio Returns)",
        replace_existing=True,
    )
