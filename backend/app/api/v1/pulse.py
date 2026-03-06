"""
api/v1/pulse.py

MF Pulse endpoints — fund signals relative to Nifty 50 via ratio returns.

Endpoints:
  GET  /pulse              — Paginated fund pulse data (period, category, signal filters)
  GET  /pulse/categories   — Signal distribution per SEBI category
  GET  /pulse/coverage     — Data coverage stats (NAV fund count, date ranges)
  POST /pulse/refresh      — Trigger NAV fetch + snapshot recompute
  POST /pulse/backfill     — Trigger 3-year NAV backfill (one-time)
"""

from typing import Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.core.database import get_db, get_standalone_session
from app.core.exceptions import AppException
from app.core.rate_limit import RATE_COMPUTE, RATE_READ, limiter
from app.models.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.models.schemas.pulse import (
    PulseCategoryResponse,
    PulseCoverageStats,
    PulseDataResponse,
    PulseFundItem,
)
from app.services.nav_fetcher_service import NavFetcherService
from app.services.pulse_data_service import PulseDataService

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[PulseFundItem],
    summary="List fund pulse data with ratio returns and signals",
)
@limiter.limit(RATE_READ)
async def list_pulse_data(
    request: Request,
    period: str = Query(default="1m", description="Period: 1m, 3m, 6m, 1y, 2y, 3y"),
    category_name: Optional[str] = Query(default=None, alias="category_name", description="Filter by SEBI category"),
    signal: Optional[str] = Query(default=None, description="Filter by signal: STRONG_OW, OVERWEIGHT, NEUTRAL, UNDERWEIGHT, STRONG_UW"),
    sort_by: str = Query(default="ratio_return", description="Sort column: ratio_return, fund_return, nifty_return, excess_return, signal"),
    sort_desc: bool = Query(default=True, description="Sort descending"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[PulseFundItem]:
    """Get paginated fund pulse data with ratio returns relative to Nifty 50."""
    try:
        valid_periods = {"1m", "3m", "6m", "1y", "2y", "3y"}
        if period not in valid_periods:
            raise AppException(
                message=f"Invalid period: {period}. Valid: {sorted(valid_periods)}",
                error_code="INVALID_PERIOD",
            )

        valid_signals = {"STRONG_OW", "OVERWEIGHT", "NEUTRAL", "UNDERWEIGHT", "STRONG_UW"}
        if signal and signal not in valid_signals:
            raise AppException(
                message=f"Invalid signal: {signal}. Valid: {sorted(valid_signals)}",
                error_code="INVALID_SIGNAL",
            )

        valid_sorts = {"ratio_return", "fund_return", "nifty_return", "excess_return", "signal"}
        if sort_by not in valid_sorts:
            raise AppException(
                message=f"Invalid sort_by: {sort_by}. Valid: {sorted(valid_sorts)}",
                error_code="INVALID_SORT",
            )

        service = PulseDataService(db)
        offset = (page - 1) * limit
        result = await service.get_pulse_data(
            period=period,
            category_name=category_name,
            signal=signal,
            sort_by=sort_by,
            sort_desc=sort_desc,
            limit=limit,
            offset=offset,
        )

        return PaginatedResponse.create(
            items=result.funds,
            page=page,
            limit=limit,
            total=result.total_funds,
        )

    except AppException:
        raise
    except Exception as exc:
        logger.error("pulse_list_failed", period=period, error=str(exc))
        raise AppException(message="Failed to list pulse data", error_code="PULSE_LIST_ERROR")


@router.get(
    "/categories",
    response_model=ApiResponse[PulseCategoryResponse],
    summary="Signal distribution per SEBI category",
)
@limiter.limit(RATE_READ)
async def get_pulse_categories(
    request: Request,
    period: str = Query(default="1m", description="Period: 1m, 3m, 6m, 1y, 2y, 3y"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PulseCategoryResponse]:
    """Get signal distribution (STRONG_OW, OW, NEUTRAL, UW, STRONG_UW) per SEBI category."""
    try:
        valid_periods = {"1m", "3m", "6m", "1y", "2y", "3y"}
        if period not in valid_periods:
            raise AppException(
                message=f"Invalid period: {period}. Valid: {sorted(valid_periods)}",
                error_code="INVALID_PERIOD",
            )

        service = PulseDataService(db)
        result = await service.get_category_summary(period)
        return ApiResponse.ok(data=result)
    except AppException:
        raise
    except Exception as exc:
        logger.error("pulse_categories_failed", period=period, error=str(exc))
        raise AppException(
            message="Failed to get category summary",
            error_code="PULSE_CATEGORY_ERROR",
        )


@router.get(
    "/coverage",
    response_model=ApiResponse[PulseCoverageStats],
    summary="Data coverage stats",
)
@limiter.limit(RATE_READ)
async def get_pulse_coverage(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PulseCoverageStats]:
    """Get data coverage stats: fund count with NAV data, date ranges, benchmark info."""
    try:
        service = PulseDataService(db)
        result = await service.get_coverage_stats()
        return ApiResponse.ok(data=result)
    except Exception as exc:
        logger.error("pulse_coverage_failed", error=str(exc))
        raise AppException(
            message="Failed to get coverage stats",
            error_code="PULSE_COVERAGE_ERROR",
        )


@router.post(
    "/refresh",
    response_model=ApiResponse[dict],
    summary="Trigger NAV refresh + snapshot recompute",
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(RATE_COMPUTE)
async def refresh_pulse(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """
    Manual trigger: refresh benchmark prices, refresh fund NAVs (latest),
    then recompute all pulse snapshots. Runs in background (~30 seconds).
    Returns 202 Accepted immediately.
    """
    from app.jobs.daily_pulse_refresh import run_daily_pulse_refresh

    logger.info("pulse_refresh_triggered")
    background_tasks.add_task(run_daily_pulse_refresh)

    return ApiResponse.ok(data={
        "status": "accepted",
        "message": "Pulse refresh started in background. Check /pulse/coverage for completion.",
    })


@router.post(
    "/diagnose",
    response_model=ApiResponse[dict],
    summary="Diagnostic: test NAV fetch pipeline synchronously",
)
@limiter.limit(RATE_COMPUTE)
async def diagnose_pulse(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """Run a quick diagnostic of the pulse pipeline and return results/errors."""
    import traceback

    results: dict = {}

    # Step 1: Check fund_master has amfi_codes
    try:
        from sqlalchemy import func, select
        from app.models.db.fund_master import FundMaster

        total_q = await db.execute(select(func.count(FundMaster.mstar_id)))
        total = total_q.scalar() or 0
        amfi_q = await db.execute(
            select(func.count(FundMaster.mstar_id)).where(
                FundMaster.amfi_code.isnot(None),
                FundMaster.amfi_code != "",
            )
        )
        with_amfi = amfi_q.scalar() or 0
        results["fund_master"] = {"total": total, "with_amfi_code": with_amfi}
    except Exception as exc:
        results["fund_master"] = {"error": f"{type(exc).__name__}: {exc}"}

    # Step 2: Test AMFI bulk file download
    try:
        import httpx

        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            resp = await client.get("https://www.amfiindia.com/spages/NAVAll.txt")
            lines = resp.text.strip().split("\n")
            results["amfi_bulk_file"] = {
                "status_code": resp.status_code,
                "total_lines": len(lines),
                "sample_line": lines[2] if len(lines) > 2 else "empty",
            }
    except Exception as exc:
        results["amfi_bulk_file"] = {"error": f"{type(exc).__name__}: {exc}"}

    # Step 3: Test yfinance
    try:
        import asyncio
        import yfinance as yf

        loop = asyncio.get_running_loop()
        df = await loop.run_in_executor(
            None, lambda: yf.download("^NSEI", period="5d", progress=False)
        )
        results["yfinance"] = {
            "rows": len(df),
            "columns": list(str(c) for c in df.columns),
        }
    except Exception as exc:
        results["yfinance"] = {"error": f"{type(exc).__name__}: {exc}", "tb": traceback.format_exc()[-500:]}

    # Step 4: Test mftool (single fund)
    try:
        import asyncio
        from mftool import Mftool

        loop = asyncio.get_running_loop()
        mf = Mftool()
        nav_data = await loop.run_in_executor(
            None, lambda: mf.get_scheme_historical_nav("119551", as_Dataframe=True)
        )
        results["mftool"] = {
            "rows": len(nav_data) if nav_data is not None else 0,
            "type": str(type(nav_data).__name__),
        }
    except Exception as exc:
        results["mftool"] = {"error": f"{type(exc).__name__}: {exc}", "tb": traceback.format_exc()[-500:]}

    return ApiResponse.ok(data=results)


@router.post(
    "/backfill",
    response_model=ApiResponse[dict],
    summary="Trigger 3-year NAV backfill (one-time)",
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(RATE_COMPUTE)
async def backfill_pulse(
    request: Request,
    background_tasks: BackgroundTasks,
    years: int = Query(default=3, ge=1, le=10, description="Years of history to fetch"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """
    One-time backfill: fetch 3 years of historical NAV for all funds + Nifty 50.
    Then compute snapshots. Takes ~5 minutes for 535 funds.
    Returns 202 Accepted immediately — work runs in background.
    """
    logger.info("pulse_backfill_triggered", years=years)

    async def _run_backfill() -> None:
        async with get_standalone_session() as session:
            fetcher = NavFetcherService(session)
            service = PulseDataService(session)
            await fetcher.backfill_benchmark(years=years)
            await fetcher.backfill_all_fund_navs(years=years)
            await service.compute_all_snapshots()

    background_tasks.add_task(_run_backfill)

    return ApiResponse.ok(data={
        "status": "accepted",
        "message": f"Backfill ({years}yr) started in background. Check /pulse/coverage for completion.",
    })
