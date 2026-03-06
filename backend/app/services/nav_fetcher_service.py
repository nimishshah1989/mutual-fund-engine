"""
services/nav_fetcher_service.py

Fetches daily NAV data from AMFI (via mftool) and Nifty 50 prices from yfinance.
Handles both one-time backfill (3yr history) and daily incremental updates.

Data sources:
  - Fund NAVs: mftool.Mftool().get_scheme_historical_nav(amfi_code)
  - Nifty 50:  yfinance download("^NSEI")

Daily efficiency:
  - Backfill: Downloads full history (one-time only)
  - Daily refresh: Downloads recent NAVs only via AMFI API (single bulk request),
    NOT per-fund full history. Uses the AMFI daily NAV file for incremental updates.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from typing import Any, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.fund_master import FundMaster
from app.repositories.benchmark_history_repo import BenchmarkHistoryRepository
from app.repositories.nav_history_repo import NavHistoryRepository

logger = structlog.get_logger(__name__)

# Batch size and delay for mftool to avoid rate limiting
MFTOOL_BATCH_SIZE: int = 30
MFTOOL_BATCH_DELAY_SECONDS: float = 0.5

# Timeout for individual mftool/yfinance HTTP calls (seconds)
FETCH_TIMEOUT_SECONDS: float = 30.0


class NavFetcherService:
    """Fetches and persists NAV data from AMFI and benchmark prices from yfinance."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.nav_repo = NavHistoryRepository(session)
        self.benchmark_repo = BenchmarkHistoryRepository(session)

    @staticmethod
    def _parse_yfinance_df(
        df: Any, benchmark: str, ticker: str,
    ) -> list[dict[str, Any]]:
        """
        Parse a yfinance DataFrame into benchmark history records.
        Handles both yfinance v0.x (flat columns) and v1.x (MultiIndex columns).
        """
        import pandas as pd

        records: list[dict[str, Any]] = []

        # yfinance >= 1.0 returns MultiIndex columns: (Price, Ticker)
        if isinstance(df.columns, pd.MultiIndex):
            close_series = df[("Close", ticker)]
        else:
            close_series = df["Close"]

        for idx_val in close_series.index:
            price_date = idx_val.date() if hasattr(idx_val, "date") else idx_val
            close_price = close_series[idx_val]
            if close_price is not None and not pd.isna(close_price):
                records.append({
                    "benchmark_name": benchmark,
                    "price_date": price_date,
                    "close_price": round(float(close_price), 4),
                    "source": "yfinance",
                })

        return records

    async def _get_eligible_funds_with_amfi(self) -> list[dict[str, str]]:
        """Get all eligible funds that have an amfi_code."""
        result = await self.session.execute(
            select(FundMaster.mstar_id, FundMaster.amfi_code, FundMaster.fund_name)
            .where(
                FundMaster.is_eligible.is_(True),
                FundMaster.deleted_at.is_(None),
                FundMaster.amfi_code.isnot(None),
            )
        )
        return [
            {"mstar_id": row.mstar_id, "amfi_code": row.amfi_code, "fund_name": row.fund_name}
            for row in result.all()
        ]

    def _parse_mftool_nav_data(
        self, raw_data: dict[str, Any], mstar_id: str,
    ) -> list[dict[str, Any]]:
        """
        Parse mftool historical NAV response into DB-ready records.

        mftool returns: {"data": [{"date": "06-03-2026", "nav": "123.4567"}, ...]}
        """
        records: list[dict[str, Any]] = []
        data_list = raw_data.get("data", [])

        for entry in data_list:
            try:
                nav_str = entry.get("nav", "")
                date_str = entry.get("date", "")

                if not nav_str or not date_str or nav_str == "N/A":
                    continue

                nav_val = float(nav_str)
                # mftool date format: DD-MM-YYYY
                nav_date = datetime.strptime(date_str, "%d-%m-%Y").date()

                records.append({
                    "mstar_id": mstar_id,
                    "nav_date": nav_date,
                    "nav": nav_val,
                    "source": "amfi",
                })
            except (ValueError, TypeError) as exc:
                logger.debug(
                    "nav_parse_skip", mstar_id=mstar_id, entry=str(entry), error=str(exc),
                )
                continue

        return records

    # ------------------------------------------------------------------
    #  Backfill: Full history per fund (one-time use)
    # ------------------------------------------------------------------

    async def _fetch_single_fund_nav_full(
        self, amfi_code: str, mstar_id: str, mf_instance: Any,
        fund_name: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch full historical NAV for one fund from mftool (HTTP only, no DB).
        Uses a shared Mftool instance to avoid redundant scheme-code downloads.
        Returns parsed records ready for DB upsert.
        """
        try:
            loop = asyncio.get_running_loop()
            raw_data = await asyncio.wait_for(
                loop.run_in_executor(
                    None, mf_instance.get_scheme_historical_nav, amfi_code,
                ),
                timeout=FETCH_TIMEOUT_SECONDS,
            )

            if not raw_data or "data" not in raw_data:
                logger.warning(
                    "nav_fetch_empty", amfi_code=amfi_code, mstar_id=mstar_id,
                    fund_name=fund_name,
                )
                return []

            return self._parse_mftool_nav_data(raw_data, mstar_id)

        except asyncio.TimeoutError:
            logger.error(
                "nav_fetch_timeout", amfi_code=amfi_code, mstar_id=mstar_id,
                fund_name=fund_name, timeout_s=FETCH_TIMEOUT_SECONDS,
            )
            return []
        except Exception as exc:
            logger.error(
                "nav_fetch_failed", amfi_code=amfi_code, mstar_id=mstar_id,
                fund_name=fund_name, error=str(exc),
            )
            return []

    async def backfill_all_fund_navs(self, years: int = 3) -> dict[str, Any]:
        """
        One-time backfill: fetch full historical NAV for all eligible funds with amfi_code.
        Fetches HTTP data concurrently in batches of 30, then upserts to DB sequentially.
        Uses a single Mftool instance to avoid 535 redundant scheme-code HTTP calls.
        Expected: ~535 funds × ~756 trading days = ~404K rows.
        """
        from mftool import Mftool

        funds = await self._get_eligible_funds_with_amfi()
        logger.info("nav_backfill_start", fund_count=len(funds), years=years)

        # Single Mftool instance shared across all fund fetches
        mf = Mftool()

        total_rows = 0
        success_count = 0
        fail_count = 0

        for batch_start in range(0, len(funds), MFTOOL_BATCH_SIZE):
            batch = funds[batch_start : batch_start + MFTOOL_BATCH_SIZE]
            batch_num = (batch_start // MFTOOL_BATCH_SIZE) + 1
            total_batches = (len(funds) + MFTOOL_BATCH_SIZE - 1) // MFTOOL_BATCH_SIZE

            logger.info(
                "nav_backfill_batch", batch=batch_num, total_batches=total_batches,
                funds_in_batch=len(batch),
            )

            # Step 1: Fetch NAV data concurrently (HTTP only, no DB)
            fetch_tasks = [
                self._fetch_single_fund_nav_full(
                    amfi_code=fund["amfi_code"],
                    mstar_id=fund["mstar_id"],
                    mf_instance=mf,
                    fund_name=fund.get("fund_name"),
                )
                for fund in batch
            ]
            fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

            # Step 2: Upsert to DB sequentially (avoids concurrent session error)
            for fund, result in zip(batch, fetch_results):
                if isinstance(result, Exception):
                    logger.error(
                        "nav_backfill_fund_error",
                        mstar_id=fund["mstar_id"], error=str(result),
                    )
                    fail_count += 1
                elif result and len(result) > 0:
                    try:
                        rows = await self.nav_repo.bulk_upsert(result)
                        total_rows += rows
                        success_count += 1
                    except Exception as exc:
                        logger.error(
                            "nav_upsert_failed",
                            mstar_id=fund["mstar_id"], error=str(exc),
                        )
                        fail_count += 1
                else:
                    fail_count += 1

            # Commit after each batch
            await self.session.commit()

            # Rate limit delay between batches
            if batch_start + MFTOOL_BATCH_SIZE < len(funds):
                await asyncio.sleep(MFTOOL_BATCH_DELAY_SECONDS)

        logger.info(
            "nav_backfill_complete",
            total_funds=len(funds), success=success_count, failed=fail_count,
            total_rows=total_rows,
        )

        return {
            "status": "completed",
            "total_funds": len(funds),
            "success_count": success_count,
            "fail_count": fail_count,
            "total_rows_upserted": total_rows,
        }

    # ------------------------------------------------------------------
    #  Daily refresh: Efficient bulk NAV from AMFI daily file
    # ------------------------------------------------------------------

    async def _fetch_latest_navs_from_amfi(self) -> dict[str, dict[str, Any]]:
        """
        Fetch the latest NAV for ALL mutual fund schemes in a single HTTP request
        from the AMFI NAV file (https://www.amfiindia.com/spages/NAVAll.txt).

        This is the efficient daily path — ONE request instead of 535 per-fund calls.

        Returns: {amfi_code: {"nav": float, "nav_date": date}} for all schemes
        """
        import httpx

        url = "https://www.amfiindia.com/spages/NAVAll.txt"
        logger.info("amfi_bulk_nav_fetch_start", url=url)

        try:
            loop = asyncio.get_running_loop()

            def _download() -> str:
                with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                    resp = client.get(url)
                    resp.raise_for_status()
                    return resp.text

            raw_text = await asyncio.wait_for(
                loop.run_in_executor(None, _download),
                timeout=90.0,
            )
        except Exception as exc:
            logger.error("amfi_bulk_nav_fetch_failed", error=str(exc))
            return {}

        # Parse the AMFI NAV file
        # Format: Scheme Code;ISIN Div Payout/ISIN Growth;ISIN Div Reinvestment;
        #         Scheme Name;Net Asset Value;Date
        nav_lookup: dict[str, dict[str, Any]] = {}
        for line in raw_text.split("\n"):
            parts = line.strip().split(";")
            if len(parts) < 6:
                continue
            scheme_code = parts[0].strip()
            nav_str = parts[4].strip()
            date_str = parts[5].strip()

            if not scheme_code.isdigit() or not nav_str or nav_str == "N/A":
                continue

            try:
                nav_val = float(nav_str)
                nav_date = datetime.strptime(date_str, "%d-%b-%Y").date()
                nav_lookup[scheme_code] = {"nav": nav_val, "nav_date": nav_date}
            except (ValueError, TypeError):
                continue

        logger.info("amfi_bulk_nav_fetch_complete", schemes_parsed=len(nav_lookup))
        return nav_lookup

    async def refresh_fund_navs(self, days: int = 5) -> dict[str, Any]:
        """
        Daily incremental: fetch latest NAVs for all funds via a single AMFI bulk file.

        This is EFFICIENT — one HTTP request (~2MB) gives us the latest NAV for every
        mutual fund scheme in India. We then match by amfi_code and upsert only the
        new data points. NO per-fund API calls needed.

        Contrast with backfill which uses per-fund mftool calls (full history).
        """
        funds = await self._get_eligible_funds_with_amfi()
        logger.info("nav_refresh_start", fund_count=len(funds), days=days)

        # Step 1: Single bulk download of all latest NAVs
        nav_lookup = await self._fetch_latest_navs_from_amfi()

        if not nav_lookup:
            logger.error("nav_refresh_no_amfi_data")
            return {
                "status": "error",
                "error": "Failed to fetch AMFI NAV file",
                "total_funds": len(funds),
                "success_count": 0,
                "fail_count": len(funds),
                "total_rows_upserted": 0,
            }

        # Step 2: Match fund amfi_codes to NAV data and build upsert records
        records: list[dict[str, Any]] = []
        matched = 0
        unmatched = 0

        for fund in funds:
            amfi_code = fund["amfi_code"]
            nav_data = nav_lookup.get(amfi_code)
            if nav_data:
                records.append({
                    "mstar_id": fund["mstar_id"],
                    "nav_date": nav_data["nav_date"],
                    "nav": nav_data["nav"],
                    "source": "amfi",
                })
                matched += 1
            else:
                logger.debug(
                    "nav_refresh_no_match",
                    mstar_id=fund["mstar_id"], amfi_code=amfi_code,
                )
                unmatched += 1

        # Step 3: Bulk upsert all records at once
        total_rows = 0
        if records:
            total_rows = await self.nav_repo.bulk_upsert(records)
            await self.session.commit()

        logger.info(
            "nav_refresh_complete",
            matched=matched, unmatched=unmatched, total_rows=total_rows,
        )

        return {
            "status": "completed",
            "total_funds": len(funds),
            "success_count": matched,
            "fail_count": unmatched,
            "total_rows_upserted": total_rows,
        }

    # ------------------------------------------------------------------
    #  Benchmark (Nifty 50) data
    # ------------------------------------------------------------------

    async def backfill_benchmark(
        self, benchmark: str = "NIFTY_50", ticker: str = "^NSEI", years: int = 3,
    ) -> dict[str, Any]:
        """
        Fetch benchmark (Nifty 50) historical prices from yfinance.
        Uses the ^NSEI ticker for Nifty 50.
        """
        try:
            import yfinance as yf

            end_date = date.today()
            start_date = end_date - timedelta(days=years * 365 + 30)

            logger.info(
                "benchmark_backfill_start",
                benchmark=benchmark, ticker=ticker,
                start=str(start_date), end=str(end_date),
            )

            loop = asyncio.get_running_loop()

            def _download() -> Any:
                data = yf.download(ticker, start=str(start_date), end=str(end_date), progress=False)
                return data

            df = await asyncio.wait_for(
                loop.run_in_executor(None, _download),
                timeout=FETCH_TIMEOUT_SECONDS,
            )

            if df is None or df.empty:
                logger.warning("benchmark_backfill_empty", benchmark=benchmark, ticker=ticker)
                return {"status": "empty", "total_rows": 0}

            records = self._parse_yfinance_df(df, benchmark, ticker)

            if not records:
                return {"status": "no_valid_records", "total_rows": 0}

            rows = await self.benchmark_repo.bulk_upsert(records)
            await self.session.commit()

            logger.info(
                "benchmark_backfill_complete",
                benchmark=benchmark, total_rows=rows,
                date_range=f"{records[0]['price_date']} to {records[-1]['price_date']}",
            )

            return {
                "status": "completed",
                "benchmark": benchmark,
                "total_rows_upserted": rows,
                "earliest_date": str(records[0]["price_date"]),
                "latest_date": str(records[-1]["price_date"]),
            }

        except asyncio.TimeoutError:
            logger.error("benchmark_backfill_timeout", benchmark=benchmark, ticker=ticker)
            return {"status": "error", "error": "Timeout fetching benchmark data"}
        except Exception as exc:
            logger.error("benchmark_backfill_failed", benchmark=benchmark, error=str(exc))
            return {"status": "error", "error": str(exc)}

    async def refresh_benchmark(
        self, benchmark: str = "NIFTY_50", ticker: str = "^NSEI", days: int = 10,
    ) -> dict[str, Any]:
        """
        Daily incremental: fetch last N days of benchmark prices.
        yfinance supports date-range queries, so this is efficient — only fetches ~10 rows.
        """
        try:
            import yfinance as yf

            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            loop = asyncio.get_running_loop()

            def _download() -> Any:
                return yf.download(ticker, start=str(start_date), end=str(end_date), progress=False)

            df = await asyncio.wait_for(
                loop.run_in_executor(None, _download),
                timeout=FETCH_TIMEOUT_SECONDS,
            )

            if df is None or df.empty:
                logger.warning("benchmark_refresh_empty", benchmark=benchmark, ticker=ticker)
                return {"status": "empty", "total_rows": 0}

            records = self._parse_yfinance_df(df, benchmark, ticker)

            if not records:
                return {"status": "no_valid_records", "total_rows": 0}

            rows = await self.benchmark_repo.bulk_upsert(records)
            await self.session.commit()

            return {"status": "completed", "total_rows_upserted": rows}

        except asyncio.TimeoutError:
            logger.error("benchmark_refresh_timeout", benchmark=benchmark, ticker=ticker)
            return {"status": "error", "error": "Timeout fetching benchmark data"}
        except Exception as exc:
            logger.error("benchmark_refresh_failed", benchmark=benchmark, error=str(exc))
            return {"status": "error", "error": str(exc)}
