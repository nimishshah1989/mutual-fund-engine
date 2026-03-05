"""
engines/fsas_engine.py

FM Sector Alignment Score (FSAS) — Layer 2 of the JIP Recommendation Engine.

Computes a forward-looking score based on how well a fund's sector allocation
aligns with the Fund Manager's active sector signals. Sectors the FM is
bullish on (OVERWEIGHT, ACCUMULATE) boost the score; sectors marked AVOID
or UNDERWEIGHT drag it down.

Algorithm:
    1. For each fund, iterate over its sector exposures
    2. Look up the FM signal for that sector
    3. contribution = exposure_pct * signal_weight * confidence_multiplier
    4. raw_fsas = sum of all sector contributions
    5. Track avoid_exposure_pct = total exposure in AVOID sectors
    6. Track stale_holdings_flag = holdings older than STALE_HOLDINGS_DAYS
    7. Normalize raw_fsas across all funds in the batch to 0-100

The engine is a pure computation module — it receives data, returns results.
All DB I/O is handled by the scoring_service orchestrator.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

import structlog

from app.engines.base_engine import min_max_normalise

logger = structlog.get_logger(__name__)

# Current engine version — bump when algorithm changes
ENGINE_VERSION = "1.0.0"


class FSASEngine:
    """Computes FM Sector Alignment Score for all funds in a batch."""

    # Signal → numeric weight (how the FM views the sector)
    SIGNAL_WEIGHTS: dict[str, float] = {
        "OVERWEIGHT": 1.0,
        "ACCUMULATE": 0.6,
        "NEUTRAL": 0.1,
        "UNDERWEIGHT": -0.5,
        "AVOID": -1.0,
    }

    # Confidence → multiplier (how sure the FM is about the signal)
    CONFIDENCE_MULTIPLIERS: dict[str, float] = {
        "HIGH": 1.3,
        "MEDIUM": 1.0,
        "LOW": 0.5,
    }

    # Holdings older than this are flagged as stale
    STALE_HOLDINGS_DAYS: int = 45

    def compute(
        self,
        fund_exposures: dict[str, list[dict[str, Any]]],
        active_signals: list[dict[str, Any]],
        reference_date: Optional[date] = None,
    ) -> list[dict[str, Any]]:
        """
        Compute FSAS for all funds in the provided exposure dict.

        Args:
            fund_exposures: {mstar_id: [{sector_name, exposure_pct, month_end_date}]}
                Each fund has a list of sector exposure records from the
                most recent holdings date.
            active_signals: [{sector_name, signal, signal_weight, confidence, effective_date}]
                Currently active FM signals. One per sector.
            reference_date: Date to use for stale holdings check.
                Defaults to today.

        Returns:
            List of dicts ready for fund_fsas DB insert. One per fund.
        """
        if not fund_exposures:
            logger.warning("fsas_no_funds")
            return []

        if reference_date is None:
            reference_date = date.today()

        # Build a lookup from sector_name → signal data for fast access
        signal_lookup: dict[str, dict[str, Any]] = {}
        for sig in active_signals:
            signal_lookup[sig["sector_name"]] = sig

        # Determine the FM signal date (the effective_date of the signal set)
        fm_signal_date = reference_date
        if active_signals:
            # Use the most recent effective_date from the signal set
            signal_dates = [
                sig["effective_date"]
                for sig in active_signals
                if sig.get("effective_date") is not None
            ]
            if signal_dates:
                fm_signal_date = max(signal_dates)

        logger.info(
            "fsas_compute_start",
            fund_count=len(fund_exposures),
            signal_count=len(active_signals),
            fm_signal_date=str(fm_signal_date),
        )

        # Step 1: Compute raw FSAS for each fund
        fund_results: list[dict[str, Any]] = []
        raw_fsas_values: list[Optional[float]] = []

        stale_cutoff = reference_date - timedelta(days=self.STALE_HOLDINGS_DAYS)

        for mstar_id, exposures in fund_exposures.items():
            if not exposures:
                # Fund has no sector exposure data at all
                fund_results.append(self._empty_result(
                    mstar_id, fm_signal_date, reference_date
                ))
                raw_fsas_values.append(None)
                continue

            raw_fsas = 0.0
            avoid_exposure_pct = 0.0
            sector_contributions: dict[str, dict[str, Any]] = {}
            holdings_date: Optional[date] = None

            for exposure in exposures:
                sector_name = exposure["sector_name"]
                exposure_pct = float(exposure["exposure_pct"])

                # Track the holdings date (should be same for all sectors in a fund)
                if holdings_date is None and exposure.get("month_end_date") is not None:
                    holdings_date = exposure["month_end_date"]

                # Look up the FM signal for this sector
                signal_data = signal_lookup.get(sector_name)

                if signal_data is None:
                    # No FM signal for this sector — treat as NEUTRAL
                    signal = "NEUTRAL"
                    signal_weight = self.SIGNAL_WEIGHTS["NEUTRAL"]
                    confidence = "MEDIUM"
                    confidence_multiplier = self.CONFIDENCE_MULTIPLIERS["MEDIUM"]
                else:
                    signal = signal_data["signal"]
                    signal_weight = float(signal_data.get(
                        "signal_weight",
                        self.SIGNAL_WEIGHTS.get(signal, 0.0),
                    ))
                    confidence = signal_data.get("confidence", "MEDIUM")
                    confidence_multiplier = self.CONFIDENCE_MULTIPLIERS.get(
                        confidence, 1.0
                    )

                # Compute this sector's contribution
                contribution = exposure_pct * signal_weight * confidence_multiplier
                raw_fsas += contribution

                # Track AVOID exposure
                if signal == "AVOID":
                    avoid_exposure_pct += exposure_pct

                # Store per-sector breakdown for transparency
                sector_contributions[sector_name] = {
                    "exposure_pct": round(exposure_pct, 4),
                    "signal": signal,
                    "signal_weight": signal_weight,
                    "confidence": confidence,
                    "confidence_multiplier": confidence_multiplier,
                    "contribution": round(contribution, 4),
                }

            # Check if holdings are stale
            stale_holdings_flag = False
            if holdings_date is not None and holdings_date < stale_cutoff:
                stale_holdings_flag = True

            fund_results.append({
                "mstar_id": mstar_id,
                "fm_signal_date": fm_signal_date,
                "holdings_date": holdings_date or reference_date,
                "raw_fsas": round(raw_fsas, 5),
                "fsas": 0.0,  # Placeholder — filled after normalization
                "sector_contributions": sector_contributions,
                "stale_holdings_flag": stale_holdings_flag,
                "sector_drift_alerts": None,  # Computed separately if needed
                "avoid_exposure_pct": round(avoid_exposure_pct, 2),
                "engine_version": ENGINE_VERSION,
            })
            raw_fsas_values.append(raw_fsas)

        # Step 2: Normalize raw FSAS across all funds to 0-100
        normalised_fsas = min_max_normalise(raw_fsas_values, higher_is_better=True)

        for idx, result in enumerate(fund_results):
            fsas_score = normalised_fsas[idx]
            result["fsas"] = round(fsas_score, 4) if fsas_score is not None else 0.0

        logger.info(
            "fsas_compute_complete",
            fund_count=len(fund_results),
            avg_avoid_exposure=round(
                sum(r["avoid_exposure_pct"] for r in fund_results) / len(fund_results),
                2,
            ) if fund_results else 0.0,
            stale_count=sum(1 for r in fund_results if r["stale_holdings_flag"]),
        )

        return fund_results

    def _empty_result(
        self,
        mstar_id: str,
        fm_signal_date: date,
        reference_date: date,
    ) -> dict[str, Any]:
        """Build a result dict for a fund with no sector exposure data."""
        return {
            "mstar_id": mstar_id,
            "fm_signal_date": fm_signal_date,
            "holdings_date": reference_date,
            "raw_fsas": None,
            "fsas": 0.0,
            "sector_contributions": {},
            "stale_holdings_flag": True,
            "sector_drift_alerts": None,
            "avoid_exposure_pct": 0.0,
            "engine_version": ENGINE_VERSION,
        }
