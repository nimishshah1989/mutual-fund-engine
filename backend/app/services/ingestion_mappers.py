"""
services/ingestion_mappers.py

Morningstar API response -> DB record mapping functions.

Each function maps fields from a specific Morningstar API response (XML tags)
to the corresponding database columns and calls the repository upsert.

Extracted from ingestion_service.py to keep files under 300 lines.
"""

from __future__ import annotations

import structlog

from app.services.morningstar_parser import safe_date, safe_float, safe_int

logger = structlog.get_logger(__name__)

# Morningstar XML sector tag -> human-readable sector name
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


async def upsert_fund_master(repo, mstar_id: str, dp: dict[str, str]) -> None:
    """Extract fund master data from DailyPerformance response and upsert."""
    fund_name = dp.get("FundName", "")
    if not fund_name:
        logger.warning("ingestion_skip_master_no_name", mstar_id=mstar_id)
        return
    await repo.upsert_from_morningstar({
        "mstar_id": mstar_id,
        "legal_name": fund_name,
        "fund_name": fund_name,
        "isin": dp.get("ISIN"),
        "category_name": dp.get("CategoryName", "Unknown"),
        "pricing_frequency": dp.get("PricingFrequency"),
        "data_source": "morningstar",
    })


async def upsert_performance(
    repo, mstar_id: str, dp: dict[str, str], cyr: dict[str, str],
) -> None:
    """Map DailyPerformance + CalendarYearReturn fields and upsert."""
    nav_date = safe_date(dp.get("DayEndDate"))
    if nav_date is None:
        logger.warning("ingestion_skip_perf_no_date", mstar_id=mstar_id)
        return

    calendar_years: dict[str, float | None] = {}
    for year_num in range(1, 11):
        val = safe_float(cyr.get(f"Year{year_num}"))
        if val is not None:
            calendar_years[f"year_{year_num}"] = val

    await repo.upsert({
        "mstar_id": mstar_id,
        "nav_date": nav_date,
        "nav": safe_float(dp.get("DayEndNAV")),
        "nav_change": safe_float(dp.get("NAVChange")),
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
        "cumulative_return_3y": safe_float(dp.get("CumulativeReturn3Yr")),
        "cumulative_return_5y": safe_float(dp.get("CumulativeReturn5Yr")),
        "cumulative_return_10y": safe_float(dp.get("CumulativeReturn10Yr")),
        "calendar_year_returns": calendar_years if calendar_years else None,
    })


async def upsert_risk_stats(
    repo, mstar_id: str, rm: dict[str, str], rmp: dict[str, str],
) -> None:
    """Map RiskMeasure + RelativeRiskMeasureProspectus fields and upsert."""
    end_date = safe_date(rm.get("EndDate")) or safe_date(rmp.get("EndDate"))
    if end_date is None:
        logger.warning("ingestion_skip_risk_no_date", mstar_id=mstar_id)
        return

    await repo.upsert({
        "mstar_id": mstar_id,
        "month_end_date": end_date,
        # Sharpe, Std Dev, Sortino, Max Drawdown (from RM)
        "sharpe_1y": safe_float(rm.get("SharpeRatio1Yr")),
        "sharpe_3y": safe_float(rm.get("SharpeRatio3Yr")),
        "sharpe_5y": safe_float(rm.get("SharpeRatio5Yr")),
        "std_dev_1y": safe_float(rm.get("StdDev1Yr")),
        "std_dev_3y": safe_float(rm.get("StdDev3Yr")),
        "std_dev_5y": safe_float(rm.get("StdDev5Yr")),
        "sortino_1y": safe_float(rm.get("SortinoRatio1Yr")),
        "sortino_3y": safe_float(rm.get("SortinoRatio3Yr")),
        "sortino_5y": safe_float(rm.get("SortinoRatio5Yr")),
        "max_drawdown_1y": safe_float(rm.get("MaxDrawdown1Yr")),
        "max_drawdown_3y": safe_float(rm.get("MaxDrawdown3Yr")),
        "max_drawdown_5y": safe_float(rm.get("MaxDrawdown5Yr")),
        "skewness_1y": safe_float(rm.get("Skewness1Yr")),
        "skewness_3y": safe_float(rm.get("Skewness3Yr")),
        "kurtosis_1y": safe_float(rm.get("Kurtosis1Yr")),
        "kurtosis_3y": safe_float(rm.get("Kurtosis3Yr")),
        # Alpha, Beta (from RMP)
        "alpha_3y": safe_float(rmp.get("Alpha3Yr")),
        "alpha_5y": safe_float(rmp.get("Alpha5Yr")),
        "alpha_10y": safe_float(rmp.get("Alpha10Yr")),
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
        # Capture ratios (from RMP)
        "capture_up_1y": safe_float(rmp.get("CaptureRatioUpside1Yr")),
        "capture_up_3y": safe_float(rmp.get("CaptureRatioUpside3Yr")),
        "capture_up_5y": safe_float(rmp.get("CaptureRatioUpside5Yr")),
        "capture_up_10y": safe_float(rmp.get("CaptureRatioUpside10Yr")),
        "capture_down_1y": safe_float(rmp.get("CaptureRatioDownside1Yr")),
        "capture_down_3y": safe_float(rmp.get("CaptureRatioDownside3Yr")),
        "capture_down_5y": safe_float(rmp.get("CaptureRatioDownside5Yr")),
        # Correlation, R-Squared (from RMP)
        "correlation_1y": safe_float(rmp.get("Correlation1Yr")),
        "correlation_3y": safe_float(rmp.get("Correlation3Yr")),
        "correlation_5y": safe_float(rmp.get("Correlation5Yr")),
        "r_squared_1y": safe_float(rmp.get("Rsquared1Yr")),
        "r_squared_3y": safe_float(rmp.get("Rsquared3Yr")),
        "r_squared_5y": safe_float(rmp.get("Rsquared5Yr")),
    })


async def upsert_ranks(repo, mstar_id: str, ttrr: dict[str, str]) -> None:
    """Map TrailingTotalReturnRank fields and upsert."""
    month_end = safe_date(ttrr.get("MonthEndDate"))
    if month_end is None:
        logger.warning("ingestion_skip_ranks_no_date", mstar_id=mstar_id)
        return

    await repo.upsert({
        "mstar_id": mstar_id,
        "month_end_date": month_end,
        "rank_1m_quartile": safe_int(ttrr.get("Rank1MthQuartile")),
        "rank_3m_quartile": safe_int(ttrr.get("Rank3MthQuartile")),
        "rank_6m_quartile": safe_int(ttrr.get("Rank6MthQuartile")),
        "rank_1y_quartile": safe_int(ttrr.get("Rank1YrQuartile")),
        "rank_2y_quartile": safe_int(ttrr.get("Rank2YrQuartile")),
        "rank_3y_quartile": safe_int(ttrr.get("Rank3YrQuartile")),
        "rank_5y_quartile": safe_int(ttrr.get("Rank5YrQuartile")),
        "rank_7y_quartile": safe_int(ttrr.get("Rank7YrQuartile")),
        "rank_10y_quartile": safe_int(ttrr.get("Rank10YrQuartile")),
        "abs_rank_1m": safe_int(ttrr.get("AbsRank1Mth")),
        "abs_rank_3m": safe_int(ttrr.get("AbsRank3Mth")),
        "abs_rank_6m": safe_int(ttrr.get("AbsRank6Mth")),
        "abs_rank_1y": safe_int(ttrr.get("AbsRank1Yr")),
        "abs_rank_2y": safe_int(ttrr.get("AbsRank2Yr")),
        "abs_rank_3y": safe_int(ttrr.get("AbsRank3Yr")),
        "abs_rank_5y": safe_int(ttrr.get("AbsRank5Yr")),
        "abs_rank_7y": safe_int(ttrr.get("AbsRank7Yr")),
        "abs_rank_10y": safe_int(ttrr.get("AbsRank10Yr")),
    })


async def upsert_sector_exposure(repo, mstar_id: str, gssb: dict[str, str]) -> None:
    """Map GlobalStockSectorBreakdown fields and bulk upsert."""
    portfolio_date = safe_date(gssb.get("PortfolioDate"))
    if portfolio_date is None:
        logger.warning("ingestion_skip_sector_no_date", mstar_id=mstar_id)
        return

    records: list[dict] = []
    for xml_field, sector_name in SECTOR_FIELD_MAP.items():
        pct = safe_float(gssb.get(xml_field))
        if pct is not None:
            records.append({
                "mstar_id": mstar_id, "month_end_date": portfolio_date,
                "sector_name": sector_name, "exposure_pct": pct, "source": "morningstar",
            })
    if records:
        await repo.bulk_upsert(records)
