"""
engines/fsas_engine.py

FM Sector Alignment Score (FMS) — Layer 2 of the JIP Recommendation Engine.

v2.0.0 (Decision Matrix): Computes alignment using ACTIVE WEIGHTS relative
to a benchmark (NIFTY 50), not raw exposure percentages.

Algorithm:
    For each fund, for each of 11 Morningstar sectors:
        active_weight = fund_exposure_pct - benchmark_weight_pct
        contribution = active_weight * signal_weight * confidence_multiplier
    raw_fms = sum(all 11 sector contributions)
    fms = min_max_normalise(raw_fms, within_category) -> 0-100

A fund overweight in sectors the FM favors scores well.
A fund overweight in sectors the FM avoids is penalised.
Benchmark-aligned positions with neutral signals are near-zero.

The engine is a pure computation module — it receives data, returns results.
All DB I/O is handled by the scoring_service orchestrator.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

import structlog

from app.engines.base_engine import min_max_normalise

logger = structlog.get_logger(__name__)

# Bump: active weight formula replaces raw exposure formula
ENGINE_VERSION = "2.0.0"


class FSASEngine:
    """Computes FM Sector Alignment Score for all funds in a batch."""

    # Signal -> numeric weight (how the FM views the sector)
    SIGNAL_WEIGHTS: dict[str, float] = {
        "OVERWEIGHT": 1.0,
        "ACCUMULATE": 0.6,
        "NEUTRAL": 0.1,
        "UNDERWEIGHT": -0.5,
        "AVOID": -1.0,
    }

    # Confidence -> multiplier (how sure the FM is about the signal)
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
        benchmark_weights: Optional[dict[str, float]] = None,
        reference_date: Optional[date] = None,
    ) -> list[dict[str, Any]]:
        """
        Compute FMS for all funds in the provided exposure dict.

        Args:
            fund_exposures: {mstar_id: [{sector_name, exposure_pct, month_end_date}]}
            active_signals: [{sector_name, signal, signal_weight, confidence, effective_date}]
            benchmark_weights: {sector_name: weight_pct} — NIFTY 50 allocations.
                If None, falls back to raw exposure formula (v1 compat).
            reference_date: Date for stale holdings check. Defaults to today.

        Returns:
            List of dicts ready for fund_fsas DB insert. One per fund.
        """
        if not fund_exposures:
            logger.warning("fsas_no_funds")
            return []

        if reference_date is None:
            reference_date = date.today()

        use_active_weights = benchmark_weights is not None and len(benchmark_weights) > 0

        # Build a lookup from sector_name -> signal data
        signal_lookup: dict[str, dict[str, Any]] = {}
        for sig in active_signals:
            signal_lookup[sig["sector_name"]] = sig

        # Determine the FM signal date
        fm_signal_date = reference_date
        if active_signals:
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
            use_active_weights=use_active_weights,
            engine_version=ENGINE_VERSION,
        )

        # Step 1: Compute raw FMS for each fund
        fund_results: list[dict[str, Any]] = []
        raw_fsas_values: list[Optional[float]] = []
        stale_cutoff = reference_date - timedelta(days=self.STALE_HOLDINGS_DAYS)

        for mstar_id, exposures in fund_exposures.items():
            if not exposures:
                fund_results.append(self._empty_result(
                    mstar_id, fm_signal_date, reference_date
                ))
                raw_fsas_values.append(None)
                continue

            result = self._compute_single_fund(
                mstar_id=mstar_id,
                exposures=exposures,
                signal_lookup=signal_lookup,
                benchmark_weights=benchmark_weights or {},
                use_active_weights=use_active_weights,
                fm_signal_date=fm_signal_date,
                reference_date=reference_date,
                stale_cutoff=stale_cutoff,
            )
            fund_results.append(result)
            raw_fsas_values.append(result["raw_fsas"])

        # Step 2: Normalize raw FMS across all funds to 0-100
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

    def _compute_single_fund(
        self,
        mstar_id: str,
        exposures: list[dict[str, Any]],
        signal_lookup: dict[str, dict[str, Any]],
        benchmark_weights: dict[str, float],
        use_active_weights: bool,
        fm_signal_date: date,
        reference_date: date,
        stale_cutoff: date,
    ) -> dict[str, Any]:
        """Compute raw FMS and sector contributions for one fund."""
        raw_fsas = 0.0
        avoid_exposure_pct = 0.0
        sector_contributions: dict[str, dict[str, Any]] = {}
        holdings_date: Optional[date] = None

        for exposure in exposures:
            sector_name = exposure["sector_name"]
            exposure_pct = float(exposure["exposure_pct"])

            if holdings_date is None and exposure.get("month_end_date") is not None:
                holdings_date = exposure["month_end_date"]

            # Look up the FM signal for this sector
            signal_data = signal_lookup.get(sector_name)
            if signal_data is None:
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

            # v2: Active weight = fund_exposure - benchmark_weight
            benchmark_wt = benchmark_weights.get(sector_name, 0.0)
            if use_active_weights:
                active_weight = exposure_pct - benchmark_wt
                contribution = active_weight * signal_weight * confidence_multiplier
            else:
                # v1 fallback: raw exposure * signal_weight * confidence
                active_weight = exposure_pct  # No benchmark subtraction
                contribution = exposure_pct * signal_weight * confidence_multiplier

            raw_fsas += contribution

            # Track AVOID exposure
            if signal == "AVOID":
                avoid_exposure_pct += exposure_pct

            # Store per-sector breakdown for transparency
            sector_contributions[sector_name] = {
                "exposure_pct": round(exposure_pct, 4),
                "benchmark_weight_pct": round(benchmark_wt, 4),
                "active_weight": round(active_weight, 4),
                "signal": signal,
                "signal_weight": signal_weight,
                "confidence": confidence,
                "confidence_multiplier": confidence_multiplier,
                "contribution": round(contribution, 4),
            }

        stale_holdings_flag = False
        if holdings_date is not None and holdings_date < stale_cutoff:
            stale_holdings_flag = True

        return {
            "mstar_id": mstar_id,
            "fm_signal_date": fm_signal_date,
            "holdings_date": holdings_date or reference_date,
            "raw_fsas": round(raw_fsas, 5),
            "fsas": 0.0,  # Placeholder — filled after normalization
            "sector_contributions": sector_contributions,
            "stale_holdings_flag": stale_holdings_flag,
            "sector_drift_alerts": None,
            "avoid_exposure_pct": round(avoid_exposure_pct, 2),
            "engine_version": ENGINE_VERSION,
        }

    def get_alignment_summary(
        self,
        sector_contributions: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Build a per-fund alignment summary from sector contributions.

        Returns dict with aligned_sectors, misaligned_sectors, neutral_sectors,
        avoid_exposure_pct, top_aligned, top_misaligned.
        """
        aligned: list[dict[str, Any]] = []
        misaligned: list[dict[str, Any]] = []
        neutral: list[str] = []
        avoid_exposure_pct = 0.0

        for sector_name, data in sector_contributions.items():
            signal = data.get("signal", "NEUTRAL")
            exposure_pct = data.get("exposure_pct", 0.0)
            contribution = data.get("contribution", 0.0)
            active_weight = data.get("active_weight", exposure_pct)

            if signal == "AVOID":
                avoid_exposure_pct += exposure_pct

            if signal in ("OVERWEIGHT", "ACCUMULATE") and active_weight > 0:
                aligned.append({
                    "sector": sector_name,
                    "signal": signal,
                    "exposure_pct": exposure_pct,
                    "active_weight": active_weight,
                    "contribution": contribution,
                })
            elif signal in ("UNDERWEIGHT", "AVOID") and active_weight > 0:
                misaligned.append({
                    "sector": sector_name,
                    "signal": signal,
                    "exposure_pct": exposure_pct,
                    "active_weight": active_weight,
                    "contribution": contribution,
                })
            elif signal == "NEUTRAL":
                neutral.append(sector_name)

        aligned.sort(key=lambda x: x["contribution"], reverse=True)
        misaligned.sort(key=lambda x: x["contribution"])

        return {
            "aligned_sectors": aligned,
            "misaligned_sectors": misaligned,
            "neutral_sectors": neutral,
            "avoid_exposure_pct": round(avoid_exposure_pct, 2),
            "top_aligned": aligned[:3],
            "top_misaligned": misaligned[:3],
        }

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
