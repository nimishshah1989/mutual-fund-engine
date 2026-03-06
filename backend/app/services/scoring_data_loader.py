"""
services/scoring_data_loader.py

Data loading and persistence helpers for the scoring pipeline.

Contains:
  - ScoringDataLoader: async methods to load fund data from the database
  - Audit log creation for score change tracking
  - orm_to_dict: utility to convert SQLAlchemy ORM rows to plain dicts
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

import structlog
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.fund_master import FundMaster
from app.models.db.fund_performance import FundPerformance
from app.models.db.fund_risk_stats import FundRiskStats
from app.models.db.fund_sector_exposure import FundSectorExposure
from app.models.db.sector_signals import SectorSignal
from app.repositories.score_repo import ScoreRepository

logger = structlog.get_logger(__name__)


def orm_to_dict(obj: Any) -> dict[str, Any]:
    """Convert an SQLAlchemy ORM instance to a plain dict (Decimal -> float)."""
    result: dict[str, Any] = {}
    for column in obj.__table__.columns:
        val = getattr(obj, column.name)
        if isinstance(val, Decimal):
            val = float(val)
        result[column.name] = val
    return result


class ScoringDataLoader:
    """Handles all database reads and audit writes for the scoring pipeline."""

    def __init__(self, session: AsyncSession, score_repo: ScoreRepository) -> None:
        self.session = session
        self.score_repo = score_repo

    async def load_eligible_fund_ids(self, category_name: str) -> list[str]:
        """Load mstar_ids of all eligible, non-deleted funds in a category."""
        result = await self.session.execute(
            select(FundMaster.mstar_id).where(
                FundMaster.category_name == category_name,
                FundMaster.is_eligible.is_(True),
                FundMaster.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def get_eligible_categories(self) -> list[str]:
        """Get all distinct category names that have eligible, non-deleted funds."""
        result = await self.session.execute(
            select(FundMaster.category_name)
            .where(FundMaster.is_eligible.is_(True), FundMaster.deleted_at.is_(None))
            .distinct()
            .order_by(FundMaster.category_name)
        )
        return list(result.scalars().all())

    async def load_latest_risk_stats(
        self, fund_ids: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Load the LATEST risk stats for each fund (by month_end_date)."""
        if not fund_ids:
            return {}

        latest_subq = (
            select(
                FundRiskStats.mstar_id,
                sa_func.max(FundRiskStats.month_end_date).label("max_date"),
            )
            .where(FundRiskStats.mstar_id.in_(fund_ids))
            .group_by(FundRiskStats.mstar_id)
            .subquery()
        )
        result = await self.session.execute(
            select(FundRiskStats).join(
                latest_subq,
                (FundRiskStats.mstar_id == latest_subq.c.mstar_id)
                & (FundRiskStats.month_end_date == latest_subq.c.max_date),
            )
        )
        return {row.mstar_id: orm_to_dict(row) for row in result.scalars().all()}

    async def load_latest_performance(
        self, fund_ids: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Load the LATEST performance data for each fund (by nav_date)."""
        if not fund_ids:
            return {}

        latest_subq = (
            select(
                FundPerformance.mstar_id,
                sa_func.max(FundPerformance.nav_date).label("max_date"),
            )
            .where(FundPerformance.mstar_id.in_(fund_ids))
            .group_by(FundPerformance.mstar_id)
            .subquery()
        )
        result = await self.session.execute(
            select(FundPerformance).join(
                latest_subq,
                (FundPerformance.mstar_id == latest_subq.c.mstar_id)
                & (FundPerformance.nav_date == latest_subq.c.max_date),
            )
        )
        return {row.mstar_id: orm_to_dict(row) for row in result.scalars().all()}

    async def load_latest_sector_exposures(
        self, fund_ids: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        """Load the latest sector exposure data for each fund."""
        if not fund_ids:
            return {}

        latest_subq = (
            select(
                FundSectorExposure.mstar_id,
                sa_func.max(FundSectorExposure.month_end_date).label("max_date"),
            )
            .where(FundSectorExposure.mstar_id.in_(fund_ids))
            .group_by(FundSectorExposure.mstar_id)
            .subquery()
        )
        result = await self.session.execute(
            select(FundSectorExposure).join(
                latest_subq,
                (FundSectorExposure.mstar_id == latest_subq.c.mstar_id)
                & (FundSectorExposure.month_end_date == latest_subq.c.max_date),
            )
        )

        exposures: dict[str, list[dict[str, Any]]] = {}
        for row in result.scalars().all():
            exposures.setdefault(row.mstar_id, []).append({
                "sector_name": row.sector_name,
                "exposure_pct": float(row.exposure_pct) if row.exposure_pct is not None else 0.0,
                "month_end_date": row.month_end_date,
            })

        # Ensure every requested fund has an entry (empty list if no data)
        for fund_id in fund_ids:
            exposures.setdefault(fund_id, [])
        return exposures

    async def load_active_signals(self) -> list[dict[str, Any]]:
        """Load all currently active FM sector signals."""
        result = await self.session.execute(
            select(SectorSignal)
            .where(SectorSignal.is_active.is_(True))
            .order_by(SectorSignal.sector_name)
        )
        return [
            {
                "sector_name": row.sector_name,
                "signal": row.signal,
                "signal_weight": float(row.signal_weight) if row.signal_weight is not None else 0.0,
                "confidence": row.confidence,
                "effective_date": row.effective_date,
            }
            for row in result.scalars().all()
        ]

    async def load_fund_metadata(self, fund_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Load fund master metadata needed for override checks."""
        if not fund_ids:
            return {}
        result = await self.session.execute(
            select(FundMaster).where(FundMaster.mstar_id.in_(fund_ids))
        )
        return {
            row.mstar_id: {
                "inception_date": row.inception_date,
                "legal_name": row.legal_name,
                "category_name": row.category_name,
            }
            for row in result.scalars().all()
        }

    async def load_old_qfs_values(self, fund_ids: list[str]) -> dict[str, Optional[float]]:
        """Load previous QFS scores for audit delta tracking."""
        if not fund_ids:
            return {}
        records = await self.score_repo.get_latest_qfs_by_mstar_ids(fund_ids)
        old_values: dict[str, Optional[float]] = {mid: None for mid in fund_ids}
        for rec in records:
            old_values[rec.mstar_id] = float(rec.qfs) if rec.qfs is not None else None
        return old_values

    async def load_old_fsas_values(self, fund_ids: list[str]) -> dict[str, Optional[float]]:
        """Load previous FSAS scores for audit delta tracking."""
        if not fund_ids:
            return {}
        records = await self.score_repo.get_latest_fsas_by_mstar_ids(fund_ids)
        old_values: dict[str, Optional[float]] = {mid: None for mid in fund_ids}
        for rec in records:
            old_values[rec.mstar_id] = float(rec.fsas) if rec.fsas is not None else None
        return old_values

    async def create_audit_logs(
        self,
        results: list[dict[str, Any]],
        old_values_by_fund: dict[str, Optional[float]],
        trigger_event: str,
        computation_type: str,
        score_key: str,
    ) -> int:
        """Create audit log entries for funds whose score changed."""
        audit_count = 0
        for result in results:
            mstar_id = result["mstar_id"]
            new_value = result[score_key]
            old_value = old_values_by_fund.get(mstar_id)

            if old_value is None or abs(float(new_value) - float(old_value)) > 0.001:
                await self.score_repo.create_audit_log({
                    "mstar_id": mstar_id,
                    "computation_type": computation_type,
                    "old_value": old_value,
                    "new_value": new_value,
                    "trigger_event": trigger_event,
                    "computed_by": "system",
                })
                audit_count += 1
        return audit_count
