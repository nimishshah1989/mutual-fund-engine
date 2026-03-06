"""
engines/qfs_engine.py

Quantitative Fund Score (QFS) — Layer 1 of the JIP Recommendation Engine.

Scores every mutual fund on 12 risk/return metrics across 3 scoring horizons
(1Y, 3Y, 5Y) using two-tier weighted blending (must-have 75%, good-to-have 25%).

Configuration (metric definitions, weights, constants) lives in qfs_metric_config.py.
The engine is a pure computation module — all DB I/O is handled by scoring_service.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any, Optional

import structlog

from app.engines.base_engine import compute_data_completeness, min_max_normalise
from app.engines.qfs_metric_config import (
    ALL_HORIZONS,
    COMPLETENESS_THRESHOLD,
    ENGINE_VERSION,
    GOOD_TO_HAVE_ONLY_CAP,
    GOOD_TO_HAVE_WEIGHT,
    HORIZON_WEIGHTS,
    METRIC_CONFIG,
    MUST_HAVE_WEIGHT,
    SCORING_HORIZONS,
    count_must_have_horizons,
    safe_round,
)

logger = structlog.get_logger(__name__)


class QFSEngine:
    """Computes Quantitative Fund Score for all funds in a category."""

    def compute(
        self,
        fund_ids: list[str],
        risk_stats_by_fund: dict[str, dict[str, Any]],
        performance_by_fund: dict[str, dict[str, Any]],
        category_name: str,
    ) -> list[dict[str, Any]]:
        """
        Compute QFS for all funds in a category. Takes pre-loaded data (no DB access)
        and returns a list of result dicts ready for DB insertion.
        """
        if not fund_ids:
            logger.warning("qfs_no_funds", category=category_name)
            return []

        total_must_have = count_must_have_horizons()
        logger.info(
            "qfs_compute_start", category=category_name, fund_count=len(fund_ids),
            total_must_have_slots=total_must_have, engine_version=ENGINE_VERSION,
        )

        # Steps 1-3: Extract raw values and normalise within peer group
        cat_avg = self._compute_category_avg_returns(fund_ids, performance_by_fund)
        raw_by_metric = self._extract_all_raw_values(
            fund_ids, risk_stats_by_fund, performance_by_fund, cat_avg,
        )
        norm_by_metric = self._normalise_all(raw_by_metric)

        # Step 4: Build per-fund results with horizon scores and WFS
        fund_results: list[dict[str, Any]] = []
        wfs_values: list[Optional[float]] = []
        today = date.today()

        for fund_idx, mstar_id in enumerate(fund_ids):
            result, wfs_raw = self._compute_single_fund(
                fund_idx, mstar_id, fund_ids, raw_by_metric, norm_by_metric,
                risk_stats_by_fund, performance_by_fund, total_must_have, today,
            )
            fund_results.append(result)
            wfs_values.append(wfs_raw)

        # Step 6: Normalise WFS across category to get final QFS (0-100)
        normalised_qfs = min_max_normalise(wfs_values, higher_is_better=True)
        for idx, result in enumerate(fund_results):
            raw_qfs = round(normalised_qfs[idx], 4) if normalised_qfs[idx] is not None else 0.0
            completeness = result["data_completeness_pct"]
            penalty_factor = min(1.0, completeness / COMPLETENESS_THRESHOLD)
            result["qfs"] = round(raw_qfs * penalty_factor, 4)

        logger.info(
            "qfs_compute_complete", category=category_name, fund_count=len(fund_results),
            avg_completeness=round(
                sum(r["data_completeness_pct"] for r in fund_results) / len(fund_results), 2,
            ) if fund_results else 0.0,
        )
        return fund_results

    def _extract_all_raw_values(
        self,
        fund_ids: list[str],
        risk_stats: dict[str, dict[str, Any]],
        performance: dict[str, dict[str, Any]],
        cat_avg: dict[str, Optional[float]],
    ) -> dict[str, dict[str, list[Optional[float]]]]:
        """Extract raw metric values for every fund x metric x horizon."""
        raw: dict[str, dict[str, list[Optional[float]]]] = {}
        for metric_name, config in METRIC_CONFIG.items():
            raw[metric_name] = {}
            horizons = config["horizons"]
            for horizon in ALL_HORIZONS:
                vals: list[Optional[float]] = []
                for mstar_id in fund_ids:
                    vals.append(self._extract_metric_value(
                        metric_name, horizon, horizons.get(horizon),
                        mstar_id, risk_stats, performance, cat_avg,
                    ))
                raw[metric_name][horizon] = vals
        return raw

    def _normalise_all(
        self, raw: dict[str, dict[str, list[Optional[float]]]],
    ) -> dict[str, dict[str, list[Optional[float]]]]:
        """Normalise each metric x horizon within the peer group."""
        norm: dict[str, dict[str, list[Optional[float]]]] = {}
        for metric_name, config in METRIC_CONFIG.items():
            norm[metric_name] = {}
            higher = config["higher_is_better"]
            for horizon in ALL_HORIZONS:
                norm[metric_name][horizon] = min_max_normalise(raw[metric_name][horizon], higher)
        return norm

    def _compute_single_fund(
        self,
        fund_idx: int,
        mstar_id: str,
        fund_ids: list[str],
        raw: dict[str, dict[str, list[Optional[float]]]],
        norm: dict[str, dict[str, list[Optional[float]]]],
        risk_stats: dict[str, dict[str, Any]],
        performance: dict[str, dict[str, Any]],
        total_must_have: int,
        today: date,
    ) -> tuple[dict[str, Any], Optional[float]]:
        """Compute per-fund metric scores, horizon scores, and WFS."""
        metric_scores: dict[str, dict[str, dict[str, Optional[float]]]] = {}
        must_have_comp: dict[str, dict[str, Optional[float]]] = {}
        missing: list[dict[str, Any]] = []

        for metric_name, config in METRIC_CONFIG.items():
            metric_scores[metric_name] = {}
            priority = config["priority"]
            for horizon in ALL_HORIZONS:
                raw_val = raw[metric_name][horizon][fund_idx]
                norm_val = norm[metric_name][horizon][fund_idx]
                metric_scores[metric_name][horizon] = {
                    "raw": safe_round(raw_val, 5), "normalised": safe_round(norm_val, 4),
                }
                if raw_val is None:
                    missing.append({"metric": metric_name, "horizon": horizon, "reason": "data_unavailable"})
                if priority == "must_have" and horizon in SCORING_HORIZONS and horizon in config["horizons"]:
                    must_have_comp.setdefault(metric_name, {})[horizon] = raw_val

        # Compute per-horizon scores using two-tier weighted blend
        horizon_scores = self._compute_horizon_scores(fund_idx, norm)

        # Compute WFS using only SCORING_HORIZONS
        wfs_num, wfs_den, avail = 0.0, 0, 0
        for h in SCORING_HORIZONS:
            w = HORIZON_WEIGHTS[h]
            s = horizon_scores.get(h)
            if s is not None:
                wfs_num += w * s
                wfs_den += w
                avail += 1
        wfs_raw = round(wfs_num / wfs_den, 4) if wfs_den > 0 else None

        data_comp = compute_data_completeness(must_have_comp, total_possible=total_must_have)
        input_hash = hashlib.sha256(json.dumps({
            "risk_stats": risk_stats.get(mstar_id, {}),
            "performance": performance.get(mstar_id, {}),
        }, sort_keys=True, default=str).encode()).hexdigest()

        result = {
            "mstar_id": mstar_id, "computed_date": today,
            "score_1y": horizon_scores.get("1y"), "score_3y": horizon_scores.get("3y"),
            "score_5y": horizon_scores.get("5y"), "score_10y": horizon_scores.get("10y"),
            "wfs_raw": wfs_raw, "qfs": 0.0,
            "data_completeness_pct": data_comp,
            "missing_metrics": missing if missing else None,
            "available_horizons": avail, "metric_scores": metric_scores,
            "data_vintage": today, "input_hash": input_hash,
            "engine_version": ENGINE_VERSION, "category_universe_size": len(fund_ids),
        }
        return result, wfs_raw

    def _compute_horizon_scores(
        self, fund_idx: int, norm: dict[str, dict[str, list[Optional[float]]]],
    ) -> dict[str, Optional[float]]:
        """Compute per-horizon scores using two-tier weighted blend."""
        scores: dict[str, Optional[float]] = {}
        for horizon in ALL_HORIZONS:
            must_vals: list[float] = []
            good_vals: list[float] = []
            for metric_name, config in METRIC_CONFIG.items():
                val = norm[metric_name][horizon][fund_idx]
                if val is None:
                    continue
                if config["priority"] == "must_have":
                    must_vals.append(val)
                else:
                    good_vals.append(val)

            if must_vals and good_vals:
                must_avg = sum(must_vals) / len(must_vals)
                good_avg = sum(good_vals) / len(good_vals)
                scores[horizon] = round(MUST_HAVE_WEIGHT * must_avg + GOOD_TO_HAVE_WEIGHT * good_avg, 4)
            elif must_vals:
                scores[horizon] = round(sum(must_vals) / len(must_vals), 4)
            elif good_vals:
                scores[horizon] = round(sum(good_vals) / len(good_vals) * GOOD_TO_HAVE_ONLY_CAP, 4)
            else:
                scores[horizon] = None
        return scores

    def _compute_category_avg_returns(
        self, fund_ids: list[str], performance: dict[str, dict[str, Any]],
    ) -> dict[str, Optional[float]]:
        """Compute average return per horizon — benchmark for category_alpha."""
        cols = {"1y": "return_1y", "3y": "return_3y", "5y": "return_5y", "10y": "return_10y"}
        avg: dict[str, Optional[float]] = {}
        for h, col in cols.items():
            vals = [float(performance[mid][col]) for mid in fund_ids
                    if mid in performance and performance[mid].get(col) is not None]
            avg[h] = sum(vals) / len(vals) if vals else None
        return avg

    def _extract_metric_value(
        self, metric_name: str, horizon: str, column_name: Optional[str],
        mstar_id: str, risk_stats: dict[str, dict[str, Any]],
        performance: dict[str, dict[str, Any]], cat_avg: dict[str, Optional[float]],
    ) -> Optional[float]:
        """Extract a single metric value for one fund at one horizon."""
        config = METRIC_CONFIG[metric_name]
        if horizon not in config["horizons"]:
            return None
        source = config["source"]

        if source in ("risk_stats", "performance"):
            if column_name is None:
                return None
            data = (risk_stats if source == "risk_stats" else performance).get(mstar_id, {})
            val = data.get(column_name)
            return float(val) if val is not None else None

        if source == "computed" and metric_name == "category_alpha":
            fund_ret = performance.get(mstar_id, {}).get(f"return_{horizon}")
            avg = cat_avg.get(horizon)
            if fund_ret is not None and avg is not None:
                return float(fund_ret) - avg
        return None
