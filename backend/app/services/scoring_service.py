"""
services/scoring_service.py

Orchestrator for the scoring pipeline:
    1. QFS  — compute quantitative scores for all eligible funds
    2. FMS  — FM alignment scoring for ALL funds (v3 — no shortlist)
    3. Matrix — 3x3 decision matrix classification
    4. Recommend — tiers and actions from matrix + overrides

Data loading: scoring_data_loader.py (ScoringDataLoader)
FMS computation: fsas_scoring.py (FSASScorer)
Pipeline + recommendations: scoring_pipeline.py (ScoringPipeline)
Benchmark management: benchmark_service.py (BenchmarkService)
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.fsas_engine import FSASEngine
from app.engines.matrix_engine import MatrixEngine
from app.engines.qfs_engine import QFSEngine
from app.engines.tier_engine import TierEngine
from app.repositories.score_repo import ScoreRepository
from app.services.benchmark_service import BenchmarkService
from app.services.fsas_scoring import FSASScorer
from app.services.scoring_data_loader import ScoringDataLoader
from app.services.scoring_pipeline import ScoringPipeline

logger = structlog.get_logger(__name__)

# Default: top 5 funds per category (legacy — not used in v3 pipeline)
DEFAULT_SHORTLIST_N = 5


class ScoringService:
    """Orchestrates QFS, FMS, benchmark, matrix, and recommendation scoring."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.score_repo = ScoreRepository(session)
        self.qfs_engine = QFSEngine()
        self.fsas_engine = FSASEngine()
        self.tier_engine = TierEngine()
        self.data_loader = ScoringDataLoader(session, self.score_repo)
        self._fsas_scorer = FSASScorer(self.score_repo, self.data_loader, self.fsas_engine)
        self._pipeline = ScoringPipeline(self)
        self._benchmark_service = BenchmarkService(session)

        # Initialize matrix engine — load thresholds from config if available
        self.matrix_engine = MatrixEngine()

    async def _load_matrix_thresholds(self) -> None:
        """Load matrix tercile thresholds from engine_config if available."""
        config = await self.data_loader.load_engine_config("matrix_thresholds")
        if config and isinstance(config, dict):
            low_upper = config.get("low_upper", 33.33)
            high_lower = config.get("high_lower", 66.67)
            self.matrix_engine = MatrixEngine(
                low_upper=float(low_upper),
                high_lower=float(high_lower),
            )

    # ===================================================================
    # Benchmark management
    # ===================================================================

    async def ensure_benchmark_weights(self) -> dict[str, float]:
        """
        Get benchmark weights, auto-refreshing if stale.
        Reads benchmark_mstar_id and benchmark_name from engine_config.
        """
        mstar_id_config = await self.data_loader.load_engine_config("benchmark_mstar_id")
        name_config = await self.data_loader.load_engine_config("benchmark_name")
        stale_config = await self.data_loader.load_engine_config("benchmark_stale_days")

        benchmark_mstar_id = (
            mstar_id_config.get("value", "F00000VBPN") if mstar_id_config else "F00000VBPN"
        )
        benchmark_name = (
            name_config.get("value", "NIFTY 50") if name_config else "NIFTY 50"
        )
        max_age_days = int(
            stale_config.get("value", 45) if stale_config else 45
        )

        return await self._benchmark_service.ensure_fresh_weights(
            benchmark_mstar_id=benchmark_mstar_id,
            benchmark_name=benchmark_name,
            max_age_days=max_age_days,
        )

    async def refresh_benchmark(self) -> dict[str, Any]:
        """Force-refresh benchmark weights from Morningstar."""
        mstar_id_config = await self.data_loader.load_engine_config("benchmark_mstar_id")
        name_config = await self.data_loader.load_engine_config("benchmark_name")

        benchmark_mstar_id = (
            mstar_id_config.get("value", "F00000VBPN") if mstar_id_config else "F00000VBPN"
        )
        benchmark_name = (
            name_config.get("value", "NIFTY 50") if name_config else "NIFTY 50"
        )

        return await self._benchmark_service.refresh_benchmark_weights(
            benchmark_mstar_id=benchmark_mstar_id,
            benchmark_name=benchmark_name,
        )

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
    # Shortlist generation (Legacy — kept for backward compat)
    # ===================================================================

    async def generate_shortlist(
        self,
        shortlist_n: int = DEFAULT_SHORTLIST_N,
        trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """
        DEPRECATED: Generate shortlist. In v3, shortlist is not used.
        Kept for backward compat — returns empty summary.
        """
        logger.warning("generate_shortlist_deprecated", trigger=trigger_event)
        return {
            "total_shortlisted": 0,
            "categories": 0,
            "category_counts": {},
            "computed_date": str(date.today()),
            "status": "deprecated",
            "note": "Shortlist is deprecated in v3 Decision Matrix pipeline.",
        }

    # ===================================================================
    # FMS (Layer 2) — delegated to FSASScorer
    # ===================================================================

    async def compute_fms_for_all_funds(
        self,
        benchmark_weights: Optional[dict[str, float]] = None,
        trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """Compute FMS for ALL eligible funds (v3 default)."""
        return await self._fsas_scorer.compute_for_all_funds(
            benchmark_weights=benchmark_weights,
            trigger_event=trigger_event,
        )

    async def compute_fsas_for_shortlisted(
        self, trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """Legacy: Compute FMS for shortlisted funds only."""
        benchmark_weights = await self.ensure_benchmark_weights()
        return await self._fsas_scorer.compute_for_shortlisted(
            benchmark_weights=benchmark_weights,
            trigger_event=trigger_event,
        )

    async def compute_fsas_for_category(
        self, category_name: str, trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """Compute FMS for all eligible funds in one category."""
        benchmark_weights = await self.ensure_benchmark_weights()
        return await self._fsas_scorer.compute_for_category(
            category_name=category_name,
            benchmark_weights=benchmark_weights,
            trigger_event=trigger_event,
        )

    async def compute_fsas_for_all_categories(
        self, trigger_event: str = "scheduled_recompute",
    ) -> list[dict[str, Any]]:
        """Compute FMS for every category with eligible funds."""
        benchmark_weights = await self.ensure_benchmark_weights()
        return await self._fsas_scorer.compute_for_all_categories(
            benchmark_weights=benchmark_weights,
            trigger_event=trigger_event,
        )

    # ===================================================================
    # Pipeline + Recommendations — delegated to ScoringPipeline
    # ===================================================================

    async def assign_recommendations(
        self, trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """Assign tiers and actions via 3x3 matrix."""
        await self._load_matrix_thresholds()
        return await self._pipeline.assign_matrix_recommendations(
            trigger_event=trigger_event,
        )

    async def compute_full_pipeline(
        self,
        category_name: Optional[str] = None,
        trigger_event: str = "full_pipeline",
        shortlist_n: Optional[int] = None,
    ) -> dict[str, Any]:
        """Run QFS -> FMS -> Matrix -> Recommend pipeline."""
        await self._load_matrix_thresholds()
        return await self._pipeline.compute_full_pipeline(
            category_name=category_name,
            trigger_event=trigger_event,
            shortlist_n=shortlist_n or DEFAULT_SHORTLIST_N,
        )

    async def compute_full_pipeline_all_categories(
        self, trigger_event: str = "scheduled_full_pipeline",
    ) -> list[dict[str, Any]]:
        """Run the complete pipeline for all categories."""
        await self._load_matrix_thresholds()
        return await self._pipeline.compute_full_pipeline_all_categories(
            trigger_event=trigger_event,
        )
