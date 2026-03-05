"""
services/morningstar_client.py

Authenticated HTTP client for Morningstar API Center.
Handles the OAuth2/Auth0 SSO flow programmatically and provides
session-based access to all Morningstar data APIs.

API URL pattern:
    https://api.morningstar.com/v2/service/mf/{ApiName}/{IdType}/{Id}?accesscode={code}

Key API IDs for the engine:
    OMF  - Operations MasterFile (fund master data)
    TTR  - Trailing Total Returns (performance)
    RM   - Risk Measures (Sharpe, StdDev, Sortino, etc.)
    RMP  - Relative Risk Measures: Prospectus Primary Index (Alpha, Beta, etc.)
    RMC  - Relative Risk Measures: Category Index
    TTRR - Trailing Total Return Ranks (quartile/absolute ranks)
    CYR  - Calendar Year Returns
    CYRR - Calendar Year Return Ranks
    DP   - Daily Performance (NAV)
    FH   - Full Holdings (portfolio holdings)
    GSSB - Global Stock Sector Breakdown
    PBR  - Portfolio Breakdowns Raw
"""

from __future__ import annotations
import base64
import json
import re
from html import unescape
from typing import Any
from urllib.parse import urljoin

import httpx
import structlog

from app.core.dependencies import get_settings

logger = structlog.get_logger(__name__)

# Morningstar API Center endpoints
APICENTER_BASE = "https://apicenter.morningstar.com"
SSO_URL = "https://uim-session-manager-awsprod.morningstar.com/sso/json/msusers/app-login"
AUTH0_DOMAIN = "https://login-prod.morningstar.com"
API_BASE = "https://api.morningstar.com/v2/service/mf"


class MorningstarAuthError(Exception):
    """Raised when Morningstar authentication fails."""


class MorningstarAPIError(Exception):
    """Raised when a Morningstar API call fails."""


class MorningstarClient:
    """
    Authenticated client for Morningstar API Center.

    Usage:
        client = MorningstarClient()
        await client.authenticate()
        data = await client.get_api_data("TTR", "SecId", "F000015GTQ")
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._username = settings.morningstar_username
        self._password = settings.morningstar_password
        self._access_code = settings.morningstar_access_code
        self._csrf_token: str = ""
        self._nonce: str = ""
        self._authenticated = False
        self._sync_client: httpx.Client | None = None

    def _get_sync_client(self) -> httpx.Client:
        """Lazy-init a synchronous httpx client (auth flow requires sync redirects)."""
        if self._sync_client is None or self._sync_client.is_closed:
            self._sync_client = httpx.Client(
                timeout=30.0,
                follow_redirects=False,
            )
        return self._sync_client

    def authenticate(self) -> None:
        """
        Perform the full OAuth2/Auth0 SSO authentication flow.
        After success, the client has session cookies for API Center access.
        """
        client = self._get_sync_client()

        try:
            # Step 1: Start SSO flow → get Auth0 authorize URL
            resp = client.get(SSO_URL, params={
                "prompt": "login",
                "source": "bus0009",
                "targetUrl": APICENTER_BASE,
            })
            if resp.status_code != 302:
                raise MorningstarAuthError(f"SSO init failed: {resp.status_code}")

            # Step 2: Follow to Auth0 authorize
            resp = client.get(resp.headers["location"])
            if resp.status_code != 302:
                raise MorningstarAuthError(f"Auth0 authorize failed: {resp.status_code}")

            # Step 3: Get Auth0 login page with config
            login_url = AUTH0_DOMAIN + resp.headers["location"]
            resp = client.get(login_url)
            if resp.status_code != 200:
                raise MorningstarAuthError(f"Auth0 login page failed: {resp.status_code}")

            # Extract Auth0 config from base64-encoded JSON
            b64_match = re.search(r"window\.atob\('([^']+)'\)", resp.text)
            if not b64_match:
                raise MorningstarAuthError("Could not find Auth0 config in login page")

            config = json.loads(
                base64.b64decode(b64_match.group(1)).decode("utf-8")
            )
            internal = config.get("internalOptions", {})
            csrf = internal.get("_csrf", "")
            state = internal.get("state", "")
            client_id = config.get("clientID", "")
            callback_url = config.get("callbackURL", "")

            # Step 4: Submit credentials via Auth0 usernamepassword/login
            resp = client.post(
                f"{AUTH0_DOMAIN}/usernamepassword/login",
                data={
                    "state": state,
                    "_csrf": csrf,
                    "username": self._username,
                    "password": self._password,
                    "connection": "Username-Password-Authentication",
                    "client_id": client_id,
                    "redirect_uri": callback_url,
                    "response_type": "code",
                    "scope": "openid profile offline_access email",
                    "tenant": "uim-prod",
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": AUTH0_DOMAIN,
                },
            )
            if resp.status_code != 200:
                raise MorningstarAuthError(
                    f"Auth0 login failed: {resp.status_code}"
                )

            # Step 5: Extract and submit the callback form
            action_match = re.search(r'action="([^"]+)"', resp.text)
            if not action_match:
                raise MorningstarAuthError("No callback form in auth response")

            form_data: dict[str, str] = {}
            for field in ["wa", "wresult", "wctx"]:
                match = re.search(
                    rf'name="{field}"\s+value="([^"]*)"', resp.text
                )
                if match:
                    form_data[field] = unescape(match.group(1))

            resp = client.post(action_match.group(1), data=form_data)

            # Step 6: Follow redirect chain back to API Center
            while resp.status_code in (301, 302, 303, 307):
                loc = resp.headers.get("location", "")
                if not loc:
                    break
                if not loc.startswith("http"):
                    loc = urljoin(str(resp.url), loc)
                resp = client.get(loc)

            # Step 7: Get CSRF token and nonce from authenticated page
            page_resp = client.get(
                f"{APICENTER_BASE}/default", follow_redirects=True
            )
            csrf_match = re.search(
                r'var csrfToken = "([^"]+)"', page_resp.text
            )
            nonce_match = re.search(
                r'id="sessionNonce">([^<]+)<', page_resp.text
            )

            if not csrf_match or not nonce_match:
                raise MorningstarAuthError(
                    "Could not extract CSRF/nonce after login"
                )

            self._csrf_token = csrf_match.group(1)
            self._nonce = nonce_match.group(1)
            self._authenticated = True

            logger.info(
                "morningstar_auth_success",
                username=self._username,
            )

        except MorningstarAuthError:
            raise
        except Exception as exc:
            raise MorningstarAuthError(
                f"Authentication failed: {exc}"
            ) from exc

    def _ensure_authenticated(self) -> None:
        if not self._authenticated:
            self.authenticate()

    def get_api_list(self, inv_type_id: str = "1") -> list[dict[str, Any]]:
        """Get list of available APIs for an investment type (1=Open End MF)."""
        self._ensure_authenticated()
        client = self._get_sync_client()
        resp = client.get(
            f"{APICENTER_BASE}/api/getAllApiByInvTypeId",
            params={"invTypeId": inv_type_id},
            headers={"X-Requested-With": "XMLHttpRequest"},
            follow_redirects=True,
        )
        data = resp.json()
        return data.get("data", [])

    def get_api_details(self, api_id: str) -> dict[str, Any]:
        """Get details and URL template for a specific API."""
        self._ensure_authenticated()
        client = self._get_sync_client()
        resp = client.get(
            f"{APICENTER_BASE}/api/getApiDetails",
            params={"apiId": api_id},
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRF-TOKEN": self._csrf_token,
            },
            follow_redirects=True,
        )
        data = resp.json()
        return data.get("data", {})

    def get_data_via_api_url(
        self,
        api_name: str,
        id_type: str,
        identifier: str,
    ) -> dict[str, Any]:
        """
        Fetch data directly from the Morningstar data API.

        Args:
            api_name: API path segment (e.g. "TrailingTotalReturn")
            id_type: Identifier type (e.g. "SecId", "ISIN")
            identifier: The fund identifier value

        Requires MORNINGSTAR_ACCESS_CODE to be set in environment.
        """
        if not self._access_code:
            raise MorningstarAPIError(
                "MORNINGSTAR_ACCESS_CODE not configured. "
                "Generate one at https://apicenter.morningstar.com/myaccount"
            )

        url = f"{API_BASE}/{api_name}/{id_type}/{identifier}"
        client = self._get_sync_client()
        resp = client.get(
            url,
            params={"accesscode": self._access_code},
            follow_redirects=True,
        )

        if resp.status_code != 200:
            raise MorningstarAPIError(
                f"API call failed: {resp.status_code} for {api_name}"
            )

        return resp.json()

    def close(self) -> None:
        """Close the HTTP client."""
        if self._sync_client and not self._sync_client.is_closed:
            self._sync_client.close()

    def __del__(self) -> None:
        self.close()


# API ID to URL path mapping (discovered from API Center)
API_URL_PATHS: dict[str, str] = {
    "OMF": "OperationsMasterFile",
    "TTR": "TrailingTotalReturn",
    "RM": "RiskMeasure",
    "RMP": "RelativeRiskMeasureProspectus",
    "RMC": "RelativeRiskMeasureCategory",
    "TTRR": "TrailingTotalReturnRank",
    "CYR": "CalendarYearReturn",
    "CYRR": "CalendarYearReturnRank",
    "DP": "DailyPerformance",
    "FH": "FullHoldings",
    "GSSB": "GlobalStockSectorBreakdown",
    "PBR": "PortfolioBreakdownsRaw",
    "CTR": "CategoryTotalReturn",
    "CRM": "CategoryRiskMeasures",
}
