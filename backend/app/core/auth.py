"""
core/auth.py

API key authentication dependency for FastAPI endpoints.
Uses a simple header-based API key until full JWT user auth is implemented.

Protected endpoints require the X-API-Key header to match the configured key.
Read-only endpoints can optionally skip auth (controlled per-route).
"""

from __future__ import annotations

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader

from app.core.config import Settings
from app.core.dependencies import get_settings
from app.core.exceptions import AuthenticationError

# Header name for API key — standard convention
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    api_key: str | None = Security(API_KEY_HEADER),
    settings: Settings = Depends(get_settings),
) -> str:
    """
    FastAPI dependency that validates the X-API-Key header.

    Raises AuthenticationError if:
      - No API key is provided
      - The key does not match the configured API_KEY

    Returns the validated API key string on success.
    """
    configured_key = settings.api_key

    if not configured_key:
        # No API key configured — auth is disabled (dev mode only)
        return "dev-mode-no-key"

    if not api_key:
        raise AuthenticationError(
            message="Missing X-API-Key header",
            error_code="MISSING_API_KEY",
        )

    if api_key != configured_key:
        raise AuthenticationError(
            message="Invalid API key",
            error_code="INVALID_API_KEY",
        )

    return api_key
