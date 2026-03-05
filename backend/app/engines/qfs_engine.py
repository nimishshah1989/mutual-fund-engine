"""
engines/qfs_engine.py

Quantitative Fund Score (QFS) — Layer 1 of the JIP Recommendation Engine.

Scores every mutual fund on 13 risk/return metrics across 4 time horizons
(1Y, 3Y, 5Y, 10Y). All scoring is relative — funds are normalised within
their SEBI category peer group using min-max normalization (0-100).

Algorithm:
    1. Load all eligible funds in the same category
    2. For each metric x horizon, collect values across all peers
    3. Min-max normalise within the peer group (respecting metric direction)
    4. Compute per-horizon average scores
    5. Weight horizons (1Y=1, 3Y=2, 5Y=3, 10Y=4) to get WFS
    6. Normalise WFS within category to produce final QFS (0-100)

The engine is a pure computation module — it receives data, returns results.
All DB I/O is handled by the scoring_service orchestrator.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any, Optional

import structlog

from app.engines.base_engine import compute_data_completeness, min_max_normalise

logger = structlog.get_logger(__name__)

# Current engine version — bump when algorithm changes
ENGINE_VERSION = "1.0.0"


class QFSEngine:
    """Computes Quantitative Fund Score for all funds in a category."""

    # -----------------------------------------------------------------------
    # Metric configuration — maps each metric to its DB columns and direction
    # -----------------------------------------------------------------------
    METRIC_CONFIG: dict[str, dict[str, Any]] = {
        "sharpe": {
            "higher_is_better": True,
            "horizons": {"1y": "sharpe_1y", "3y": "sharpe_3y", "5y": "sharpe_5y"},
            "source": "risk_stats",
        },
        "alpha": {
            "higher_is_better": True,
            "horizons": {"3y": "alpha_3y", "5y": "alpha_5y", "10y": "alpha_10y"},
            "source": "risk_stats",
        },
        "beta": {
            "higher_is_better": False,
            "horizons": {"3y": "beta_3y", "5y": "beta_5y", "10y": "beta_10y"},
            "source": "risk_stats",
        },
        "std_dev": {
            "higher_is_better": False,
            "horizons": {"1y": "std_dev_1y", "3y": "std_dev_3y", "5y": "std_dev_5y"},
            "source": "risk_stats",
        },
        "sortino": {
            "higher_is_better": True,
            "horizons": {"1y": "sortino_1y", "3y": "sortino_3y", "5y": "sortino_5y"},
            "source": "risk_stats",
        },
        "treynor": {
            "higher_is_better": True,
            "horizons": {
                "1y": "treynor_1y",
                "3y": "treynor_3y",
                "5y": "treynor_5y",
                "10y": "treynor_10y",
            },
            "source": "risk_stats",
        },
        "tracking_error": {
            "higher_is_better": False,
            "horizons": {
                "1y": "tracking_error_1y",
                "3y": "tracking_error_3y",
                "5y": "tracking_error_5y",
                "10y": "tracking_error_10y",
            },
            "source": "risk_stats",
        },
        "info_ratio": {
            "higher_is_better": True,
            "horizons": {
                "1y": "info_ratio_1y",
                "3y": "info_ratio_3y",
                "5y": "info_ratio_5y",
                "10y": "info_ratio_10y",
            },
            "source": "risk_stats",
        },
        "capture_up": {
            "higher_is_better": True,
            "horizons": {
                "1y": "capture_up_1y",
                "3y": "capture_up_3y",
                "5y": "capture_up_5y",
                "10y": "capture_up_10y",
            },
            "source": "risk_stats",
        },
        "capture_down": {
            "higher_is_better": False,
            "horizons": {
                "1y": "capture_down_1y",
                "3y": "capture_down_3y",
                "5y": "capture_down_5y",
            },
            "source": "risk_stats",
        },
        "batting_avg": {
            "higher_is_better": True,
            "horizons": {},
            "source": "risk_stats",
        },
        "total_return": {
            "higher_is_better": True,
            "horizons": {
                "1y": "return_1y",
                "3y": "return_3y",
                "5y": "return_5y",
                "10y": "return_10y",
            },
            "source": "performance",
        },
        "category_alpha": {
            "higher_is_better": True,
            "horizons": {"1y": None, "3y": None, "5y": None, "10y": None},
            "source": "computed",
        },
    }

    # Horizon weights: longer track record = more weight
    HORIZON_WEIGHTS: dict[str, int] = {"1y": 1, "3y": 2, "5y": 3, "10y": 4}

    # All horizon keys in order
    ALL_HORIZONS: list[str] = ["1y", "3y", "5y", "10y"]

    def compute(
        self,
        fund_ids: list[str],
        risk_stats_by_fund: dict[str, dict[str, Any]],
        performance_by_fund: dict[str, dict[str, Any]],
        category_name: str,
    ) -> list[dict[str, Any]]:
        """
        Compute QFS for all funds in a category.

        This is the main entry point. It takes pre-loaded data (no DB access)
        and returns a list of result dicts ready for DB insertion.

        Args:
            fund_ids: List of mstar_ids for all eligible funds in the category.
            risk_stats_by_fund: {mstar_id: {column_name: value}} from fund_risk_stats.
            performance_by_fund: {mstar_id: {column_name: value}} from fund_performance.
            category_name: SEBI category name (used for logging).

        Returns:
            List of dicts, one per fund, containing all QFS fields for DB storage.
        """
        if not fund_ids:
            logger.warning("qfs_no_funds", category=category_name)
            return []

        logger.info(
            "qfs_compute_start",
            category=category_name,
            fund_count=len(fund_ids),
        )

        # Step 1: Compute category average returns for category_alpha metric
        category_avg_returns = self._compute_category_avg_returns(
            fund_ids, performance_by_fund
        )

        # Step 2: Extract raw metric values for every fund x metric x horizon
        # Structure: {metric: {horizon: [value_for_fund_0, value_for_fund_1, ...]}}
        raw_values_by_metric: dict[str, dict[str, list[Optional[float]]]] = {}

        for metric_name, config in self.METRIC_CONFIG.items():
            raw_values_by_metric[metric_name] = {}
            horizons = config["horizons"]

            for horizon in self.ALL_HORIZONS:
                values: list[Optional[float]] = []

                for mstar_id in fund_ids:
                    value = self._extract_metric_value(
                        metric_name=metric_name,
                        horizon=horizon,
                        column_name=horizons.get(horizon),
                        mstar_id=mstar_id,
                        risk_stats_by_fund=risk_stats_by_fund,
                        performance_by_fund=performance_by_fund,
                        category_avg_returns=category_avg_returns,
                    )
                    values.append(value)

                raw_values_by_metric[metric_name][horizon] = values

        # Step 3: Normalise each metric x horizon within the peer group
        normalised_by_metric: dict[str, dict[str, list[Optional[float]]]] = {}

        for metric_name, config in self.METRIC_CONFIG.items():
            normalised_by_metric[metric_name] = {}
            higher_is_better = config["higher_is_better"]

            for horizon in self.ALL_HORIZONS:
                raw_vals = raw_values_by_metric[metric_name][horizon]
                normalised_vals = min_max_normalise(raw_vals, higher_is_better)
                normalised_by_metric[metric_name][horizon] = normalised_vals

        # Step 4: For each fund, compute per-horizon scores and WFS
        fund_results: list[dict[str, Any]] = []
        wfs_values: list[Optional[float]] = []

        today = date.today()

        for fund_idx, mstar_id in enumerate(fund_ids):
            # Build per-fund metric scores for deep-dive transparency
            metric_scores: dict[str, dict[str, dict[str, Optional[float]]]] = {}
            # Collect all metric values for data completeness calculation
            metric_values_for_completeness: dict[str, dict[str, Optional[float]]] = {}
            # Track which metrics are missing
            missing_metrics: list[dict[str, Any]] = []

            for metric_name in self.METRIC_CONFIG:
                metric_scores[metric_name] = {}
                metric_values_for_completeness[metric_name] = {}

                for horizon in self.ALL_HORIZONS:
                    raw_val = raw_values_by_metric[metric_name][horizon][fund_idx]
                    norm_val = normalised_by_metric[metric_name][horizon][fund_idx]

                    metric_scores[metric_name][horizon] = {
                        "raw": _safe_round(raw_val, 5),
                        "normalised": _safe_round(norm_val, 4),
                    }
                    metric_values_for_completeness[metric_name][horizon] = raw_val

                    if raw_val is None:
                        missing_metrics.append({
                            "metric": metric_name,
                            "horizon": horizon,
                            "reason": "data_unavailable",
                        })

            # Compute per-horizon average scores
            horizon_scores: dict[str, Optional[float]] = {}

            for horizon in self.ALL_HORIZONS:
                # Collect all normalised values for this fund at this horizon
                normalised_vals_for_horizon: list[float] = []

                for metric_name in self.METRIC_CONFIG:
                    norm_val = normalised_by_metric[metric_name][horizon][fund_idx]
                    if norm_val is not None:
                        normalised_vals_for_horizon.append(norm_val)

                if normalised_vals_for_horizon:
                    horizon_scores[horizon] = round(
                        sum(normalised_vals_for_horizon) / len(normalised_vals_for_horizon),
                        4,
                    )
                else:
                    horizon_scores[horizon] = None

            # Compute WFS (Weighted Fund Score) using only available horizons
            wfs_numerator = 0.0
            wfs_denominator = 0
            available_horizons = 0

            for horizon, weight in self.HORIZON_WEIGHTS.items():
                score = horizon_scores.get(horizon)
                if score is not None:
                    wfs_numerator += weight * score
                    wfs_denominator += weight
                    available_horizons += 1

            wfs_raw: Optional[float] = None
            if wfs_denominator > 0:
                wfs_raw = round(wfs_numerator / wfs_denominator, 4)

            wfs_values.append(wfs_raw)

            # Compute data completeness
            data_completeness = compute_data_completeness(
                metric_values_for_completeness
            )

            # Build input hash for traceability — hash of all raw input data
            input_data_for_hash = {
                "risk_stats": risk_stats_by_fund.get(mstar_id, {}),
                "performance": performance_by_fund.get(mstar_id, {}),
            }
            input_hash = hashlib.sha256(
                json.dumps(input_data_for_hash, sort_keys=True, default=str).encode()
            ).hexdigest()

            fund_results.append({
                "mstar_id": mstar_id,
                "computed_date": today,
                "score_1y": horizon_scores.get("1y"),
                "score_3y": horizon_scores.get("3y"),
                "score_5y": horizon_scores.get("5y"),
                "score_10y": horizon_scores.get("10y"),
                "wfs_raw": wfs_raw,
                "qfs": 0.0,  # placeholder — will be filled after WFS normalization
                "data_completeness_pct": data_completeness,
                "missing_metrics": missing_metrics if missing_metrics else None,
                "available_horizons": available_horizons,
                "metric_scores": metric_scores,
                "data_vintage": today,
                "input_hash": input_hash,
                "engine_version": ENGINE_VERSION,
                "category_universe_size": len(fund_ids),
            })

        # Step 5: Normalise WFS across all funds in the category to get final QFS
        normalised_qfs = min_max_normalise(wfs_values, higher_is_better=True)

        for idx, result in enumerate(fund_results):
            qfs_score = normalised_qfs[idx]
            # If normalization returns None (fund had no WFS), default to 0
            result["qfs"] = round(qfs_score, 4) if qfs_score is not None else 0.0

        logger.info(
            "qfs_compute_complete",
            category=category_name,
            fund_count=len(fund_results),
            avg_completeness=round(
                sum(r["data_completeness_pct"] for r in fund_results) / len(fund_results),
                2,
            ) if fund_results else 0.0,
        )

        return fund_results

    # -------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------

    def _compute_category_avg_returns(
        self,
        fund_ids: list[str],
        performance_by_fund: dict[str, dict[str, Any]],
    ) -> dict[str, Optional[float]]:
        """
        Compute the average return for the category across each horizon.
        Used as the benchmark for the category_alpha metric.

        Returns:
            Dict of {horizon: average_return_or_None}.
        """
        return_columns = {"1y": "return_1y", "3y": "return_3y", "5y": "return_5y", "10y": "return_10y"}
        avg_returns: dict[str, Optional[float]] = {}

        for horizon, col_name in return_columns.items():
            values: list[float] = []
            for mstar_id in fund_ids:
                perf = performance_by_fund.get(mstar_id, {})
                val = perf.get(col_name)
                if val is not None:
                    values.append(float(val))

            if values:
                avg_returns[horizon] = sum(values) / len(values)
            else:
                avg_returns[horizon] = None

        return avg_returns

    def _extract_metric_value(
        self,
        metric_name: str,
        horizon: str,
        column_name: Optional[str],
        mstar_id: str,
        risk_stats_by_fund: dict[str, dict[str, Any]],
        performance_by_fund: dict[str, dict[str, Any]],
        category_avg_returns: dict[str, Optional[float]],
    ) -> Optional[float]:
        """
        Extract a single metric value for one fund at one horizon.

        Handles three data sources:
            - risk_stats: direct column lookup in fund_risk_stats
            - performance: direct column lookup in fund_performance
            - computed: category_alpha = fund_return - category_avg_return

        Returns:
            The metric value as float, or None if unavailable.
        """
        config = self.METRIC_CONFIG[metric_name]
        source = config["source"]

        # Metric has no data for this horizon (not defined in the config)
        if horizon not in config["horizons"]:
            return None

        if source == "risk_stats":
            if column_name is None:
                return None
            data = risk_stats_by_fund.get(mstar_id, {})
            val = data.get(column_name)
            return float(val) if val is not None else None

        elif source == "performance":
            if column_name is None:
                return None
            data = performance_by_fund.get(mstar_id, {})
            val = data.get(column_name)
            return float(val) if val is not None else None

        elif source == "computed" and metric_name == "category_alpha":
            # category_alpha = fund_return - category_avg_return
            return_col = f"return_{horizon}"
            perf = performance_by_fund.get(mstar_id, {})
            fund_return = perf.get(return_col)
            category_avg = category_avg_returns.get(horizon)

            if fund_return is not None and category_avg is not None:
                return float(fund_return) - category_avg
            return None

        return None


def _safe_round(value: Optional[float], decimals: int) -> Optional[float]:
    """Round a value if not None."""
    if value is None:
        return None
    return round(value, decimals)
