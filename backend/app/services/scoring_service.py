"""
services/scoring_service.py

Orchestrator for the scoring pipeline:
    1. QFS  — compute quantitative scores for all eligible funds
    2. Shortlist — top N per category by QFS rank
    3. FSAS — sector alignment scoring (delegated to fsas_scoring.py)
    4. Recommend — tiers and actions (delegated to scoring_pipeline.py)

Data loading: scoring_data_loader.py (ScoringDataLoader)
FSAS computation: fsas_scoring.py (FSASScorer)
Pipeline + recommendations: scoring_pipeline.py (ScoringPipeline)
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.fsas_engine import FSASEngine
from app.engines.qfs_engine import QFSEngine
from app.engines.tier_engine import TierEngine
from app.repositories.score_repo import ScoreRepository
from app.services.fsas_scoring import FSASScorer
from app.services.scoring_data_loader import ScoringDataLoader
from app.services.scoring_pipeline import ScoringPipeline

logger = structlog.get_logger(__name__)

# Default: top 5 funds per category are shortlisted
# TODO: move to engine_config table
DEFAULT_SHORTLIST_N = 5


class ScoringService:
    """Orchestrates QFS, shortlist, FSAS, and recommendation scoring."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.score_repo = ScoreRepository(session)
        self.qfs_engine = QFSEngine()
        self.fsas_engine = FSASEngine()
        self.tier_engine = TierEngine()
        self.data_loader = ScoringDataLoader(session, self.score_repo)
        self._fsas_scorer = FSASScorer(self.score_repo, self.data_loader, self.fsas_engine)
        self._pipeline = ScoringPipeline(self)

    # ===================================================================
    # QFS computation (Layer 1)
    # ===================================================================

    async def compute_qfs_for_category(
        self, category_name: str, trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """Compute QFS for all eligible funds in a single category."""
        logger.info("scoring_service_start", category=category_name, trigger=trigger_event)

        fund_ids = await self.data_loader.load_eligible_fund_ids(category_name)
        if not fund_ids:
            logger.warning("scoring_no_eligible_funds", category=category_name)
            return {
                "category": category_name, "fund_count": 0,
                "computed_date": str(date.today()), "status": "skipped",
                "reason": "no_eligible_funds",
            }

        risk_stats_by_fund = await self.data_loader.load_latest_risk_stats(fund_ids)
        performance_by_fund = await self.data_loader.load_latest_performance(fund_ids)

        results = self.qfs_engine.compute(
            fund_ids=fund_ids,
            risk_stats_by_fund=risk_stats_by_fund,
            performance_by_fund=performance_by_fund,
            category_name=category_name,
        )

        if not results:
            logger.warning("scoring_no_results", category=category_name)
            return {
                "category": category_name, "fund_count": 0,
                "computed_date": str(date.today()), "status": "no_results",
            }

        old_qfs = await self.data_loader.load_old_qfs_values(fund_ids)
        rows_affected = await self.score_repo.bulk_upsert_qfs(results)

        audit_count = await self.data_loader.create_audit_logs(
            results=results, old_values_by_fund=old_qfs,
            trigger_event=trigger_event, computation_type="QFS", score_key="qfs",
        )

        logger.info(
            "scoring_service_complete", category=category_name,
            fund_count=len(results), rows_upserted=rows_affected, audits_created=audit_count,
        )
        return {
            "category": category_name, "fund_count": len(results),
            "rows_upserted": rows_affected, "audits_created": audit_count,
            "computed_date": str(date.today()), "status": "completed",
        }

    async def compute_qfs_for_all_categories(
        self, trigger_event: str = "scheduled_recompute",
    ) -> list[dict[str, Any]]:
        """Compute QFS for every category that has eligible funds."""
        logger.info("scoring_all_categories_start", trigger=trigger_event)
        categories = await self.data_loader.get_eligible_categories()
        logger.info("scoring_categories_found", count=len(categories))

        results: list[dict[str, Any]] = []
        for category_name in categories:
            try:
                summary = await self.compute_qfs_for_category(
                    category_name=category_name, trigger_event=trigger_event,
                )
                results.append(summary)
            except Exception as exc:
                logger.error("scoring_category_failed", category=category_name, error=str(exc))
                results.append({"category": category_name, "status": "error", "error": str(exc)})

        total_funds = sum(r.get("fund_count", 0) for r in results)
        logger.info(
            "scoring_all_categories_complete",
            categories_processed=len(results), total_funds=total_funds,
        )
        return results

    # ===================================================================
    # Shortlist generation (Layer 2a)
    # ===================================================================

    async def generate_shortlist(
        self,
        shortlist_n: int = DEFAULT_SHORTLIST_N,
        trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """Generate the shortlist: top N funds per category by QFS rank."""
        today = date.today()
        logger.info("shortlist_generation_start", n=shortlist_n, date=str(today))

        categories = await self.data_loader.get_eligible_categories()
        total_shortlisted = 0
        category_counts: dict[str, int] = {}

        await self.score_repo.clear_shortlist_for_date(today)

        for category_name in categories:
            fund_ids = await self.data_loader.load_eligible_fund_ids(category_name)
            if not fund_ids:
                continue

            qfs_records = await self.score_repo.get_latest_qfs_by_mstar_ids(fund_ids)
            if not qfs_records:
                continue

            sorted_records = sorted(
                qfs_records,
                key=lambda r: float(r.qfs) if r.qfs is not None else 0.0,
                reverse=True,
            )
            total_in_category = len(sorted_records)
            top_n = sorted_records[:shortlist_n]

            MIN_SHORTLIST_PERCENTILE = 40.0
            shortlist_records = []
            for rank, record in enumerate(top_n, start=1):
                if total_in_category > 1:
                    percentile = (total_in_category - rank) / (total_in_category - 1) * 100.0
                    # Compress to [20, 80] for tiny categories — prevents extreme
                    # tier assignments from minimal peer differences
                    if total_in_category < 5:
                        percentile = 20.0 + (percentile / 100.0) * 60.0
                else:
                    percentile = 50.0

                if percentile < MIN_SHORTLIST_PERCENTILE:
                    continue

                shortlist_records.append({
                    "mstar_id": record.mstar_id,
                    "category_name": category_name,
                    "qfs_score": float(record.qfs) if record.qfs is not None else 0.0,
                    "qfs_rank": rank,
                    "total_in_category": total_in_category,
                    "shortlist_reason": "top_n_by_qfs",
                    "computed_date": today,
                })

            if shortlist_records:
                await self.score_repo.bulk_upsert_shortlist(shortlist_records)
                total_shortlisted += len(shortlist_records)
                category_counts[category_name] = len(shortlist_records)

        logger.info(
            "shortlist_generation_complete",
            total_shortlisted=total_shortlisted, categories=len(category_counts),
        )
        return {
            "total_shortlisted": total_shortlisted,
            "categories": len(category_counts),
            "category_counts": category_counts,
            "computed_date": str(today),
            "status": "completed",
        }

    # ===================================================================
    # FSAS (Layer 2b) — delegated to FSASScorer
    # ===================================================================

    async def compute_fsas_for_shortlisted(
        self, trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """Compute FSAS for shortlisted funds only."""
        return await self._fsas_scorer.compute_for_shortlisted(trigger_event=trigger_event)

    async def compute_fsas_for_category(
        self, category_name: str, trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """Compute FSAS for all eligible funds in one category."""
        return await self._fsas_scorer.compute_for_category(
            category_name=category_name, trigger_event=trigger_event,
        )

    async def compute_fsas_for_all_categories(
        self, trigger_event: str = "scheduled_recompute",
    ) -> list[dict[str, Any]]:
        """Compute FSAS for every category with eligible funds."""
        return await self._fsas_scorer.compute_for_all_categories(trigger_event=trigger_event)

    # ===================================================================
    # Pipeline + Recommendations — delegated to ScoringPipeline
    # ===================================================================

    async def assign_recommendations(
        self, trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """Assign tiers and actions based on QFS percentile rank."""
        return await self._pipeline.assign_recommendations(trigger_event=trigger_event)

    async def compute_full_pipeline(
        self,
        category_name: Optional[str] = None,
        trigger_event: str = "full_pipeline",
        shortlist_n: Optional[int] = None,
    ) -> dict[str, Any]:
        """Run QFS -> shortlist -> FSAS -> recommend pipeline."""
        return await self._pipeline.compute_full_pipeline(
            category_name=category_name,
            trigger_event=trigger_event,
            shortlist_n=shortlist_n or DEFAULT_SHORTLIST_N,
        )

    async def compute_full_pipeline_all_categories(
        self, trigger_event: str = "scheduled_full_pipeline",
    ) -> list[dict[str, Any]]:
        """Run the complete pipeline for all categories."""
        return await self._pipeline.compute_full_pipeline_all_categories(
            trigger_event=trigger_event,
        )
