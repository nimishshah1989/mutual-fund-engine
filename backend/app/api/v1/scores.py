"""
api/v1/scores.py

Score computation and category listing endpoints.

- POST /compute    — Trigger score computation (QFS, FSAS, or full pipeline)
- GET  /categories — List unique SEBI category names for filter dropdowns

Read/query endpoints (overview, shortlist, detail) are in scores_read.py.
"""

import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.core.database import get_db
from app.core.rate_limit import RATE_COMPUTE, RATE_READ, limiter
from app.core.exceptions import AppException
from app.models.db.fund_master import FundMaster
from app.models.schemas.common import ApiResponse
from app.models.schemas.scores import (
    ComputeLayer,
    PipelineComputeResponse,
    PipelineComputeResult,
    ScoreComputeRequest,
    ScoreComputeResponse,
    ScoreComputeResult,
)
from app.services.scoring_service import ScoringService

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post(
    "/compute",
    response_model=ApiResponse,
    status_code=201,
    summary="Trigger score computation",
)
@limiter.limit(RATE_COMPUTE)
async def compute_scores(
    request: Request,
    body: ScoreComputeRequest,
    _api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Trigger score computation for a specific category or all categories.

    Supported layers:
    - qfs: Quantitative Fund Score (Layer 1)
    - fsas: FM Sector Alignment Score (Layer 2) -- shortlisted funds only
    - all: Full pipeline -- QFS -> shortlist -> FSAS -> recommend
    """
    try:
        service = ScoringService(db)
        layer = body.layer

        # Full pipeline: QFS -> shortlist -> FSAS -> recommend
        if layer == ComputeLayer.ALL:
            return await _compute_full_pipeline(service, body)

        # Single layer computation
        if layer == ComputeLayer.QFS:
            summaries = await _compute_single_layer_qfs(service, body)
        elif layer == ComputeLayer.FSAS:
            summaries = await _compute_single_layer_fsas(service, body)
        else:
            raise AppException(
                message=f"Unknown compute layer: {layer}",
                error_code="INVALID_LAYER",
            )

        results = [
            ScoreComputeResult(
                category=s.get("category", "unknown"),
                fund_count=s.get("fund_count", 0),
                computed_date=s.get("computed_date", ""),
                status=s.get("status", "unknown"),
                rows_upserted=s.get("rows_upserted"),
                audits_created=s.get("audits_created"),
                reason=s.get("reason"),
                error=s.get("error"),
                tier_distribution=s.get("tier_distribution"),
                override_count=s.get("override_count"),
            )
            for s in summaries
        ]

        total_funds = sum(r.fund_count for r in results)

        logger.info(
            "score_compute_triggered",
            category=body.category_name,
            layer=body.layer.value,
            total_categories=len(results),
            total_funds=total_funds,
        )

        return ApiResponse.ok(
            data=ScoreComputeResponse(
                results=results,
                total_categories=len(results),
                total_funds_computed=total_funds,
                layer=layer.value,
            ),
        )

    except AppException:
        # Re-raise AppException subclasses (e.g. INVALID_LAYER above)
        raise
    except Exception as exc:
        logger.error(
            "score_compute_failed",
            category=body.category_name,
            layer=body.layer.value,
            error=str(exc),
        )
        raise AppException(
            message="Failed to compute scores",
            error_code="SCORE_COMPUTE_ERROR",
        )


@router.get(
    "/categories",
    response_model=ApiResponse[list[str]],
    summary="List unique SEBI category names",
)
@limiter.limit(RATE_READ)
async def list_categories(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[str]]:
    """Return sorted list of unique category names from eligible funds."""
    try:
        result = await db.execute(
            select(distinct(FundMaster.category_name))
            .where(
                FundMaster.is_eligible.is_(True),
                FundMaster.deleted_at.is_(None),
                FundMaster.category_name.isnot(None),
            )
            .order_by(FundMaster.category_name)
        )
        categories = list(result.scalars().all())
        return ApiResponse(success=True, data=categories)
    except Exception as exc:
        logger.error("categories_list_failed", error=str(exc))
        raise AppException(
            message="Failed to list categories",
            error_code="CATEGORIES_ERROR",
        )


# ---------------------------------------------------------------------------
# Private helpers for compute endpoint
# ---------------------------------------------------------------------------

async def _compute_single_layer_qfs(
    service: ScoringService,
    body: ScoreComputeRequest,
) -> list[dict]:
    """Run QFS computation only."""
    if body.category_name:
        summary = await service.compute_qfs_for_category(
            category_name=body.category_name,
            trigger_event=body.trigger_event,
        )
        return [summary]
    else:
        return await service.compute_qfs_for_all_categories(
            trigger_event=body.trigger_event,
        )


async def _compute_single_layer_fsas(
    service: ScoringService,
    body: ScoreComputeRequest,
) -> list[dict]:
    """Run FSAS for shortlisted funds."""
    summary = await service.compute_fsas_for_shortlisted(
        trigger_event=body.trigger_event,
    )
    return [summary]


async def _compute_full_pipeline(
    service: ScoringService,
    body: ScoreComputeRequest,
) -> ApiResponse:
    """Run the full QFS -> shortlist -> FSAS -> recommend pipeline."""
    summary = await service.compute_full_pipeline(
        category_name=body.category_name,
        trigger_event=body.trigger_event,
    )

    result = PipelineComputeResult(
        category=summary.get("category", "all"),
        status=summary.get("status", "unknown"),
        computed_date=summary.get("computed_date", ""),
        fund_count=summary.get("fund_count", 0),
        trigger_event=summary.get("trigger_event"),
        layers=summary.get("layers"),
        tier_distribution=summary.get("tier_distribution"),
        shortlisted_count=summary.get("shortlisted_count"),
        error=summary.get("error"),
    )

    return ApiResponse.ok(
        data=PipelineComputeResponse(
            results=[result],
            total_categories=1,
            total_funds_computed=result.fund_count,
            total_shortlisted=result.shortlisted_count or 0,
        ),
    )
