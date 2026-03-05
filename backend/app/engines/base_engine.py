"""
engines/base_engine.py

Shared utility functions for all scoring engines (QFS, FSAS, CRS).
Provides min-max normalization and data completeness computation
that every Layer uses for peer-group scoring.
"""

from __future__ import annotations

from typing import Optional


def min_max_normalise(
    values: list[Optional[float]],
    higher_is_better: bool,
) -> list[Optional[float]]:
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

    result: list[Optional[float]] = []
    for val in values:
        if val is None:
            result.append(None)
        elif value_range == 0:
            # All funds have the same value — cannot differentiate, give midpoint
            result.append(50.0)
        elif higher_is_better:
            result.append((val - min_val) / value_range * 100.0)
        else:
            # Invert: lower raw value = higher score
            result.append((1.0 - (val - min_val) / value_range) * 100.0)

    return result


def compute_data_completeness(
    metric_values: dict[str, dict[str, Optional[float]]],
) -> float:
    """
    Calculate the percentage of available data points across all metrics and horizons.

    The QFS engine uses 13 metrics x 4 horizons = 52 possible data points.
    This function counts how many are non-None and returns a percentage.

    Args:
        metric_values: Nested dict of {metric_name: {horizon: value_or_None}}.

    Returns:
        Percentage (0.0 - 100.0) of non-None data points.
    """
    total_possible = 13 * 4  # 52 data points
    non_none_count = 0

    for _metric_name, horizons in metric_values.items():
        for _horizon, value in horizons.items():
            if value is not None:
                non_none_count += 1

    if total_possible == 0:
        return 0.0

    return round((non_none_count / total_possible) * 100.0, 2)
