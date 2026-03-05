"""
engines/tier_engine.py

Tier Assignment + Hard Override Rules for the JIP Recommendation Engine.

Takes a CRS score and assigns a tier (CORE / QUALITY / WATCH / CAUTION / EXIT)
and an action (BUY / SIP / HOLD / REDUCE / EXIT). Then applies hard override
rules that can DOWNGRADE a tier (never upgrade).

Hard Override Rules:
    1. AVOID exposure > 25% → force to CAUTION minimum
    2. Manager tenure < 12 months → force to WATCH minimum (uses inception_date)
    3. Data completeness < 60% → force to WATCH minimum + flag INSUFFICIENT_DATA
    4. Emerging fund (< 36 months) → force to WATCH minimum + flag EMERGING_FUND

Override rules can only downgrade — if a fund is already at CAUTION and an
override would push to WATCH, CAUTION stays because CAUTION is lower.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


class TierEngine:
    """Assigns tier, action, and applies hard override rules."""

    # Tier thresholds — ordered highest first.
    # CRS >= threshold → assigned that tier. Below 20 → EXIT.
    TIER_THRESHOLDS: list[Tuple[str, int]] = [
        ("CORE", 72),
        ("QUALITY", 55),
        ("WATCH", 38),
        ("CAUTION", 20),
    ]

    # Tier → recommended action
    TIER_ACTIONS: dict[str, str] = {
        "CORE": "BUY",
        "QUALITY": "SIP",
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
    AVOID_EXPOSURE_THRESHOLD: float = 25.0  # percentage
    MANAGER_TENURE_MONTHS: int = 12
    DATA_COMPLETENESS_THRESHOLD: float = 60.0  # percentage
    FUND_AGE_MONTHS: int = 36

    def assign_tier(self, crs: float) -> str:
        """
        Assign a tier based on the CRS score.

        Args:
            crs: Composite Recommendation Score (0-100).

        Returns:
            Tier string: CORE, QUALITY, WATCH, CAUTION, or EXIT.
        """
        for tier_name, threshold in self.TIER_THRESHOLDS:
            if crs >= threshold:
                return tier_name
        return "EXIT"

    def assign_action(self, tier: str) -> str:
        """
        Map a tier to its recommended action.

        Args:
            tier: One of CORE, QUALITY, WATCH, CAUTION, EXIT.

        Returns:
            Action string: BUY, SIP, HOLD, REDUCE, or EXIT.
        """
        return self.TIER_ACTIONS.get(tier, "HOLD")

    def apply_overrides(
        self,
        tier: str,
        action: str,
        fund_data: dict[str, Any],
    ) -> Tuple[str, str, bool, Optional[str], Optional[str]]:
        """
        Apply hard override rules that can DOWNGRADE a tier (never upgrade).

        Four rules are checked in sequence. If multiple rules trigger,
        the most severe downgrade wins.

        Args:
            tier: Current tier from CRS-based assignment.
            action: Current action from tier mapping.
            fund_data: Dict containing fund metadata needed for override checks:
                - avoid_exposure_pct (float): % of portfolio in AVOID sectors
                - inception_date (date or None): fund inception date
                - data_completeness_pct (float): QFS data completeness
                - reference_date (date): current date for age calculations

        Returns:
            Tuple of (final_tier, final_action, override_applied, override_reason,
                      override_flag).
            override_flag is a machine-readable label like "INSUFFICIENT_DATA"
            or "EMERGING_FUND".
        """
        original_tier = tier
        override_applied = False
        override_reasons: list[str] = []
        override_flag: Optional[str] = None

        # Current tier rank (lower = better)
        current_rank = self.TIER_RANK.get(tier, 4)

        # Rule 1: AVOID exposure > 25% → force to CAUTION minimum
        avoid_exposure = fund_data.get("avoid_exposure_pct", 0.0)
        if avoid_exposure > self.AVOID_EXPOSURE_THRESHOLD:
            caution_rank = self.TIER_RANK["CAUTION"]
            if current_rank < caution_rank:
                current_rank = caution_rank
                override_reasons.append(
                    f"High AVOID sector exposure ({avoid_exposure:.1f}% > "
                    f"{self.AVOID_EXPOSURE_THRESHOLD}%)"
                )

        # Rule 2: Manager tenure < 12 months → force to WATCH minimum
        # Uses inception_date from fund_master as proxy for FM tenure
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
                        f"Manager tenure < {self.MANAGER_TENURE_MONTHS} months "
                        f"(~{months_active} months)"
                    )

        # Rule 3: Data completeness < 60% → force to WATCH minimum + flag
        data_completeness = fund_data.get("data_completeness_pct", 100.0)
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
                # EMERGING_FUND flag takes precedence only if no other flag set
                if override_flag is None:
                    override_flag = "EMERGING_FUND"

        # Determine final tier from the (possibly downgraded) rank
        final_tier = tier
        if current_rank > self.TIER_RANK.get(tier, 4):
            # Tier was downgraded — find the tier name for the new rank
            for tier_name, rank in self.TIER_RANK.items():
                if rank == current_rank:
                    final_tier = tier_name
                    break
            override_applied = True

        # If overrides were applied via the flag rules but rank didn't change
        # (fund was already at or below WATCH), still mark override_applied
        # if there are any reasons collected
        if override_reasons and not override_applied:
            # Check if any reason was actually triggered for a fund at/below threshold
            # In this case, we log the flag but don't change the tier
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
        self,
        tier: str,
        action: str,
        crs: float,
        qfs: float,
        fsas: float,
        override_reason: Optional[str],
    ) -> str:
        """
        Generate a human-readable rationale for the tier/action assignment.

        This text is stored in fund_crs.action_rationale and displayed
        in the fund detail UI.

        Args:
            tier: Final tier after overrides.
            action: Final action.
            crs: Composite Recommendation Score.
            qfs: Quantitative Fund Score (Layer 1).
            fsas: FM Sector Alignment Score (Layer 2).
            override_reason: Human-readable override reason, if any.

        Returns:
            A concise rationale string.
        """
        # Describe the score components
        parts: list[str] = []

        parts.append(
            f"CRS {crs:.1f} (QFS {qfs:.1f} x 60% + FSAS {fsas:.1f} x 40%)"
        )

        # Describe the tier assignment
        parts.append(f"assigns to {tier} tier with {action} recommendation")

        # Add score quality commentary
        if qfs >= 70 and fsas >= 70:
            parts.append(
                "Strong quantitative metrics combined with favorable "
                "sector alignment."
            )
        elif qfs >= 70 and fsas < 40:
            parts.append(
                "Strong quantitative metrics but poor alignment with current "
                "FM sector views."
            )
        elif qfs < 40 and fsas >= 70:
            parts.append(
                "Weak quantitative metrics despite favorable sector alignment."
            )
        elif qfs < 40 and fsas < 40:
            parts.append(
                "Weak quantitative metrics compounded by unfavorable "
                "sector positioning."
            )
        else:
            parts.append(
                "Moderate risk-return profile with mixed sector alignment."
            )

        # Append override information if applicable
        if override_reason:
            parts.append(f"Override applied: {override_reason}.")

        return " ".join(parts)
