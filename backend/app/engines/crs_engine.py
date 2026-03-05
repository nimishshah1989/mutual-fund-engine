"""
engines/crs_engine.py

Composite Recommendation Score (CRS) — Layer 3 of the JIP Recommendation Engine.

CRS = QFS x qfs_weight + FSAS x fsas_weight (default 60/40).

After computing CRS, the tier engine assigns a tier (CORE / QUALITY / WATCH
/ CAUTION / EXIT) and action (BUY / SIP / HOLD / REDUCE / EXIT), then
applies hard override rules.

The engine is a pure computation module — it receives data, returns results.
All DB I/O is handled by the scoring_service orchestrator.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

import structlog

from app.engines.tier_engine import TierEngine

logger = structlog.get_logger(__name__)

# Current engine version — bump when algorithm changes
ENGINE_VERSION = "1.0.0"


class CRSEngine:
    """Computes Composite Recommendation Score and assigns tiers/actions."""

    DEFAULT_QFS_WEIGHT: float = 0.60
    DEFAULT_FSAS_WEIGHT: float = 0.40

    def __init__(self) -> None:
        self.tier_engine = TierEngine()

    def compute(
        self,
        qfs_scores: dict[str, dict[str, Any]],
        fsas_scores: dict[str, dict[str, Any]],
        fund_metadata: dict[str, dict[str, Any]],
        qfs_weight: Optional[float] = None,
        fsas_weight: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """
        Compute CRS for all funds that have BOTH QFS and FSAS scores.

        Args:
            qfs_scores: {mstar_id: {qfs, qfs_id, data_completeness_pct, ...}}
                Latest QFS results keyed by mstar_id.
            fsas_scores: {mstar_id: {fsas, fsas_id, avoid_exposure_pct, ...}}
                Latest FSAS results keyed by mstar_id.
            fund_metadata: {mstar_id: {inception_date, ...}}
                Fund master data needed for override checks.
            qfs_weight: Override the default QFS weight (0.60).
            fsas_weight: Override the default FSAS weight (0.40).

        Returns:
            List of dicts ready for fund_crs DB insert. One per fund.
        """
        effective_qfs_weight = qfs_weight or self.DEFAULT_QFS_WEIGHT
        effective_fsas_weight = fsas_weight or self.DEFAULT_FSAS_WEIGHT

        # Validate weights sum to 1.0 (with tolerance for floating point)
        weight_sum = effective_qfs_weight + effective_fsas_weight
        if abs(weight_sum - 1.0) > 0.01:
            logger.warning(
                "crs_weight_mismatch",
                qfs_weight=effective_qfs_weight,
                fsas_weight=effective_fsas_weight,
                sum=weight_sum,
            )

        # Find funds that have BOTH QFS and FSAS
        common_ids = set(qfs_scores.keys()) & set(fsas_scores.keys())

        if not common_ids:
            logger.warning(
                "crs_no_common_funds",
                qfs_count=len(qfs_scores),
                fsas_count=len(fsas_scores),
            )
            return []

        logger.info(
            "crs_compute_start",
            fund_count=len(common_ids),
            qfs_weight=effective_qfs_weight,
            fsas_weight=effective_fsas_weight,
        )

        today = date.today()
        results: list[dict[str, Any]] = []

        for mstar_id in sorted(common_ids):
            qfs_data = qfs_scores[mstar_id]
            fsas_data = fsas_scores[mstar_id]

            qfs_value = float(qfs_data.get("qfs", 0.0))
            fsas_value = float(fsas_data.get("fsas", 0.0))

            # CRS = QFS * weight + FSAS * weight
            crs = (qfs_value * effective_qfs_weight) + (
                fsas_value * effective_fsas_weight
            )
            crs = round(crs, 4)

            # Assign tier and action from CRS
            tier = self.tier_engine.assign_tier(crs)
            action = self.tier_engine.assign_action(tier)

            # Build fund data dict for override checks
            metadata = fund_metadata.get(mstar_id, {})
            override_fund_data: dict[str, Any] = {
                "avoid_exposure_pct": float(
                    fsas_data.get("avoid_exposure_pct", 0.0)
                ),
                "inception_date": metadata.get("inception_date"),
                "data_completeness_pct": float(
                    qfs_data.get("data_completeness_pct", 100.0)
                ),
                "reference_date": today,
            }

            # Apply hard override rules
            (
                final_tier,
                final_action,
                override_applied,
                override_reason,
                override_flag,
            ) = self.tier_engine.apply_overrides(tier, action, override_fund_data)

            # Generate human-readable rationale
            rationale = self.tier_engine.generate_rationale(
                tier=final_tier,
                action=final_action,
                crs=crs,
                qfs=qfs_value,
                fsas=fsas_value,
                override_reason=override_reason,
            )

            results.append({
                "mstar_id": mstar_id,
                "computed_date": today,
                "qfs": qfs_value,
                "fsas": fsas_value,
                "qfs_weight": effective_qfs_weight,
                "fsas_weight": effective_fsas_weight,
                "crs": crs,
                "tier": final_tier,
                "action": final_action,
                "override_applied": override_applied,
                "override_reason": override_reason,
                "original_tier": tier if override_applied else None,
                "action_rationale": rationale,
                "qfs_id": qfs_data.get("qfs_id"),
                "fsas_id": fsas_data.get("fsas_id"),
                "engine_version": ENGINE_VERSION,
            })

        # Log summary statistics
        tier_counts: dict[str, int] = {}
        override_count = 0
        for result in results:
            tier_name = result["tier"]
            tier_counts[tier_name] = tier_counts.get(tier_name, 0) + 1
            if result["override_applied"]:
                override_count += 1

        logger.info(
            "crs_compute_complete",
            fund_count=len(results),
            tier_distribution=tier_counts,
            override_count=override_count,
            avg_crs=round(
                sum(r["crs"] for r in results) / len(results), 2
            ) if results else 0.0,
        )

        return results
