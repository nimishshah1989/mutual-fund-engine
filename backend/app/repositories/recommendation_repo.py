"""
repositories/recommendation_repo.py

Repository for the fund_recommendation table. Handles upsert
(INSERT ... ON CONFLICT) and retrieval of recommendation records
(tier, action, QFS rank, percentile).
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.fund_recommendation import FundRecommendation
from app.repositories.base import BaseRepository


class RecommendationRepository(BaseRepository[FundRecommendation]):
    """Repository for recommendation persistence and retrieval."""

    model = FundRecommendation

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def bulk_upsert_recommendations(self, records: list[dict]) -> int:
        """Bulk upsert recommendation records. Returns the number of rows affected."""
        if not records:
            return 0

        update_keys = [
            k for k in records[0] if k not in ("mstar_id", "computed_date")
        ]
        stmt = pg_insert(FundRecommendation).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_recommendation_mstar_date",
            set_={key: stmt.excluded[key] for key in update_keys},
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def get_latest_recommendation(
        self, mstar_id: str
    ) -> Optional[FundRecommendation]:
        """Get the most recent recommendation for a specific fund."""
        result = await self.session.execute(
            select(FundRecommendation)
            .where(FundRecommendation.mstar_id == mstar_id)
            .order_by(FundRecommendation.computed_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_recommendations_by_mstar_ids(
        self, mstar_ids: list[str]
    ) -> list[FundRecommendation]:
        """Get the latest recommendation for each fund in the list."""
        if not mstar_ids:
            return []

        latest_date_subq = (
            select(
                FundRecommendation.mstar_id,
                func.max(FundRecommendation.computed_date).label("max_date"),
            )
            .where(FundRecommendation.mstar_id.in_(mstar_ids))
            .group_by(FundRecommendation.mstar_id)
            .subquery()
        )

        result = await self.session.execute(
            select(FundRecommendation).join(
                latest_date_subq,
                (FundRecommendation.mstar_id == latest_date_subq.c.mstar_id)
                & (FundRecommendation.computed_date == latest_date_subq.c.max_date),
            )
        )
        return list(result.scalars().all())

    async def get_latest_shortlisted_recommendations(
        self,
    ) -> list[FundRecommendation]:
        """Get recommendations for all currently shortlisted funds."""
        latest_date_subq = (
            select(
                FundRecommendation.mstar_id,
                func.max(FundRecommendation.computed_date).label("max_date"),
            )
            .where(FundRecommendation.is_shortlisted.is_(True))
            .group_by(FundRecommendation.mstar_id)
            .subquery()
        )

        result = await self.session.execute(
            select(FundRecommendation)
            .join(
                latest_date_subq,
                (FundRecommendation.mstar_id == latest_date_subq.c.mstar_id)
                & (FundRecommendation.computed_date == latest_date_subq.c.max_date),
            )
            .order_by(FundRecommendation.tier, FundRecommendation.qfs.desc())
        )
        return list(result.scalars().all())
