"""
services/scoring_pipeline.py

Full pipeline orchestrator and recommendation assignment.

Handles:
  - assign_recommendations: Tier/action assignment based on QFS percentile (4 actions: ACCUMULATE, HOLD, REDUCE, EXIT)
  - compute_full_pipeline: QFS -> shortlist -> FSAS -> recommend
  - compute_full_pipeline_all_categories: Pipeline for all categories

Note: FSAS no longer refines actions. Actions map directly from tier.
FSAS is still computed and displayed for sector alignment context.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any, Optional

import structlog

if TYPE_CHECKING:
    from app.services.scoring_service import ScoringService

logger = structlog.get_logger(__name__)


class ScoringPipeline:
    """Orchestrates the full scoring pipeline and recommendation assignment."""

    def __init__(self, service: ScoringService) -> None:
        self.service = service

    async def assign_recommendations(
        self, trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """
        Assign tiers and actions based on QFS percentile rank within each category.
        For shortlisted funds, refine actions with FSAS context.
        """
        today = date.today()
        logger.info("recommendation_assignment_start", trigger=trigger_event)

        svc = self.service
        categories = await svc.data_loader.get_eligible_categories()
        all_recommendations: list[dict[str, Any]] = []
        tier_distribution: dict[str, int] = {}
        override_count = 0
        shortlisted_count = 0

        shortlisted_mstar_ids = set(await svc.score_repo.get_shortlisted_mstar_ids())

        for category_name in categories:
            fund_ids = await svc.data_loader.load_eligible_fund_ids(category_name)
            if not fund_ids:
                continue

            qfs_records = await svc.score_repo.get_latest_qfs_by_mstar_ids(fund_ids)
            if not qfs_records:
                continue

            sorted_records = sorted(
                qfs_records,
                key=lambda r: float(r.qfs) if r.qfs is not None else 0.0,
                reverse=True,
            )
            total_in_category = len(sorted_records)

            shortlisted_in_cat = [
                r.mstar_id for r in sorted_records if r.mstar_id in shortlisted_mstar_ids
            ]
            fsas_lookup: dict[str, float] = {}
            avoid_lookup: dict[str, float] = {}

            if shortlisted_in_cat:
                fsas_records = await svc.score_repo.get_latest_fsas_by_mstar_ids(shortlisted_in_cat)
                for f in fsas_records:
                    fsas_lookup[f.mstar_id] = float(f.fsas) if f.fsas is not None else 0.0
                    avoid_lookup[f.mstar_id] = (
                        float(f.avoid_exposure_pct) if f.avoid_exposure_pct is not None else 0.0
                    )

            fund_metadata = await svc.data_loader.load_fund_metadata(fund_ids)

            for rank, record in enumerate(sorted_records, start=1):
                rec = self._build_recommendation(
                    record=record, rank=rank, total_in_category=total_in_category,
                    today=today, shortlisted_mstar_ids=shortlisted_mstar_ids,
                    fsas_lookup=fsas_lookup, avoid_lookup=avoid_lookup,
                    fund_metadata=fund_metadata,
                )
                if rec["override_applied"]:
                    override_count += 1
                if rec["is_shortlisted"]:
                    shortlisted_count += 1
                all_recommendations.append(rec)
                tier_distribution[rec["tier"]] = tier_distribution.get(rec["tier"], 0) + 1

        if all_recommendations:
            rows_affected = await svc.score_repo.bulk_upsert_recommendations(all_recommendations)
        else:
            rows_affected = 0

        logger.info(
            "recommendation_assignment_complete",
            fund_count=len(all_recommendations), rows_upserted=rows_affected,
            tier_distribution=tier_distribution, override_count=override_count,
            shortlisted_count=shortlisted_count,
        )
        return {
            "fund_count": len(all_recommendations), "rows_upserted": rows_affected,
            "tier_distribution": tier_distribution, "override_count": override_count,
            "shortlisted_count": shortlisted_count, "computed_date": str(today),
            "status": "completed",
        }

    def _build_recommendation(
        self,
        record: Any,
        rank: int,
        total_in_category: int,
        today: date,
        shortlisted_mstar_ids: set[str],
        fsas_lookup: dict[str, float],
        avoid_lookup: dict[str, float],
        fund_metadata: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Build a single recommendation dict for one fund."""
        mstar_id = record.mstar_id
        qfs_value = float(record.qfs) if record.qfs is not None else 0.0
        data_completeness = (
            float(record.data_completeness_pct)
            if record.data_completeness_pct is not None else 100.0
        )

        if total_in_category > 1:
            percentile = (total_in_category - rank) / (total_in_category - 1) * 100.0
            # Compress to [20, 80] for tiny categories — prevents CORE/EXIT from
            # minimal peer differences when the sample size is unreliable
            if total_in_category < 5:
                percentile = 20.0 + (percentile / 100.0) * 60.0
        else:
            percentile = 50.0

        tier_engine = self.service.tier_engine
        tier = tier_engine.assign_tier_by_percentile(percentile)
        action = tier_engine.assign_action(tier)

        is_shortlisted = mstar_id in shortlisted_mstar_ids
        fsas_value = fsas_lookup.get(mstar_id) if is_shortlisted else None
        avoid_pct = avoid_lookup.get(mstar_id, 0.0)

        # Actions are now determined directly by tier (no FSAS refinement).
        # FSAS data is still computed and displayed for sector alignment context.

        metadata = fund_metadata.get(mstar_id, {})
        override_fund_data: dict[str, Any] = {
            "avoid_exposure_pct": avoid_pct,
            "inception_date": metadata.get("inception_date"),
            "data_completeness_pct": data_completeness,
            "reference_date": today,
        }

        final_tier, final_action, applied_override, override_reason, _flag = (
            tier_engine.apply_overrides(tier, action, override_fund_data)
        )
        rationale = tier_engine.generate_rationale(
            tier=final_tier, action=final_action, qfs=qfs_value, percentile=percentile,
            fsas=fsas_value, override_reason=override_reason, is_shortlisted=is_shortlisted,
        )

        return {
            "mstar_id": mstar_id, "computed_date": today,
            "qfs": qfs_value, "fsas": fsas_value,
            "qfs_rank": rank, "category_rank_pct": round(percentile, 2),
            "is_shortlisted": is_shortlisted,
            "tier": final_tier, "action": final_action,
            "override_applied": applied_override, "override_reason": override_reason,
            "original_tier": tier if applied_override else None,
            "action_rationale": rationale,
            "qfs_id": record.id, "fsas_id": None,
            "engine_version": "2.0.0",
        }

    async def compute_full_pipeline(
        self,
        category_name: Optional[str] = None,
        trigger_event: str = "full_pipeline",
        shortlist_n: int = 5,
    ) -> dict[str, Any]:
        """
        Run the complete scoring pipeline:
        1. QFS for all categories (or one specific category)
        2. Generate shortlist (top N per category)
        3. FSAS for shortlisted funds only
        4. Assign tiers and actions for all funds
        """
        logger.info("full_pipeline_start", category=category_name, trigger=trigger_event)
        svc = self.service

        pipeline_results: dict[str, Any] = {
            "category": category_name or "all",
            "trigger_event": trigger_event,
            "computed_date": str(date.today()),
            "layers": {},
        }

        # Layer 1: QFS
        try:
            if category_name:
                qfs_summary = await svc.compute_qfs_for_category(
                    category_name=category_name, trigger_event=trigger_event,
                )
                pipeline_results["layers"]["qfs"] = [qfs_summary]
            else:
                qfs_summaries = await svc.compute_qfs_for_all_categories(
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
            shortlist_summary = await svc.generate_shortlist(
                shortlist_n=shortlist_n, trigger_event=trigger_event,
            )
            pipeline_results["layers"]["shortlist"] = shortlist_summary
        except Exception as exc:
            logger.error("pipeline_shortlist_failed", error=str(exc))
            pipeline_results["layers"]["shortlist"] = {"status": "error", "error": str(exc)}
            pipeline_results["status"] = "partial_failure"
            return pipeline_results

        # Layer 2b: FSAS for shortlisted funds
        try:
            fsas_summary = await svc.compute_fsas_for_shortlisted(trigger_event=trigger_event)
            pipeline_results["layers"]["fsas"] = fsas_summary
        except Exception as exc:
            logger.error("pipeline_fsas_failed", error=str(exc))
            pipeline_results["layers"]["fsas"] = {"status": "error", "error": str(exc)}
            # FSAS failure is non-fatal — recommendations still work via QFS percentile alone

        # Layer 3: Assign tiers and actions
        try:
            rec_summary = await self.assign_recommendations(trigger_event=trigger_event)
            pipeline_results["layers"]["recommendation"] = rec_summary
        except Exception as exc:
            logger.error("pipeline_recommendation_failed", error=str(exc))
            pipeline_results["layers"]["recommendation"] = {"status": "error", "error": str(exc)}
            pipeline_results["status"] = "partial_failure"
            return pipeline_results

        total_funds = rec_summary.get("fund_count", 0)
        pipeline_results["status"] = "completed"
        pipeline_results["fund_count"] = total_funds
        pipeline_results["tier_distribution"] = rec_summary.get("tier_distribution", {})
        pipeline_results["shortlisted_count"] = rec_summary.get("shortlisted_count", 0)

        logger.info(
            "full_pipeline_complete",
            fund_count=total_funds, shortlisted=rec_summary.get("shortlisted_count", 0),
        )
        return pipeline_results

    async def compute_full_pipeline_all_categories(
        self, trigger_event: str = "scheduled_full_pipeline",
    ) -> list[dict[str, Any]]:
        """Run the complete pipeline for all categories."""
        result = await self.compute_full_pipeline(
            category_name=None, trigger_event=trigger_event,
        )
        return [result]
