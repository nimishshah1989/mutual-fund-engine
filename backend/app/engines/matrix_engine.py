"""
engines/matrix_engine.py

3x3 Decision Matrix Engine for the JIP Recommendation Engine.

Two independent axes — QFS percentile and FMS percentile — each divided
into terciles (LOW / MID / HIGH). Their intersection determines the
recommended action and tier.

Matrix Layout (QFS on Y-axis, FMS on X-axis):
                         FM Alignment Score Percentile
                    LOW (<33)      MID (33-66)     HIGH (>66)
              +---------------+---------------+---------------+
  HIGH (>66)  |     HOLD      |  ACCUMULATE   |  ACCUMULATE   |
              |    WATCH      |   QUALITY     |   CORE (STAR) |
              +---------------+---------------+---------------+
  MID (33-66) |    REDUCE     |     HOLD      |  ACCUMULATE   |
              |   CAUTION     |    WATCH      |   QUALITY     |
              +---------------+---------------+---------------+
  LOW (<33)   |     EXIT      |    REDUCE     |     HOLD      |
              |    EXIT       |   CAUTION     |    WATCH      |
              +---------------+---------------+---------------+

The engine is a pure computation module — no DB I/O.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# Each cell: (action, tier)
MATRIX_CELLS: dict[str, tuple[str, str]] = {
    "HIGH_HIGH": ("ACCUMULATE", "CORE"),
    "HIGH_MID": ("ACCUMULATE", "QUALITY"),
    "HIGH_LOW": ("HOLD", "WATCH"),
    "MID_HIGH": ("ACCUMULATE", "QUALITY"),
    "MID_MID": ("HOLD", "WATCH"),
    "MID_LOW": ("REDUCE", "CAUTION"),
    "LOW_HIGH": ("HOLD", "WATCH"),
    "LOW_MID": ("REDUCE", "CAUTION"),
    "LOW_LOW": ("EXIT", "EXIT"),
}

# Default tercile boundaries (configurable via engine_config)
DEFAULT_LOW_UPPER = Decimal("33.33")
DEFAULT_HIGH_LOWER = Decimal("66.67")


class MatrixEngine:
    """Classifies funds into a 3x3 decision matrix based on QFS and FMS percentiles."""

    def __init__(
        self,
        low_upper: Decimal = DEFAULT_LOW_UPPER,
        high_lower: Decimal = DEFAULT_HIGH_LOWER,
    ) -> None:
        """
        Args:
            low_upper: Percentile threshold — below this is LOW band.
            high_lower: Percentile threshold — above this is HIGH band.
        """
        self.low_upper = low_upper
        self.high_lower = high_lower

    def _get_band(self, percentile: Decimal) -> str:
        """Map a percentile (0-100) to a tercile band."""
        if percentile < self.low_upper:
            return "LOW"
        if percentile >= self.high_lower:
            return "HIGH"
        return "MID"

    def classify(
        self,
        qfs_percentile: Decimal,
        fms_percentile: Decimal,
    ) -> dict[str, Any]:
        """
        Classify a fund into the 3x3 matrix.

        Args:
            qfs_percentile: QFS percentile rank within category (0-100).
            fms_percentile: FMS percentile rank within category (0-100).

        Returns:
            Dict with: row, col, position, action, tier.
        """
        row = self._get_band(qfs_percentile)
        col = self._get_band(fms_percentile)
        position = f"{row}_{col}"

        action, tier = MATRIX_CELLS[position]

        return {
            "matrix_row": row,
            "matrix_col": col,
            "matrix_position": position,
            "action": action,
            "tier": tier,
        }

    def classify_batch(
        self,
        fund_percentiles: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Classify a batch of funds. Each entry must have:
            mstar_id, qfs_percentile, fms_percentile.

        Returns list with matrix classification added to each fund dict.
        """
        results: list[dict[str, Any]] = []
        for fund in fund_percentiles:
            classification = self.classify(
                qfs_percentile=fund["qfs_percentile"],
                fms_percentile=fund["fms_percentile"],
            )
            results.append({**fund, **classification})
        return results

    @staticmethod
    def get_all_positions() -> list[str]:
        """Return all 9 valid matrix positions."""
        return list(MATRIX_CELLS.keys())

    @staticmethod
    def get_cell_metadata(position: str) -> dict[str, str]:
        """Get action and tier for a specific matrix position."""
        if position not in MATRIX_CELLS:
            return {"action": "HOLD", "tier": "WATCH"}
        action, tier = MATRIX_CELLS[position]
        return {"action": action, "tier": tier}
