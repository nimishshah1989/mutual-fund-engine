"""
services/fsas_scoring.py

FMS (FM Sector Alignment Score) computation methods.

v2 (Decision Matrix): FMS is computed for ALL eligible funds (not just
shortlisted). Uses active weights relative to NIFTY 50 benchmark.

Handles Layer 2 scoring:
  - compute_for_all_funds: FMS for every eligible fund (new default)
  - compute_for_category: FMS for all eligible funds in one category
  - compute_for_all_categories: FMS across all categories
  - compute_for_shortlisted: LEGACY — kept for backward compat
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

import structlog

from app.engines.fsas_engine import FSASEngine
from app.repositories.score_repo import ScoreRepository
from app.services.scoring_data_loader import ScoringDataLoader

logger = structlog.get_logger(__name__)


class FSASScorer:
    """Computes FMS scores for funds using FM sector signals and benchmark weights."""

    def __init__(
        self,
        score_repo: ScoreRepository,
        data_loader: ScoringDataLoader,
        fsas_engine: FSASEngine,
    ) -> None:
        self.score_repo = score_repo
        self.data_loader = data_loader
        self.fsas_engine = fsas_engine

    async def compute_for_all_funds(
        self,
        benchmark_weights: Optional[dict[str, float]] = None,
        trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """
        Compute FMS for ALL eligible funds across all categories.
        This is the v2 default — no shortlist filtering.

        Args:
            benchmark_weights: {sector_name: weight_pct} for active weight calc.
                If None, falls back to v1 raw exposure formula.
            trigger_event: Audit trail trigger description.
        """
        logger.info("fms_all_funds_start", trigger=trigger_event)

        categories = await self.data_loader.get_eligible_categories()
        total_computed = 0
        total_upserted = 0
        total_audits = 0
        category_summaries: list[dict[str, Any]] = []

        for category_name in categories:
            try:
                summary = await self.compute_for_category(
                    category_name=category_name,
                    benchmark_weights=benchmark_weights,
                    trigger_event=trigger_event,
                )
                total_computed += summary.get("fund_count", 0)
                total_upserted += summary.get("rows_upserted", 0)
                total_audits += summary.get("audits_created", 0)
                category_summaries.append(summary)
            except Exception as exc:
                logger.error("fms_category_failed", category=category_name, error=str(exc))
                category_summaries.append({
                    "category": category_name, "status": "error", "error": str(exc),
                })

        logger.info(
            "fms_all_funds_complete",
            categories=len(categories),
            total_computed=total_computed,
            total_upserted=total_upserted,
        )

        # Determine aggregate reason if no funds were computed
        aggregate_reason = None
        if total_computed == 0 and category_summaries:
            skip_reasons = [s.get("reason") for s in category_summaries if s.get("reason")]
            if skip_reasons:
                # Use the most common skip reason
                aggregate_reason = max(set(skip_reasons), key=skip_reasons.count)

        result: dict[str, Any] = {
            "fund_count": total_computed,
            "rows_upserted": total_upserted,
            "audits_created": total_audits,
            "categories_processed": len(category_summaries),
            "computed_date": str(date.today()),
            "status": "completed" if total_computed > 0 else "skipped",
        }
        if aggregate_reason:
            result["reason"] = aggregate_reason

        return result

    async def compute_for_category(
        self,
        category_name: str,
        benchmark_weights: Optional[dict[str, float]] = None,
        trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """Compute FMS for all eligible funds in a single category."""
        logger.info("fms_category_start", category=category_name, trigger=trigger_event)

        fund_ids = await self.data_loader.load_eligible_fund_ids(category_name)
        if not fund_ids:
            return {
                "category": category_name, "fund_count": 0,
                "computed_date": str(date.today()), "status": "skipped",
                "reason": "no_eligible_funds",
            }

        fund_exposures = await self.data_loader.load_latest_sector_exposures(fund_ids)
        active_signals = await self.data_loader.load_active_signals()

        # Log data availability for diagnostics
        funds_with_exposure = len(fund_exposures) if fund_exposures else 0
        logger.info(
            "fms_category_data_availability",
            category=category_name,
            eligible_funds=len(fund_ids),
            funds_with_exposure=funds_with_exposure,
            active_signal_count=len(active_signals) if active_signals else 0,
        )

        if not active_signals:
            logger.warning(
                "fms_no_active_signals",
                category=category_name,
                eligible_funds=len(fund_ids),
            )
            return {
                "category": category_name, "fund_count": 0,
                "computed_date": str(date.today()), "status": "skipped",
                "reason": "no_active_signals",
            }

        if funds_with_exposure == 0:
            logger.warning(
                "fms_no_sector_exposure_data",
                category=category_name,
                eligible_funds=len(fund_ids),
                message="Run ingestion first to populate sector exposure data",
            )
            return {
                "category": category_name, "fund_count": 0,
                "computed_date": str(date.today()), "status": "skipped",
                "reason": "no_sector_exposure_data",
            }

        results = self.fsas_engine.compute(
            fund_exposures=fund_exposures,
            active_signals=active_signals,
            benchmark_weights=benchmark_weights,
        )
        if not results:
            return {
                "category": category_name, "fund_count": 0,
                "computed_date": str(date.today()), "status": "no_results",
            }

        old_fsas = await self.data_loader.load_old_fsas_values(fund_ids)
        rows_affected = await self.score_repo.bulk_upsert_fsas(results)

        audit_count = await self.data_loader.create_audit_logs(
            results=results, old_values_by_fund=old_fsas,
            trigger_event=trigger_event, computation_type="FMS", score_key="fsas",
        )
        return {
            "category": category_name, "fund_count": len(results),
            "rows_upserted": rows_affected, "audits_created": audit_count,
            "computed_date": str(date.today()), "status": "completed",
        }

    async def compute_for_all_categories(
        self,
        benchmark_weights: Optional[dict[str, float]] = None,
        trigger_event: str = "scheduled_recompute",
    ) -> list[dict[str, Any]]:
        """Compute FMS for every category that has eligible funds."""
        categories = await self.data_loader.get_eligible_categories()
        results: list[dict[str, Any]] = []
        for category_name in categories:
            try:
                summary = await self.compute_for_category(
                    category_name=category_name,
                    benchmark_weights=benchmark_weights,
                    trigger_event=trigger_event,
                )
                results.append(summary)
            except Exception as exc:
                logger.error("fms_category_failed", category=category_name, error=str(exc))
                results.append({"category": category_name, "status": "error", "error": str(exc)})
        return results

    async def compute_for_shortlisted(
        self,
        benchmark_weights: Optional[dict[str, float]] = None,
        trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """
        LEGACY: Compute FMS for shortlisted funds ONLY.
        Kept for backward compat. New pipeline uses compute_for_all_funds().
        """
        logger.info("fms_shortlisted_start", trigger=trigger_event)

        shortlisted_mstar_ids = await self.score_repo.get_shortlisted_mstar_ids()
        if not shortlisted_mstar_ids:
            logger.warning("fms_no_shortlisted_funds")
            return {"fund_count": 0, "status": "skipped", "reason": "no_shortlisted_funds"}

        fund_exposures = await self.data_loader.load_latest_sector_exposures(shortlisted_mstar_ids)
        active_signals = await self.data_loader.load_active_signals()
        if not active_signals:
            logger.warning("fms_no_active_signals")
            return {"fund_count": 0, "status": "skipped", "reason": "no_active_signals"}

        results = self.fsas_engine.compute(
            fund_exposures=fund_exposures,
            active_signals=active_signals,
            benchmark_weights=benchmark_weights,
        )
        if not results:
            return {"fund_count": 0, "status": "no_results"}

        old_fsas = await self.data_loader.load_old_fsas_values(shortlisted_mstar_ids)
        rows_affected = await self.score_repo.bulk_upsert_fsas(results)

        audit_count = await self.data_loader.create_audit_logs(
            results=results, old_values_by_fund=old_fsas,
            trigger_event=trigger_event, computation_type="FMS", score_key="fsas",
        )

        logger.info(
            "fms_shortlisted_complete",
            fund_count=len(results), rows_upserted=rows_affected, audits_created=audit_count,
        )
        return {
            "fund_count": len(results), "rows_upserted": rows_affected,
            "audits_created": audit_count, "computed_date": str(date.today()),
            "status": "completed",
        }
