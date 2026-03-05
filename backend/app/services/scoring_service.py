"""
services/scoring_service.py

Orchestrator for QFS, FSAS, and CRS computation. Handles:
    1. Loading data from repositories (fund_master, fund_risk_stats, etc.)
    2. Passing prepared data to the engine for pure computation
    3. Writing results to the DB via score_repo
    4. Creating audit log entries for traceability

This service is the glue between DB I/O and the stateless computation engines.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.crs_engine import CRSEngine
from app.engines.fsas_engine import FSASEngine
from app.engines.qfs_engine import QFSEngine
from app.models.db.fund_master import FundMaster
from app.models.db.fund_performance import FundPerformance
from app.models.db.fund_risk_stats import FundRiskStats
from app.models.db.fund_sector_exposure import FundSectorExposure
from app.models.db.sector_signals import SectorSignal
from app.repositories.score_repo import ScoreRepository

logger = structlog.get_logger(__name__)


class ScoringService:
    """Orchestrates QFS, FSAS, and CRS scoring — loads data, runs engines, persists results."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.score_repo = ScoreRepository(session)
        self.qfs_engine = QFSEngine()
        self.fsas_engine = FSASEngine()
        self.crs_engine = CRSEngine()

    # ===================================================================
    # QFS computation (Layer 1)
    # ===================================================================

    async def compute_qfs_for_category(
        self,
        category_name: str,
        trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """
        Compute QFS for all eligible funds in a single category.

        Args:
            category_name: SEBI category name (e.g. "Large Cap Fund").
            trigger_event: What triggered this computation (for audit trail).

        Returns:
            Summary dict with category, fund_count, and computed_date.
        """
        logger.info("scoring_service_start", category=category_name, trigger=trigger_event)

        # Step 1: Load eligible funds in the category
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

        # Step 2: Load risk stats and performance data for all funds
        risk_stats_by_fund = await self._load_latest_risk_stats(fund_ids)
        performance_by_fund = await self._load_latest_performance(fund_ids)

        # Step 3: Run the QFS engine (pure computation, no DB access)
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

        # Step 4: Fetch old QFS values for audit logging (before overwrite)
        old_qfs_by_fund = await self._load_old_qfs_values(fund_ids)

        # Step 5: Bulk upsert results to fund_qfs table
        rows_affected = await self.score_repo.bulk_upsert_qfs(results)

        # Step 6: Create audit log entries for any score changes
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
        """
        Compute QFS for every category that has eligible funds.

        Returns:
            List of summary dicts, one per category processed.
        """
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
    # FSAS computation (Layer 2)
    # ===================================================================

    async def compute_fsas_for_category(
        self,
        category_name: str,
        trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """
        Compute FSAS for all eligible funds in a single category.

        Loads the latest sector exposure data for each fund and the
        active FM sector signals, then runs the FSAS engine.

        Args:
            category_name: SEBI category name.
            trigger_event: What triggered this computation.

        Returns:
            Summary dict with category, fund_count, and status.
        """
        logger.info(
            "fsas_service_start",
            category=category_name,
            trigger=trigger_event,
        )

        # Step 1: Load eligible fund IDs
        fund_ids = await self._load_eligible_fund_ids(category_name)
        if not fund_ids:
            logger.warning("fsas_no_eligible_funds", category=category_name)
            return {
                "category": category_name,
                "fund_count": 0,
                "computed_date": str(date.today()),
                "status": "skipped",
                "reason": "no_eligible_funds",
            }

        # Step 2: Load latest sector exposures for all funds
        fund_exposures = await self._load_latest_sector_exposures(fund_ids)

        # Step 3: Load active FM signals
        active_signals = await self._load_active_signals()

        if not active_signals:
            logger.warning(
                "fsas_no_active_signals",
                category=category_name,
            )
            return {
                "category": category_name,
                "fund_count": 0,
                "computed_date": str(date.today()),
                "status": "skipped",
                "reason": "no_active_signals",
            }

        # Step 4: Run the FSAS engine
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

        # Step 5: Load old FSAS values for audit logging
        old_fsas_by_fund = await self._load_old_fsas_values(fund_ids)

        # Step 6: Bulk upsert
        rows_affected = await self.score_repo.bulk_upsert_fsas(results)

        # Step 7: Audit logs
        audit_count = await self._create_audit_logs(
            results=results,
            old_values_by_fund=old_fsas_by_fund,
            trigger_event=trigger_event,
            computation_type="FSAS",
            score_key="fsas",
        )

        logger.info(
            "fsas_service_complete",
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

    async def compute_fsas_for_all_categories(
        self,
        trigger_event: str = "scheduled_recompute",
    ) -> list[dict[str, Any]]:
        """Compute FSAS for every category that has eligible funds."""
        logger.info("fsas_all_categories_start", trigger=trigger_event)

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
                logger.error(
                    "fsas_category_failed",
                    category=category_name,
                    error=str(exc),
                )
                results.append({
                    "category": category_name,
                    "status": "error",
                    "error": str(exc),
                })

        return results

    # ===================================================================
    # CRS computation (Layer 3)
    # ===================================================================

    async def compute_crs_for_category(
        self,
        category_name: str,
        trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """
        Compute CRS for all eligible funds in a single category.

        Loads latest QFS and FSAS scores, runs the CRS engine (which
        internally uses the tier engine for classification and overrides),
        then persists results.

        Args:
            category_name: SEBI category name.
            trigger_event: What triggered this computation.

        Returns:
            Summary dict with category, fund_count, tier_distribution, etc.
        """
        logger.info(
            "crs_service_start",
            category=category_name,
            trigger=trigger_event,
        )

        # Step 1: Load eligible fund IDs
        fund_ids = await self._load_eligible_fund_ids(category_name)
        if not fund_ids:
            logger.warning("crs_no_eligible_funds", category=category_name)
            return {
                "category": category_name,
                "fund_count": 0,
                "computed_date": str(date.today()),
                "status": "skipped",
                "reason": "no_eligible_funds",
            }

        # Step 2: Load latest QFS scores
        qfs_records = await self.score_repo.get_latest_qfs_by_mstar_ids(fund_ids)
        qfs_scores: dict[str, dict[str, Any]] = {}
        for record in qfs_records:
            qfs_scores[record.mstar_id] = {
                "qfs": float(record.qfs) if record.qfs is not None else 0.0,
                "qfs_id": record.id,
                "data_completeness_pct": (
                    float(record.data_completeness_pct)
                    if record.data_completeness_pct is not None
                    else 100.0
                ),
            }

        # Step 3: Load latest FSAS scores
        fsas_records = await self.score_repo.get_latest_fsas_by_mstar_ids(fund_ids)
        fsas_scores: dict[str, dict[str, Any]] = {}
        for record in fsas_records:
            fsas_scores[record.mstar_id] = {
                "fsas": float(record.fsas) if record.fsas is not None else 0.0,
                "fsas_id": record.id,
                "avoid_exposure_pct": (
                    float(record.avoid_exposure_pct)
                    if record.avoid_exposure_pct is not None
                    else 0.0
                ),
            }

        if not qfs_scores or not fsas_scores:
            logger.warning(
                "crs_missing_layer_scores",
                category=category_name,
                qfs_count=len(qfs_scores),
                fsas_count=len(fsas_scores),
            )
            return {
                "category": category_name,
                "fund_count": 0,
                "computed_date": str(date.today()),
                "status": "skipped",
                "reason": "missing_layer_scores",
            }

        # Step 4: Load fund metadata for override checks
        fund_metadata = await self._load_fund_metadata(fund_ids)

        # Step 5: Run the CRS engine
        results = self.crs_engine.compute(
            qfs_scores=qfs_scores,
            fsas_scores=fsas_scores,
            fund_metadata=fund_metadata,
        )

        if not results:
            return {
                "category": category_name,
                "fund_count": 0,
                "computed_date": str(date.today()),
                "status": "no_results",
            }

        # Step 6: Load old CRS values for audit logging
        old_crs_by_fund = await self._load_old_crs_values(fund_ids)

        # Step 7: Bulk upsert
        rows_affected = await self.score_repo.bulk_upsert_crs(results)

        # Step 8: Create audit logs (track both score and tier changes)
        audit_count = await self._create_crs_audit_logs(
            results=results,
            old_crs_by_fund=old_crs_by_fund,
            trigger_event=trigger_event,
        )

        # Compute tier distribution for summary
        tier_distribution: dict[str, int] = {}
        override_count = 0
        for result in results:
            tier_name = result["tier"]
            tier_distribution[tier_name] = tier_distribution.get(tier_name, 0) + 1
            if result["override_applied"]:
                override_count += 1

        logger.info(
            "crs_service_complete",
            category=category_name,
            fund_count=len(results),
            rows_upserted=rows_affected,
            audits_created=audit_count,
            tier_distribution=tier_distribution,
            override_count=override_count,
        )

        return {
            "category": category_name,
            "fund_count": len(results),
            "rows_upserted": rows_affected,
            "audits_created": audit_count,
            "computed_date": str(date.today()),
            "status": "completed",
            "tier_distribution": tier_distribution,
            "override_count": override_count,
        }

    async def compute_crs_for_all_categories(
        self,
        trigger_event: str = "scheduled_recompute",
    ) -> list[dict[str, Any]]:
        """Compute CRS for every category that has eligible funds."""
        logger.info("crs_all_categories_start", trigger=trigger_event)

        categories = await self._get_eligible_categories()
        results: list[dict[str, Any]] = []

        for category_name in categories:
            try:
                summary = await self.compute_crs_for_category(
                    category_name=category_name,
                    trigger_event=trigger_event,
                )
                results.append(summary)
            except Exception as exc:
                logger.error(
                    "crs_category_failed",
                    category=category_name,
                    error=str(exc),
                )
                results.append({
                    "category": category_name,
                    "status": "error",
                    "error": str(exc),
                })

        return results

    # ===================================================================
    # Full pipeline (QFS -> FSAS -> CRS)
    # ===================================================================

    async def compute_full_pipeline(
        self,
        category_name: str,
        trigger_event: str = "full_pipeline",
    ) -> dict[str, Any]:
        """
        Run the complete scoring pipeline for a single category:
        QFS (Layer 1) -> FSAS (Layer 2) -> CRS (Layer 3).

        Each layer depends on the previous one being computed first.

        Args:
            category_name: SEBI category name.
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
            "category": category_name,
            "trigger_event": trigger_event,
            "computed_date": str(date.today()),
            "layers": {},
        }

        # Layer 1: QFS
        try:
            qfs_summary = await self.compute_qfs_for_category(
                category_name=category_name,
                trigger_event=trigger_event,
            )
            pipeline_results["layers"]["qfs"] = qfs_summary
        except Exception as exc:
            logger.error(
                "pipeline_qfs_failed",
                category=category_name,
                error=str(exc),
            )
            pipeline_results["layers"]["qfs"] = {
                "status": "error",
                "error": str(exc),
            }
            # Cannot proceed without QFS
            pipeline_results["status"] = "partial_failure"
            return pipeline_results

        # Layer 2: FSAS
        try:
            fsas_summary = await self.compute_fsas_for_category(
                category_name=category_name,
                trigger_event=trigger_event,
            )
            pipeline_results["layers"]["fsas"] = fsas_summary
        except Exception as exc:
            logger.error(
                "pipeline_fsas_failed",
                category=category_name,
                error=str(exc),
            )
            pipeline_results["layers"]["fsas"] = {
                "status": "error",
                "error": str(exc),
            }
            # Cannot proceed without FSAS
            pipeline_results["status"] = "partial_failure"
            return pipeline_results

        # Layer 3: CRS
        try:
            crs_summary = await self.compute_crs_for_category(
                category_name=category_name,
                trigger_event=trigger_event,
            )
            pipeline_results["layers"]["crs"] = crs_summary
        except Exception as exc:
            logger.error(
                "pipeline_crs_failed",
                category=category_name,
                error=str(exc),
            )
            pipeline_results["layers"]["crs"] = {
                "status": "error",
                "error": str(exc),
            }
            pipeline_results["status"] = "partial_failure"
            return pipeline_results

        # All layers completed successfully
        total_funds = crs_summary.get("fund_count", 0)
        pipeline_results["status"] = "completed"
        pipeline_results["fund_count"] = total_funds
        pipeline_results["tier_distribution"] = crs_summary.get(
            "tier_distribution", {}
        )

        logger.info(
            "full_pipeline_complete",
            category=category_name,
            fund_count=total_funds,
        )

        return pipeline_results

    async def compute_full_pipeline_all_categories(
        self,
        trigger_event: str = "scheduled_full_pipeline",
    ) -> list[dict[str, Any]]:
        """
        Run the complete scoring pipeline for every category with eligible funds.
        Processes categories sequentially: QFS -> FSAS -> CRS for each.

        Returns:
            List of pipeline result dicts, one per category.
        """
        logger.info("full_pipeline_all_start", trigger=trigger_event)

        categories = await self._get_eligible_categories()
        logger.info(
            "full_pipeline_all_categories",
            count=len(categories),
        )

        results: list[dict[str, Any]] = []
        for category_name in categories:
            try:
                summary = await self.compute_full_pipeline(
                    category_name=category_name,
                    trigger_event=trigger_event,
                )
                results.append(summary)
            except Exception as exc:
                logger.error(
                    "full_pipeline_category_failed",
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
            "full_pipeline_all_complete",
            categories_processed=len(results),
            total_funds=total_funds,
        )

        return results

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
        """
        Load the LATEST risk stats for each fund (by month_end_date).
        Returns a dict keyed by mstar_id with column values as flat dicts.
        """
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

        logger.debug(
            "loaded_risk_stats",
            requested=len(fund_ids),
            found=len(stats_by_fund),
        )
        return stats_by_fund

    async def _load_latest_performance(
        self, fund_ids: list[str]
    ) -> dict[str, dict[str, Any]]:
        """
        Load the LATEST performance data for each fund (by nav_date).
        Returns a dict keyed by mstar_id with column values as flat dicts.
        """
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

        logger.debug(
            "loaded_performance",
            requested=len(fund_ids),
            found=len(perf_by_fund),
        )
        return perf_by_fund

    async def _load_latest_sector_exposures(
        self, fund_ids: list[str]
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Load the latest sector exposure data for each fund.
        Returns {mstar_id: [{sector_name, exposure_pct, month_end_date}]}.
        """
        if not fund_ids:
            return {}

        from sqlalchemy import func as sa_func

        # Get the latest month_end_date per fund
        latest_date_subq = (
            select(
                FundSectorExposure.mstar_id,
                sa_func.max(FundSectorExposure.month_end_date).label("max_date"),
            )
            .where(FundSectorExposure.mstar_id.in_(fund_ids))
            .group_by(FundSectorExposure.mstar_id)
            .subquery()
        )

        # Fetch all sector rows for the latest date per fund
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

        # Group by mstar_id
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

        # Include funds that had no exposure data (empty list)
        for fund_id in fund_ids:
            if fund_id not in exposures_by_fund:
                exposures_by_fund[fund_id] = []

        logger.debug(
            "loaded_sector_exposures",
            requested=len(fund_ids),
            with_data=sum(1 for v in exposures_by_fund.values() if v),
        )
        return exposures_by_fund

    async def _load_active_signals(self) -> list[dict[str, Any]]:
        """
        Load all currently active FM sector signals.
        Returns a list of signal dicts.
        """
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

        logger.debug("loaded_active_signals", count=len(signals))
        return signals

    async def _load_fund_metadata(
        self, fund_ids: list[str]
    ) -> dict[str, dict[str, Any]]:
        """
        Load fund master metadata needed for CRS override checks.
        Returns {mstar_id: {inception_date, ...}}.
        """
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
        """Load the previous FSAS score for each fund (for audit delta tracking)."""
        old_values: dict[str, Optional[float]] = {}

        for mstar_id in fund_ids:
            existing = await self.score_repo.get_latest_fsas(mstar_id)
            if existing is not None:
                old_values[mstar_id] = float(existing.fsas) if existing.fsas is not None else None
            else:
                old_values[mstar_id] = None

        return old_values

    async def _load_old_crs_values(
        self, fund_ids: list[str]
    ) -> dict[str, dict[str, Any]]:
        """
        Load the previous CRS score and tier for each fund.
        Returns {mstar_id: {crs, tier}} for audit comparison.
        """
        old_values: dict[str, dict[str, Any]] = {}

        for mstar_id in fund_ids:
            existing = await self.score_repo.get_latest_crs(mstar_id)
            if existing is not None:
                old_values[mstar_id] = {
                    "crs": float(existing.crs) if existing.crs is not None else None,
                    "tier": existing.tier,
                }
            else:
                old_values[mstar_id] = {"crs": None, "tier": None}

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

            # Only log if the score actually changed (or is new)
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

    async def _create_crs_audit_logs(
        self,
        results: list[dict[str, Any]],
        old_crs_by_fund: dict[str, dict[str, Any]],
        trigger_event: str,
    ) -> int:
        """Create audit log entries for CRS changes, tracking both score and tier."""
        audit_count = 0

        for result in results:
            mstar_id = result["mstar_id"]
            new_crs = result["crs"]
            new_tier = result["tier"]
            old_data = old_crs_by_fund.get(mstar_id, {"crs": None, "tier": None})
            old_crs = old_data["crs"]
            old_tier = old_data["tier"]

            # Log if CRS changed or tier changed
            crs_changed = old_crs is None or abs(float(new_crs) - float(old_crs)) > 0.001
            tier_changed = old_tier is None or old_tier != new_tier

            if crs_changed or tier_changed:
                await self.score_repo.create_audit_log({
                    "mstar_id": mstar_id,
                    "computation_type": "CRS",
                    "old_value": old_crs,
                    "new_value": new_crs,
                    "old_tier": old_tier,
                    "new_tier": new_tier,
                    "trigger_event": trigger_event,
                    "computed_by": "system",
                })
                audit_count += 1

        return audit_count


def _orm_to_dict(obj: Any) -> dict[str, Any]:
    """
    Convert an SQLAlchemy ORM instance to a plain dict.
    Converts Decimal/date types to float/str for the engine's consumption.
    """
    result: dict[str, Any] = {}
    for column in obj.__table__.columns:
        val = getattr(obj, column.name)
        if isinstance(val, Decimal):
            val = float(val)
        result[column.name] = val
    return result
