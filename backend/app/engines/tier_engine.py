"""
engines/tier_engine.py

Tier Assignment + Hard Override Rules for the JIP Recommendation Engine.

NEW (v2): Tiers are assigned based on QFS percentile rank within category,
not on an absolute CRS threshold. This means a fund's tier depends on how
it compares to peers in the same SEBI category.

Percentile Ranges:
    90-100 → CORE (top 10%)
    70-89  → QUALITY
    40-69  → WATCH
    20-39  → CAUTION
    0-19   → EXIT

Hard Override Rules (can only DOWNGRADE, never upgrade):
    1. AVOID exposure > 25% → force to CAUTION minimum
    2. Manager tenure < 12 months → force to WATCH minimum (uses inception_date)
    3. Data completeness < 60% → force to WATCH minimum + flag INSUFFICIENT_DATA
    4. Emerging fund (< 36 months) → force to WATCH minimum + flag EMERGING_FUND
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


class TierEngine:
    """Assigns tier, action, and applies hard override rules based on QFS percentile rank."""

    # Percentile-based tier thresholds — percentile >= threshold → assigned that tier
    # Ordered highest first. Below 20 → EXIT.
    TIER_PERCENTILE_THRESHOLDS: list[tuple[str, Decimal]] = [
        ("CORE", Decimal("90")),
        ("QUALITY", Decimal("70")),
        ("WATCH", Decimal("40")),
        ("CAUTION", Decimal("20")),
    ]

    # Tier → recommended action (simplified 4-action system)
    TIER_ACTIONS: dict[str, str] = {
        "CORE": "ACCUMULATE",
        "QUALITY": "ACCUMULATE",
        "WATCH": "HOLD",
        "CAUTION": "REDUCE",
        "EXIT": "EXIT",
    }

    # Tier rank — lower number = better tier (used for override comparisons)
    TIER_RANK: dict[str, int] = {
        "CORE": 0,
        "QUALITY": 1,
        "WATCH": 2,
        "CAUTION": 3,
        "EXIT": 4,
    }

    # Override thresholds
    AVOID_EXPOSURE_THRESHOLD: Decimal = Decimal("25")
    MANAGER_TENURE_MONTHS: int = 12
    DATA_COMPLETENESS_THRESHOLD: Decimal = Decimal("60")
    FUND_AGE_MONTHS: int = 36

    def assign_tier_by_percentile(self, percentile: Decimal) -> str:
        """Assign tier based on QFS percentile rank (0-100) within category."""
        for tier_name, threshold in self.TIER_PERCENTILE_THRESHOLDS:
            if percentile >= threshold:
                return tier_name
        return "EXIT"

    def assign_action(self, tier: str) -> str:
        """Map a tier to its recommended action."""
        return self.TIER_ACTIONS.get(tier, "HOLD")

    def apply_overrides(
        self,
        tier: str,
        action: str,
        fund_data: dict[str, Any],
    ) -> tuple[str, str, bool, Optional[str], Optional[str]]:
        """
        Apply hard override rules that can DOWNGRADE a tier (never upgrade).

        Four rules are checked in sequence. If multiple rules trigger,
        the most severe downgrade wins.

        Args:
            tier: Current tier from QFS percentile-based assignment.
            action: Current action from tier mapping.
            fund_data: Dict containing fund metadata needed for override checks:
                - avoid_exposure_pct (float): % of portfolio in AVOID sectors
                - inception_date (date or None): fund inception date
                - data_completeness_pct (float): QFS data completeness
                - reference_date (date): current date for age calculations

        Returns:
            Tuple of (final_tier, final_action, override_applied, override_reason,
                      override_flag).
        """
        original_tier = tier
        override_applied = False
        override_reasons: list[str] = []
        override_flag: Optional[str] = None

        # Current tier rank (lower = better)
        current_rank = self.TIER_RANK.get(tier, 4)

        # Rule 1: AVOID exposure > 25% → force to CAUTION minimum
        avoid_exposure = fund_data.get("avoid_exposure_pct", Decimal("0"))
        if avoid_exposure > self.AVOID_EXPOSURE_THRESHOLD:
            caution_rank = self.TIER_RANK["CAUTION"]
            if current_rank < caution_rank:
                current_rank = caution_rank
                override_reasons.append(
                    f"High AVOID sector exposure ({avoid_exposure:.1f}% > "
                    f"{self.AVOID_EXPOSURE_THRESHOLD}%)"
                )

        # Rule 2: Fund too young (< 12 months since inception) → force to WATCH minimum
        # Note: uses inception_date as proxy — actual manager tenure data not available
        inception_date = fund_data.get("inception_date")
        reference_date = fund_data.get("reference_date", date.today())
        if inception_date is not None:
            tenure_cutoff = reference_date - timedelta(
                days=self.MANAGER_TENURE_MONTHS * 30
            )
            if inception_date > tenure_cutoff:
                watch_rank = self.TIER_RANK["WATCH"]
                if current_rank < watch_rank:
                    current_rank = watch_rank
                    months_active = (
                        (reference_date.year - inception_date.year) * 12
                        + (reference_date.month - inception_date.month)
                    )
                    override_reasons.append(
                        f"Fund age < {self.MANAGER_TENURE_MONTHS} months "
                        f"since inception (~{months_active} months)"
                    )

        # Rule 3: Data completeness < 60% → force to WATCH minimum + flag
        data_completeness = fund_data.get("data_completeness_pct", Decimal("100"))
        if data_completeness < self.DATA_COMPLETENESS_THRESHOLD:
            watch_rank = self.TIER_RANK["WATCH"]
            if current_rank < watch_rank:
                current_rank = watch_rank
            override_reasons.append(
                f"Low data completeness ({data_completeness:.1f}% < "
                f"{self.DATA_COMPLETENESS_THRESHOLD}%)"
            )
            override_flag = "INSUFFICIENT_DATA"

        # Rule 4: Emerging fund (< 36 months old) → force to WATCH minimum + flag
        if inception_date is not None:
            age_cutoff = reference_date - timedelta(
                days=self.FUND_AGE_MONTHS * 30
            )
            if inception_date > age_cutoff:
                watch_rank = self.TIER_RANK["WATCH"]
                if current_rank < watch_rank:
                    current_rank = watch_rank
                fund_age_months = (
                    (reference_date.year - inception_date.year) * 12
                    + (reference_date.month - inception_date.month)
                )
                override_reasons.append(
                    f"Emerging fund ({fund_age_months} months < "
                    f"{self.FUND_AGE_MONTHS} months)"
                )
                if override_flag is None:
                    override_flag = "EMERGING_FUND"

        # Determine final tier from the (possibly downgraded) rank
        final_tier = tier
        if current_rank > self.TIER_RANK.get(tier, 4):
            for tier_name, rank in self.TIER_RANK.items():
                if rank == current_rank:
                    final_tier = tier_name
                    break
            override_applied = True

        # If overrides triggered flags but rank didn't change, still mark
        if override_reasons and not override_applied:
            if override_flag is not None:
                override_applied = True

        final_action = self.assign_action(final_tier)
        override_reason = "; ".join(override_reasons) if override_reasons else None

        if override_applied:
            logger.debug(
                "tier_override_applied",
                original_tier=original_tier,
                final_tier=final_tier,
                reason=override_reason,
                flag=override_flag,
            )

        return final_tier, final_action, override_applied, override_reason, override_flag

    def generate_rationale(
        self, tier: str, action: str, qfs: Decimal, percentile: Decimal,
        fsas: Optional[Decimal], override_reason: Optional[str],
        is_shortlisted: bool = False,
        matrix_position: Optional[str] = None,
        fms_percentile: Optional[Decimal] = None,
    ) -> str:
        """Generate a human-readable rationale for the tier/action assignment."""
        parts: list[str] = []

        # v3 Decision Matrix rationale
        if matrix_position is not None and fms_percentile is not None:
            parts.append(
                f"QFS {qfs:.1f} ({percentile:.0f}th pctl) + "
                f"FM Alignment ({fms_percentile:.0f}th pctl)"
            )
            parts.append(f"places fund in {matrix_position} cell →")
            parts.append(f"{tier} tier, {action} recommendation.")

            if fsas is not None:
                if fsas >= 70:
                    parts.append(
                        f"Strong FM alignment ({fsas:.1f}) supports conviction."
                    )
                elif fsas >= 40:
                    parts.append(
                        f"Moderate FM alignment ({fsas:.1f})."
                    )
                else:
                    parts.append(
                        f"Weak FM alignment ({fsas:.1f}) — "
                        "misaligned with current FM sector views."
                    )
        else:
            # Legacy v2 rationale (no matrix data)
            parts.append(
                f"Fund Score {qfs:.1f} (percentile {percentile:.0f}th in category)"
            )
            parts.append(f"assigns to {tier} tier with {action} recommendation.")

            if is_shortlisted and fsas is not None:
                if fsas >= 70:
                    parts.append(
                        f"Strong sector alignment ({fsas:.1f}) supports conviction."
                    )
                elif fsas >= 40:
                    parts.append(
                        f"Moderate sector alignment ({fsas:.1f})."
                    )
                else:
                    parts.append(
                        f"Weak sector alignment ({fsas:.1f}) — "
                        "misaligned with current FM sector views."
                    )
            elif not is_shortlisted:
                parts.append("Not shortlisted — sector alignment not computed.")

        if override_reason:
            parts.append(f"Override applied: {override_reason}.")

        return " ".join(parts)
