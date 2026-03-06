"""
api/v1/scores_read.py

Score read/query endpoints:
- GET /overview     — List latest scores with QFS-based tiers (paginated)
- GET /shortlist    — List shortlisted funds with FSAS alignment details
- GET /{mstar_id}   — Full score breakdown for a single fund (all layers)

Computation endpoints (POST /compute, GET /categories) are in scores.py.
"""

from __future__ import annotations

import re
from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import RATE_READ, limiter
from app.core.exceptions import AppException, NotFoundError
from app.engines.fsas_engine import FSASEngine
from app.models.db.fund_master import FundMaster
from app.models.schemas.common import ApiResponse, PaginatedResponse
from app.models.schemas.scores import (
    FSASDetail,
    FundScoreDetail,
    RecommendationDetail,
    ScoreDetail,
    ScoreOverviewItem,
    ShortlistItem,
)
from app.repositories.score_repo import ScoreRepository

logger = structlog.get_logger(__name__)
router = APIRouter()


def _safe_float(val: Any) -> Optional[float]:
    """Convert to float if not None."""
    return float(val) if val is not None else None


@router.get(
    "/overview",
    response_model=PaginatedResponse[ScoreOverviewItem],
    summary="List latest scores with QFS-based tiers",
)
@limiter.limit(RATE_READ)
async def list_scores(
    request: Request,
    category_name: Optional[str] = Query(default=None, description="Filter by SEBI category"),
    search: Optional[str] = Query(default=None, max_length=200, description="Search fund name"),
    sort_by: str = Query(default="qfs", description="Sort column"),
    sort_desc: bool = Query(default=True, description="Sort descending"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ScoreOverviewItem]:
    """List the latest QFS scores enriched with recommendation data."""
    try:
        score_repo = ScoreRepository(db)

        fund_query = select(
            FundMaster.mstar_id, FundMaster.fund_name, FundMaster.category_name,
        ).where(FundMaster.is_eligible.is_(True), FundMaster.deleted_at.is_(None))

        if category_name:
            fund_query = fund_query.where(FundMaster.category_name == category_name)
        if search:
            safe_search = re.sub(r'[%_\\]', lambda m: '\\' + m.group(), search)
            fund_query = fund_query.where(FundMaster.fund_name.ilike(f"%{safe_search}%"))

        fund_result = await db.execute(fund_query)
        fund_rows = fund_result.all()
        mstar_ids = [row.mstar_id for row in fund_rows]
        fund_lookup = {row.mstar_id: row for row in fund_rows}

        if not mstar_ids:
            return PaginatedResponse.create(items=[], page=page, limit=limit, total=0)

        allowed_sort = {"qfs", "wfs_raw", "data_completeness_pct", "computed_date", "available_horizons"}
        effective_sort = sort_by if sort_by in allowed_sort else "qfs"

        rows, total = await score_repo.get_latest_qfs_by_category(
            category_name=category_name or "all", mstar_ids=mstar_ids,
            sort_by=effective_sort, sort_desc=sort_desc, page=page, limit=limit,
        )

        qfs_mstar_ids = [row.mstar_id for row in rows]
        rec_records = await score_repo.get_latest_recommendations_by_mstar_ids(qfs_mstar_ids)
        rec_lookup = {rec.mstar_id: rec for rec in rec_records}

        items: list[ScoreOverviewItem] = []
        for row in rows:
            fund_info = fund_lookup.get(row.mstar_id)
            item_data: dict[str, Any] = {
                "mstar_id": row.mstar_id,
                "fund_name": fund_info.fund_name if fund_info else None,
                "category_name": fund_info.category_name if fund_info else None,
                "computed_date": row.computed_date,
                "qfs": _safe_float(row.qfs) or 0.0,
                "wfs_raw": _safe_float(row.wfs_raw),
                "score_1y": _safe_float(row.score_1y),
                "score_3y": _safe_float(row.score_3y),
                "score_5y": _safe_float(row.score_5y),
                "score_10y": _safe_float(row.score_10y),
                "data_completeness_pct": _safe_float(row.data_completeness_pct),
                "available_horizons": row.available_horizons,
                "category_universe_size": row.category_universe_size,
                "engine_version": row.engine_version,
            }
            rec = rec_lookup.get(row.mstar_id)
            if rec is not None:
                item_data["tier"] = rec.tier
                item_data["action"] = rec.action
                item_data["qfs_rank"] = rec.qfs_rank
                item_data["category_rank_pct"] = _safe_float(rec.category_rank_pct)

            items.append(ScoreOverviewItem(**item_data))

        return PaginatedResponse.create(items=items, page=page, limit=limit, total=total)

    except Exception as exc:
        logger.error("score_overview_failed", category=category_name, error=str(exc))
        raise AppException(message="Failed to list scores", error_code="SCORE_LIST_ERROR")


@router.get(
    "/shortlist",
    response_model=ApiResponse[list[ShortlistItem]],
    summary="List shortlisted funds with FSAS alignment",
)
@limiter.limit(RATE_READ)
async def list_shortlist(
    request: Request, db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[ShortlistItem]]:
    """Return the current shortlist enriched with FSAS scores and sector alignment."""
    try:
        score_repo = ScoreRepository(db)
        fsas_engine = FSASEngine()

        shortlist_records = await score_repo.get_latest_shortlist()
        if not shortlist_records:
            return ApiResponse.ok(data=[])

        mstar_ids = [r.mstar_id for r in shortlist_records]
        fund_result = await db.execute(
            select(FundMaster.mstar_id, FundMaster.fund_name)
            .where(FundMaster.mstar_id.in_(mstar_ids))
        )
        fund_lookup = {row.mstar_id: row.fund_name for row in fund_result.all()}

        rec_records = await score_repo.get_latest_recommendations_by_mstar_ids(mstar_ids)
        rec_lookup = {r.mstar_id: r for r in rec_records}

        fsas_records = await score_repo.get_latest_fsas_by_mstar_ids(mstar_ids)
        fsas_lookup = {r.mstar_id: r for r in fsas_records}

        items: list[ShortlistItem] = []
        for record in shortlist_records:
            rec = rec_lookup.get(record.mstar_id)
            fsas = fsas_lookup.get(record.mstar_id)

            alignment_summary = None
            avoid_exposure_pct = None
            if fsas is not None and fsas.sector_contributions:
                alignment_summary = fsas_engine.get_alignment_summary(fsas.sector_contributions)
                avoid_exposure_pct = _safe_float(fsas.avoid_exposure_pct)

            items.append(ShortlistItem(
                mstar_id=record.mstar_id,
                fund_name=fund_lookup.get(record.mstar_id),
                category_name=record.category_name,
                qfs_score=float(record.qfs_score) if record.qfs_score else 0.0,
                qfs_rank=record.qfs_rank,
                total_in_category=record.total_in_category,
                shortlist_reason=record.shortlist_reason,
                computed_date=record.computed_date,
                fsas=_safe_float(rec.fsas) if rec else None,
                tier=rec.tier if rec else None,
                action=rec.action if rec else None,
                avoid_exposure_pct=avoid_exposure_pct,
                alignment_summary=alignment_summary,
            ))

        return ApiResponse.ok(data=items)

    except Exception as exc:
        logger.error("shortlist_failed", error=str(exc))
        raise AppException(message="Failed to retrieve shortlist", error_code="SHORTLIST_ERROR")


@router.get(
    "/{mstar_id}",
    response_model=ApiResponse[FundScoreDetail],
    summary="Get full score breakdown for one fund (all layers)",
)
@limiter.limit(RATE_READ)
async def get_score_detail(
    request: Request, mstar_id: str, db: AsyncSession = Depends(get_db),
) -> ApiResponse[FundScoreDetail]:
    """Return QFS, FSAS, and recommendation details for a single fund."""
    try:
        score_repo = ScoreRepository(db)

        fund_result = await db.execute(
            select(FundMaster.fund_name, FundMaster.category_name)
            .where(FundMaster.mstar_id == mstar_id)
        )
        fund_row = fund_result.first()

        qfs_record = await score_repo.get_latest_qfs(mstar_id)
        qfs_detail = ScoreDetail.model_validate(qfs_record) if qfs_record else None

        fsas_record = await score_repo.get_latest_fsas(mstar_id)
        fsas_detail = FSASDetail.model_validate(fsas_record) if fsas_record else None

        rec_record = await score_repo.get_latest_recommendation(mstar_id)
        rec_detail = RecommendationDetail.model_validate(rec_record) if rec_record else None

        if qfs_detail is None and fsas_detail is None and rec_detail is None:
            raise NotFoundError(
                message=f"No score data found for fund {mstar_id}",
                error_code="SCORE_NOT_FOUND",
            )

        detail = FundScoreDetail(
            mstar_id=mstar_id,
            fund_name=fund_row.fund_name if fund_row else None,
            category_name=fund_row.category_name if fund_row else None,
            qfs=qfs_detail, fsas=fsas_detail, recommendation=rec_detail,
        )
        return ApiResponse.ok(data=detail)

    except AppException:
        raise
    except Exception as exc:
        logger.error("score_detail_failed", mstar_id=mstar_id, error=str(exc))
        raise AppException(message="Failed to retrieve score details", error_code="SCORE_DETAIL_ERROR")
