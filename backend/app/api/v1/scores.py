"""
api/v1/scores.py

Score endpoints for the JIP MF Recommendation Engine.
v2: QFS-rank based tiers, shortlist endpoint, no CRS.

- POST /compute       — Trigger score computation (QFS, FSAS, or full pipeline)
- GET  /overview      — List latest scores with QFS-based tiers (paginated)
- GET  /shortlist     — List shortlisted funds with FSAS alignment details
- GET  /categories    — List unique SEBI category names for filter dropdowns
- GET  /{mstar_id}    — Full score breakdown for a single fund (all layers)
"""

from __future__ import annotations

from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.engines.fsas_engine import FSASEngine
from app.models.db.fund_master import FundMaster
from app.models.schemas.common import ApiResponse, PaginatedResponse
from app.models.schemas.scores import (
    ComputeLayer,
    FSASDetail,
    FundScoreDetail,
    PipelineComputeResponse,
    PipelineComputeResult,
    RecommendationDetail,
    ScoreComputeRequest,
    ScoreComputeResponse,
    ScoreComputeResult,
    ScoreDetail,
    ScoreOverviewItem,
    ShortlistItem,
)
from app.repositories.score_repo import ScoreRepository
from app.services.scoring_service import ScoringService

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post(
    "/compute",
    response_model=ApiResponse,
    status_code=201,
    summary="Trigger score computation",
)
async def compute_scores(
    body: ScoreComputeRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Trigger score computation for a specific category or all categories.

    Supported layers:
    - qfs: Quantitative Fund Score (Layer 1)
    - fsas: FM Sector Alignment Score (Layer 2) — shortlisted funds only
    - all: Full pipeline — QFS -> shortlist -> FSAS -> recommend
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
            return ApiResponse.fail(
                code="INVALID_LAYER",
                message=f"Unknown compute layer: {layer}",
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

    except Exception as exc:
        logger.error(
            "score_compute_failed",
            category=body.category_name,
            layer=body.layer.value,
            error=str(exc),
        )
        return ApiResponse.fail(
            code="SCORE_COMPUTE_ERROR",
            message=f"Failed to compute scores: {exc}",
        )


@router.get(
    "/overview",
    response_model=PaginatedResponse[ScoreOverviewItem],
    summary="List latest scores with QFS-based tiers",
)
async def list_scores(
    category_name: Optional[str] = Query(default=None, description="Filter by SEBI category"),
    search: Optional[str] = Query(default=None, description="Search fund name"),
    sort_by: str = Query(default="qfs", description="Sort column"),
    sort_desc: bool = Query(default=True, description="Sort descending"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ScoreOverviewItem]:
    """
    List the latest QFS scores enriched with recommendation data
    (tier, action, QFS rank — all from QFS percentile, no CRS).
    """
    try:
        score_repo = ScoreRepository(db)

        # Load eligible funds with name and category
        fund_query = select(
            FundMaster.mstar_id,
            FundMaster.fund_name,
            FundMaster.category_name,
        ).where(
            FundMaster.is_eligible.is_(True),
            FundMaster.deleted_at.is_(None),
        )
        if category_name:
            fund_query = fund_query.where(FundMaster.category_name == category_name)
        if search:
            fund_query = fund_query.where(FundMaster.fund_name.ilike(f"%{search}%"))

        fund_result = await db.execute(fund_query)
        fund_rows = fund_result.all()
        mstar_ids = [row.mstar_id for row in fund_rows]
        fund_lookup = {row.mstar_id: row for row in fund_rows}

        if not mstar_ids:
            return PaginatedResponse.create(items=[], page=page, limit=limit, total=0)

        allowed_sort_columns = {
            "qfs", "wfs_raw", "data_completeness_pct",
            "computed_date", "available_horizons",
        }
        effective_sort_by = sort_by if sort_by in allowed_sort_columns else "qfs"

        rows, total = await score_repo.get_latest_qfs_by_category(
            category_name=category_name or "all",
            mstar_ids=mstar_ids,
            sort_by=effective_sort_by,
            sort_desc=sort_desc,
            page=page,
            limit=limit,
        )

        # Enrich with recommendation data (tier, action, rank)
        qfs_mstar_ids = [row.mstar_id for row in rows]
        rec_records = await score_repo.get_latest_recommendations_by_mstar_ids(qfs_mstar_ids)
        rec_lookup: dict[str, Any] = {}
        for rec in rec_records:
            rec_lookup[rec.mstar_id] = rec

        items: list[ScoreOverviewItem] = []
        for row in rows:
            fund_info = fund_lookup.get(row.mstar_id)

            item_data = {
                "mstar_id": row.mstar_id,
                "fund_name": fund_info.fund_name if fund_info else None,
                "category_name": fund_info.category_name if fund_info else None,
                "computed_date": row.computed_date,
                "qfs": float(row.qfs) if row.qfs is not None else 0.0,
                "wfs_raw": float(row.wfs_raw) if row.wfs_raw is not None else None,
                "score_1y": float(row.score_1y) if row.score_1y is not None else None,
                "score_3y": float(row.score_3y) if row.score_3y is not None else None,
                "score_5y": float(row.score_5y) if row.score_5y is not None else None,
                "score_10y": float(row.score_10y) if row.score_10y is not None else None,
                "data_completeness_pct": (
                    float(row.data_completeness_pct)
                    if row.data_completeness_pct is not None
                    else None
                ),
                "available_horizons": row.available_horizons,
                "category_universe_size": row.category_universe_size,
                "engine_version": row.engine_version,
            }

            # Enrich with recommendation data
            rec = rec_lookup.get(row.mstar_id)
            if rec is not None:
                item_data["tier"] = rec.tier
                item_data["action"] = rec.action
                item_data["qfs_rank"] = rec.qfs_rank
                item_data["category_rank_pct"] = (
                    float(rec.category_rank_pct)
                    if rec.category_rank_pct is not None
                    else None
                )

            items.append(ScoreOverviewItem(**item_data))

        return PaginatedResponse.create(
            items=items, page=page, limit=limit, total=total
        )

    except Exception as exc:
        logger.error("score_overview_failed", category=category_name, error=str(exc))
        return PaginatedResponse(
            success=False,
            data=[],
            meta={"page": page, "limit": limit, "total": 0, "total_pages": 0},
            error={"code": "SCORE_LIST_ERROR", "message": f"Failed to list scores: {exc}"},
        )


@router.get(
    "/shortlist",
    response_model=ApiResponse[list[ShortlistItem]],
    summary="List shortlisted funds with FSAS alignment",
)
async def list_shortlist(
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[ShortlistItem]]:
    """
    Return the current shortlist: top N funds per category by QFS rank,
    enriched with FSAS scores and sector alignment summaries.
    """
    try:
        score_repo = ScoreRepository(db)
        fsas_engine = FSASEngine()

        # Get latest shortlist
        shortlist_records = await score_repo.get_latest_shortlist()

        if not shortlist_records:
            return ApiResponse.ok(data=[])

        # Enrich with fund names
        mstar_ids = [r.mstar_id for r in shortlist_records]
        fund_result = await db.execute(
            select(FundMaster.mstar_id, FundMaster.fund_name)
            .where(FundMaster.mstar_id.in_(mstar_ids))
        )
        fund_lookup = {row.mstar_id: row.fund_name for row in fund_result.all()}

        # Enrich with recommendation data
        rec_records = await score_repo.get_latest_recommendations_by_mstar_ids(mstar_ids)
        rec_lookup = {r.mstar_id: r for r in rec_records}

        # Enrich with FSAS data for alignment summary
        fsas_records = await score_repo.get_latest_fsas_by_mstar_ids(mstar_ids)
        fsas_lookup = {r.mstar_id: r for r in fsas_records}

        items: list[ShortlistItem] = []
        for record in shortlist_records:
            rec = rec_lookup.get(record.mstar_id)
            fsas = fsas_lookup.get(record.mstar_id)

            # Build alignment summary from FSAS sector contributions
            alignment_summary = None
            avoid_exposure_pct = None
            if fsas is not None and fsas.sector_contributions:
                alignment_summary = fsas_engine.get_alignment_summary(
                    fsas.sector_contributions
                )
                avoid_exposure_pct = (
                    float(fsas.avoid_exposure_pct)
                    if fsas.avoid_exposure_pct is not None
                    else None
                )

            items.append(ShortlistItem(
                mstar_id=record.mstar_id,
                fund_name=fund_lookup.get(record.mstar_id),
                category_name=record.category_name,
                qfs_score=float(record.qfs_score) if record.qfs_score else 0.0,
                qfs_rank=record.qfs_rank,
                total_in_category=record.total_in_category,
                shortlist_reason=record.shortlist_reason,
                computed_date=record.computed_date,
                fsas=float(rec.fsas) if rec and rec.fsas is not None else None,
                tier=rec.tier if rec else None,
                action=rec.action if rec else None,
                avoid_exposure_pct=avoid_exposure_pct,
                alignment_summary=alignment_summary,
            ))

        return ApiResponse.ok(data=items)

    except Exception as exc:
        logger.error("shortlist_failed", error=str(exc))
        return ApiResponse.fail(
            code="SHORTLIST_ERROR",
            message=f"Failed to get shortlist: {exc}",
        )


@router.get(
    "/categories",
    response_model=ApiResponse[list[str]],
    summary="List unique SEBI category names",
)
async def list_categories(
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
        return ApiResponse.fail(
            code="CATEGORIES_ERROR",
            message=f"Failed to list categories: {exc}",
        )


@router.get(
    "/{mstar_id}",
    response_model=ApiResponse[FundScoreDetail],
    summary="Get full score breakdown for one fund (all layers)",
)
async def get_score_detail(
    mstar_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[FundScoreDetail]:
    """
    Return the full score breakdown for a single fund:
    - QFS (Layer 1): Per-horizon scores, WFS, metric breakdown
    - FSAS (Layer 2): Sector contributions (only if shortlisted)
    - Recommendation: Tier, action, QFS rank, percentile
    """
    try:
        score_repo = ScoreRepository(db)

        # Load QFS
        qfs_record = await score_repo.get_latest_qfs(mstar_id)
        qfs_detail: Optional[ScoreDetail] = None
        if qfs_record is not None:
            qfs_detail = ScoreDetail.model_validate(qfs_record)

        # Load FSAS
        fsas_record = await score_repo.get_latest_fsas(mstar_id)
        fsas_detail: Optional[FSASDetail] = None
        if fsas_record is not None:
            fsas_detail = FSASDetail.model_validate(fsas_record)

        # Load recommendation
        rec_record = await score_repo.get_latest_recommendation(mstar_id)
        rec_detail: Optional[RecommendationDetail] = None
        if rec_record is not None:
            rec_detail = RecommendationDetail.model_validate(rec_record)

        if qfs_detail is None and fsas_detail is None and rec_detail is None:
            return ApiResponse.fail(
                code="SCORE_NOT_FOUND",
                message=f"No score data found for fund {mstar_id}",
            )

        detail = FundScoreDetail(
            mstar_id=mstar_id,
            qfs=qfs_detail,
            fsas=fsas_detail,
            recommendation=rec_detail,
        )

        return ApiResponse.ok(data=detail)

    except Exception as exc:
        logger.error("score_detail_failed", mstar_id=mstar_id, error=str(exc))
        return ApiResponse.fail(
            code="SCORE_DETAIL_ERROR",
            message=f"Failed to retrieve score for {mstar_id}: {exc}",
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
