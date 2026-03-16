"""
engines/base_engine.py

Shared utility functions for all scoring engines (QFS, FSAS, CRS).
Provides min-max normalization and data completeness computation
that every Layer uses for peer-group scoring.

All financial computations use Decimal for precision.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Union

# Constants
ZERO = Decimal("0")
ONE = Decimal("1")
FIFTY = Decimal("50")
HUNDRED = Decimal("100")

NumericType = Union[Decimal, float, int]


def to_decimal(val: Optional[NumericType]) -> Optional[Decimal]:
    """Safely convert a numeric value to Decimal."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def decimal_round(val: Optional[Decimal], places: int) -> Optional[Decimal]:
    """Round a Decimal to the given number of decimal places using ROUND_HALF_UP."""
    if val is None:
        return None
    quantizer = Decimal(10) ** -places
    return val.quantize(quantizer, rounding=ROUND_HALF_UP)


def min_max_normalise(
    values: list[Optional[Decimal]],
    higher_is_better: bool,
) -> list[Optional[Decimal]]:
    """
    Min-max normalise a list of values to a 0-100 scale within their peer group.

    Non-None values are scaled based on their position between min and max.
    None values remain None (missing data is not penalised).

    Args:
        values: Raw metric values for all funds in a category. None = missing.
        higher_is_better: If True, highest raw value maps to 100.
                          If False, lowest raw value maps to 100 (inverted).

    Returns:
        List of normalised scores (0-100) with None preserved for missing values.
    """
    # Extract non-None values for computing range
    valid_values = [v for v in values if v is not None]

    # Edge case: no valid values at all — return all Nones
    if not valid_values:
        return [None] * len(values)

    min_val = min(valid_values)
    max_val = max(valid_values)
    value_range = max_val - min_val

    result: list[Optional[Decimal]] = []
    for val in values:
        if val is None:
            result.append(None)
        elif value_range == ZERO:
            # All funds have the same value — cannot differentiate, give midpoint
            result.append(FIFTY)
        elif higher_is_better:
            result.append((val - min_val) / value_range * HUNDRED)
        else:
            # Invert: lower raw value = higher score
            result.append((ONE - (val - min_val) / value_range) * HUNDRED)

    return result


def compute_data_completeness(
    metric_values: dict[str, dict[str, Optional[Decimal]]],
    total_possible: int = 0,
) -> Decimal:
    """
    Calculate the percentage of available data points across all metrics and horizons.

    Args:
        metric_values: Nested dict of {metric_name: {horizon: value_or_None}}.
        total_possible: The actual number of scorable data points from METRIC_CONFIG.
                        If 0, falls back to counting all keys in metric_values.

    Returns:
        Percentage (0.0 - 100.0) of non-None data points.
    """
    non_none_count = 0

    for _metric_name, horizons in metric_values.items():
        for _horizon, value in horizons.items():
            if value is not None:
                non_none_count += 1

    # Derive denominator dynamically if not provided
    if total_possible <= 0:
        total_possible = sum(
            len(horizons) for horizons in metric_values.values()
        )

    if total_possible == 0:
        return ZERO

    return (Decimal(non_none_count) / Decimal(total_possible) * HUNDRED).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
