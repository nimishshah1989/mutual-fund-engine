"""
services/nifty_benchmark.py

Hardcoded NIFTY 50 sector weights mapped to Morningstar's 11-sector taxonomy.

Source: NSE India index factsheet, March 2026.
NSE industry classifications are mapped to Morningstar Global Equity
Classification Structure (GECS) sectors.

This serves as a fallback when the Morningstar GSSB API returns empty data
for the benchmark index (F00000VBPN).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.benchmark_repo import BenchmarkRepository

logger = structlog.get_logger(__name__)

# NSE → Morningstar 11-sector mapping (March 2026 NIFTY 50 weights)
# Derivation:
#   Financial Services = Banks (21.05) + Financial Services (6.30) + Insurance (1.73)
#   Consumer Cyclical  = Automobiles (7.52) + Consumer Goods (3.60) + Retail (1.83)
#   Energy             = Petroleum Products (9.74) + Oil & Gas (1.78) + Energy (1.38)
#   Technology         = Information Technology (11.02)
#   Industrials        = Construction (5.53) + Aerospace (1.75) + Transport (1.75) + Aviation (0.88)
#   Consumer Defensive = FMCG (4.64) + Food Products (1.23)
#   Communication Svcs = Telecom (5.44)
#   Basic Materials    = Metals & Mining (5.13)
#   Healthcare         = Healthcare (3.30) + Healthcare Services (1.08)
#   Utilities          = Power (3.31)
#   Real Estate        = 0.00 (none in NIFTY 50)
NIFTY50_SECTOR_WEIGHTS: dict[str, Decimal] = {
    "Financial Services": Decimal("29.08"),
    "Consumer Cyclical": Decimal("12.95"),
    "Energy": Decimal("12.90"),
    "Technology": Decimal("11.02"),
    "Industrials": Decimal("9.91"),
    "Consumer Defensive": Decimal("5.87"),
    "Communication Services": Decimal("5.44"),
    "Basic Materials": Decimal("5.13"),
    "Healthcare": Decimal("4.38"),
    "Utilities": Decimal("3.31"),
    "Real Estate": Decimal("0.00"),
}


async def seed_nifty50_weights(
    session: AsyncSession,
    benchmark_name: str = "NIFTY 50",
    benchmark_mstar_id: str = "F00000VBPN",
) -> dict[str, Any]:
    """
    Seed the benchmark_sector_weights table with hardcoded NIFTY 50 data.

    This is a fallback for when Morningstar GSSB returns empty.
    Weights are based on NSE March 2026 index composition.

    Returns:
        Summary dict with sector count, total weight, rows upserted.
    """
    today = date.today()
    now = datetime.now(timezone.utc)
    repo = BenchmarkRepository(session)

    records: list[dict[str, Any]] = []
    for sector_name, weight_pct in NIFTY50_SECTOR_WEIGHTS.items():
        records.append({
            "benchmark_name": benchmark_name,
            "benchmark_mstar_id": benchmark_mstar_id,
            "sector_name": sector_name,
            "weight_pct": weight_pct,
            "effective_date": today,
            "source": "nse_nifty50_manual",
            "fetched_at": now,
        })

    rows_affected = await repo.upsert_weights(records)
    total_weight = sum(r["weight_pct"] for r in records)

    logger.info(
        "nifty50_seed_complete",
        benchmark=benchmark_name,
        sectors=len(records),
        total_weight=total_weight.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        rows_upserted=rows_affected,
    )

    return {
        "status": "completed",
        "benchmark_name": benchmark_name,
        "benchmark_mstar_id": benchmark_mstar_id,
        "sector_count": len(records),
        "total_weight_pct": total_weight.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "rows_upserted": rows_affected,
        "source": "nse_nifty50_manual",
        "fetched_at": now.isoformat(),
    }
