"""
api/v1/ingestion.py

Endpoints for triggering Morningstar data ingestion and viewing
ingestion run history. These are admin-only operations in production.
"""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.core.database import get_db
from app.core.rate_limit import RATE_MUTATION, RATE_READ, limiter
from app.core.exceptions import AppException, DataIngestionError, NotFoundError
from app.models.schemas.common import ApiResponse
from app.models.schemas.ingestion import (
    IngestionLogResponse,
    IngestionRequest,
    IngestionResponse,
)
from app.repositories.ingestion_log_repo import IngestionLogRepository
from app.services.ingestion_service import IngestionService

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post(
    "/morningstar",
    response_model=ApiResponse[IngestionResponse],
    status_code=201,
    summary="Trigger Morningstar data ingestion",
)
@limiter.limit(RATE_MUTATION)
async def ingest_morningstar(
    request: Request,
    body: IngestionRequest,
    _api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[IngestionResponse]:
    """
    Accepts a list of Morningstar fund IDs and ingests performance,
    risk, rank, and sector data for each. Runs sequentially — one fund
    at a time — so that a single failure does not abort the batch.
    """
    try:
        logger.info(
            "ingestion_triggered",
            fund_count=len(body.mstar_ids),
        )

        service = IngestionService(db)
        summary = await service.ingest_all_funds(body.mstar_ids)

        return ApiResponse.ok(
            data=IngestionResponse(
                total=summary["total"],
                succeeded=summary["succeeded"],
                failed=summary["failed"],
                errors=summary["errors"],
                log_id=UUID(summary["log_id"]),
                duration_seconds=summary["duration_seconds"],
            ),
        )

    except Exception as exc:
        logger.error("ingestion_endpoint_failed", error=str(exc))
        raise DataIngestionError(
            message="Ingestion failed",
            error_code="INGESTION_ERROR",
        )


@router.get(
    "/logs",
    response_model=ApiResponse[list[IngestionLogResponse]],
    summary="List recent ingestion logs",
)
@limiter.limit(RATE_READ)
async def list_ingestion_logs(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100, description="Max logs to return"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[IngestionLogResponse]]:
    """Return the most recent ingestion log entries, newest first."""
    try:
        repo = IngestionLogRepository(db)
        logs = await repo.list_recent(limit=limit)

        return ApiResponse.ok(
            data=[
                IngestionLogResponse(
                    id=log.id,
                    feed_name=log.feed_name,
                    status=log.status,
                    started_at=log.started_at,
                    completed_at=log.completed_at,
                    records_total=log.records_total,
                    records_inserted=log.records_inserted,
                    records_updated=log.records_updated,
                    records_failed=log.records_failed,
                    error_details=log.errors,
                    created_at=log.created_at,
                )
                for log in logs
            ],
        )

    except Exception as exc:
        logger.error("ingestion_logs_list_failed", error=str(exc))
        raise AppException(
            message="Failed to retrieve ingestion logs",
            error_code="INGESTION_LOG_ERROR",
        )


@router.get(
    "/logs/{log_id}",
    response_model=ApiResponse[IngestionLogResponse],
    summary="Get a single ingestion log",
)
@limiter.limit(RATE_READ)
async def get_ingestion_log(
    request: Request,
    log_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[IngestionLogResponse]:
    """Return a single ingestion log entry by ID."""
    try:
        repo = IngestionLogRepository(db)
        log = await repo.get_by_id(log_id)

        if log is None:
            raise NotFoundError(
                message=f"Ingestion log {log_id} not found",
                error_code="LOG_NOT_FOUND",
            )

        return ApiResponse.ok(
            data=IngestionLogResponse(
                id=log.id,
                feed_name=log.feed_name,
                status=log.status,
                started_at=log.started_at,
                completed_at=log.completed_at,
                records_total=log.records_total,
                records_inserted=log.records_inserted,
                records_updated=log.records_updated,
                records_failed=log.records_failed,
                error_details=log.errors,
                created_at=log.created_at,
            ),
        )

    except AppException:
        # Re-raise AppException subclasses (e.g. NotFoundError above)
        raise
    except Exception as exc:
        logger.error("ingestion_log_get_failed", log_id=str(log_id), error=str(exc))
        raise AppException(
            message="Failed to retrieve ingestion log",
            error_code="INGESTION_LOG_ERROR",
        )
