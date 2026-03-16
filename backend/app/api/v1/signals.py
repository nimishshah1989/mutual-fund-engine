"""
api/v1/signals.py

FM sector signal endpoints.
v2: Added bulk update, sectors list, and signal change history.
"""


from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_api_key
from app.core.database import get_db
from app.core.rate_limit import RATE_MUTATION, RATE_READ, limiter
from app.core.exceptions import AppException, NotFoundError
from app.models.db.sector_signals import SIGNAL_WEIGHTS
from app.models.schemas.common import ApiResponse, PaginatedResponse
from app.models.schemas.signals import (
    BulkSignalUpdateRequest,
    BulkSignalUpdateResponse,
    SectorListResponse,
    SectorWithSignal,
    SignalChangeLogEntry,
    SignalCreate,
    SignalListResponse,
    SignalResponse,
)
from app.repositories.sector_signals_repo import SectorSignalRepository

logger = structlog.get_logger(__name__)

router = APIRouter()

# The 11 Morningstar sectors used across the platform
# (Morningstar naming convention — matches sector_signals.sector_name)
MORNINGSTAR_SECTORS = [
    "Basic Materials",
    "Communication Services",
    "Consumer Cyclical",
    "Consumer Defensive",
    "Energy",
    "Financial Services",
    "Healthcare",
    "Industrials",
    "Real Estate",
    "Technology",
    "Utilities",
]


@router.get(
    "",
    response_model=ApiResponse[SignalListResponse],
    summary="List active sector signals",
)
@limiter.limit(RATE_READ)
async def list_signals(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SignalListResponse]:
    """Return all currently active FM sector signals, ordered by sector name."""
    try:
        repo = SectorSignalRepository(db)
        signals = await repo.get_active_signals()
        return ApiResponse.ok(
            data=SignalListResponse(signals=[SignalResponse.model_validate(sig) for sig in signals]),
        )
    except Exception as exc:
        logger.error("signals_list_failed", error=str(exc))
        raise AppException(message="Failed to list sector signals", error_code="SIGNAL_LIST_ERROR")


@router.get(
    "/sectors",
    response_model=ApiResponse[SectorListResponse],
    summary="List all 11 GICS sectors with current signal",
)
@limiter.limit(RATE_READ)
async def list_sectors(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SectorListResponse]:
    """
    Return all 11 GICS sectors, each with its current active signal
    (or null fields if no signal has been set for that sector).
    """
    try:
        repo = SectorSignalRepository(db)
        active_signals = await repo.get_active_signals()

        # Build lookup of active signals by sector name
        signal_lookup: dict[str, object] = {}
        for sig in active_signals:
            signal_lookup[sig.sector_name] = sig

        sectors: list[SectorWithSignal] = []
        for sector_name in MORNINGSTAR_SECTORS:
            sig = signal_lookup.get(sector_name)
            if sig is not None:
                sectors.append(SectorWithSignal(
                    sector_name=sector_name,
                    signal=sig.signal,
                    confidence=sig.confidence,
                    signal_weight=sig.signal_weight,
                    notes=sig.notes,
                    effective_date=sig.effective_date,
                    updated_by=sig.updated_by,
                    last_updated=sig.created_at,
                ))
            else:
                sectors.append(SectorWithSignal(sector_name=sector_name))

        return ApiResponse.ok(data=SectorListResponse(sectors=sectors))

    except Exception as exc:
        logger.error("sectors_list_failed", error=str(exc))
        raise AppException(message="Failed to list sectors", error_code="SECTORS_LIST_ERROR")


@router.put(
    "/bulk",
    response_model=ApiResponse[BulkSignalUpdateResponse],
    summary="Bulk update sector signals",
)
@limiter.limit(RATE_MUTATION)
async def bulk_update_signals(
    request: Request,
    body: BulkSignalUpdateRequest,
    _api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[BulkSignalUpdateResponse]:
    """
    Update multiple sector signals at once. For each sector in the request:
    1. If signal/confidence/notes changed, deactivates old and creates new
    2. Logs the change in signal_change_log for audit trail
    3. Unchanged sectors are skipped

    Returns the count of updated vs unchanged sectors.
    """
    try:
        repo = SectorSignalRepository(db)
        updates = [
            {
                "sector_name": entry.sector_name, "signal": entry.signal.value,
                "confidence": entry.confidence.value, "notes": entry.notes,
                "updated_by": body.updated_by, "effective_date": body.effective_date,
                "change_reason": body.change_reason,
            }
            for entry in body.signals
        ]

        created_signals = await repo.bulk_update_signals(updates)
        updated_count = len(created_signals)
        unchanged_count = len(body.signals) - updated_count

        logger.info("signals_bulk_updated", updated=updated_count, unchanged=unchanged_count, updated_by=body.updated_by)
        return ApiResponse.ok(
            data=BulkSignalUpdateResponse(
                updated_count=updated_count, unchanged_count=unchanged_count,
                changes=[SignalResponse.model_validate(sig) for sig in created_signals],
            ),
        )
    except Exception as exc:
        logger.error("signals_bulk_update_failed", error=str(exc))
        raise AppException(message="Failed to bulk update signals", error_code="SIGNAL_BULK_UPDATE_ERROR")


@router.get(
    "/history",
    response_model=PaginatedResponse[SignalChangeLogEntry],
    summary="Signal change audit history",
)
@limiter.limit(RATE_READ)
async def signal_change_history(
    request: Request,
    sector_name: Optional[str] = Query(
        default=None, description="Filter by sector name"
    ),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[SignalChangeLogEntry]:
    """Return paginated signal change history, filterable by sector."""
    try:
        repo = SectorSignalRepository(db)
        rows, total = await repo.get_signal_change_history(
            sector_name=sector_name, page=page, limit=limit,
        )
        items = [SignalChangeLogEntry.model_validate(row) for row in rows]
        return PaginatedResponse.create(items=items, page=page, limit=limit, total=total)
    except Exception as exc:
        logger.error("signal_history_failed", error=str(exc))
        raise AppException(message="Failed to retrieve signal change history", error_code="SIGNAL_HISTORY_ERROR")


@router.post(
    "",
    response_model=ApiResponse[SignalResponse],
    status_code=201,
    summary="Create a sector signal",
)
@limiter.limit(RATE_MUTATION)
async def create_signal(
    request: Request,
    body: SignalCreate,
    _api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SignalResponse]:
    """
    Create a new FM sector signal. Automatically deactivates the
    previous active signal for the same sector.
    """
    try:
        repo = SectorSignalRepository(db)
        new_signal = await repo.create_signal({
            "sector_name": body.sector_name, "signal": body.signal.value,
            "confidence": body.confidence.value,
            "signal_weight": SIGNAL_WEIGHTS.get(body.signal.value, 0.0),
            "effective_date": body.effective_date, "updated_by": body.updated_by,
            "notes": body.notes,
        })
        logger.info("signal_created", sector=body.sector_name, signal=body.signal.value, updated_by=body.updated_by)
        return ApiResponse.ok(data=SignalResponse.model_validate(new_signal))
    except Exception as exc:
        logger.error("signal_create_failed", sector=body.sector_name, error=str(exc))
        raise AppException(message="Failed to create sector signal", error_code="SIGNAL_CREATE_ERROR")


@router.delete(
    "/{signal_id}",
    response_model=ApiResponse[dict],
    summary="Deactivate a sector signal",
)
@limiter.limit(RATE_MUTATION)
async def deactivate_signal(
    request: Request,
    signal_id: UUID,
    _api_key: str = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """Soft-delete a signal by setting is_active=False."""
    try:
        repo = SectorSignalRepository(db)
        deactivated = await repo.deactivate_signal(signal_id)
        if not deactivated:
            raise NotFoundError(
                message=f"Signal {signal_id} not found or already inactive",
                error_code="SIGNAL_NOT_FOUND",
            )
        logger.info("signal_deactivated", signal_id=str(signal_id))
        return ApiResponse.ok(data={"signal_id": str(signal_id), "is_active": False})
    except AppException:
        raise
    except Exception as exc:
        logger.error("signal_deactivate_failed", signal_id=str(signal_id), error=str(exc))
        raise AppException(message="Failed to deactivate signal", error_code="SIGNAL_DEACTIVATE_ERROR")
