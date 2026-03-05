"""
api/v1/ingestion.py

Endpoints for triggering Morningstar data ingestion and viewing
ingestion run history. These are admin-only operations in production.
"""

from __future__ import annotations
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
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
    status_code=200,
    summary="Trigger Morningstar data ingestion",
)
async def ingest_morningstar(
    body: IngestionRequest,
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
        return ApiResponse.fail(
            code="INGESTION_ERROR",
            message=f"Ingestion failed: {exc}",
        )


@router.get(
    "/logs",
    response_model=ApiResponse[list[IngestionLogResponse]],
    summary="List recent ingestion logs",
)
async def list_ingestion_logs(
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
        return ApiResponse.fail(
            code="INGESTION_LOG_ERROR",
            message=f"Failed to retrieve ingestion logs: {exc}",
        )


@router.get(
    "/logs/{log_id}",
    response_model=ApiResponse[IngestionLogResponse],
    summary="Get a single ingestion log",
)
async def get_ingestion_log(
    log_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[IngestionLogResponse]:
    """Return a single ingestion log entry by ID."""
    try:
        repo = IngestionLogRepository(db)
        log = await repo.get_by_id(log_id)

        if log is None:
            return ApiResponse.fail(
                code="LOG_NOT_FOUND",
                message=f"Ingestion log {log_id} not found",
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

    except Exception as exc:
        logger.error("ingestion_log_get_failed", log_id=str(log_id), error=str(exc))
        return ApiResponse.fail(
            code="INGESTION_LOG_ERROR",
            message=f"Failed to retrieve ingestion log: {exc}",
        )
