"""
services/morningstar_fetcher.py

Async HTTP client for fetching data from the Morningstar v2 API.

Uses the access-code-based URL pattern (no OAuth needed):
    https://api.morningstar.com/v2/service/mf/{ApiName}/{IdType}/{Id}?accesscode={code}

Each method fetches one API endpoint, parses the XML response, and
returns a flat dict of field names to string values. The caller
(ingestion_service) handles type conversion and DB mapping.
"""

from __future__ import annotations
import asyncio

import httpx
import structlog

from app.core.dependencies import get_settings
from app.services.morningstar_parser import parse_xml_response

logger = structlog.get_logger(__name__)

API_BASE = "https://api.morningstar.com/v2/service/mf"

# Short code -> full API path name
API_PATHS: dict[str, str] = {
    "DP": "DailyPerformance",
    "TTR": "TrailingTotalReturn",
    "RM": "RiskMeasure",
    "RMP": "RelativeRiskMeasureProspectus",
    "TTRR": "TrailingTotalReturnRank",
    "CYR": "CalendarYearReturn",
    "GSSB": "GlobalStockSectorBreakdown",
}

# Timeout and retry configuration
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0  # seconds — exponential backoff


class MorningstarFetchError(Exception):
    """Raised when a Morningstar API call fails after retries."""


class MorningstarFetcher:
    """
    Async client that fetches and parses Morningstar XML data.

    Usage:
        async with MorningstarFetcher() as fetcher:
            data = await fetcher.fetch_daily_performance("F00000XXXX")
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._access_code = settings.morningstar_access_code
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "MorningstarFetcher":
        self._client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        """Return the active client, creating one if needed."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT,
                follow_redirects=True,
            )
        return self._client

    async def fetch_api(
        self, api_name: str, id_type: str, identifier: str
    ) -> dict[str, str]:
        """
        Fetch a single API endpoint and return parsed XML as a flat dict.

        Args:
            api_name: Short code (e.g. "DP") or full path (e.g. "DailyPerformance")
            id_type: "mstarid" or "isin"
            identifier: The fund identifier value

        Returns:
            Flat dict of {FieldName: string_value} from the XML response.

        Raises:
            MorningstarFetchError: After MAX_RETRIES failures.
        """
        # Resolve short code to full path
        api_path = API_PATHS.get(api_name, api_name)
        url = f"{API_BASE}/{api_path}/{id_type}/{identifier}"
        client = self._get_client()

        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await client.get(
                    url, params={"accesscode": self._access_code}
                )
                if resp.status_code == 200:
                    parsed = parse_xml_response(resp.text)
                    logger.debug(
                        "morningstar_fetch_ok",
                        api=api_name,
                        identifier=identifier,
                        fields=len(parsed),
                    )
                    return parsed

                # Non-200 but not a transient error — log and retry anyway
                logger.warning(
                    "morningstar_fetch_http_error",
                    api=api_name,
                    identifier=identifier,
                    status=resp.status_code,
                    attempt=attempt,
                )
                last_error = MorningstarFetchError(
                    f"HTTP {resp.status_code} for {api_name}/{identifier}"
                )

            except httpx.TimeoutException as exc:
                logger.warning(
                    "morningstar_fetch_timeout",
                    api=api_name,
                    identifier=identifier,
                    attempt=attempt,
                )
                last_error = exc
            except httpx.HTTPError as exc:
                logger.warning(
                    "morningstar_fetch_error",
                    api=api_name,
                    identifier=identifier,
                    attempt=attempt,
                    error=str(exc),
                )
                last_error = exc

            # Exponential backoff before retry
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF_BASE**attempt)

        raise MorningstarFetchError(
            f"Failed after {MAX_RETRIES} attempts for {api_name}/{identifier}: {last_error}"
        )

    # -- Convenience methods for each API endpoint --

    async def fetch_daily_performance(self, mstar_id: str) -> dict[str, str]:
        """Fetch DailyPerformance (NAV, returns, category returns)."""
        return await self.fetch_api("DP", "mstarid", mstar_id)

    async def fetch_trailing_returns(self, mstar_id: str) -> dict[str, str]:
        """Fetch TrailingTotalReturn (month-end trailing returns)."""
        return await self.fetch_api("TTR", "mstarid", mstar_id)

    async def fetch_risk_measures(self, mstar_id: str) -> dict[str, str]:
        """Fetch RiskMeasure (Sharpe, StdDev, Sortino, MaxDrawdown)."""
        return await self.fetch_api("RM", "mstarid", mstar_id)

    async def fetch_relative_risk_measures(self, mstar_id: str) -> dict[str, str]:
        """Fetch RelativeRiskMeasureProspectus (Alpha, Beta, Treynor, etc.)."""
        return await self.fetch_api("RMP", "mstarid", mstar_id)

    async def fetch_return_ranks(self, mstar_id: str) -> dict[str, str]:
        """Fetch TrailingTotalReturnRank (quartile and absolute ranks)."""
        return await self.fetch_api("TTRR", "mstarid", mstar_id)

    async def fetch_calendar_year_returns(self, mstar_id: str) -> dict[str, str]:
        """Fetch CalendarYearReturn (Year1 through Year10)."""
        return await self.fetch_api("CYR", "mstarid", mstar_id)

    async def fetch_sector_breakdown(self, mstar_id: str) -> dict[str, str]:
        """Fetch GlobalStockSectorBreakdown (sector allocation percentages)."""
        return await self.fetch_api("GSSB", "mstarid", mstar_id)

    async def fetch_all_for_fund(self, mstar_id: str) -> dict[str, dict[str, str]]:
        """
        Fetch all API endpoints for a single fund concurrently.

        Returns a dict keyed by API short code, each containing the parsed XML data.
        If any individual API fails, its entry will contain an empty dict
        and the error is logged (does not stop the others).
        """
        api_methods = {
            "DP": self.fetch_daily_performance,
            "TTR": self.fetch_trailing_returns,
            "RM": self.fetch_risk_measures,
            "RMP": self.fetch_relative_risk_measures,
            "TTRR": self.fetch_return_ranks,
            "CYR": self.fetch_calendar_year_returns,
            "GSSB": self.fetch_sector_breakdown,
        }

        # Fire all API calls concurrently
        tasks = {
            code: asyncio.create_task(method(mstar_id))
            for code, method in api_methods.items()
        }

        results: dict[str, dict[str, str]] = {}
        for code, task in tasks.items():
            try:
                results[code] = await task
            except (MorningstarFetchError, Exception) as exc:
                logger.error(
                    "morningstar_fetch_all_partial_failure",
                    api=code,
                    mstar_id=mstar_id,
                    error=str(exc),
                )
                results[code] = {}

        return results

    async def close(self) -> None:
        """Explicitly close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
