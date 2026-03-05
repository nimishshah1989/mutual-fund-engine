"""
api/v1/signals.py

CRUD endpoints for Fund Manager sector signals.
Creating a signal automatically deactivates the previous active signal
for the same sector — there is always at most one active signal per sector.
"""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.db.sector_signals import SIGNAL_WEIGHTS
from app.models.schemas.common import ApiResponse
from app.models.schemas.signals import (
    SignalCreate,
    SignalListResponse,
    SignalResponse,
)
from app.repositories.sector_signals_repo import SectorSignalRepository

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=ApiResponse[SignalListResponse],
    summary="List active sector signals",
)
async def list_signals(
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SignalListResponse]:
    """Return all currently active FM sector signals, ordered by sector name."""
    try:
        repo = SectorSignalRepository(db)
        signals = await repo.get_active_signals()

        return ApiResponse.ok(
            data=SignalListResponse(
                signals=[
                    SignalResponse.model_validate(sig) for sig in signals
                ],
            ),
        )

    except Exception as exc:
        logger.error("signals_list_failed", error=str(exc))
        return ApiResponse.fail(
            code="SIGNAL_LIST_ERROR",
            message=f"Failed to list signals: {exc}",
        )


@router.post(
    "",
    response_model=ApiResponse[SignalResponse],
    status_code=201,
    summary="Create a sector signal",
)
async def create_signal(
    body: SignalCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SignalResponse]:
    """
    Create a new FM sector signal. If an active signal already exists
    for the same sector, it is automatically deactivated (archived).
    The signal_weight is derived from the signal enum value.
    """
    try:
        # Derive numeric weight from the signal enum
        signal_weight = SIGNAL_WEIGHTS.get(body.signal.value, 0.0)

        repo = SectorSignalRepository(db)
        new_signal = await repo.create_signal({
            "sector_name": body.sector_name,
            "signal": body.signal.value,
            "confidence": body.confidence.value,
            "signal_weight": signal_weight,
            "effective_date": body.effective_date,
            "updated_by": body.updated_by,
            "notes": body.notes,
        })

        logger.info(
            "signal_created",
            sector=body.sector_name,
            signal=body.signal.value,
            updated_by=body.updated_by,
        )

        return ApiResponse.ok(
            data=SignalResponse.model_validate(new_signal),
        )

    except Exception as exc:
        logger.error(
            "signal_create_failed",
            sector=body.sector_name,
            error=str(exc),
        )
        return ApiResponse.fail(
            code="SIGNAL_CREATE_ERROR",
            message=f"Failed to create signal: {exc}",
        )


@router.delete(
    "/{signal_id}",
    response_model=ApiResponse[dict],
    summary="Deactivate a sector signal",
)
async def deactivate_signal(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """
    Soft-delete a signal by setting is_active=False.
    Signals are never hard-deleted — they remain as audit history.
    """
    try:
        repo = SectorSignalRepository(db)
        deactivated = await repo.deactivate_signal(signal_id)

        if not deactivated:
            return ApiResponse.fail(
                code="SIGNAL_NOT_FOUND",
                message=f"Signal {signal_id} not found or already inactive",
            )

        logger.info("signal_deactivated", signal_id=str(signal_id))

        return ApiResponse.ok(
            data={"signal_id": str(signal_id), "is_active": False},
        )

    except Exception as exc:
        logger.error(
            "signal_deactivate_failed",
            signal_id=str(signal_id),
            error=str(exc),
        )
        return ApiResponse.fail(
            code="SIGNAL_DEACTIVATE_ERROR",
            message=f"Failed to deactivate signal: {exc}",
        )
