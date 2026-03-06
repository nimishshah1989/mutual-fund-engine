"""
services/scoring_pipeline.py

Full pipeline orchestrator and recommendation assignment.

v3 (Decision Matrix):
    NEW: QFS (all) -> FMS (all) -> Percentiles -> Matrix Classification -> Overrides -> Action
    OLD: QFS (all) -> Shortlist (top 5) -> FSAS (shortlisted) -> Tier by QFS pctl -> Action

The shortlist step is bypassed. FMS is computed for ALL funds.
Tier and action come from the 3x3 matrix, not QFS percentile alone.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any, Optional

import structlog

from app.engines.matrix_engine import MatrixEngine

if TYPE_CHECKING:
    from app.services.scoring_service import ScoringService

logger = structlog.get_logger(__name__)


class ScoringPipeline:
    """Orchestrates the full scoring pipeline and recommendation assignment."""

    def __init__(self, service: ScoringService) -> None:
        self.service = service

    async def assign_matrix_recommendations(
        self,
        benchmark_weights: Optional[dict[str, float]] = None,
        trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """
        v3: Assign tiers and actions based on 3x3 decision matrix.
        Both QFS and FMS percentiles determine the recommendation.
        """
        today = date.today()
        logger.info("matrix_recommendation_start", trigger=trigger_event)

        svc = self.service
        matrix_engine = svc.matrix_engine
        tier_engine = svc.tier_engine

        categories = await svc.data_loader.get_eligible_categories()
        all_recommendations: list[dict[str, Any]] = []
        action_distribution: dict[str, int] = {}
        override_count = 0
        fms_data_available = False

        for category_name in categories:
            fund_ids = await svc.data_loader.load_eligible_fund_ids(category_name)
            if not fund_ids:
                continue

            # Load QFS scores for all funds in category
            qfs_records = await svc.score_repo.get_latest_qfs_by_mstar_ids(fund_ids)
            if not qfs_records:
                continue

            # Load FMS scores for all funds in category
            fsas_records = await svc.score_repo.get_latest_fsas_by_mstar_ids(fund_ids)
            fsas_lookup: dict[str, float] = {}
            avoid_lookup: dict[str, float] = {}
            for f in fsas_records:
                fsas_lookup[f.mstar_id] = float(f.fsas) if f.fsas is not None else 0.0
                avoid_lookup[f.mstar_id] = (
                    float(f.avoid_exposure_pct) if f.avoid_exposure_pct is not None else 0.0
                )

            if fsas_lookup:
                fms_data_available = True
            else:
                logger.warning(
                    "matrix_no_fms_data_for_category",
                    category=category_name,
                    fund_count=len(fund_ids),
                    message="All funds will get midpoint FMS percentile (50.0)",
                )

            # Sort by QFS descending for rank assignment
            sorted_qfs = sorted(
                qfs_records,
                key=lambda r: float(r.qfs) if r.qfs is not None else 0.0,
                reverse=True,
            )
            total_in_category = len(sorted_qfs)

            # Compute QFS percentiles
            qfs_percentiles: dict[str, float] = {}
            for rank, record in enumerate(sorted_qfs, start=1):
                qfs_percentiles[record.mstar_id] = self._compute_percentile(
                    rank, total_in_category
                )

            # Compute FMS percentiles
            fms_percentiles = self._compute_fms_percentiles(
                fund_ids, fsas_lookup
            )

            # Load fund metadata for overrides
            fund_metadata = await svc.data_loader.load_fund_metadata(fund_ids)

            for rank, record in enumerate(sorted_qfs, start=1):
                mstar_id = record.mstar_id
                qfs_value = float(record.qfs) if record.qfs is not None else 0.0
                qfs_pctl = qfs_percentiles[mstar_id]
                fms_pctl = fms_percentiles.get(mstar_id, 50.0)
                fms_value = fsas_lookup.get(mstar_id)

                # Matrix classification
                classification = matrix_engine.classify(qfs_pctl, fms_pctl)

                # Override checks
                data_completeness = (
                    float(record.data_completeness_pct)
                    if record.data_completeness_pct is not None else 100.0
                )
                metadata = fund_metadata.get(mstar_id, {})
                override_fund_data: dict[str, Any] = {
                    "avoid_exposure_pct": avoid_lookup.get(mstar_id, 0.0),
                    "inception_date": metadata.get("inception_date"),
                    "data_completeness_pct": data_completeness,
                    "reference_date": today,
                }

                matrix_tier = classification["tier"]
                matrix_action = classification["action"]

                final_tier, final_action, applied_override, override_reason, _flag = (
                    tier_engine.apply_overrides(
                        matrix_tier, matrix_action, override_fund_data,
                    )
                )

                if applied_override:
                    override_count += 1

                rationale = tier_engine.generate_rationale(
                    tier=final_tier, action=final_action, qfs=qfs_value,
                    percentile=qfs_pctl, fsas=fms_value,
                    override_reason=override_reason,
                    matrix_position=classification["matrix_position"],
                    fms_percentile=fms_pctl,
                )

                rec = {
                    "mstar_id": mstar_id,
                    "computed_date": today,
                    "qfs": qfs_value,
                    "fsas": fms_value,
                    "qfs_rank": rank,
                    "category_rank_pct": round(qfs_pctl, 2),
                    "is_shortlisted": False,
                    # v3 matrix fields
                    "fm_score": fms_value,
                    "fm_score_percentile": round(fms_pctl, 2),
                    "qfs_percentile": round(qfs_pctl, 2),
                    "matrix_row": classification["matrix_row"],
                    "matrix_col": classification["matrix_col"],
                    "matrix_position": classification["matrix_position"],
                    # Classification
                    "tier": final_tier,
                    "action": final_action,
                    "override_applied": applied_override,
                    "override_reason": override_reason,
                    "original_tier": matrix_tier if applied_override else None,
                    "action_rationale": rationale,
                    "qfs_id": record.id,
                    "fsas_id": None,
                    "engine_version": "3.0.0",
                }
                all_recommendations.append(rec)
                action_distribution[final_action] = action_distribution.get(final_action, 0) + 1

        if all_recommendations:
            rows_affected = await svc.score_repo.bulk_upsert_recommendations(
                all_recommendations
            )
        else:
            rows_affected = 0

        # Build tier distribution from action distribution
        tier_distribution: dict[str, int] = {}
        for rec in all_recommendations:
            tier_distribution[rec["tier"]] = tier_distribution.get(rec["tier"], 0) + 1

        logger.info(
            "matrix_recommendation_complete",
            fund_count=len(all_recommendations),
            rows_upserted=rows_affected,
            action_distribution=action_distribution,
            tier_distribution=tier_distribution,
            override_count=override_count,
        )

        result: dict[str, Any] = {
            "fund_count": len(all_recommendations),
            "rows_upserted": rows_affected,
            "tier_distribution": tier_distribution,
            "action_distribution": action_distribution,
            "override_count": override_count,
            "computed_date": str(today),
            "status": "completed",
            "fms_data_available": fms_data_available,
        }

        if not fms_data_available:
            logger.warning(
                "matrix_recommendation_no_fms",
                message="No FMS data available — all funds assigned midpoint FMS percentile (50.0). "
                        "Set FM sector signals on the Signals page to enable FMS scoring.",
            )

        return result

    def _compute_percentile(self, rank: int, total: int) -> float:
        """Compute percentile from rank and total. Compresses small categories."""
        if total <= 1:
            return 50.0
        percentile = (total - rank) / (total - 1) * 100.0
        # Compress to [20, 80] for tiny categories
        if total < 5:
            percentile = 20.0 + (percentile / 100.0) * 60.0
        return percentile

    def _compute_fms_percentiles(
        self,
        fund_ids: list[str],
        fms_lookup: dict[str, float],
    ) -> dict[str, float]:
        """Compute FMS percentile ranks within the fund set."""
        # Build sorted list of (mstar_id, fms_value)
        scored_funds = [
            (mid, fms_lookup.get(mid, 0.0))
            for mid in fund_ids
            if mid in fms_lookup
        ]
        if not scored_funds:
            return {mid: 50.0 for mid in fund_ids}

        scored_funds.sort(key=lambda x: x[1], reverse=True)
        total = len(scored_funds)

        percentiles: dict[str, float] = {}
        for rank, (mstar_id, _fms) in enumerate(scored_funds, start=1):
            percentiles[mstar_id] = self._compute_percentile(rank, total)

        # Funds without FMS get midpoint
        for mid in fund_ids:
            if mid not in percentiles:
                percentiles[mid] = 50.0

        return percentiles

    # ===================================================================
    # Legacy method — kept for backward compat but delegates to matrix
    # ===================================================================

    async def assign_recommendations(
        self, trigger_event: str = "manual_compute",
    ) -> dict[str, Any]:
        """Legacy entry point — now delegates to assign_matrix_recommendations."""
        return await self.assign_matrix_recommendations(
            trigger_event=trigger_event,
        )

    # ===================================================================
    # Full pipeline
    # ===================================================================

    async def compute_full_pipeline(
        self,
        category_name: Optional[str] = None,
        trigger_event: str = "full_pipeline",
        shortlist_n: int = 5,
    ) -> dict[str, Any]:
        """
        v3 pipeline: QFS (all) -> FMS (all) -> Matrix -> Overrides -> Action.

        Shortlist generation is skipped. shortlist_n param kept for API compat
        but is not used.
        """
        logger.info(
            "full_pipeline_start",
            category=category_name,
            trigger=trigger_event,
            pipeline_version="v3_matrix",
        )
        svc = self.service

        warnings: list[str] = []

        pipeline_results: dict[str, Any] = {
            "category": category_name or "all",
            "trigger_event": trigger_event,
            "computed_date": str(date.today()),
            "pipeline_version": "v3_matrix",
            "layers": {},
            "warnings": warnings,
        }

        # Layer 1: QFS for all funds
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

        # Auto-refresh benchmark weights if stale
        benchmark_weights = await svc.ensure_benchmark_weights()
        if not benchmark_weights:
            warnings.append(
                "Benchmark weights not available — refresh from System page or check Morningstar GSSB API"
            )
            logger.warning("pipeline_no_benchmark_weights")

        # Layer 2: FMS for ALL funds (no shortlist)
        try:
            if benchmark_weights:
                fms_summary = await svc.compute_fms_for_all_funds(
                    benchmark_weights=benchmark_weights,
                    trigger_event=trigger_event,
                )
            else:
                fms_summary = await svc.compute_fms_for_all_funds(
                    trigger_event=trigger_event,
                )
            pipeline_results["layers"]["fms"] = fms_summary

            # Check if FMS was skipped due to missing signals or exposure data
            if isinstance(fms_summary, dict):
                fms_status = fms_summary.get("status", "")
                fms_fund_count = fms_summary.get("fund_count", 0)
                if fms_status == "skipped" or fms_fund_count == 0:
                    reason = fms_summary.get("reason", "unknown")
                    if reason == "no_active_signals":
                        warnings.append(
                            "No FM sector signals configured — set signals on the Signals page to enable FMS scoring"
                        )
                    elif reason == "no_sector_exposure_data":
                        warnings.append(
                            "No sector exposure data for funds — run ingestion first to populate GSSB data"
                        )
                    elif reason == "no_eligible_funds":
                        warnings.append(
                            "No eligible funds found for FMS computation"
                        )
                    else:
                        warnings.append(
                            f"FMS computation returned 0 funds (reason: {reason})"
                        )
                    logger.warning(
                        "pipeline_fms_skipped",
                        status=fms_status,
                        reason=reason,
                        fund_count=fms_fund_count,
                    )
        except Exception as exc:
            logger.error("pipeline_fms_failed", error=str(exc))
            pipeline_results["layers"]["fms"] = {"status": "error", "error": str(exc)}
            warnings.append(f"FMS computation failed: {exc}")
            # FMS failure is non-fatal — matrix will use midpoint FMS

        # Layer 3: Matrix classification + overrides
        try:
            rec_summary = await self.assign_matrix_recommendations(
                benchmark_weights=benchmark_weights,
                trigger_event=trigger_event,
            )
            pipeline_results["layers"]["recommendation"] = rec_summary
        except Exception as exc:
            logger.error("pipeline_recommendation_failed", error=str(exc))
            pipeline_results["layers"]["recommendation"] = {
                "status": "error", "error": str(exc),
            }
            pipeline_results["status"] = "partial_failure"
            return pipeline_results

        total_funds = rec_summary.get("fund_count", 0)
        pipeline_results["status"] = "completed"
        pipeline_results["fund_count"] = total_funds
        pipeline_results["tier_distribution"] = rec_summary.get("tier_distribution", {})
        pipeline_results["action_distribution"] = rec_summary.get("action_distribution", {})

        logger.info(
            "full_pipeline_complete",
            fund_count=total_funds,
            pipeline_version="v3_matrix",
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
