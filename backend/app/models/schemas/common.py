"""
models/schemas/common.py

Shared Pydantic schemas used across all API endpoints.
Defines the standard API response envelope, pagination metadata,
error detail structure, and domain-specific enums.

Every API endpoint returns an ApiResponse[T] — no raw dicts, no ad-hoc shapes.
"""

import enum
import math
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------

class TierEnum(str, enum.Enum):
    """Fund tier classification based on Composite Recommendation Score."""
    CORE = "CORE"
    QUALITY = "QUALITY"
    WATCH = "WATCH"
    CAUTION = "CAUTION"
    EXIT = "EXIT"


class ActionEnum(str, enum.Enum):
    """Recommended action for a fund position."""
    BUY = "BUY"
    SIP = "SIP"
    HOLD_PLUS = "HOLD_PLUS"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    EXIT = "EXIT"


class SignalEnum(str, enum.Enum):
    """Fund manager sector signal — maps to FM signal table."""
    OVERWEIGHT = "OVERWEIGHT"
    ACCUMULATE = "ACCUMULATE"
    NEUTRAL = "NEUTRAL"
    UNDERWEIGHT = "UNDERWEIGHT"
    AVOID = "AVOID"


class ConfidenceEnum(str, enum.Enum):
    """Confidence level for a recommendation or signal."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ---------------------------------------------------------------------------
# Error Detail
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    """Structured error information returned in API error responses."""
    code: str = Field(..., description="Machine-readable error code, e.g. FUND_NOT_FOUND")
    message: str = Field(..., description="Human-readable error description")
    details: dict[str, Any] | None = Field(
        default=None,
        description="Optional additional context about the error",
    )


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class PaginationMeta(BaseModel):
    """Pagination metadata included in paginated list responses."""
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    limit: int = Field(..., ge=1, le=1000, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of items across all pages")
    total_pages: int = Field(..., ge=0, description="Total number of pages")

    @classmethod
    def create(cls, page: int, limit: int, total: int) -> "PaginationMeta":
        """Factory method that auto-calculates total_pages."""
        return cls(
            page=page,
            limit=limit,
            total=total,
            total_pages=math.ceil(total / limit) if limit > 0 else 0,
        )


# ---------------------------------------------------------------------------
# Standard API Response Envelope
# ---------------------------------------------------------------------------

class ApiResponse(BaseModel, Generic[T]):
    """
    Standard envelope for all API responses.

    Success:  { success: true, data: T, meta: {...}, error: null }
    Failure:  { success: false, data: null, error: { code, message, details } }
    """
    success: bool = Field(..., description="Whether the request succeeded")
    data: T | None = Field(default=None, description="Response payload")
    meta: dict[str, Any] | None = Field(
        default=None,
        description="Optional metadata (pagination, timestamps, etc.)",
    )
    error: ErrorDetail | None = Field(
        default=None,
        description="Error details if success is false",
    )

    @classmethod
    def ok(cls, data: T, meta: dict[str, Any] | None = None) -> "ApiResponse[T]":
        """Convenience factory for a successful response."""
        return cls(success=True, data=data, meta=meta, error=None)

    @classmethod
    def fail(
        cls,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> "ApiResponse[None]":
        """Convenience factory for an error response."""
        return cls(
            success=False,
            data=None,
            meta=None,
            error=ErrorDetail(code=code, message=message, details=details),
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated list response with items and pagination metadata.
    Wraps inside ApiResponse at the route level for consistency.
    """
    success: bool = Field(default=True, description="Whether the request succeeded")
    data: list[T] = Field(default_factory=list, description="List of items for the current page")
    meta: PaginationMeta = Field(..., description="Pagination metadata")
    error: ErrorDetail | None = Field(default=None, description="Error details if success is false")

    @classmethod
    def create(
        cls,
        items: list[T],
        page: int,
        limit: int,
        total: int,
    ) -> "PaginatedResponse[T]":
        """Factory that builds the paginated response with auto-calculated pages."""
        return cls(
            success=True,
            data=items,
            meta=PaginationMeta.create(page=page, limit=limit, total=total),
            error=None,
        )
