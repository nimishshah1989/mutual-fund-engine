"""
services/pulse_calculator.py

Pure computation module for MF Pulse ratio returns and signal classification.
No database access — all inputs are passed in, all outputs are returned.

Formula:
  ratio_today = fund_nav_today / nifty_today
  ratio_old   = fund_nav_old / nifty_old
  ratio_return = ((ratio_today / ratio_old) - 1) × 100

Signal thresholds (configurable via engine_config):
  ratio_period = 1 + (ratio_return / 100)
  > strong_ow (1.05)  → STRONG_OW
  > 1.00              → OVERWEIGHT
  == 1.00             → NEUTRAL
  >= strong_uw (0.95) → UNDERWEIGHT
  < strong_uw         → STRONG_UW
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

# Default signal thresholds (overridden by engine_config.pulse_signal_thresholds)
DEFAULT_STRONG_OW = Decimal("1.05")
DEFAULT_STRONG_UW = Decimal("0.95")

# Period definitions: name -> calendar days to look back
PULSE_PERIODS: dict[str, int] = {
    "1m": 30,
    "3m": 90,
    "6m": 180,
    "1y": 365,
    "2y": 730,
    "3y": 1095,
}

# Date tolerance: how many calendar days of slack when looking up NAV/price
DATE_TOLERANCE_DAYS: int = 5


def compute_ratio_return(
    nav_current: Decimal,
    nav_old: Decimal,
    nifty_current: Decimal,
    nifty_old: Decimal,
) -> dict[str, Decimal]:
    """
    Compute ratio return and component returns for a single fund × period.

    Returns:
        dict with ratio_current, ratio_old, ratio_return,
        fund_return, nifty_return, excess_return
    """
    _100 = Decimal("100")
    _6_places = Decimal("0.000001")
    _4_places = Decimal("0.0001")

    ratio_current = (nav_current / nifty_current).quantize(_6_places, rounding=ROUND_HALF_UP)
    ratio_old = (nav_old / nifty_old).quantize(_6_places, rounding=ROUND_HALF_UP)
    ratio_return = (((ratio_current / ratio_old) - 1) * _100).quantize(_4_places, rounding=ROUND_HALF_UP)
    fund_return = (((nav_current / nav_old) - 1) * _100).quantize(_4_places, rounding=ROUND_HALF_UP)
    nifty_return = (((nifty_current / nifty_old) - 1) * _100).quantize(_4_places, rounding=ROUND_HALF_UP)
    excess_return = (fund_return - nifty_return).quantize(_4_places, rounding=ROUND_HALF_UP)

    return {
        "ratio_current": ratio_current,
        "ratio_old": ratio_old,
        "ratio_return": ratio_return,
        "fund_return": fund_return,
        "nifty_return": nifty_return,
        "excess_return": excess_return,
    }


def classify_signal(
    ratio_return: Decimal,
    strong_ow: Decimal = DEFAULT_STRONG_OW,
    strong_uw: Decimal = DEFAULT_STRONG_UW,
) -> str:
    """
    Classify a ratio return into a signal.

    Uses ratio_period = 1 + (ratio_return / 100) to determine signal.
    """
    ratio_period = Decimal("1") + (ratio_return / Decimal("100"))

    if ratio_period > strong_ow:
        return "STRONG_OW"
    elif ratio_period > Decimal("1"):
        return "OVERWEIGHT"
    elif ratio_period >= strong_uw:
        if abs(ratio_period - Decimal("1")) < Decimal("0.0001"):
            return "NEUTRAL"
        return "UNDERWEIGHT"
    else:
        return "STRONG_UW"


def get_lookback_date(reference_date: date, period: str) -> date:
    """Get the lookback date for a given period from a reference date."""
    days = PULSE_PERIODS.get(period)
    if days is None:
        raise ValueError(f"Unknown period: {period}. Valid: {list(PULSE_PERIODS.keys())}")
    return reference_date - timedelta(days=days)


def compute_snapshot_for_fund(
    mstar_id: str,
    period: str,
    snapshot_date: date,
    nav_current: Optional[Decimal],
    nav_old: Optional[Decimal],
    nifty_current: Optional[Decimal],
    nifty_old: Optional[Decimal],
    strong_ow: Decimal = DEFAULT_STRONG_OW,
    strong_uw: Decimal = DEFAULT_STRONG_UW,
) -> dict[str, Any]:
    """
    Compute a complete pulse snapshot for one fund × one period.

    Returns a dict ready for DB insertion into mf_pulse_snapshot.
    Returns partial data (with None ratio_return/signal) if any input is missing.
    """
    result: dict[str, Any] = {
        "mstar_id": mstar_id,
        "snapshot_date": snapshot_date,
        "period": period,
        "nav_current": nav_current,
        "nav_old": nav_old,
        "nifty_current": nifty_current,
        "nifty_old": nifty_old,
    }

    # Cannot compute if any data is missing
    if any(v is None or v == 0 for v in [nav_current, nav_old, nifty_current, nifty_old]):
        result.update({
            "fund_return": None,
            "nifty_return": None,
            "ratio_current": None,
            "ratio_old": None,
            "ratio_return": None,
            "signal": None,
            "excess_return": None,
        })
        return result

    computed = compute_ratio_return(
        nav_current=nav_current,  # type: ignore[arg-type]
        nav_old=nav_old,  # type: ignore[arg-type]
        nifty_current=nifty_current,  # type: ignore[arg-type]
        nifty_old=nifty_old,  # type: ignore[arg-type]
    )
    signal = classify_signal(computed["ratio_return"], strong_ow, strong_uw)

    result.update(computed)
    result["signal"] = signal
    return result
