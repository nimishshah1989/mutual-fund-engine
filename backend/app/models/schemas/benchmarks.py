"""
models/schemas/benchmarks.py

Pydantic schemas for the benchmark sector weights API endpoints.
Read-only display of NIFTY 50 sector allocations used for FMS.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.schemas.common import DecimalFloat


class BenchmarkWeightItem(BaseModel):
    """One sector's weight in the benchmark."""
    sector_name: str = Field(..., description="Morningstar sector name")
    weight_pct: DecimalFloat = Field(..., description="Sector weight as percentage (0-100)")
    effective_date: date = Field(..., description="Date weights are effective from")
    source: str = Field("morningstar_gssb", description="Data source")
    fetched_at: Optional[str] = Field(None, description="ISO timestamp of last fetch")


class BenchmarkWeightsResponse(BaseModel):
    """Full benchmark weights response."""
    benchmark_name: str = Field(..., description="Benchmark name, e.g. 'NIFTY 50'")
    benchmark_mstar_id: Optional[str] = Field(None, description="Morningstar ID used")
    sectors: list[BenchmarkWeightItem] = Field(default_factory=list)
    sector_count: int = Field(0)
    total_weight_pct: DecimalFloat = Field(Decimal("0"), description="Sum of all sector weights")
    last_fetched: Optional[str] = Field(None, description="ISO timestamp of most recent fetch")


class BenchmarkRefreshResponse(BaseModel):
    """Response from a benchmark refresh operation."""
    status: str = Field(..., description="completed / error")
    benchmark_name: Optional[str] = None
    benchmark_mstar_id: Optional[str] = None
    sector_count: int = 0
    total_weight_pct: DecimalFloat = Decimal("0")
    rows_upserted: int = 0
    fetched_at: Optional[str] = None
    reason: Optional[str] = None
    source: Optional[str] = Field(None, description="Data source: morningstar_gssb or nse_nifty50_manual")


class MatrixCellSummary(BaseModel):
    """Summary for one cell in the 3x3 decision matrix."""
    matrix_position: str = Field(..., description="e.g. HIGH_HIGH, MID_LOW")
    matrix_row: str = Field(..., description="QFS band: HIGH / MID / LOW")
    matrix_col: str = Field(..., description="FMS band: HIGH / MID / LOW")
    tier: str = Field(..., description="Tier for this cell")
    action: str = Field(..., description="Action for this cell")
    fund_count: int = Field(0, description="Number of funds in this cell")
    avg_qfs: DecimalFloat = Field(Decimal("0"), description="Average QFS of funds in cell")
    avg_fms: DecimalFloat = Field(Decimal("0"), description="Average FMS of funds in cell")


class MatrixSummaryResponse(BaseModel):
    """Full 3x3 matrix summary — used to render the decision matrix UI."""
    cells: list[MatrixCellSummary] = Field(default_factory=list)
    total_funds: int = Field(0, description="Total funds across all cells")
    computed_date: Optional[str] = None
