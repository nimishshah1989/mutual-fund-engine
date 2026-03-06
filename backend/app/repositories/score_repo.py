"""
repositories/score_repo.py

Facade repository that composes QFS, FSAS, shortlist, recommendation,
and audit sub-repositories. Provides backward-compatible access via
delegation so that existing consumers (scores.py, scoring_service.py)
do not need import changes.

For new code, prefer importing the domain-specific repositories directly:
  - QFSRepository       (qfs_repo.py)
  - FSASRepository      (fsas_repo.py)
  - ShortlistRepository (shortlist_repo.py)
  - RecommendationRepository (recommendation_repo.py)
  - AuditRepository     (audit_repo.py)
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.fund_fsas import FundFSAS
from app.models.db.fund_qfs import FundQFS
from app.models.db.fund_recommendation import FundRecommendation
from app.models.db.fund_shortlist import FundShortlist
from app.models.db.score_audit_log import ScoreAuditLog
from app.repositories.audit_repo import AuditRepository
from app.repositories.fsas_repo import FSASRepository
from app.repositories.qfs_repo import QFSRepository
from app.repositories.recommendation_repo import RecommendationRepository
from app.repositories.shortlist_repo import ShortlistRepository


class ScoreRepository:
    """
    Backward-compatible facade that delegates to domain-specific repositories.

    Sub-repositories are accessible as attributes for direct use:
        repo = ScoreRepository(session)
        repo.qfs.get_qfs_history(mstar_id)

    All original methods are preserved as thin delegates so existing call
    sites (e.g. score_repo.bulk_upsert_qfs(...)) continue to work unchanged.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.qfs = QFSRepository(session)
        self.fsas = FSASRepository(session)
        self.shortlist = ShortlistRepository(session)
        self.recommendation = RecommendationRepository(session)
        self.audit = AuditRepository(session)

    # ===================================================================
    # QFS delegates
    # ===================================================================

    async def upsert_qfs(self, record: dict) -> FundQFS:
        return await self.qfs.upsert_qfs(record)

    async def bulk_upsert_qfs(self, records: list[dict]) -> int:
        return await self.qfs.bulk_upsert_qfs(records)

    async def get_latest_qfs(self, mstar_id: str) -> Optional[FundQFS]:
        return await self.qfs.get_latest_qfs(mstar_id)

    async def get_latest_qfs_by_mstar_ids(
        self, mstar_ids: list[str]
    ) -> list[FundQFS]:
        return await self.qfs.get_latest_qfs_by_mstar_ids(mstar_ids)

    async def get_latest_qfs_by_category(
        self,
        category_name: str,
        mstar_ids: list[str],
        sort_by: str = "qfs",
        sort_desc: bool = True,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[FundQFS], int]:
        return await self.qfs.get_latest_qfs_by_category(
            category_name=category_name,
            mstar_ids=mstar_ids,
            sort_by=sort_by,
            sort_desc=sort_desc,
            page=page,
            limit=limit,
        )

    async def get_qfs_history(
        self, mstar_id: str, limit: int = 12
    ) -> list[FundQFS]:
        return await self.qfs.get_qfs_history(mstar_id, limit=limit)

    # ===================================================================
    # FSAS delegates
    # ===================================================================

    async def upsert_fsas(self, record: dict) -> FundFSAS:
        return await self.fsas.upsert_fsas(record)

    async def bulk_upsert_fsas(self, records: list[dict]) -> int:
        return await self.fsas.bulk_upsert_fsas(records)

    async def get_latest_fsas(self, mstar_id: str) -> Optional[FundFSAS]:
        return await self.fsas.get_latest_fsas(mstar_id)

    async def get_latest_fsas_by_mstar_ids(
        self, mstar_ids: list[str]
    ) -> list[FundFSAS]:
        return await self.fsas.get_latest_fsas_by_mstar_ids(mstar_ids)

    # ===================================================================
    # Shortlist delegates
    # ===================================================================

    async def bulk_upsert_shortlist(self, records: list[dict]) -> int:
        return await self.shortlist.bulk_upsert_shortlist(records)

    async def get_latest_shortlist(self) -> list[FundShortlist]:
        return await self.shortlist.get_latest_shortlist()

    async def get_shortlisted_mstar_ids(self) -> list[str]:
        return await self.shortlist.get_shortlisted_mstar_ids()

    async def clear_shortlist_for_date(self, computed_date: date) -> int:
        return await self.shortlist.clear_shortlist_for_date(computed_date)

    # ===================================================================
    # Recommendation delegates
    # ===================================================================

    async def bulk_upsert_recommendations(self, records: list[dict]) -> int:
        return await self.recommendation.bulk_upsert_recommendations(records)

    async def get_latest_recommendation(
        self, mstar_id: str
    ) -> Optional[FundRecommendation]:
        return await self.recommendation.get_latest_recommendation(mstar_id)

    async def get_latest_recommendations_by_mstar_ids(
        self, mstar_ids: list[str]
    ) -> list[FundRecommendation]:
        return await self.recommendation.get_latest_recommendations_by_mstar_ids(
            mstar_ids
        )

    async def get_latest_shortlisted_recommendations(
        self,
    ) -> list[FundRecommendation]:
        return await self.recommendation.get_latest_shortlisted_recommendations()

    async def get_matrix_summary(self) -> list[dict]:
        return await self.recommendation.get_matrix_summary()

    async def get_funds_by_matrix_position(
        self, position: str,
    ) -> list[FundRecommendation]:
        return await self.recommendation.get_funds_by_matrix_position(position)

    # ===================================================================
    # Audit log delegate
    # ===================================================================

    async def create_audit_log(self, audit_data: dict) -> ScoreAuditLog:
        return await self.audit.create_audit_log(audit_data)
