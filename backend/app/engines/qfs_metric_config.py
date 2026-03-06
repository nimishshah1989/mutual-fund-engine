"""
engines/qfs_metric_config.py

Configuration constants for the QFS (Quantitative Fund Score) engine.

Defines:
  - METRIC_CONFIG: maps each metric to DB columns, direction, priority tier
  - Scoring horizons and weights
  - Two-tier weighting constants (must-have vs good-to-have)
  - Engine version for traceability
"""

from __future__ import annotations

from typing import Any, Optional

ENGINE_VERSION = "2.0.0"

# Horizons used for WFS/QFS scoring — 10Y excluded because very few
# Indian MFs have a 10-year track record. 10Y data is still extracted and displayed.
SCORING_HORIZONS: list[str] = ["1y", "3y", "5y"]
ALL_HORIZONS: list[str] = ["1y", "3y", "5y", "10y"]
HORIZON_WEIGHTS: dict[str, int] = {"1y": 1, "3y": 2, "5y": 3}

# Two-tier metric weighting within each horizon
MUST_HAVE_WEIGHT: float = 0.75
GOOD_TO_HAVE_WEIGHT: float = 0.25
GOOD_TO_HAVE_ONLY_CAP: float = 0.5  # Cap when only good-to-have metrics present

# Minimum completeness threshold: funds below this get proportional QFS penalty
COMPLETENESS_THRESHOLD: float = 60.0

# Maps each metric to its DB columns, direction, and priority tier
METRIC_CONFIG: dict[str, dict[str, Any]] = {
    "sharpe": {
        "higher_is_better": True,
        "horizons": {"1y": "sharpe_1y", "3y": "sharpe_3y", "5y": "sharpe_5y"},
        "source": "risk_stats",
        "priority": "must_have",
    },
    "alpha": {
        "higher_is_better": True,
        "horizons": {"3y": "alpha_3y", "5y": "alpha_5y", "10y": "alpha_10y"},
        "source": "risk_stats",
        "priority": "must_have",
    },
    "beta": {
        "higher_is_better": False,
        "horizons": {"3y": "beta_3y", "5y": "beta_5y", "10y": "beta_10y"},
        "source": "risk_stats",
        "priority": "good_to_have",
    },
    "std_dev": {
        "higher_is_better": False,
        "horizons": {"1y": "std_dev_1y", "3y": "std_dev_3y", "5y": "std_dev_5y"},
        "source": "risk_stats",
        "priority": "must_have",
    },
    "sortino": {
        "higher_is_better": True,
        "horizons": {"1y": "sortino_1y", "3y": "sortino_3y", "5y": "sortino_5y"},
        "source": "risk_stats",
        "priority": "must_have",
    },
    "treynor": {
        "higher_is_better": True,
        "horizons": {"1y": "treynor_1y", "3y": "treynor_3y", "5y": "treynor_5y", "10y": "treynor_10y"},
        "source": "risk_stats",
        "priority": "good_to_have",
    },
    "tracking_error": {
        "higher_is_better": False,
        "horizons": {"1y": "tracking_error_1y", "3y": "tracking_error_3y", "5y": "tracking_error_5y", "10y": "tracking_error_10y"},
        "source": "risk_stats",
        "priority": "good_to_have",
    },
    "info_ratio": {
        "higher_is_better": True,
        "horizons": {"1y": "info_ratio_1y", "3y": "info_ratio_3y", "5y": "info_ratio_5y", "10y": "info_ratio_10y"},
        "source": "risk_stats",
        "priority": "good_to_have",
    },
    "capture_up": {
        "higher_is_better": True,
        "horizons": {"1y": "capture_up_1y", "3y": "capture_up_3y", "5y": "capture_up_5y", "10y": "capture_up_10y"},
        "source": "risk_stats",
        "priority": "good_to_have",
    },
    "capture_down": {
        "higher_is_better": False,
        "horizons": {"1y": "capture_down_1y", "3y": "capture_down_3y", "5y": "capture_down_5y"},
        "source": "risk_stats",
        "priority": "good_to_have",
    },
    "excess_return": {
        "higher_is_better": True,
        "horizons": {"1y": None, "3y": None, "5y": None, "10y": None},
        "source": "computed",
        "priority": "must_have",
    },
    "category_alpha": {
        "higher_is_better": True,
        "horizons": {"1y": None, "3y": None, "5y": None, "10y": None},
        "source": "computed",
        "priority": "must_have",
    },
}


def count_must_have_horizons() -> int:
    """
    Count must-have metric x horizon slots within SCORING_HORIZONS.
    This is the denominator for data completeness (currently 17).
    """
    count = 0
    for config in METRIC_CONFIG.values():
        if config["priority"] != "must_have":
            continue
        for horizon in SCORING_HORIZONS:
            if horizon in config["horizons"]:
                count += 1
    return count


def safe_round(value: Optional[float], decimals: int) -> Optional[float]:
    """Round a value if not None."""
    return round(value, decimals) if value is not None else None
