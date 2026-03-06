"""
services/pulse_data_service.py

Orchestration service for the MF Pulse pipeline:
  1. Load NAV data + Nifty prices from DB
  2. Compute ratio returns via pulse_calculator
  3. Persist snapshots to mf_pulse_snapshot
  4. Serve enriched query results (joined with QFS/FSAS/recommendation)

Also provides get_nifty_returns() for QFS excess return computation.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.fund_master import FundMaster
from app.models.db.fund_qfs import FundQFS
from app.models.db.fund_recommendation import FundRecommendation
from app.models.db.mf_pulse_snapshot import MFPulseSnapshot
from app.models.schemas.pulse import (
    PulseCategoryResponse,
    PulseCategorySummary,
    PulseCoverageStats,
    PulseDataResponse,
    PulseFundItem,
)
from app.repositories.benchmark_history_repo import BenchmarkHistoryRepository
from app.repositories.nav_history_repo import NavHistoryRepository
from app.repositories.pulse_snapshot_repo import PulseSnapshotRepository
from app.services.pulse_calculator import (
    DATE_TOLERANCE_DAYS,
    PULSE_PERIODS,
    compute_snapshot_for_fund,
    get_lookback_date,
)

logger = structlog.get_logger(__name__)


class PulseDataService:
    """Orchestrates the full MF Pulse pipeline and serves enriched queries."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.nav_repo = NavHistoryRepository(session)
        self.benchmark_repo = BenchmarkHistoryRepository(session)
        self.snapshot_repo = PulseSnapshotRepository(session)

    async def _load_signal_thresholds(self) -> tuple[float, float]:
        """Load signal thresholds from engine_config, with defaults."""
        from app.models.db.engine_config import EngineConfig

        result = await self.session.execute(
            select(EngineConfig.config_value)
            .where(EngineConfig.config_key == "pulse_signal_thresholds")
        )
        row = result.scalar_one_or_none()
        if row and isinstance(row, dict):
            return (
                float(row.get("strong_ow", 1.05)),
                float(row.get("strong_uw", 0.95)),
            )
        return (1.05, 0.95)

    async def compute_all_snapshots(self) -> dict[str, Any]:
        """
        For all eligible funds × 6 periods, compute ratio returns and
        bulk upsert into mf_pulse_snapshot.

        Expected: ~535 funds × 6 periods = ~3,210 rows.
        """
        strong_ow, strong_uw = await self._load_signal_thresholds()
        snapshot_date = date.today()

        # Get all eligible funds
        fund_result = await self.session.execute(
            select(FundMaster.mstar_id)
            .where(
                FundMaster.is_eligible.is_(True),
                FundMaster.deleted_at.is_(None),
            )
        )
        fund_ids = [row.mstar_id for row in fund_result.all()]

        if not fund_ids:
            logger.warning("pulse_no_eligible_funds")
            return {"status": "no_funds", "snapshots_created": 0}

        logger.info("pulse_compute_start", fund_count=len(fund_ids), periods=list(PULSE_PERIODS.keys()))

        # Pre-load current NAVs for all funds
        current_navs = await self.nav_repo.get_latest_navs_bulk(fund_ids)

        # Get current Nifty price (latest available)
        nifty_current_data = await self.benchmark_repo.get_price_on_or_before(
            "NIFTY_50", snapshot_date, tolerance_days=DATE_TOLERANCE_DAYS,
        )
        if nifty_current_data is None:
            logger.error("pulse_no_nifty_current", snapshot_date=str(snapshot_date))
            return {"status": "error", "error": "No current Nifty 50 price available"}

        nifty_current = nifty_current_data["close_price"]

        all_snapshots: list[dict[str, Any]] = []
        skipped_no_nav = 0

        for period, lookback_days in PULSE_PERIODS.items():
            lookback_date = get_lookback_date(snapshot_date, period)

            # Get historical Nifty price for this period
            nifty_old_data = await self.benchmark_repo.get_price_on_or_before(
                "NIFTY_50", lookback_date, tolerance_days=DATE_TOLERANCE_DAYS,
            )
            nifty_old = nifty_old_data["close_price"] if nifty_old_data else None

            # Get historical NAVs for all funds at lookback date
            old_navs = await self.nav_repo.get_navs_on_or_before_bulk(
                fund_ids, lookback_date, tolerance_days=DATE_TOLERANCE_DAYS,
            )

            for mstar_id in fund_ids:
                nav_curr = current_navs.get(mstar_id, {}).get("nav")
                nav_old_entry = old_navs.get(mstar_id)
                nav_old = nav_old_entry["nav"] if nav_old_entry else None

                if nav_curr is None:
                    skipped_no_nav += 1
                    continue

                snapshot = compute_snapshot_for_fund(
                    mstar_id=mstar_id,
                    period=period,
                    snapshot_date=snapshot_date,
                    nav_current=nav_curr,
                    nav_old=nav_old,
                    nifty_current=nifty_current,
                    nifty_old=nifty_old,
                    strong_ow=strong_ow,
                    strong_uw=strong_uw,
                )
                all_snapshots.append(snapshot)

        # Bulk upsert all snapshots
        rows = await self.snapshot_repo.bulk_upsert(all_snapshots)
        await self.session.commit()

        # Count by signal
        signal_counts: dict[str, int] = {}
        for s in all_snapshots:
            sig = s.get("signal") or "NONE"
            signal_counts[sig] = signal_counts.get(sig, 0) + 1

        logger.info(
            "pulse_compute_complete",
            total_snapshots=len(all_snapshots),
            rows_upserted=rows,
            skipped_no_nav=skipped_no_nav,
            signal_distribution=signal_counts,
        )

        return {
            "status": "completed",
            "snapshot_date": str(snapshot_date),
            "total_snapshots": len(all_snapshots),
            "rows_upserted": rows,
            "skipped_no_nav": skipped_no_nav,
            "signal_distribution": signal_counts,
        }

    async def get_pulse_data(
        self,
        period: str = "1m",
        category_name: Optional[str] = None,
        signal: Optional[str] = None,
        sort_by: str = "ratio_return",
        sort_desc: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> PulseDataResponse:
        """
        Get enriched pulse data: snapshot joined with fund_master, QFS, and recommendation.
        Returns PulseDataResponse with paginated fund items.
        """
        snapshots, total = await self.snapshot_repo.get_latest_for_period(
            period=period,
            category_name=category_name,
            signal=signal,
            sort_by=sort_by,
            sort_desc=sort_desc,
            limit=limit,
            offset=offset,
        )

        if not snapshots:
            return PulseDataResponse(funds=[], period=period, total_funds=total)

        # Enrich with fund master + scores
        mstar_ids = [s.mstar_id for s in snapshots]
        fund_lookup = await self._load_fund_enrichment(mstar_ids)

        snapshot_date = snapshots[0].snapshot_date if snapshots else None

        items: list[PulseFundItem] = []
        for snap in snapshots:
            enrichment = fund_lookup.get(snap.mstar_id, {})
            items.append(PulseFundItem(
                mstar_id=snap.mstar_id,
                fund_name=enrichment.get("fund_name"),
                category_name=enrichment.get("category_name"),
                period=snap.period,
                snapshot_date=snap.snapshot_date,
                ratio_return=_safe_float(snap.ratio_return),
                fund_return=_safe_float(snap.fund_return),
                nifty_return=_safe_float(snap.nifty_return),
                excess_return=_safe_float(snap.excess_return),
                signal=snap.signal,
                qfs=enrichment.get("qfs"),
                fm_score=enrichment.get("fm_score"),
                qfs_quadrant=enrichment.get("qfs_quadrant"),
                fm_quadrant=enrichment.get("fm_quadrant"),
                tier=enrichment.get("tier"),
                action=enrichment.get("action"),
            ))

        return PulseDataResponse(
            funds=items,
            period=period,
            snapshot_date=snapshot_date,
            total_funds=total,
        )

    async def get_category_summary(self, period: str = "1m") -> PulseCategoryResponse:
        """Get signal distribution per SEBI category."""
        raw = await self.snapshot_repo.get_category_summary(period)
        summaries = [PulseCategorySummary(**cat) for cat in raw]
        return PulseCategoryResponse(
            categories=summaries,
            period=period,
            total_categories=len(summaries),
        )

    async def get_coverage_stats(self) -> PulseCoverageStats:
        """Get data coverage stats for NAV and benchmark data."""
        nav_cov = await self.nav_repo.get_data_coverage()
        bench_cov = await self.benchmark_repo.get_data_coverage("NIFTY_50")

        # Latest snapshot date
        from sqlalchemy import func as sa_func
        result = await self.session.execute(
            select(sa_func.max(MFPulseSnapshot.snapshot_date))
        )
        snapshot_date = result.scalar_one_or_none()

        return PulseCoverageStats(
            nav_fund_count=nav_cov.get("fund_count", 0),
            nav_earliest_date=nav_cov.get("earliest_date"),
            nav_latest_date=nav_cov.get("latest_date"),
            nav_total_rows=nav_cov.get("total_rows", 0),
            benchmark_earliest_date=bench_cov.get("earliest_date"),
            benchmark_latest_date=bench_cov.get("latest_date"),
            benchmark_total_rows=bench_cov.get("total_rows", 0),
            snapshot_date=snapshot_date,
        )

    async def get_nifty_returns(
        self, horizons: list[str] | None = None,
    ) -> dict[str, Optional[float]]:
        """
        Compute Nifty 50 returns for specified horizons (default: 1y, 3y, 5y).
        Returns annualized CAGR for 3y/5y, trailing 12mo % for 1y.
        Used by QFS engine for excess_return metric.
        """
        if horizons is None:
            horizons = ["1y", "3y", "5y"]

        today = date.today()
        nifty_current_data = await self.benchmark_repo.get_price_on_or_before(
            "NIFTY_50", today, tolerance_days=DATE_TOLERANCE_DAYS,
        )
        if nifty_current_data is None:
            logger.warning("nifty_returns_no_current_price")
            return {h: None for h in horizons}

        nifty_current = nifty_current_data["close_price"]
        returns: dict[str, Optional[float]] = {}

        horizon_days = {"1y": 365, "3y": 1095, "5y": 1825, "10y": 3650}

        for horizon in horizons:
            days = horizon_days.get(horizon)
            if days is None:
                returns[horizon] = None
                continue

            lookback = today - timedelta(days=days)
            old_data = await self.benchmark_repo.get_price_on_or_before(
                "NIFTY_50", lookback, tolerance_days=DATE_TOLERANCE_DAYS,
            )

            if old_data is None:
                returns[horizon] = None
                continue

            nifty_old = old_data["close_price"]
            if nifty_old <= 0:
                returns[horizon] = None
                continue

            years = days / 365.0
            if years <= 1:
                # Simple return for 1y
                returns[horizon] = round(((nifty_current / nifty_old) - 1) * 100, 4)
            else:
                # Annualized CAGR for multi-year horizons
                cagr = ((nifty_current / nifty_old) ** (1.0 / years) - 1) * 100
                returns[horizon] = round(cagr, 4)

        return returns

    async def _load_fund_enrichment(
        self, mstar_ids: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Load fund master data + latest QFS + recommendation for enrichment."""
        if not mstar_ids:
            return {}

        # Fund master
        fund_result = await self.session.execute(
            select(FundMaster.mstar_id, FundMaster.fund_name, FundMaster.category_name)
            .where(FundMaster.mstar_id.in_(mstar_ids))
        )
        lookup: dict[str, dict[str, Any]] = {}
        for row in fund_result.all():
            lookup[row.mstar_id] = {
                "fund_name": row.fund_name,
                "category_name": row.category_name,
            }

        # Latest QFS scores
        from sqlalchemy import func as sa_func
        qfs_subq = (
            select(
                FundQFS.mstar_id,
                sa_func.max(FundQFS.computed_date).label("max_date"),
            )
            .where(FundQFS.mstar_id.in_(mstar_ids))
            .group_by(FundQFS.mstar_id)
            .subquery()
        )
        qfs_result = await self.session.execute(
            select(FundQFS.mstar_id, FundQFS.qfs)
            .join(
                qfs_subq,
                (FundQFS.mstar_id == qfs_subq.c.mstar_id)
                & (FundQFS.computed_date == qfs_subq.c.max_date),
            )
        )
        for row in qfs_result.all():
            if row.mstar_id in lookup:
                lookup[row.mstar_id]["qfs"] = float(row.qfs) if row.qfs is not None else None

        # Latest recommendations (tier, action, matrix position, fm_score)
        rec_subq = (
            select(
                FundRecommendation.mstar_id,
                sa_func.max(FundRecommendation.computed_date).label("max_date"),
            )
            .where(FundRecommendation.mstar_id.in_(mstar_ids))
            .group_by(FundRecommendation.mstar_id)
            .subquery()
        )
        rec_result = await self.session.execute(
            select(
                FundRecommendation.mstar_id,
                FundRecommendation.tier,
                FundRecommendation.action,
                FundRecommendation.fm_score,
                FundRecommendation.matrix_row,
                FundRecommendation.matrix_col,
            )
            .join(
                rec_subq,
                (FundRecommendation.mstar_id == rec_subq.c.mstar_id)
                & (FundRecommendation.computed_date == rec_subq.c.max_date),
            )
        )
        for row in rec_result.all():
            if row.mstar_id in lookup:
                lookup[row.mstar_id].update({
                    "tier": row.tier,
                    "action": row.action,
                    "fm_score": float(row.fm_score) if row.fm_score is not None else None,
                    "qfs_quadrant": row.matrix_row,
                    "fm_quadrant": row.matrix_col,
                })

        return lookup


def _safe_float(val: Any) -> Optional[float]:
    """Convert Decimal/numeric to float, None-safe."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    return float(val)
