"""
core/exceptions.py

Custom exception hierarchy for the JIP MF Recommendation Engine.
Each exception carries an HTTP status_code and a machine-readable error_code
so that API error handlers can return consistent, typed error responses.

Usage:
    raise NotFoundError(
        message="Fund not found",
        error_code="FUND_NOT_FOUND",
        details={"mstar_id": "F00000XXXX"}
    )
"""

from __future__ import annotations
from typing import Any


class AppException(Exception):
    """
    Base exception for all application-level errors.
    Subclasses set status_code and default error_code.
    """

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        if error_code is not None:
            self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    """Resource not found (HTTP 404)."""

    status_code: int = 404
    error_code: str = "NOT_FOUND"

    def __init__(
        self,
        message: str = "Resource not found",
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, details=details)


class ValidationError(AppException):
    """Input validation failed (HTTP 400)."""

    status_code: int = 400
    error_code: str = "VALIDATION_ERROR"

    def __init__(
        self,
        message: str = "Validation failed",
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, details=details)


class AuthenticationError(AppException):
    """Authentication failed — invalid or missing credentials (HTTP 401)."""

    status_code: int = 401
    error_code: str = "AUTHENTICATION_FAILED"

    def __init__(
        self,
        message: str = "Authentication required",
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, details=details)


class AuthorizationError(AppException):
    """Authorization failed — insufficient permissions (HTTP 403)."""

    status_code: int = 403
    error_code: str = "FORBIDDEN"

    def __init__(
        self,
        message: str = "Insufficient permissions",
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, details=details)


class ServiceUnavailableError(AppException):
    """External service or dependency is unavailable (HTTP 503)."""

    status_code: int = 503
    error_code: str = "SERVICE_UNAVAILABLE"

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, details=details)


class DataIngestionError(AppException):
    """Data ingestion or ETL pipeline failure (HTTP 502)."""

    status_code: int = 502
    error_code: str = "DATA_INGESTION_FAILED"

    def __init__(
        self,
        message: str = "Data ingestion failed",
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, error_code=error_code, details=details)
