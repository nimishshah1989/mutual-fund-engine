"""
api/v1/benchmarks.py

Benchmark sector weights API — read-only display + manual refresh.

- GET  /benchmarks         — Latest benchmark sector weights (NIFTY 50)
- POST /benchmarks/refresh — Trigger re-fetch from Morningstar GSSB API
"""

import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.core.database import get_db
from app.core.rate_limit import RATE_COMPUTE, RATE_READ, limiter
from app.core.exceptions import AppException
from app.models.schemas.benchmarks import (
    BenchmarkRefreshResponse,
    BenchmarkWeightItem,
    BenchmarkWeightsResponse,
)
from app.models.schemas.common import ApiResponse
from app.services.benchmark_service import BenchmarkService
from app.services.scoring_data_loader import ScoringDataLoader
from app.repositories.score_repo import ScoreRepository

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=ApiResponse[BenchmarkWeightsResponse],
    summary="Get latest benchmark sector weights",
)
@limiter.limit(RATE_READ)
async def get_benchmark_weights(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[BenchmarkWeightsResponse]:
    """Return the latest NIFTY 50 sector weights used for FMS active weight calculation."""
    try:
        service = BenchmarkService(db)
        data_loader = ScoringDataLoader(db, ScoreRepository(db))

        name_config = await data_loader.load_engine_config("benchmark_name")
        mstar_id_config = await data_loader.load_engine_config("benchmark_mstar_id")

        benchmark_name = name_config.get("value", "NIFTY 50") if name_config else "NIFTY 50"
        benchmark_mstar_id = (
            mstar_id_config.get("value") if mstar_id_config else None
        )

        weights_detail = await service.get_latest_weights_detail(benchmark_name)

        sectors = [BenchmarkWeightItem(**w) for w in weights_detail]
        total_weight = sum(s.weight_pct for s in sectors)
        last_fetched = sectors[0].fetched_at if sectors else None

        return ApiResponse.ok(
            data=BenchmarkWeightsResponse(
                benchmark_name=benchmark_name,
                benchmark_mstar_id=benchmark_mstar_id,
                sectors=sectors,
                sector_count=len(sectors),
                total_weight_pct=round(total_weight, 2),
                last_fetched=last_fetched,
            )
        )
    except Exception as exc:
        logger.error("benchmark_get_failed", error=str(exc))
        raise AppException(
            message="Failed to retrieve benchmark weights",
            error_code="BENCHMARK_GET_ERROR",
        )


@router.post(
    "/refresh",
    response_model=ApiResponse[BenchmarkRefreshResponse],
    status_code=201,
    summary="Refresh benchmark weights from Morningstar",
)
@limiter.limit(RATE_COMPUTE)
async def refresh_benchmark_weights(
    request: Request,
    _api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[BenchmarkRefreshResponse]:
    """
    Trigger a re-fetch of benchmark sector weights from Morningstar GSSB API.
    Uses the benchmark_mstar_id from engine_config.
    """
    try:
        data_loader = ScoringDataLoader(db, ScoreRepository(db))
        mstar_id_config = await data_loader.load_engine_config("benchmark_mstar_id")
        name_config = await data_loader.load_engine_config("benchmark_name")

        if not mstar_id_config or not mstar_id_config.get("value"):
            raise AppException(
                message="benchmark_mstar_id not configured in engine_config",
                error_code="BENCHMARK_NOT_CONFIGURED",
            )

        benchmark_mstar_id = mstar_id_config["value"]
        benchmark_name = name_config.get("value", "NIFTY 50") if name_config else "NIFTY 50"

        service = BenchmarkService(db)
        result = await service.refresh_benchmark_weights(
            benchmark_mstar_id=benchmark_mstar_id,
            benchmark_name=benchmark_name,
        )

        logger.info(
            "benchmark_refresh_result",
            status=result.get("status"),
            sector_count=result.get("sector_count", 0),
            reason=result.get("reason"),
            benchmark_mstar_id=benchmark_mstar_id,
        )

        return ApiResponse.ok(
            data=BenchmarkRefreshResponse(**result)
        )
    except AppException:
        raise
    except Exception as exc:
        logger.error("benchmark_refresh_failed", error=str(exc))
        raise AppException(
            message="Failed to refresh benchmark weights",
            error_code="BENCHMARK_REFRESH_ERROR",
        )
