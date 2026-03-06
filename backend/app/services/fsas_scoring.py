"""
services/fsas_scoring.py

FSAS (FM Sector Alignment Score) computation methods.

Handles Layer 2 scoring:
  - compute_for_shortlisted: FSAS for shortlisted funds only
  - compute_for_category: FSAS for all eligible funds in one category
  - compute_for_all_categories: FSAS across all categories
"""

from __future__ import annotations

from datetime import date
from typing import Any

import structlog

from app.engines.fsas_engine import FSASEngine
from app.repositories.score_repo import ScoreRepository
from app.services.scoring_data_loader import ScoringDataLoader

logger = structlog.get_logger(__name__)


class FSASScorer:
    """Computes FSAS scores for funds using FM sector signals."""

    def __init__(
        self,
        score_repo: ScoreRepository,
        data_loader: ScoringDataLoader,
        fsas_engine: FSASEngine,
    ) -> None:
        self.score_repo = score_repo
        self.data_loader = data_loader
        self.fsas_engine = fsas_engine

    async def compute_for_shortlisted(
        self, trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """Compute FSAS for shortlisted funds ONLY (not all funds)."""
        logger.info("fsas_shortlisted_start", trigger=trigger_event)

        shortlisted_mstar_ids = await self.score_repo.get_shortlisted_mstar_ids()
        if not shortlisted_mstar_ids:
            logger.warning("fsas_no_shortlisted_funds")
            return {"fund_count": 0, "status": "skipped", "reason": "no_shortlisted_funds"}

        fund_exposures = await self.data_loader.load_latest_sector_exposures(shortlisted_mstar_ids)
        active_signals = await self.data_loader.load_active_signals()
        if not active_signals:
            logger.warning("fsas_no_active_signals")
            return {"fund_count": 0, "status": "skipped", "reason": "no_active_signals"}

        results = self.fsas_engine.compute(
            fund_exposures=fund_exposures, active_signals=active_signals,
        )
        if not results:
            return {"fund_count": 0, "status": "no_results"}

        old_fsas = await self.data_loader.load_old_fsas_values(shortlisted_mstar_ids)
        rows_affected = await self.score_repo.bulk_upsert_fsas(results)

        audit_count = await self.data_loader.create_audit_logs(
            results=results, old_values_by_fund=old_fsas,
            trigger_event=trigger_event, computation_type="FSAS", score_key="fsas",
        )

        logger.info(
            "fsas_shortlisted_complete",
            fund_count=len(results), rows_upserted=rows_affected, audits_created=audit_count,
        )
        return {
            "fund_count": len(results), "rows_upserted": rows_affected,
            "audits_created": audit_count, "computed_date": str(date.today()),
            "status": "completed",
        }

    async def compute_for_category(
        self, category_name: str, trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """Compute FSAS for all eligible funds in a single category."""
        logger.info("fsas_service_start", category=category_name, trigger=trigger_event)

        fund_ids = await self.data_loader.load_eligible_fund_ids(category_name)
        if not fund_ids:
            return {
                "category": category_name, "fund_count": 0,
                "computed_date": str(date.today()), "status": "skipped",
                "reason": "no_eligible_funds",
            }

        fund_exposures = await self.data_loader.load_latest_sector_exposures(fund_ids)
        active_signals = await self.data_loader.load_active_signals()
        if not active_signals:
            return {
                "category": category_name, "fund_count": 0,
                "computed_date": str(date.today()), "status": "skipped",
                "reason": "no_active_signals",
            }

        results = self.fsas_engine.compute(
            fund_exposures=fund_exposures, active_signals=active_signals,
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
            trigger_event=trigger_event, computation_type="FSAS", score_key="fsas",
        )
        return {
            "category": category_name, "fund_count": len(results),
            "rows_upserted": rows_affected, "audits_created": audit_count,
            "computed_date": str(date.today()), "status": "completed",
        }

    async def compute_for_all_categories(
        self, trigger_event: str = "scheduled_recompute",
    ) -> list[dict[str, Any]]:
        """Compute FSAS for every category that has eligible funds."""
        categories = await self.data_loader.get_eligible_categories()
        results: list[dict[str, Any]] = []
        for category_name in categories:
            try:
                summary = await self.compute_for_category(
                    category_name=category_name, trigger_event=trigger_event,
                )
                results.append(summary)
            except Exception as exc:
                logger.error("fsas_category_failed", category=category_name, error=str(exc))
                results.append({"category": category_name, "status": "error", "error": str(exc)})
        return results
