"""
repositories/sector_signals_repo.py

Repository for sector_signals and signal_change_log tables.
Handles CRUD for FM signals and audit trail for signal changes.
"""

from __future__ import annotations
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.sector_signals import SectorSignal, SIGNAL_WEIGHTS
from app.models.db.signal_change_log import SignalChangeLog
from app.repositories.base import BaseRepository


class SectorSignalRepository(BaseRepository[SectorSignal]):
    model = SectorSignal

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_active_signals(self) -> list[SectorSignal]:
        result = await self.session.execute(
            select(SectorSignal)
            .where(SectorSignal.is_active.is_(True))
            .order_by(SectorSignal.sector_name)
        )
        return list(result.scalars().all())

    async def get_active_by_sector(
        self, sector_name: str
    ) -> Optional[SectorSignal]:
        result = await self.session.execute(
            select(SectorSignal).where(
                SectorSignal.sector_name == sector_name,
                SectorSignal.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def create_signal(self, data: dict) -> SectorSignal:
        """Create a new signal, deactivating any existing active signal for the same sector."""
        await self.session.execute(
            update(SectorSignal)
            .where(
                SectorSignal.sector_name == data["sector_name"],
                SectorSignal.is_active.is_(True),
            )
            .values(is_active=False)
        )
        new_signal = SectorSignal(**data)
        self.session.add(new_signal)
        await self.session.flush()
        return new_signal

    async def deactivate_signal(self, signal_id: UUID) -> bool:
        result = await self.session.execute(
            update(SectorSignal)
            .where(SectorSignal.id == signal_id)
            .values(is_active=False)
        )
        await self.session.flush()
        return result.rowcount > 0

    async def bulk_update_signals(
        self,
        updates: list[dict[str, Any]],
    ) -> list[SectorSignal]:
        """
        Bulk update FM signals. For each sector in the update list:
        1. Load existing active signal
        2. If signal/confidence/notes changed, deactivate old and create new
        3. Log the change in signal_change_log

        Args:
            updates: list of {sector_name, signal, confidence, notes, updated_by,
                              effective_date, change_reason?}

        Returns:
            List of new/updated SectorSignal objects.
        """
        created_signals: list[SectorSignal] = []

        for entry in updates:
            sector_name = entry["sector_name"]
            new_signal_value = entry["signal"]
            new_confidence = entry.get("confidence", "MEDIUM")
            new_notes = entry.get("notes")
            updated_by = entry["updated_by"]
            effective_date = entry.get("effective_date")
            change_reason = entry.get("change_reason")

            # Load existing active signal for this sector
            existing = await self.get_active_by_sector(sector_name)

            # Check if anything actually changed
            if existing is not None:
                same_signal = existing.signal == new_signal_value
                same_confidence = existing.confidence == new_confidence
                same_notes = (existing.notes or "") == (new_notes or "")

                if same_signal and same_confidence and same_notes:
                    # Nothing changed — skip this sector
                    continue

            # Derive numeric weight from signal
            signal_weight = SIGNAL_WEIGHTS.get(new_signal_value, 0.0)

            # Log the change
            change_log = SignalChangeLog(
                sector_name=sector_name,
                old_signal=existing.signal if existing else None,
                old_confidence=existing.confidence if existing else None,
                old_notes=existing.notes if existing else None,
                new_signal=new_signal_value,
                new_confidence=new_confidence,
                new_notes=new_notes,
                changed_by=updated_by,
                change_reason=change_reason,
            )
            self.session.add(change_log)

            # Deactivate the old signal
            if existing is not None:
                await self.session.execute(
                    update(SectorSignal)
                    .where(SectorSignal.id == existing.id)
                    .values(is_active=False)
                )

            # Create the new signal
            new_signal = SectorSignal(
                sector_name=sector_name,
                signal=new_signal_value,
                confidence=new_confidence,
                signal_weight=signal_weight,
                effective_date=effective_date,
                updated_by=updated_by,
                notes=new_notes,
                is_active=True,
            )
            self.session.add(new_signal)
            created_signals.append(new_signal)

        await self.session.flush()
        return created_signals

    async def get_signal_change_history(
        self,
        sector_name: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[SignalChangeLog], int]:
        """
        Get paginated signal change history.

        Args:
            sector_name: Filter by sector (None = all sectors).
            page: 1-indexed page number.
            limit: Items per page.

        Returns:
            Tuple of (list of change log entries, total count).
        """
        from sqlalchemy import func as sa_func

        base_query = select(SignalChangeLog)
        count_query = select(sa_func.count()).select_from(SignalChangeLog)

        if sector_name:
            base_query = base_query.where(
                SignalChangeLog.sector_name == sector_name
            )
            count_query = count_query.where(
                SignalChangeLog.sector_name == sector_name
            )

        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        base_query = base_query.order_by(SignalChangeLog.changed_at.desc())
        offset = (page - 1) * limit
        base_query = base_query.offset(offset).limit(limit)

        result = await self.session.execute(base_query)
        rows = list(result.scalars().all())

        return rows, total
