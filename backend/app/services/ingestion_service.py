"""
services/ingestion_service.py

Orchestrates Morningstar data ingestion: fetches all API endpoints for
each fund, maps response fields to ORM columns, and upserts into the
database. Tracks progress via IngestionLog entries.

One fund's failure never stops the batch — errors are captured and
reported in the final summary.
"""

from __future__ import annotations
from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.fund_master_repo import FundMasterRepository
from app.repositories.fund_performance_repo import FundPerformanceRepository
from app.repositories.fund_ranks_repo import FundRanksRepository
from app.repositories.fund_risk_stats_repo import FundRiskStatsRepository
from app.repositories.fund_sector_exposure_repo import FundSectorExposureRepository
from app.repositories.ingestion_log_repo import IngestionLogRepository
from app.services.morningstar_fetcher import MorningstarFetcher
from app.services.morningstar_parser import safe_date, safe_float, safe_int

logger = structlog.get_logger(__name__)

# -- Field mapping: Morningstar XML tag -> DB column --

# Sector names in the XML mapped to human-readable names for the DB
SECTOR_FIELD_MAP: dict[str, str] = {
    "BasicMaterials": "Basic Materials",
    "ConsumerCyclical": "Consumer Cyclical",
    "FinancialServices": "Financial Services",
    "RealEstate": "Real Estate",
    "ConsumerDefensive": "Consumer Defensive",
    "Healthcare": "Healthcare",
    "Utilities": "Utilities",
    "CommunicationServices": "Communication Services",
    "Energy": "Energy",
    "Industrials": "Industrials",
    "Technology": "Technology",
}


class IngestionService:
    """
    Coordinates fetching from Morningstar APIs and upserting into all
    fund data tables (performance, risk, ranks, sectors).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.master_repo = FundMasterRepository(session)
        self.perf_repo = FundPerformanceRepository(session)
        self.risk_repo = FundRiskStatsRepository(session)
        self.ranks_repo = FundRanksRepository(session)
        self.sector_repo = FundSectorExposureRepository(session)
        self.log_repo = IngestionLogRepository(session)
        self.fetcher = MorningstarFetcher()

    async def ingest_fund(self, mstar_id: str) -> dict:
        """
        Fetch all Morningstar data for a single fund, parse, and upsert
        into all relevant tables.

        Returns:
            Dict with keys: mstar_id, status, tables_updated, error
        """
        result = {
            "mstar_id": mstar_id,
            "status": "success",
            "tables_updated": [],
            "error": None,
        }

        try:
            api_data = await self.fetcher.fetch_all_for_fund(mstar_id)

            # -- 0. Fund Master (extracted from DailyPerformance metadata) --
            dp_data = api_data.get("DP", {})
            if dp_data:
                await self._upsert_fund_master(mstar_id, dp_data)
                result["tables_updated"].append("fund_master")

            # -- 1. Fund Performance (from DailyPerformance + CalendarYearReturn) --
            cyr_data = api_data.get("CYR", {})
            if dp_data:
                await self._upsert_performance(mstar_id, dp_data, cyr_data)
                result["tables_updated"].append("fund_performance")

            # -- 2. Risk Stats (from RiskMeasure + RelativeRiskMeasureProspectus) --
            rm_data = api_data.get("RM", {})
            rmp_data = api_data.get("RMP", {})
            if rm_data or rmp_data:
                await self._upsert_risk_stats(mstar_id, rm_data, rmp_data)
                result["tables_updated"].append("fund_risk_stats")

            # -- 3. Ranks (from TrailingTotalReturnRank) --
            ttrr_data = api_data.get("TTRR", {})
            if ttrr_data:
                await self._upsert_ranks(mstar_id, ttrr_data)
                result["tables_updated"].append("fund_ranks")

            # -- 4. Sector Exposure (from GlobalStockSectorBreakdown) --
            gssb_data = api_data.get("GSSB", {})
            if gssb_data:
                await self._upsert_sector_exposure(mstar_id, gssb_data)
                result["tables_updated"].append("fund_sector_exposure")

            logger.info(
                "ingestion_fund_complete",
                mstar_id=mstar_id,
                tables=result["tables_updated"],
            )

        except Exception as exc:
            result["status"] = "failed"
            result["error"] = str(exc)
            logger.error(
                "ingestion_fund_failed",
                mstar_id=mstar_id,
                error=str(exc),
            )

        return result

    async def ingest_all_funds(self, mstar_ids: list[str]) -> dict:
        """
        Run ingestion for a batch of funds sequentially.
        Creates an IngestionLog entry tracking the overall run.

        Returns:
            Summary dict: {total, succeeded, failed, errors, log_id}
        """
        started_at = datetime.now(timezone.utc)

        # Create log entry for tracking
        log = await self.log_repo.create_log({
            "feed_name": "MORNINGSTAR_API",
            "file_name": None,
            "records_total": len(mstar_ids),
            "records_inserted": 0,
            "records_updated": 0,
            "records_failed": 0,
            "status": "RUNNING",
            "started_at": started_at,
        })
        log_id = log.id

        succeeded = 0
        failed = 0
        errors: list[dict[str, str]] = []

        async with self.fetcher:
            for index, mstar_id in enumerate(mstar_ids, 1):
                logger.info(
                    "ingestion_progress",
                    current=index,
                    total=len(mstar_ids),
                    mstar_id=mstar_id,
                )
                fund_result = await self.ingest_fund(mstar_id)

                if fund_result["status"] == "success":
                    succeeded += 1
                else:
                    failed += 1
                    errors.append({
                        "mstar_id": mstar_id,
                        "error": fund_result["error"] or "Unknown error",
                    })

        # Determine overall status
        if failed == 0:
            status = "SUCCESS"
        elif succeeded == 0:
            status = "FAILED"
        else:
            status = "PARTIAL"

        # Update the log entry with results
        completed_at = datetime.now(timezone.utc)
        await self.log_repo.update_log(log_id, {
            "records_inserted": succeeded,
            "records_updated": succeeded,  # upserts count as updates
            "records_failed": failed,
            "errors": {"fund_errors": errors} if errors else None,
            "status": status,
            "completed_at": completed_at,
        })

        summary = {
            "total": len(mstar_ids),
            "succeeded": succeeded,
            "failed": failed,
            "errors": errors,
            "log_id": str(log_id),
            "duration_seconds": (completed_at - started_at).total_seconds(),
        }

        logger.info("ingestion_batch_complete", **summary)
        return summary

    # -- Private mapping/upsert methods --

    async def _upsert_fund_master(
        self,
        mstar_id: str,
        dp: dict[str, str],
    ) -> None:
        """Extract fund master data from DailyPerformance response and upsert."""
        fund_name = dp.get("FundName", "")
        if not fund_name:
            logger.warning("ingestion_skip_master_no_name", mstar_id=mstar_id)
            return

        record = {
            "mstar_id": mstar_id,
            "legal_name": fund_name,  # Best available from DP
            "fund_name": fund_name,
            "isin": dp.get("ISIN"),
            "category_name": dp.get("CategoryName", "Unknown"),
            "pricing_frequency": dp.get("PricingFrequency"),
            "data_source": "morningstar",
        }

        await self.master_repo.upsert_from_morningstar(record)

    async def _upsert_performance(
        self,
        mstar_id: str,
        dp: dict[str, str],
        cyr: dict[str, str],
    ) -> None:
        """Map DailyPerformance + CalendarYearReturn fields and upsert."""
        nav_date = safe_date(dp.get("DayEndDate"))
        if nav_date is None:
            logger.warning("ingestion_skip_perf_no_date", mstar_id=mstar_id)
            return

        # Build calendar year returns JSON from CYR data
        calendar_years: dict[str, float | None] = {}
        for year_num in range(1, 11):
            val = safe_float(cyr.get(f"Year{year_num}"))
            if val is not None:
                calendar_years[f"year_{year_num}"] = val
        calendar_year_json = calendar_years if calendar_years else None

        record = {
            "mstar_id": mstar_id,
            "nav_date": nav_date,
            "nav": safe_float(dp.get("DayEndNAV")),
            "nav_change": safe_float(dp.get("NAVChange")),
            # Standard period returns
            "return_1d": safe_float(dp.get("Return1Day")),
            "return_1w": safe_float(dp.get("Return1Week")),
            "return_1m": safe_float(dp.get("Return1Mth")),
            "return_3m": safe_float(dp.get("Return3Mth")),
            "return_6m": safe_float(dp.get("Return6Mth")),
            "return_ytd": safe_float(dp.get("ReturnYTD")),
            "return_1y": safe_float(dp.get("Return1Yr")),
            "return_2y": safe_float(dp.get("Return2Yr")),
            "return_3y": safe_float(dp.get("Return3Yr")),
            "return_5y": safe_float(dp.get("Return5Yr")),
            "return_7y": safe_float(dp.get("Return7Yr")),
            "return_10y": safe_float(dp.get("Return10Yr")),
            "return_since_inception": safe_float(dp.get("ReturnSinceInception")),
            # Cumulative returns
            "cumulative_return_3y": safe_float(dp.get("CumulativeReturn3Yr")),
            "cumulative_return_5y": safe_float(dp.get("CumulativeReturn5Yr")),
            "cumulative_return_10y": safe_float(dp.get("CumulativeReturn10Yr")),
            # Calendar year returns
            "calendar_year_returns": calendar_year_json,
        }

        await self.perf_repo.upsert(record)

    async def _upsert_risk_stats(
        self,
        mstar_id: str,
        rm: dict[str, str],
        rmp: dict[str, str],
    ) -> None:
        """Map RiskMeasure + RelativeRiskMeasureProspectus fields and upsert."""
        # Prefer the RM EndDate; fall back to RMP EndDate
        end_date = safe_date(rm.get("EndDate")) or safe_date(rmp.get("EndDate"))
        if end_date is None:
            logger.warning("ingestion_skip_risk_no_date", mstar_id=mstar_id)
            return

        record = {
            "mstar_id": mstar_id,
            "month_end_date": end_date,
            # Sharpe (from RM)
            "sharpe_1y": safe_float(rm.get("SharpeRatio1Yr")),
            "sharpe_3y": safe_float(rm.get("SharpeRatio3Yr")),
            "sharpe_5y": safe_float(rm.get("SharpeRatio5Yr")),
            # Std Dev (from RM)
            "std_dev_1y": safe_float(rm.get("StdDev1Yr")),
            "std_dev_3y": safe_float(rm.get("StdDev3Yr")),
            "std_dev_5y": safe_float(rm.get("StdDev5Yr")),
            # Sortino (from RM)
            "sortino_1y": safe_float(rm.get("SortinoRatio1Yr")),
            "sortino_3y": safe_float(rm.get("SortinoRatio3Yr")),
            "sortino_5y": safe_float(rm.get("SortinoRatio5Yr")),
            # Max Drawdown (from RM)
            "max_drawdown_1y": safe_float(rm.get("MaxDrawdown1Yr")),
            "max_drawdown_3y": safe_float(rm.get("MaxDrawdown3Yr")),
            "max_drawdown_5y": safe_float(rm.get("MaxDrawdown5Yr")),
            # Skewness & Kurtosis (from RM)
            "skewness_1y": safe_float(rm.get("Skewness1Yr")),
            "skewness_3y": safe_float(rm.get("Skewness3Yr")),
            "kurtosis_1y": safe_float(rm.get("Kurtosis1Yr")),
            "kurtosis_3y": safe_float(rm.get("Kurtosis3Yr")),
            # Alpha (from RMP) — API provides 1y/3y/5y/10y, DB stores 3y/5y/10y
            "alpha_3y": safe_float(rmp.get("Alpha3Yr")),
            "alpha_5y": safe_float(rmp.get("Alpha5Yr")),
            "alpha_10y": safe_float(rmp.get("Alpha10Yr")),
            # Beta (from RMP)
            "beta_3y": safe_float(rmp.get("Beta3Yr")),
            "beta_5y": safe_float(rmp.get("Beta5Yr")),
            "beta_10y": safe_float(rmp.get("Beta10Yr")),
            # Treynor (from RMP)
            "treynor_1y": safe_float(rmp.get("TreynorRatio1Yr")),
            "treynor_3y": safe_float(rmp.get("TreynorRatio3Yr")),
            "treynor_5y": safe_float(rmp.get("TreynorRatio5Yr")),
            "treynor_10y": safe_float(rmp.get("TreynorRatio10Yr")),
            # Tracking Error (from RMP)
            "tracking_error_1y": safe_float(rmp.get("TrackingError1Yr")),
            "tracking_error_3y": safe_float(rmp.get("TrackingError3Yr")),
            "tracking_error_5y": safe_float(rmp.get("TrackingError5Yr")),
            "tracking_error_10y": safe_float(rmp.get("TrackingError10Yr")),
            # Information Ratio (from RMP)
            "info_ratio_1y": safe_float(rmp.get("InformationRatio1Yr")),
            "info_ratio_3y": safe_float(rmp.get("InformationRatio3Yr")),
            "info_ratio_5y": safe_float(rmp.get("InformationRatio5Yr")),
            "info_ratio_10y": safe_float(rmp.get("InformationRatio10Yr")),
            # Upside Capture (from RMP)
            "capture_up_1y": safe_float(rmp.get("CaptureRatioUpside1Yr")),
            "capture_up_3y": safe_float(rmp.get("CaptureRatioUpside3Yr")),
            "capture_up_5y": safe_float(rmp.get("CaptureRatioUpside5Yr")),
            "capture_up_10y": safe_float(rmp.get("CaptureRatioUpside10Yr")),
            # Downside Capture (from RMP)
            "capture_down_1y": safe_float(rmp.get("CaptureRatioDownside1Yr")),
            "capture_down_3y": safe_float(rmp.get("CaptureRatioDownside3Yr")),
            "capture_down_5y": safe_float(rmp.get("CaptureRatioDownside5Yr")),
            # Correlation (from RMP)
            "correlation_1y": safe_float(rmp.get("Correlation1Yr")),
            "correlation_3y": safe_float(rmp.get("Correlation3Yr")),
            "correlation_5y": safe_float(rmp.get("Correlation5Yr")),
            # R-Squared (from RMP)
            "r_squared_1y": safe_float(rmp.get("Rsquared1Yr")),
            "r_squared_3y": safe_float(rmp.get("Rsquared3Yr")),
            "r_squared_5y": safe_float(rmp.get("Rsquared5Yr")),
        }

        await self.risk_repo.upsert(record)

    async def _upsert_ranks(
        self,
        mstar_id: str,
        ttrr: dict[str, str],
    ) -> None:
        """Map TrailingTotalReturnRank fields and upsert."""
        month_end = safe_date(ttrr.get("MonthEndDate"))
        if month_end is None:
            logger.warning("ingestion_skip_ranks_no_date", mstar_id=mstar_id)
            return

        record = {
            "mstar_id": mstar_id,
            "month_end_date": month_end,
            # Quartile ranks
            "rank_1m_quartile": safe_int(ttrr.get("Rank1MthQuartile")),
            "rank_3m_quartile": safe_int(ttrr.get("Rank3MthQuartile")),
            "rank_6m_quartile": safe_int(ttrr.get("Rank6MthQuartile")),
            "rank_1y_quartile": safe_int(ttrr.get("Rank1YrQuartile")),
            "rank_2y_quartile": safe_int(ttrr.get("Rank2YrQuartile")),
            "rank_3y_quartile": safe_int(ttrr.get("Rank3YrQuartile")),
            "rank_5y_quartile": safe_int(ttrr.get("Rank5YrQuartile")),
            "rank_7y_quartile": safe_int(ttrr.get("Rank7YrQuartile")),
            "rank_10y_quartile": safe_int(ttrr.get("Rank10YrQuartile")),
            # Absolute ranks
            "abs_rank_1m": safe_int(ttrr.get("AbsRank1Mth")),
            "abs_rank_3m": safe_int(ttrr.get("AbsRank3Mth")),
            "abs_rank_6m": safe_int(ttrr.get("AbsRank6Mth")),
            "abs_rank_1y": safe_int(ttrr.get("AbsRank1Yr")),
            "abs_rank_2y": safe_int(ttrr.get("AbsRank2Yr")),
            "abs_rank_3y": safe_int(ttrr.get("AbsRank3Yr")),
            "abs_rank_5y": safe_int(ttrr.get("AbsRank5Yr")),
            "abs_rank_7y": safe_int(ttrr.get("AbsRank7Yr")),
            "abs_rank_10y": safe_int(ttrr.get("AbsRank10Yr")),
        }

        await self.ranks_repo.upsert(record)

    async def _upsert_sector_exposure(
        self,
        mstar_id: str,
        gssb: dict[str, str],
    ) -> None:
        """Map GlobalStockSectorBreakdown fields and bulk upsert."""
        # Use PortfolioDate from the response; fall back to today
        portfolio_date = safe_date(gssb.get("PortfolioDate"))
        if portfolio_date is None:
            logger.warning("ingestion_skip_sector_no_date", mstar_id=mstar_id)
            return

        records: list[dict] = []
        for xml_field, sector_name in SECTOR_FIELD_MAP.items():
            pct = safe_float(gssb.get(xml_field))
            if pct is not None:
                records.append({
                    "mstar_id": mstar_id,
                    "month_end_date": portfolio_date,
                    "sector_name": sector_name,
                    "exposure_pct": pct,
                    "source": "morningstar",
                })

        if records:
            await self.sector_repo.bulk_upsert(records)
