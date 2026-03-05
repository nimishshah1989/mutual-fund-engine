"""
services/scoring_service.py

Orchestrator for the scoring pipeline (v2):
    1. QFS — compute quantitative scores for all eligible funds
    2. Shortlist — top N per category by QFS rank
    3. FSAS — sector alignment scoring for shortlisted funds ONLY
    4. Recommend — assign tiers (QFS percentile) and actions (tier + FSAS)

No more blended CRS score. QFS and FSAS are displayed separately.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.fsas_engine import FSASEngine
from app.engines.qfs_engine import QFSEngine
from app.engines.tier_engine import TierEngine
from app.models.db.fund_master import FundMaster
from app.models.db.fund_performance import FundPerformance
from app.models.db.fund_risk_stats import FundRiskStats
from app.models.db.fund_sector_exposure import FundSectorExposure
from app.models.db.sector_signals import SectorSignal
from app.repositories.score_repo import ScoreRepository

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

    # ===================================================================
    # QFS computation (Layer 1 — unchanged)
    # ===================================================================

    async def compute_qfs_for_category(
        self,
        category_name: str,
        trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """Compute QFS for all eligible funds in a single category."""
        logger.info("scoring_service_start", category=category_name, trigger=trigger_event)

        fund_ids = await self._load_eligible_fund_ids(category_name)
        if not fund_ids:
            logger.warning("scoring_no_eligible_funds", category=category_name)
            return {
                "category": category_name,
                "fund_count": 0,
                "computed_date": str(date.today()),
                "status": "skipped",
                "reason": "no_eligible_funds",
            }

        risk_stats_by_fund = await self._load_latest_risk_stats(fund_ids)
        performance_by_fund = await self._load_latest_performance(fund_ids)

        results = self.qfs_engine.compute(
            fund_ids=fund_ids,
            risk_stats_by_fund=risk_stats_by_fund,
            performance_by_fund=performance_by_fund,
            category_name=category_name,
        )

        if not results:
            logger.warning("scoring_no_results", category=category_name)
            return {
                "category": category_name,
                "fund_count": 0,
                "computed_date": str(date.today()),
                "status": "no_results",
            }

        old_qfs_by_fund = await self._load_old_qfs_values(fund_ids)
        rows_affected = await self.score_repo.bulk_upsert_qfs(results)

        audit_count = await self._create_audit_logs(
            results=results,
            old_values_by_fund=old_qfs_by_fund,
            trigger_event=trigger_event,
            computation_type="QFS",
            score_key="qfs",
        )

        logger.info(
            "scoring_service_complete",
            category=category_name,
            fund_count=len(results),
            rows_upserted=rows_affected,
            audits_created=audit_count,
        )

        return {
            "category": category_name,
            "fund_count": len(results),
            "rows_upserted": rows_affected,
            "audits_created": audit_count,
            "computed_date": str(date.today()),
            "status": "completed",
        }

    async def compute_qfs_for_all_categories(
        self,
        trigger_event: str = "scheduled_recompute",
    ) -> list[dict[str, Any]]:
        """Compute QFS for every category that has eligible funds."""
        logger.info("scoring_all_categories_start", trigger=trigger_event)

        categories = await self._get_eligible_categories()
        logger.info("scoring_categories_found", count=len(categories))

        results: list[dict[str, Any]] = []
        for category_name in categories:
            try:
                summary = await self.compute_qfs_for_category(
                    category_name=category_name,
                    trigger_event=trigger_event,
                )
                results.append(summary)
            except Exception as exc:
                logger.error(
                    "scoring_category_failed",
                    category=category_name,
                    error=str(exc),
                )
                results.append({
                    "category": category_name,
                    "status": "error",
                    "error": str(exc),
                })

        total_funds = sum(r.get("fund_count", 0) for r in results)
        logger.info(
            "scoring_all_categories_complete",
            categories_processed=len(results),
            total_funds=total_funds,
        )

        return results

    # ===================================================================
    # Shortlist generation (NEW — Layer 2a)
    # ===================================================================

    async def generate_shortlist(
        self,
        shortlist_n: int = DEFAULT_SHORTLIST_N,
        trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """
        Generate the shortlist: top N funds per category by QFS rank.
        Clears and rebuilds the shortlist for today's date.

        Returns:
            Summary with total shortlisted, per-category counts.
        """
        today = date.today()
        logger.info("shortlist_generation_start", n=shortlist_n, date=str(today))

        categories = await self._get_eligible_categories()
        total_shortlisted = 0
        category_counts: dict[str, int] = {}

        # Clear existing shortlist for today (idempotent rebuild)
        await self.score_repo.clear_shortlist_for_date(today)

        for category_name in categories:
            fund_ids = await self._load_eligible_fund_ids(category_name)
            if not fund_ids:
                continue

            # Get latest QFS scores for this category
            qfs_records = await self.score_repo.get_latest_qfs_by_mstar_ids(fund_ids)
            if not qfs_records:
                continue

            # Sort by QFS descending
            sorted_records = sorted(
                qfs_records,
                key=lambda r: float(r.qfs) if r.qfs is not None else 0.0,
                reverse=True,
            )

            total_in_category = len(sorted_records)
            top_n = sorted_records[:shortlist_n]

            shortlist_records = []
            for rank, record in enumerate(top_n, start=1):
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
            total_shortlisted=total_shortlisted,
            categories=len(category_counts),
        )

        return {
            "total_shortlisted": total_shortlisted,
            "categories": len(category_counts),
            "category_counts": category_counts,
            "computed_date": str(today),
            "status": "completed",
        }

    # ===================================================================
    # FSAS computation (Layer 2b — only for shortlisted funds)
    # ===================================================================

    async def compute_fsas_for_shortlisted(
        self,
        trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """
        Compute FSAS for shortlisted funds ONLY (not all funds).
        Groups shortlisted funds by category and computes per-category FSAS.
        """
        logger.info("fsas_shortlisted_start", trigger=trigger_event)

        shortlisted_mstar_ids = await self.score_repo.get_shortlisted_mstar_ids()
        if not shortlisted_mstar_ids:
            logger.warning("fsas_no_shortlisted_funds")
            return {
                "fund_count": 0,
                "status": "skipped",
                "reason": "no_shortlisted_funds",
            }

        # Load sector exposures for all shortlisted funds at once
        fund_exposures = await self._load_latest_sector_exposures(shortlisted_mstar_ids)

        # Load active FM signals
        active_signals = await self._load_active_signals()
        if not active_signals:
            logger.warning("fsas_no_active_signals")
            return {
                "fund_count": 0,
                "status": "skipped",
                "reason": "no_active_signals",
            }

        # Run the FSAS engine on all shortlisted funds at once
        results = self.fsas_engine.compute(
            fund_exposures=fund_exposures,
            active_signals=active_signals,
        )

        if not results:
            return {
                "fund_count": 0,
                "status": "no_results",
            }

        # Load old FSAS values for audit logging
        old_fsas_by_fund = await self._load_old_fsas_values(shortlisted_mstar_ids)

        rows_affected = await self.score_repo.bulk_upsert_fsas(results)

        audit_count = await self._create_audit_logs(
            results=results,
            old_values_by_fund=old_fsas_by_fund,
            trigger_event=trigger_event,
            computation_type="FSAS",
            score_key="fsas",
        )

        logger.info(
            "fsas_shortlisted_complete",
            fund_count=len(results),
            rows_upserted=rows_affected,
            audits_created=audit_count,
        )

        return {
            "fund_count": len(results),
            "rows_upserted": rows_affected,
            "audits_created": audit_count,
            "computed_date": str(date.today()),
            "status": "completed",
        }

    async def compute_fsas_for_category(
        self,
        category_name: str,
        trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """Compute FSAS for all eligible funds in a single category (legacy support)."""
        logger.info("fsas_service_start", category=category_name, trigger=trigger_event)

        fund_ids = await self._load_eligible_fund_ids(category_name)
        if not fund_ids:
            return {
                "category": category_name,
                "fund_count": 0,
                "computed_date": str(date.today()),
                "status": "skipped",
                "reason": "no_eligible_funds",
            }

        fund_exposures = await self._load_latest_sector_exposures(fund_ids)
        active_signals = await self._load_active_signals()

        if not active_signals:
            return {
                "category": category_name,
                "fund_count": 0,
                "computed_date": str(date.today()),
                "status": "skipped",
                "reason": "no_active_signals",
            }

        results = self.fsas_engine.compute(
            fund_exposures=fund_exposures,
            active_signals=active_signals,
        )

        if not results:
            return {
                "category": category_name,
                "fund_count": 0,
                "computed_date": str(date.today()),
                "status": "no_results",
            }

        old_fsas_by_fund = await self._load_old_fsas_values(fund_ids)
        rows_affected = await self.score_repo.bulk_upsert_fsas(results)

        audit_count = await self._create_audit_logs(
            results=results,
            old_values_by_fund=old_fsas_by_fund,
            trigger_event=trigger_event,
            computation_type="FSAS",
            score_key="fsas",
        )

        return {
            "category": category_name,
            "fund_count": len(results),
            "rows_upserted": rows_affected,
            "audits_created": audit_count,
            "computed_date": str(date.today()),
            "status": "completed",
        }

    async def compute_fsas_for_all_categories(
        self,
        trigger_event: str = "scheduled_recompute",
    ) -> list[dict[str, Any]]:
        """Compute FSAS for every category that has eligible funds."""
        categories = await self._get_eligible_categories()
        results: list[dict[str, Any]] = []

        for category_name in categories:
            try:
                summary = await self.compute_fsas_for_category(
                    category_name=category_name,
                    trigger_event=trigger_event,
                )
                results.append(summary)
            except Exception as exc:
                logger.error("fsas_category_failed", category=category_name, error=str(exc))
                results.append({"category": category_name, "status": "error", "error": str(exc)})

        return results

    # ===================================================================
    # Recommendation assignment (replaces CRS — Layer 3)
    # ===================================================================

    async def assign_recommendations(
        self,
        trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """
        Assign tiers and actions based on QFS percentile rank within each category.
        For shortlisted funds, refine actions with FSAS context.

        This replaces the old CRS computation entirely.
        """
        today = date.today()
        logger.info("recommendation_assignment_start", trigger=trigger_event)

        categories = await self._get_eligible_categories()
        all_recommendations: list[dict[str, Any]] = []
        tier_distribution: dict[str, int] = {}
        override_count = 0
        shortlisted_count = 0

        # Load shortlisted fund IDs
        shortlisted_mstar_ids = set(await self.score_repo.get_shortlisted_mstar_ids())

        for category_name in categories:
            fund_ids = await self._load_eligible_fund_ids(category_name)
            if not fund_ids:
                continue

            # Load latest QFS scores
            qfs_records = await self.score_repo.get_latest_qfs_by_mstar_ids(fund_ids)
            if not qfs_records:
                continue

            # Sort by QFS descending and compute ranks/percentiles
            sorted_records = sorted(
                qfs_records,
                key=lambda r: float(r.qfs) if r.qfs is not None else 0.0,
                reverse=True,
            )
            total_in_category = len(sorted_records)

            # Load FSAS scores for shortlisted funds in this category
            shortlisted_in_category = [
                r.mstar_id for r in sorted_records
                if r.mstar_id in shortlisted_mstar_ids
            ]
            fsas_lookup: dict[str, float] = {}
            avoid_exposure_lookup: dict[str, float] = {}

            if shortlisted_in_category:
                fsas_records = await self.score_repo.get_latest_fsas_by_mstar_ids(
                    shortlisted_in_category
                )
                for fsas_rec in fsas_records:
                    fsas_lookup[fsas_rec.mstar_id] = (
                        float(fsas_rec.fsas) if fsas_rec.fsas is not None else 0.0
                    )
                    avoid_exposure_lookup[fsas_rec.mstar_id] = (
                        float(fsas_rec.avoid_exposure_pct)
                        if fsas_rec.avoid_exposure_pct is not None
                        else 0.0
                    )

            # Load fund metadata for override checks
            fund_metadata = await self._load_fund_metadata(fund_ids)

            for rank, record in enumerate(sorted_records, start=1):
                mstar_id = record.mstar_id
                qfs_value = float(record.qfs) if record.qfs is not None else 0.0
                data_completeness = (
                    float(record.data_completeness_pct)
                    if record.data_completeness_pct is not None
                    else 100.0
                )

                # Compute percentile: (total - rank) / (total - 1) * 100
                # For a single fund, percentile is 50
                if total_in_category > 1:
                    percentile = (total_in_category - rank) / (total_in_category - 1) * 100.0
                else:
                    percentile = 50.0

                # Assign tier from percentile
                tier = self.tier_engine.assign_tier_by_percentile(percentile)
                action = self.tier_engine.assign_action(tier)

                # Check if this fund is shortlisted
                is_shortlisted = mstar_id in shortlisted_mstar_ids
                fsas_value = fsas_lookup.get(mstar_id) if is_shortlisted else None
                avoid_pct = avoid_exposure_lookup.get(mstar_id, 0.0)

                if is_shortlisted:
                    shortlisted_count += 1

                # Refine action with FSAS for shortlisted funds
                if is_shortlisted and fsas_value is not None:
                    action = self.tier_engine.refine_action_with_fsas(
                        tier=tier,
                        base_action=action,
                        fsas=fsas_value,
                        avoid_exposure_pct=avoid_pct,
                    )

                # Apply hard override rules
                metadata = fund_metadata.get(mstar_id, {})
                override_fund_data: dict[str, Any] = {
                    "avoid_exposure_pct": avoid_pct,
                    "inception_date": metadata.get("inception_date"),
                    "data_completeness_pct": data_completeness,
                    "reference_date": today,
                }

                (
                    final_tier,
                    final_action,
                    applied_override,
                    override_reason,
                    override_flag,
                ) = self.tier_engine.apply_overrides(tier, action, override_fund_data)

                if applied_override:
                    override_count += 1

                # Generate rationale
                rationale = self.tier_engine.generate_rationale(
                    tier=final_tier,
                    action=final_action,
                    qfs=qfs_value,
                    percentile=percentile,
                    fsas=fsas_value,
                    override_reason=override_reason,
                    is_shortlisted=is_shortlisted,
                )

                all_recommendations.append({
                    "mstar_id": mstar_id,
                    "computed_date": today,
                    "qfs": qfs_value,
                    "fsas": fsas_value,
                    "qfs_rank": rank,
                    "category_rank_pct": round(percentile, 2),
                    "is_shortlisted": is_shortlisted,
                    "tier": final_tier,
                    "action": final_action,
                    "override_applied": applied_override,
                    "override_reason": override_reason,
                    "original_tier": tier if applied_override else None,
                    "action_rationale": rationale,
                    "qfs_id": record.id,
                    "fsas_id": None,  # Could be populated if needed
                    "engine_version": "2.0.0",
                })

                # Track tier distribution
                tier_distribution[final_tier] = tier_distribution.get(final_tier, 0) + 1

        # Bulk upsert all recommendations
        if all_recommendations:
            rows_affected = await self.score_repo.bulk_upsert_recommendations(
                all_recommendations
            )
        else:
            rows_affected = 0

        logger.info(
            "recommendation_assignment_complete",
            fund_count=len(all_recommendations),
            rows_upserted=rows_affected,
            tier_distribution=tier_distribution,
            override_count=override_count,
            shortlisted_count=shortlisted_count,
        )

        return {
            "fund_count": len(all_recommendations),
            "rows_upserted": rows_affected,
            "tier_distribution": tier_distribution,
            "override_count": override_count,
            "shortlisted_count": shortlisted_count,
            "computed_date": str(today),
            "status": "completed",
        }

    # ===================================================================
    # Full pipeline (QFS -> shortlist -> FSAS -> recommend)
    # ===================================================================

    async def compute_full_pipeline(
        self,
        category_name: Optional[str] = None,
        trigger_event: str = "full_pipeline",
    ) -> dict[str, Any]:
        """
        Run the complete scoring pipeline:
        1. QFS for all categories (or one specific category)
        2. Generate shortlist (top N per category)
        3. FSAS for shortlisted funds only
        4. Assign tiers and actions for all funds

        Args:
            category_name: If provided, compute QFS only for this category
                          but still generate shortlist and recommendations across all.
            trigger_event: What triggered this computation.

        Returns:
            Summary dict with results from each layer.
        """
        logger.info(
            "full_pipeline_start",
            category=category_name,
            trigger=trigger_event,
        )

        pipeline_results: dict[str, Any] = {
            "category": category_name or "all",
            "trigger_event": trigger_event,
            "computed_date": str(date.today()),
            "layers": {},
        }

        # Layer 1: QFS
        try:
            if category_name:
                qfs_summary = await self.compute_qfs_for_category(
                    category_name=category_name,
                    trigger_event=trigger_event,
                )
                pipeline_results["layers"]["qfs"] = [qfs_summary]
            else:
                qfs_summaries = await self.compute_qfs_for_all_categories(
                    trigger_event=trigger_event,
                )
                pipeline_results["layers"]["qfs"] = qfs_summaries
        except Exception as exc:
            logger.error("pipeline_qfs_failed", error=str(exc))
            pipeline_results["layers"]["qfs"] = {"status": "error", "error": str(exc)}
            pipeline_results["status"] = "partial_failure"
            return pipeline_results

        # Layer 2a: Generate shortlist
        try:
            shortlist_summary = await self.generate_shortlist(
                trigger_event=trigger_event,
            )
            pipeline_results["layers"]["shortlist"] = shortlist_summary
        except Exception as exc:
            logger.error("pipeline_shortlist_failed", error=str(exc))
            pipeline_results["layers"]["shortlist"] = {"status": "error", "error": str(exc)}
            pipeline_results["status"] = "partial_failure"
            return pipeline_results

        # Layer 2b: FSAS for shortlisted funds
        try:
            fsas_summary = await self.compute_fsas_for_shortlisted(
                trigger_event=trigger_event,
            )
            pipeline_results["layers"]["fsas"] = fsas_summary
        except Exception as exc:
            logger.error("pipeline_fsas_failed", error=str(exc))
            pipeline_results["layers"]["fsas"] = {"status": "error", "error": str(exc)}
            # FSAS failure is non-fatal — we can still assign recommendations
            # based on QFS percentile alone, just without FSAS refinement

        # Layer 3: Assign tiers and actions
        try:
            rec_summary = await self.assign_recommendations(
                trigger_event=trigger_event,
            )
            pipeline_results["layers"]["recommendation"] = rec_summary
        except Exception as exc:
            logger.error("pipeline_recommendation_failed", error=str(exc))
            pipeline_results["layers"]["recommendation"] = {
                "status": "error",
                "error": str(exc),
            }
            pipeline_results["status"] = "partial_failure"
            return pipeline_results

        # All layers completed
        total_funds = rec_summary.get("fund_count", 0)
        pipeline_results["status"] = "completed"
        pipeline_results["fund_count"] = total_funds
        pipeline_results["tier_distribution"] = rec_summary.get("tier_distribution", {})
        pipeline_results["shortlisted_count"] = rec_summary.get("shortlisted_count", 0)

        logger.info(
            "full_pipeline_complete",
            fund_count=total_funds,
            shortlisted=rec_summary.get("shortlisted_count", 0),
        )

        return pipeline_results

    async def compute_full_pipeline_all_categories(
        self,
        trigger_event: str = "scheduled_full_pipeline",
    ) -> list[dict[str, Any]]:
        """
        Run the complete pipeline for all categories.
        Returns a single-item list (the pipeline runs globally, not per-category).
        """
        result = await self.compute_full_pipeline(
            category_name=None,
            trigger_event=trigger_event,
        )
        return [result]

    # -------------------------------------------------------------------
    # Private data loading helpers
    # -------------------------------------------------------------------

    async def _load_eligible_fund_ids(self, category_name: str) -> list[str]:
        """Load mstar_ids of all eligible, non-deleted funds in a category."""
        result = await self.session.execute(
            select(FundMaster.mstar_id).where(
                FundMaster.category_name == category_name,
                FundMaster.is_eligible.is_(True),
                FundMaster.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def _load_latest_risk_stats(
        self, fund_ids: list[str]
    ) -> dict[str, dict[str, Any]]:
        """Load the LATEST risk stats for each fund (by month_end_date)."""
        if not fund_ids:
            return {}

        from sqlalchemy import func as sa_func

        latest_date_subq = (
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
                latest_date_subq,
                (FundRiskStats.mstar_id == latest_date_subq.c.mstar_id)
                & (FundRiskStats.month_end_date == latest_date_subq.c.max_date),
            )
        )
        rows = result.scalars().all()

        stats_by_fund: dict[str, dict[str, Any]] = {}
        for row in rows:
            stats_by_fund[row.mstar_id] = _orm_to_dict(row)

        return stats_by_fund

    async def _load_latest_performance(
        self, fund_ids: list[str]
    ) -> dict[str, dict[str, Any]]:
        """Load the LATEST performance data for each fund (by nav_date)."""
        if not fund_ids:
            return {}

        from sqlalchemy import func as sa_func

        latest_date_subq = (
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
                latest_date_subq,
                (FundPerformance.mstar_id == latest_date_subq.c.mstar_id)
                & (FundPerformance.nav_date == latest_date_subq.c.max_date),
            )
        )
        rows = result.scalars().all()

        perf_by_fund: dict[str, dict[str, Any]] = {}
        for row in rows:
            perf_by_fund[row.mstar_id] = _orm_to_dict(row)

        return perf_by_fund

    async def _load_latest_sector_exposures(
        self, fund_ids: list[str]
    ) -> dict[str, list[dict[str, Any]]]:
        """Load the latest sector exposure data for each fund."""
        if not fund_ids:
            return {}

        from sqlalchemy import func as sa_func

        latest_date_subq = (
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
                latest_date_subq,
                (FundSectorExposure.mstar_id == latest_date_subq.c.mstar_id)
                & (
                    FundSectorExposure.month_end_date
                    == latest_date_subq.c.max_date
                ),
            )
        )
        rows = result.scalars().all()

        exposures_by_fund: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            mstar_id = row.mstar_id
            if mstar_id not in exposures_by_fund:
                exposures_by_fund[mstar_id] = []
            exposures_by_fund[mstar_id].append({
                "sector_name": row.sector_name,
                "exposure_pct": float(row.exposure_pct) if row.exposure_pct is not None else 0.0,
                "month_end_date": row.month_end_date,
            })

        for fund_id in fund_ids:
            if fund_id not in exposures_by_fund:
                exposures_by_fund[fund_id] = []

        return exposures_by_fund

    async def _load_active_signals(self) -> list[dict[str, Any]]:
        """Load all currently active FM sector signals."""
        result = await self.session.execute(
            select(SectorSignal)
            .where(SectorSignal.is_active.is_(True))
            .order_by(SectorSignal.sector_name)
        )
        rows = result.scalars().all()

        signals: list[dict[str, Any]] = []
        for row in rows:
            signals.append({
                "sector_name": row.sector_name,
                "signal": row.signal,
                "signal_weight": float(row.signal_weight) if row.signal_weight is not None else 0.0,
                "confidence": row.confidence,
                "effective_date": row.effective_date,
            })

        return signals

    async def _load_fund_metadata(
        self, fund_ids: list[str]
    ) -> dict[str, dict[str, Any]]:
        """Load fund master metadata needed for override checks."""
        if not fund_ids:
            return {}

        result = await self.session.execute(
            select(FundMaster).where(FundMaster.mstar_id.in_(fund_ids))
        )
        rows = result.scalars().all()

        metadata: dict[str, dict[str, Any]] = {}
        for row in rows:
            metadata[row.mstar_id] = {
                "inception_date": row.inception_date,
                "legal_name": row.legal_name,
                "category_name": row.category_name,
            }

        return metadata

    async def _load_old_qfs_values(
        self, fund_ids: list[str]
    ) -> dict[str, Optional[float]]:
        """Load the previous QFS score for each fund (for audit delta tracking)."""
        old_values: dict[str, Optional[float]] = {}
        for mstar_id in fund_ids:
            existing = await self.score_repo.get_latest_qfs(mstar_id)
            if existing is not None:
                old_values[mstar_id] = float(existing.qfs) if existing.qfs is not None else None
            else:
                old_values[mstar_id] = None
        return old_values

    async def _load_old_fsas_values(
        self, fund_ids: list[str]
    ) -> dict[str, Optional[float]]:
        """Load the previous FSAS score for each fund."""
        old_values: dict[str, Optional[float]] = {}
        for mstar_id in fund_ids:
            existing = await self.score_repo.get_latest_fsas(mstar_id)
            if existing is not None:
                old_values[mstar_id] = float(existing.fsas) if existing.fsas is not None else None
            else:
                old_values[mstar_id] = None
        return old_values

    async def _get_eligible_categories(self) -> list[str]:
        """Get all distinct category names that have eligible, non-deleted funds."""
        result = await self.session.execute(
            select(FundMaster.category_name)
            .where(
                FundMaster.is_eligible.is_(True),
                FundMaster.deleted_at.is_(None),
            )
            .distinct()
            .order_by(FundMaster.category_name)
        )
        return list(result.scalars().all())

    async def _create_audit_logs(
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


def _orm_to_dict(obj: Any) -> dict[str, Any]:
    """Convert an SQLAlchemy ORM instance to a plain dict."""
    result: dict[str, Any] = {}
    for column in obj.__table__.columns:
        val = getattr(obj, column.name)
        if isinstance(val, Decimal):
            val = float(val)
        result[column.name] = val
    return result
